# knitpkg/commands/login.py

"""
KnitPkg for MetaTrader login command — authenticate with the registry via OAuth.

This module handles OAuth authentication with supported providers (GitHub, GitLab,
MQL5 Forge, Bitbucket) and securely stores access tokens using keyring for
subsequent API operations like publishing packages.
"""

import typer
from typing import Optional
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.exceptions import ProviderNotFoundError

def register(app):
    """Register the login command with the Typer app."""

    @app.command()
    def login(
        provider: str = typer.Option(..., "--provider", help="Authentication provider"),
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
        console = Console(log_path=False)

        registry_url = get_registry_url()

        registry: Registry = Registry(registry_url, console=console, verbose=verbose) # type: ignore

        try:
            registry.login(provider)
        except ProviderNotFoundError as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(code=1)
