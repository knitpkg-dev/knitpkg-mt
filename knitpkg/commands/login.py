# knitpkg/commands/login.py

"""
KnitPkg for MetaTrader login command — authenticate with the registry via OAuth.

This module handles OAuth authentication with supported providers (GitHub, GitLab,
MQL5 Forge, Bitbucket) and securely stores access tokens using keyring for
subsequent API operations like publishing packages.
"""

import typer
import webbrowser
import http.server
import socketserver
import urllib.parse
import httpx
import keyring  # For secure credential storage
from typing import Optional
from rich.console import Console
import os
import sys
import asyncio

from knitpkg.core.auth import register_device_with_registry, CREDENTIALS_SERVICE, SUPPORTED_PROVIDERS
from knitpkg.core.global_config import get_registry_url

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handles the OAuth callback from the browser.

    This custom handler captures the authorization code from the redirect URL
    and stores it for the main login process.
    """
    def do_GET(self):
        """
        Processes GET requests, specifically looking for the OAuth callback.
        """
        # Extract the path and check if it matches the expected one based on the provider
        expected_path = f"/auth/{self.server.provider}/callback"
        if self.path.startswith(expected_path):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            code = params.get("code", [None])[0]
            if code:
                self.server.code = code  # Store the code in the server
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

def register(app):
    """Register the login command with the Typer app."""

    @app.command()
    def login(
        provider: str = typer.Option(None, "--provider", help="Provider: github, gitlab, mql5forge, or bitbucket"),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """
        Authenticate with the registry via OAuth and securely store the access token.

        This command opens a browser for OAuth login with the specified provider
        and stores the resulting access token securely using the system keyring.
        The token enables subsequent operations like publishing packages.
        """
        console = Console(log_path=verbose)

        registry_url = get_registry_url()

        # Descobrir configuração de autenticação do registry
        with console.status("[cyan]Connecting to registry..."):
            response = httpx.get(f"{registry_url}/auth/config", timeout=10.0)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] Failed to connect to registry: {registry_url}")
            raise typer.Exit(1)

        auth_config = response.json()

        # Registry privado: ignorar --provider
        if auth_config["type"] == "private":
            if provider:
                console.print(f"[yellow]⚠ Warning:[/yellow] --provider ignored (private registry uses SSO)")

            provider = auth_config["provider"]
            console.print(f"\n[cyan]→[/cyan] Authenticating with {provider.upper()}...")

        # Registry público: exigir --provider
        else:
            if not provider:
                console.print("[red]✗[/red] Please specify --provider:")
                for p in auth_config["providers"]:
                    console.print(f"   [dim]kp-mt login --provider {p}[/dim]")
                raise typer.Exit(1)

            # Validar provider disponível
            available = [p for p in auth_config["providers"]]
            if provider not in available:
                console.print(f"[red]✗[/red] Unknown provider: {provider}")
                console.print(f"   Available: {', '.join(available)}")
                raise typer.Exit(1)

        # Build authorization URL
        auth_url = f"{registry_url}/auth/{provider}"

        console.log(f"[bold magenta]login[/] → Opening browser for login via [cyan]{provider.capitalize()}[/]...")
        webbrowser.open(auth_url)

        # Start local server to capture the callback
        class Server(socketserver.TCPServer):
            """
            Custom TCP server to hold the authorization code and provider.
            """
            code = None
            provider = None
            allow_reuse_address = True

        Server.provider = provider

        # Redirect stderr to suppress HTTP server logs
        # Store original stderr
        original_stderr = sys.stderr
        # Open a null device for stderr
        null_device = open(os.devnull, 'w')
        sys.stderr = null_device

        try:
            with Server(("localhost", 8789), CallbackHandler) as httpd:
                httpd.handle_request()  # Wait for one request (the callback)
        except Exception as e:
            console.log(f"[red]Error:[/] Failed to start local server or handle callback: {e}")
            raise typer.Exit(code=1)
        finally:
            # Restore original stderr
            sys.stderr = original_stderr
            null_device.close()

        if not httpd.code:
            console.log("[red]Error:[/] Failed to obtain authorization code from callback.")
            raise typer.Exit(code=1)

        # Exchange code for access_token via proxy in registry (no secret stored here)
        async def fetch_token(code: str) -> Optional[dict]:
            """
            Exchanges the authorization code for an access token with the registry.
            """
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{registry_url}/auth/{provider}/exchange-token",
                        params={"code": code}
                    )
                    response.raise_for_status() # Raise an exception for bad status codes
                    return response.json()
                except httpx.HTTPStatusError as e:
                    console.log(f"[red]Error:[/] HTTP error during token exchange: {e.response.status_code} - {e.response.text}")
                    return None
                except httpx.RequestError as e:
                    console.log(f"[red]Error:[/] Network error during token exchange: {e}")
                    return None

        access_token_json = asyncio.run(fetch_token(httpd.code))
        if not access_token_json:
            console.log("[red]Error:[/] Failed to obtain access token from the registry.")
            raise typer.Exit(code=1)

        access_token = access_token_json.get('access_token')
        if not access_token:
            console.log("[red]Error:[/] Access token not found in the registry response.")
            raise typer.Exit(code=1)

        asyncio.run(register_device_with_registry(access_token, console))

        for p in SUPPORTED_PROVIDERS:
            if p == provider:
                continue
            try:
                if keyring.get_password(CREDENTIALS_SERVICE, p): # Check if token exists before trying to delete
                    keyring.delete_password(CREDENTIALS_SERVICE, p)
            except Exception as e:
                if keyring.get_password(CREDENTIALS_SERVICE, p) is not None:
                    console.log(f"[red]Error:[/] Failed to remove token for [cyan]{p.capitalize()}[/]: {e}")
                    raise typer.Exit(code=1)

        # Store the token securely with keyring and delete others
        try:
            keyring.set_password(CREDENTIALS_SERVICE, provider, access_token)
            console.log(f"[bold green]Login successful![/] Token stored for [cyan]{provider}[/cyan].")
        except Exception as e:
            console.log(f"[red]Error:[/] Failed to securely store token with keyring: {e}")
            raise typer.Exit(code=1)

