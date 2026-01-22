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
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def login_command(provider: str, console: Console, verbose: bool):
    """Command wrapper for login command."""
    registry_url = get_registry_url()

    registry: Registry = Registry(registry_url, console=console, verbose=verbose) # type: ignore
    registry.login(provider)

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
        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        try:
            console_awr.print("")
            login_command(provider, console, True if verbose else False)
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Login cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)

        except RegistryError as e:
            console_awr.print(f"\n[bold red]❌ Registry error:[/bold red] {e}. Reason: {e.reason} ")
            if verbose:
                console_awr.log(f"  Status Code: {e.status_code}")
                console_awr.log(f"  Error type: {e.error_type}")
                console_awr.log(f"  Request URL: {e.request_url}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"\n[bold red]❌ Login failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
