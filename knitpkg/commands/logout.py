# knitpkg/commands/logout.py

"""
KnitPkg for MetaTrader logout command — removes stored authentication tokens.

This module handles the secure removal of access tokens from the system keyring.
It allows users to log out from a specific provider or from all providers,
enhancing security by clearing sensitive credentials.
"""

import typer
import keyring
from typing import Optional
from rich.console import Console

# Import the service name used for keyring from login command
from .login import CREDENTIALS_SERVICE
from .login import SUPPORTED_PROVIDERS

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
        console = Console(log_path=verbose)

        if provider:
            if provider not in SUPPORTED_PROVIDERS:
                console.log(f"[red]Error:[/] Invalid provider '[cyan]{provider}[/b]'. Supported providers are: [yellow]{', '.join(SUPPORTED_PROVIDERS)}[/].")
                raise typer.Exit(code=1)

            try:
                # Attempt to delete the password for the specific provider
                keyring.delete_password(CREDENTIALS_SERVICE, provider)
                console.log(f"[bold green]Successfully logged out[/] from [cyan]{provider.capitalize()}[/]. Token removed.")
            except keyring.errors.NoKeyringError:
                console.log("[red]Error:[/] No keyring backend found. Please ensure a keyring backend is configured on your system.")
                raise typer.Exit(code=1)
            except Exception as e:
                # keyring.delete_password might raise an error if the password doesn't exist
                # or if there's another issue with the keyring backend.
                # We check if the password existed before attempting to delete for a cleaner message.
                if keyring.get_password(CREDENTIALS_SERVICE, provider) is not None:
                    console.log(f"[red]Error:[/] Failed to remove token for [cyan]{provider.capitalize()}[/]: {e}")
                raise typer.Exit(code=1)
        else:
            # No provider specified, log out from all
            console.log("[bold magenta]Logging out[/] from all providers...")
            any_token_removed = False
            for p in SUPPORTED_PROVIDERS:
                try:
                    if keyring.get_password(CREDENTIALS_SERVICE, p): # Check if token exists before trying to delete
                        keyring.delete_password(CREDENTIALS_SERVICE, p)
                        console.log(f"[green]Removed token[/] for [cyan]{p.capitalize()}[/].")
                        any_token_removed = True
                    else:
                        console.log(f"[yellow]No active login found[/] for [cyan]{p.capitalize()}[/].")
                except keyring.errors.NoKeyringError:
                    console.log("[red]Error:[/] No keyring backend found. Please ensure a keyring backend is configured on your system.")
                    raise typer.Exit(code=1)
                except Exception as e:
                    console.log(f"[red]Error:[/] Failed to remove token for [cyan]{p.capitalize()}[/]: {e}")
                    # Don't exit immediately, try to clean up other providers

            if any_token_removed:
                console.log("[bold green]Successfully logged out[/] from all active providers.")
            else:
                console.log("[yellow]No active logins found for any provider.[/] Nothing to remove.")

