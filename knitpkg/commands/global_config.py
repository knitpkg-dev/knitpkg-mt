# knitpkg/commands/global_config.py

import typer
from rich.console import Console

from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError
from knitpkg.core.global_config import (
    get_registry_url,
    set_global_registry
)

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def globalconfig_command(set_registry: str, list_all: bool, console: Console):
    """Command wrapper for install command."""
    console_awr = ConsoleAware(console=console, verbose=False)

    if set_registry:
        set_global_registry(set_registry)
        console_awr.print(f"✓ Default registry set to: {set_registry}")
        return

    if list_all:
        current_registry = get_registry_url()
        console_awr.print(f"Registry: [cyan]{current_registry}[/cyan]")
        return

    # Show all config
    console_awr.print("[bold]KnitPkg Configuration[/bold]\n")
    console_awr.print(f"Registry: [cyan]{get_registry_url()}[/cyan]")


def register(app: typer.Typer):

    @app.command()
    def globalconfig(
        set_registry: str = typer.Option(None, "--set-registry", help="Set default registry URL"),
        list_all: bool = typer.Option(False, "--list", "-l", help="Show current configuration")
    ):
        """Configure KnitPkg CLI settings."""
        console = Console(log_path=False)

        console_awr = ConsoleAware(console=console, verbose=False)

        try:
            console_awr.print("")
            globalconfig_command(set_registry, list_all, console)
            console_awr.print("")
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠ Global config setting cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"[bold red]❌ Global config setting failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
