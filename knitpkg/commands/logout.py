# knitpkg/commands/logout.py

"""
KnitPkg for MetaTrader logout command — removes stored authentication tokens.

This module handles the secure removal of access tokens from the system keyring.
It allows users to log out from a specific provider or from all providers,
enhancing security by clearing sensitive credentials.
"""

import typer
from typing import Optional
from rich.console import Console
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.registry import Registry
from knitpkg.core.exceptions import TokenRemovalError

def register(app):
    """Register the logout command with the main Typer app."""

    @app.command()
    def logout(
        provider: Optional[str] = typer.Option(
            None,
            "--provider",
            "-p",
            help="Specify a provider (e.g., github) to log out from. If not specified, logs out from all providers."
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """
        Logs out from the KnitPkg registry by removing stored access tokens.

        If a provider is specified, only the token for that provider is removed.
        If no provider is specified, all stored tokens for all known providers
        are removed from the system keyring.
        """
        console = Console(log_path=False)

        registry_url = get_registry_url()

        registry: Registry = Registry(registry_url, console=console, verbose=verbose) # type: ignore

        try:
            registry.logout()
        except TokenRemovalError as e:
            console.print(f"[red]Error:[/] {e}")
            raise typer.Exit(code=1)
