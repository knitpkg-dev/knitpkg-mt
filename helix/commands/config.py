# helix/commands/config.py

"""
Helix config command — manage CLI configuration.

This module handles compiler path configuration and other CLI settings.
"""

from pathlib import Path
from typing import Optional
from rich.console import Console
import typer

# Import MQL-specific settings
from helix.mql.settings import (
    get_mql5_compiler_path,
    get_mql4_compiler_path,
    set_mql5_compiler_path,
    set_mql4_compiler_path,
)

def register(app):
    @app.command()
    def config(
        mql5_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql5-compiler-path",
            help="Set MQL5 compiler path (MetaEditor64.exe)"
        ),
        mql4_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql4-compiler-path",
            help="Set MQL4 compiler path (MetaEditor.exe)"
        ),
        show: Optional[bool] = typer.Option(
            False,
            "--show",
            help="Show current configuration"
        )
    ):
        """Configure Helix CLI settings (compiler paths, etc)."""

        console = Console()

        # Show current configuration
        if show:
            console.log("[bold cyan]Current Configuration:[/]")
            console.log(f"  MQL5 Compiler: [yellow]{get_mql5_compiler_path()}[/]")
            console.log(f"  MQL4 Compiler: [yellow]{get_mql4_compiler_path()}[/]")
            return

        # Set MQL5 compiler path
        if mql5_compiler_path:
            if not mql5_compiler_path.exists():
                console.log(
                    f"[red]Error:[/] Compiler not found: {mql5_compiler_path}"
                )
                raise SystemExit(1)

            set_mql5_compiler_path(str(mql5_compiler_path.resolve()))
            console.log(
                f"[green]Check[/] MQL5 compiler path set to: "
                f"[bold]{mql5_compiler_path.resolve()}[/]"
            )

        # Set MQL4 compiler path
        if mql4_compiler_path:
            if not mql4_compiler_path.exists():
                console.log(
                    f"[red]Error:[/] Compiler not found: {mql4_compiler_path}"
                )
                raise SystemExit(1)

            set_mql4_compiler_path(str(mql4_compiler_path.resolve()))
            console.log(
                f"[green]Check[/] MQL4 compiler path set to: "
                f"[bold]{mql4_compiler_path.resolve()}[/]"
            )

        if not mql5_compiler_path and not mql4_compiler_path and not show:
            console.log(
                "[yellow]No configuration changes. Use --show to see current settings.[/]"
            )
