# knitpkg/commands/whoami.py

import typer
from typing import Optional
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def whoami_command(console_awr: ConsoleAware, verbose: bool):
    """Command wrapper for whoami command."""
    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console_awr.console, verbose=verbose)

    user_info = registry.whoami()

    console_awr.print("👤 [bold cyan]User Information[/bold cyan]\n")
    console_awr.print(f"  ID: [cyan]{user_info.get('id')}[/cyan]")
    console_awr.print(f"  Username: [cyan]{user_info.get('username')}[/cyan]")
    console_awr.print(f"  Provider: [cyan]{user_info.get('provider')}[/cyan]")
    console_awr.print(f"  Email: [cyan]{user_info.get('email') or 'Not provided'}[/cyan]")
    subscription_tier: Optional[str] = user_info.get('subscription_tier')
    if subscription_tier is not None:
        subscription_tier = subscription_tier.upper()
    else:
        subscription_tier = 'None'
    console_awr.print(f"  Subscription Tier: [cyan]{subscription_tier}[/cyan]")


def register(app):
    """Register the whoami command with the Typer app."""

    @app.command()
    def whoami(
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Show information about the currently authenticated user."""
        console = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=verbose)
        try:
            console_awr.print("")
            whoami_command(console_awr, verbose)
            from knitpkg.core.telemetry import print_telemetry_warning
            from pathlib import Path
            print_telemetry_warning(Path.cwd())
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Whoami cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Whoami failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
