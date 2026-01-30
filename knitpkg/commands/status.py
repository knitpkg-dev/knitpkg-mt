# knitpkg/commands/status.py

import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def status_command(console_awr: ConsoleAware, verbose: bool):
    """Command wrapper for status command."""
    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console_awr.console, verbose=verbose)

    registry_info = registry.info()

    console_awr.print("🔍 [bold cyan]Registry Status[/bold cyan]\n")

    console_awr.print(f"🏷️  [bold magenta]{registry_info.get('name')}[/bold magenta]")
    console_awr.print(f"  URL: [cyan]{registry_url}[/cyan]")
    console_awr.print(f"  Version: [cyan]{registry_info.get('version')}[/cyan]")
    console_awr.print(f"  Type: [cyan]{registry_info.get('type')}[/cyan]")

    auth_info = registry_info.get('auth', {})
    providers = auth_info.get('providers', [])
    if providers:
        console_awr.print(f"  Auth Providers: [cyan]{providers}[/cyan]")
    else:
        console_awr.print(f"  Auth Providers: [cyan]None[/cyan]")


def register(app):
    """Register the status command with the Typer app."""

    @app.command()
    def status(
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Show registry status and configuration information."""
        console = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=verbose)
        try:
            console_awr.print("")
            status_command(console_awr, verbose)
            from knitpkg.core.telemetry import print_telemetry_warning
            from pathlib import Path
            print_telemetry_warning(Path.cwd())
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Status check cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Status check failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)