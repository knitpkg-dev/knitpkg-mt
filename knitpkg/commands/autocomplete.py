# knitpkg/commands/autocomplete.py

"""
KnitPkg for MetaTrader autocomplete command — generates autocomplete files.

This module handles the generation of MQL include files that provide
autocomplete functionality for KnitPkg-managed packages within MetaEditor.
"""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from knitpkg.mql.autocomplete import AutocompleteGenerator
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def autocomplete_command(project_dir: Path, console: Console, verbose: bool):
    """Command wrapper"""
    generator = AutocompleteGenerator(project_dir, console, verbose)
    generator.generate()

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    """Register the autocomplete command with the Typer app."""

    @app.command()
    def autocomplete(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Generate autocomplete.mqh for MetaEditor for package development."""
        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()

        console = Console(log_path=False)
        
        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        
        try:
            console_awr.print("")
            autocomplete_command(project_dir, console, True if verbose else False)
            console_awr.print("")
            
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️ Autocomplete generation cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)

        except RegistryError as e:
            console_awr.print(f"[bold red]❌ Registry error:[/bold red] {e}. Reason: {e.reason} ")
            if verbose:
                console_awr.log(f"  Status Code: {e.status_code}")
                console_awr.log(f"  Error type: {e.error_type}")
                console_awr.log(f"  Request URL: {e.request_url}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"[bold red]❌ Autocomplete generation failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
