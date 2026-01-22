import httpx
import webbrowser
import http.server
import socketserver
import urllib.parse
import httpx
import keyring
import os
import sys
from typing import Optional, Tuple

from knitpkg.core.exceptions import (
    ProviderNotFoundError,
    CallbackServerError,
    AuthorizationCodeError,
    TokenExchangeError,
    AccessTokenError,
    InvalidRegistryError,
    TokenStorageError,
    TokenRemovalError,
    TokenNotFoundError,
    RegistryError
)
from knitpkg.core.console import ConsoleAware, Console

CREDENTIALS_SERVICE = "knitpkg-mt"

class _CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handles the OAuth callback from the browser.

    This custom handler captures the authorization code from the redirect URL
    and stores it for the main login process.
    """
    def do_GET(self):
        """
        Processes GET requests, specifically looking for the OAuth callback.
        """
        expected_path = self.server.endpoint_path # type: ignore
        if self.path.startswith(expected_path):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            code = params.get("code", [None])[0]
            if code:
                self.server.code = code  # type: ignore # Store the code in the server
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Login successful! Close this window and return to the KnitPkg CLI.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed to obtain authorization code.")
        else:
            # If the path doesn't match, return 404 or ignore
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Endpoint not found.")

    # Override log_message to suppress default logging
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass

class Registry(ConsoleAware):
    """Handles communication with the remote package registry."""

    """
    Initialize the Registry instance.

    Args:
        base_url (str): The base URL of the registry.
        callback_port (int): The port to use for the local callback server. Defaults to 8789.
        console (Optional[Console]): The console instance to use for output. Defaults to None.
        verbose (bool): Whether to enable verbose output. Defaults to False.
    """
    def __init__(self, base_url: str, console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console, verbose)
        self.base_url = base_url

    def login(self, provider: Optional[str] = None):
        """Perform login using the fetched auth URL."""
        provider, auth_url, local_redirect_uri = self._fetch_registry_config(provider)
        
        # Parse local_redirect_uri to extract port and endpoint path
        parsed_uri = urllib.parse.urlparse(local_redirect_uri)
        callback_host = parsed_uri.hostname or "localhost"
        callback_port = parsed_uri.port or 8789
        endpoint_path = parsed_uri.path
        
        self.print(f"🔐 [cyan]Opening browser for login via [bold]{provider}[/]...")
        webbrowser.open(auth_url)

        # Start local server to capture the callback
        class Server(socketserver.TCPServer):
            """
            Custom TCP server to hold necessary callback handler information.
            """
            code = None
            endpoint_path = None
            allow_reuse_address = True

        Server.endpoint_path = endpoint_path # type: ignore

        # Redirect stderr to suppress HTTP server logs
        # Store original stderr
        original_stderr = sys.stderr
        # Open a null device for stderr
        null_device = open(os.devnull, 'w')
        sys.stderr = null_device

        try:
            with Server((callback_host, callback_port), _CallbackHandler) as callback_server:
                callback_server.handle_request()  # Wait for one request (the callback)
        except Exception as e:
            raise CallbackServerError(str(e))
        finally:
            # Restore original stderr
            sys.stderr = original_stderr
            null_device.close()

        if not callback_server.code:
            raise AuthorizationCodeError()

        access_token_json = self._exchange_code_for_token(provider, callback_server.code)
        if not access_token_json:
            raise TokenExchangeError("No response from token exchange")

        access_token = access_token_json.get('access_token')
        if not access_token:
            raise AccessTokenError()
        
        # Store the token securely with keyring
        try:            
            keyring.set_password(CREDENTIALS_SERVICE, "provider", provider)
            keyring.set_password(CREDENTIALS_SERVICE, "token", access_token)
            self.print(f"✅ [bold green]Login successful![/]")
        except Exception as e:
            raise TokenStorageError(str(e))


    def logout(self) -> None:
        """Remove stored authentication tokens from keyring."""
        provider = keyring.get_password(CREDENTIALS_SERVICE, "provider")
        try:
            keyring.delete_password(CREDENTIALS_SERVICE, "provider")
            keyring.delete_password(CREDENTIALS_SERVICE, "token")
            if provider:
                self.print(f"🚪 [bold green]Successfully logged out[/] from [cyan]{provider}[/].")
            else:
                self.print(f"🚪 [bold green]Successfully logged out[/].")
        except Exception:
            if keyring.get_password(CREDENTIALS_SERVICE, "provider") is not None or \
                keyring.get_password(CREDENTIALS_SERVICE, "token") is not None:
                raise TokenRemovalError()

    def register(self, payload: dict) -> dict:
        """Send register request to registry."""
        provider, token = self._get_credentials()

        try:
            response = httpx.post(
                f"{self.base_url}/project/register",
                json=payload,
                headers={"Authorization": f"Bearer {token}",
                        "X-Provider": provider},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RegistryError(e)

    def resolve_package(self, target: str, org: str, pack_name: str, version_spec: str) -> dict:
        """Resolve package distribution info from registry. This is the only method that does
        NOT require initialization, as it can work with public packages.
        
        Args:
            target: Target platform (e.g., 'mt5')
            org: Organization name
            pack_name: Package name
            version_spec: Version specifier
            
        Returns:
            Dict containing package distribution info
        """
        try:
            provider, token = self._get_credentials()
        except TokenNotFoundError:
            # If no token found, proceed without auth (for public packages)
            provider = None
            token = None

        try:
            response = httpx.get(
                f"{self.base_url}/project/resolve/{target}/{org}/{pack_name}/{version_spec}",
                headers={"Authorization": f"Bearer {token}",
                        "X-Provider": provider} if provider and token else None,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise RegistryError(e)

    def _fetch_registry_config(self, provider: Optional[str] = None) -> Tuple[str, str, str]:
        """Fetch provider configuration from registry."""

        response = httpx.get(f"{self.base_url}/auth/config")
        response.raise_for_status()
        config = response.json()
        
        providers = [p["name"] for p in config.get("providers", [])]
        if not providers:
            raise InvalidRegistryError("No providers available")
        
        for p in config.get("providers", []):
            if provider:
                if p["name"] != provider:
                    continue

            provider = p["name"]
            local_redirect_uri: str = p["local_redirect_uri"]
            auth_url: str = p["auth_url"]
            return provider, auth_url, local_redirect_uri # type: ignore
        
        if provider:
            raise ProviderNotFoundError(provider, providers)
        else:
            raise ProviderNotFoundError(providers[0], providers)

    def _get_credentials(self) -> tuple[str, str]:
        """Get the access token for the current provider."""
        provider = keyring.get_password(CREDENTIALS_SERVICE, "provider")
        if not provider:
            raise TokenNotFoundError()
        
        token = keyring.get_password(CREDENTIALS_SERVICE, "token")
        if not token:
            raise TokenNotFoundError()
        
        return provider, token

    def _exchange_code_for_token(self, provider: str, code: str) -> Optional[dict]:
        """Exchange authorization code for access token with the registry."""
        response = httpx.post(
            f"{self.base_url}/auth/{provider}/exchange-token",
            json={"code": code}
        )
        response.raise_for_status()
        return response.json()
    
