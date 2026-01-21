# knitpkg/commands/config.py

"""
KnitPkg for MetaTrader config command — manage KnitPkg configuration settings.

This module provides CLI commands to view and modify KnitPkg's global
configuration, such as MetaEditor compiler paths and MQL data folder paths.
"""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from knitpkg.mql.settings import MQLSettings
from knitpkg.mql.models import Target
from knitpkg.core.exceptions import KnitPkgError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def config_command(
    project_dir: Optional[Path],
    mql5_compiler_path: Optional[Path],
    mql4_compiler_path: Optional[Path],
    mql5_data_folder_path: Optional[Path],
    mql4_data_folder_path: Optional[Path],
    list_all: bool,
    console: Console
):
    """Command wrapper for config command."""

    if project_dir is None:
        project_path = Path.cwd()
    else:
        project_path = Path(project_dir).resolve()

    settings: MQLSettings = MQLSettings(project_path)

    # Set compiler paths
    if mql5_compiler_path:
        settings.set_compiler_path(str(mql5_compiler_path.resolve()), Target.MQL5)
        console.log(
            f"[green]MQL5 compiler path set to:[/]"
            f" {mql5_compiler_path.resolve()}"
        )
    if mql4_compiler_path:
        settings.set_compiler_path(str(mql4_compiler_path.resolve()), Target.MQL4)
        console.log(
            f"[green]MQL4 compiler path set to:[/]"
            f" {mql4_compiler_path.resolve()}"
        )

    # Set MQL data folder paths
    if mql5_data_folder_path:
        settings.set_data_folder_path(str(mql5_data_folder_path.resolve()), Target.MQL5)
        console.log(
            f"[green]MQL5 data folder path set to:[/]"
            f" {mql5_data_folder_path.resolve()}"
        )
    if mql4_data_folder_path:
        settings.set_data_folder_path(str(mql4_data_folder_path.resolve()), Target.MQL4)
        console.log(
            f"[green]MQL4 data folder path set to:[/]"
            f" {mql4_data_folder_path.resolve()}"
        )

    # List all settings if requested or no settings were changed
    if list_all or (
        not mql5_compiler_path and not mql4_compiler_path and
        not mql5_data_folder_path and not mql4_data_folder_path
    ):
        table = Table(title="KnitPkg for MetaTrader Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="dim")
        table.add_column("Value")

        # Display compiler paths
        table.add_row("mql5-compiler-path", settings.get_compiler_path(Target.MQL5) or "[dim]Not set[/]")
        table.add_row("mql4-compiler-path", settings.get_compiler_path(Target.MQL4) or "[dim]Not set[/]")

        # Display data folder paths
        table.add_row("mql5-data-folder-path", settings.get_data_folder_path(Target.MQL5) or "[dim]Not set[/]")
        table.add_row("mql4-data-folder-path", settings.get_data_folder_path(Target.MQL4) or "[dim]Not set[/]")

        console.print(table)

def register(app):
    """Register the config command with the Typer app."""

    @app.command()
    def config(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        mql5_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql5-compiler-path",
            help="Set the path to MetaEditor64.exe (MQL5 compiler)"
        ),
        mql4_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql4-compiler-path",
            help="Set the path to MetaEditor.exe (MQL4 compiler)"
        ),
        mql5_data_folder_path: Optional[Path] = typer.Option(
            None,
            "--mql5-data-folder-path",
            help="Set the custom data folder path for MQL5 (e.g., C:\\Users\\User\\AppData\\Roaming\\MetaQuotes\\Terminal\\<hash>)"
        ),
        mql4_data_folder_path: Optional[Path] = typer.Option(
            None,
            "--mql4-data-folder-path",
            help="Set the custom data folder path for MQL4 (e.g., C:\\Users\\User\\AppData\\Roaming\\MetaQuotes\\Terminal\\<hash>)"
        ),
        list_all: Optional[bool] = typer.Option(
            False,
            "--list",
            "-l",
            help="List all configurations in use"
        )
    ):
        """
        Manage KnitPkg configuration settings.
        """
        console = Console(log_path=False)
        
        try:
            console.print("")
            config_command(
                project_dir,
                mql5_compiler_path,
                mql4_compiler_path,
                mql5_data_folder_path,
                mql4_data_folder_path,
                list_all or False,
                console
            )
            console.print("")
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠ Config setting cancelled by user.[/bold yellow]")
            console.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console.print(f"[bold red]❌ Config setting failed:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)
