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
from knitpkg.core.exceptions import KnitPkgError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def logout_command(console: Console, verbose: bool):
    """Command wrapper for logout command."""
    registry_url = get_registry_url()

    registry: Registry = Registry(registry_url, console=console, verbose=verbose) # type: ignore
    registry.logout()


def register(app):
    """Register the logout command with the main Typer app."""

    @app.command()
    def logout(
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
        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        try:
            console_awr.print("")
            logout_command(console, True if verbose else False)
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠ Logout cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)

        except KnitPkgError as e:
            console_awr.print(f"[bold red]❌ Logout failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
