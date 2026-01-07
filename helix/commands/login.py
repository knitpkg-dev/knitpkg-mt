# helix/commands/login.py

import typer
import webbrowser
import http.server
import socketserver
import urllib.parse
import httpx
import keyring  # Para armazenamento seguro de credenciais
from typing import Optional
import os

# Configurations (pull from .env or config; adjust for production)
REGISTRY_URL = "http://localhost:8000"  # Registry URL
GITHUB_CLIENT_ID = "Iv23liRbPmtpNq5aJNXG"  # Pull from config or env
REDIRECT_URI = "http://localhost:8080/callback"  # Local port for callback
CREDENTIALS_SERVICE = "helix-mt"  # Name for keyring
GITLAB_CLIENT_ID = ""
MQL5FORGE_CLIENT_ID = ""

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        code = params.get("code", [None])[0]
        if code:
            self.server.code = code  # Armazena o code no servidor
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Login successful! Close this window and return to the CLI.")

def register(app):
    """Register the login command with the Typer app."""

    @app.command()
    def login(provider: str = typer.Option("github", "--provider", help="Provider: github or gitlab")):
        """Logs in to the registry via OAuth and stores the token."""

        # Build authorization URL (similar to /auth/{provider} in the registry)
        if provider == "github":
            auth_url = f"{REGISTRY_URL}/auth/github"  # Usa o endpoint do registry para iniciar
        elif provider == "gitlab":
            auth_url = f"{REGISTRY_URL}/auth/gitlab"  # Ajuste se adicionar endpoint no registry
        elif provider == "mql5forge":
            auth_url = f"{REGISTRY_URL}/auth/mql5forge"  # Ajuste se adicionar endpoint no registry
        else:
            typer.echo("Invalid provider. Use 'github', 'gitlab' or 'mql5forge'.")
            raise typer.Exit(code=1)

        typer.echo(f"Opening browser for login via {provider.capitalize()}...")
        webbrowser.open(auth_url)

        # Start local server to capture the callback
        class Server(socketserver.TCPServer):
            code = None
            allow_reuse_address = True

        with Server(("localhost", 8080), CallbackHandler) as httpd:
            httpd.handle_request()  # Wait for one request (the callback)

        if not httpd.code:
            typer.echo("Failed to obtain authorization code.")
            raise typer.Exit(code=1)

        # Exchange code for access_token via proxy in registry (no secret stored here)
        async def fetch_token(code: str) -> Optional[str]:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{REGISTRY_URL}/auth/{provider}/exchange",
                    params={"code": code}
                )
                if response.status_code == 200:
                    return response.json()["access_token"]
            return None

        import asyncio
        access_token = asyncio.run(fetch_token(httpd.code))
        if not access_token:
            typer.echo("Failed to obtain access_token.")
            raise typer.Exit(code=1)

        # Store the token securely with keyring
        keyring.set_password(CREDENTIALS_SERVICE, provider, access_token)
        typer.echo(f"Login successful! Token stored for {provider}.")
