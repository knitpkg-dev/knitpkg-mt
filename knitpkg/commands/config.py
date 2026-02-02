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

from knitpkg.core.console import ConsoleAware

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

    console_awr = ConsoleAware(console=console, verbose=False)

    settings: MQLSettings = MQLSettings(project_path)

    # Set compiler paths
    if mql5_compiler_path:
        settings.set_compiler_path(str(mql5_compiler_path.resolve()), Target.mql5)
        console_awr.print(
            f"🔧 [green]MQL5 compiler path set[/green] → "
            f"[cyan]{mql5_compiler_path.resolve()}[/cyan]"
        )
    if mql4_compiler_path:
        settings.set_compiler_path(str(mql4_compiler_path.resolve()), Target.mql4)
        console_awr.print(
            f"🔧 [green]MQL4 compiler path set[/green] → "
            f"[cyan]{mql4_compiler_path.resolve()}[/cyan]"
        )

    # Set MQL data folder paths
    if mql5_data_folder_path:
        settings.set_data_folder_path(str(mql5_data_folder_path.resolve()), Target.mql5)
        console_awr.print(
            f"📁 [green]MQL5 data folder path set[/green] → "
            f"[cyan]{mql5_data_folder_path.resolve()}[/cyan]"
        )
    if mql4_data_folder_path:
        settings.set_data_folder_path(str(mql4_data_folder_path.resolve()), Target.mql4)
        console_awr.print(
            f"📁 [green]MQL4 data folder path set[/green] → "
            f"[cyan]{mql4_data_folder_path.resolve()}[/cyan]"
        )

    # List all settings if requested or no settings were changed
    if list_all or (
        not mql5_compiler_path and not mql4_compiler_path and
        not mql5_data_folder_path and not mql4_data_folder_path
    ):
        console_awr.print("📋 [bold cyan]Configuration in use:[/]")
        console_awr.print("")
        
        # Display compiler paths
        mql5_path = settings.get_compiler_path(Target.mql5) or "[dim]Not set[/]"
        mql4_path = settings.get_compiler_path(Target.mql4) or "[dim]Not set[/]"
        
        # Display data folder paths
        mql5_data = settings.get_data_folder_path(Target.mql5) or "[dim]Not set[/]"
        mql4_data = settings.get_data_folder_path(Target.mql4) or "[dim]Not set[/]"
        
        console_awr.print(f"  mql5-compiler-path:     {mql5_path}")
        console_awr.print(f"  mql4-compiler-path:     {mql4_path}")
        console_awr.print(f"  mql5-data-folder-path:  {mql5_data}")
        console_awr.print(f"  mql4-data-folder-path:  {mql4_data}")

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
        console_awr = ConsoleAware(console=console, verbose=False)
        
        try:
            console_awr.print("")
            config_command(
                project_dir,
                mql5_compiler_path,
                mql4_compiler_path,
                mql5_data_folder_path,
                mql4_data_folder_path,
                list_all or False,
                console
            )
            console_awr.print("")
            
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Config setting cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"\n[bold red]❌ Config setting failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
