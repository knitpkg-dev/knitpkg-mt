# knitpkg/commands/global_config.py

import typer
from rich.console import Console
from knitpkg.core.global_config import (
    get_registry_url,
    set_global_registry
)

console = Console()

def register(app: typer.Typer):

    @app.command()
    def globalconfig(
        set_registry: str = typer.Option(None, "--set-registry", help="Set default registry URL"),
        get: bool = typer.Option(False, "--get", help="Show current configuration")
    ):
        """Configure KnitPkg CLI settings."""

        if set_registry:
            set_global_registry(set_registry)
            console.print(f"✓ Default registry set to: {set_registry}")
            return

        if get:
            current_registry = get_registry_url()
            console.print(f"Registry: [cyan]{current_registry}[/cyan]")
            return

        # Show all config
        console.print("[bold]KnitPkg Configuration[/bold]\n")
        console.print(f"Registry: [cyan]{get_registry_url()}[/cyan]")
