# knitpkg/commands/register.py
from typing import Optional
from pathlib import Path
import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.project_register import ProjectRegister
from knitpkg.mql.models import MQLKnitPkgManifest
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def register_command(project_dir: Path, console: Console, verbose: bool):
    """Command wrapper for register command."""

    project_path = Path(project_dir).resolve()

    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console, verbose=verbose) 

    register: ProjectRegister = ProjectRegister(project_path, registry, MQLKnitPkgManifest, console, True if verbose else False)
    register.register(is_private=False)


def register(app):
    """Register the register command with the main Typer app."""

    @app.command()
    def register(
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
        """Register the current project to the KnitPkg registry."""
        
        console: Console = Console(log_path=False)

        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)

        try:
            console_awr.print("")
            project_dir = project_dir if project_dir is not None else Path.cwd()
            register_command(project_dir, 
                            console=console, 
                            verbose=True if verbose else False)
            from knitpkg.core.telemetry import print_telemetry_warning
            print_telemetry_warning(project_dir)
            console_awr.print("")
        
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Registration cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Registration failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
