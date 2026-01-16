# knitpkg/commands/global_config.py

import typer
from rich.console import Console
from knitpkg.core.global_config import (
    get_registry_url,
    set_global_registry,
    get_auth_callback_port,
    set_auth_callback_port
)

console = Console()

def register(app: typer.Typer):

    @app.command()
    def globalconfig(
        set_registry: str = typer.Option(None, "--set-registry", help="Set default registry URL"),
        set_port: int = typer.Option(None, "--set-port", help="Set auth callback port"),
        get: bool = typer.Option(False, "--get", help="Show current configuration")
    ):
        """Configure KnitPkg CLI settings."""

        if set_registry:
            set_global_registry(set_registry)
            console.print(f"✓ Default registry set to: {set_registry}")
            return

        if set_port:
            set_auth_callback_port(set_port)
            console.print(f"✓ Auth callback port set to: {set_port}")
            return

        if get:
            current_registry = get_registry_url()
            current_port = get_auth_callback_port()
            console.print(f"Registry: [cyan]{current_registry}[/cyan]")
            console.print(f"Auth callback port: [cyan]{current_port}[/cyan]")
            return

        # Show all config
        console.print("[bold]KnitPkg Configuration[/bold]\n")
        console.print(f"Registry: [cyan]{get_registry_url()}[/cyan]")
        console.print(f"Auth callback port: [cyan]{get_auth_callback_port()}[/cyan]")
