# knitpkg/commands/checkinstall.py

"""
KnitPkg for MetaTrader checkinstall command — checks if a package can be 
successfully installed.
"""
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from knitpkg.mql.autocomplete import AutocompleteTools
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def checkinstall_command(project_dir: Path, skip_autocomplete: bool, console: Console, verbose: bool):
    """Command wrapper"""
    generator = AutocompleteTools(project_dir, console, verbose)
    generator.check_install(skip_autocomplete)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    """Register the checkinstall command with the Typer app."""

    @app.command()
    def checkinstall(
        skip_autocomplete: Optional[bool] = typer.Option(
            False,
            "--skip-autocomplete",
            help="Skip autocomplete (check install only)"
        ),
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
        """Checks all the directives to verify if the package can be successfully installed."""
        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()

        console = Console(log_path=False)
        
        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        
        try:
            console_awr.print("")
            checkinstall_command(project_dir, skip_autocomplete or False, console, True if verbose else False)
            from knitpkg.core.telemetry import print_telemetry_warning
            print_telemetry_warning(project_dir)
            console_awr.print("")
            
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Check install cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Check install failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
