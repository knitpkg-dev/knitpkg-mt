# helix/commands/config.py

"""
Helix for MetaTrader config command — manage Helix configuration settings.

This module provides CLI commands to view and modify Helix's global
configuration, such as MetaEditor compiler paths and MQL data folder paths.
"""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from helix.mql.settings import (
    get_mql5_compiler_path,
    set_mql5_compiler_path,
    get_mql4_compiler_path,
    set_mql4_compiler_path,
    get_mql5_data_folder_path,
    set_mql5_data_folder_path,
    get_mql4_data_folder_path,
    set_mql4_data_folder_path,
)


def register(app):
    """Register the config command with the Typer app."""

    @app.command()
    def config(
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
            help="List all current configuration settings"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output with file/line information"
        )
    ):
        """
        Manage Helix configuration settings.
        """
        console = Console(log_path=verbose)

        # Set compiler paths
        if mql5_compiler_path:
            set_mql5_compiler_path(str(mql5_compiler_path.resolve()))
            console.log(
                f"[green]MQL5 compiler path set to:[/]"
                f" {mql5_compiler_path.resolve()}"
            )
        if mql4_compiler_path:
            set_mql4_compiler_path(str(mql4_compiler_path.resolve()))
            console.log(
                f"[green]MQL4 compiler path set to:[/]"
                f" {mql4_compiler_path.resolve()}"
            )

        # Set MQL data folder paths
        if mql5_data_folder_path:
            set_mql5_data_folder_path(str(mql5_data_folder_path.resolve()))
            console.log(
                f"[green]MQL5 data folder path set to:[/]"
                f" {mql5_data_folder_path.resolve()}"
            )
        if mql4_data_folder_path:
            set_mql4_data_folder_path(str(mql4_data_folder_path.resolve()))
            console.log(
                f"[green]MQL4 data folder path set to:[/]"
                f" {mql4_data_folder_path.resolve()}"
            )

        # List all settings if requested or no settings were changed
        if list_all or (
            not mql5_compiler_path and not mql4_compiler_path and
            not mql5_data_folder_path and not mql4_data_folder_path
        ):

            table = Table(title="Helix for MetaTrader Configuration", show_header=True, header_style="bold cyan") # Alterado
            table.add_column("Setting", style="dim")
            table.add_column("Value")

            # Display compiler paths
            table.add_row("mql5-compiler-path", get_mql5_compiler_path() or "[dim]Not set[/]")
            table.add_row("mql4-compiler-path", get_mql4_compiler_path() or "[dim]Not set[/]")

            # Display data folder paths
            table.add_row("mql5-data-folder-path", get_mql5_data_folder_path() or "[dim]Not set[/]")
            table.add_row("mql4-data-folder-path", get_mql4_data_folder_path() or "[dim]Not set[/]")

            console.print(table)
