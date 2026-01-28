from typing import Optional
from pathlib import Path
import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.project_get import ProjectGet
from knitpkg.core.exceptions import KnitPkgError, RegistryError, InvalidUsageError
from knitpkg.mql.mql_paths import find_mql_paths, get_mql_target_paths, is_valid_target_path
from knitpkg.mql.models import Target

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def get_command(target: str, proj_specifier: str, verspec: Optional[str], mql_target_folder: Path, console: Console, verbose: bool):
    """Command wrapper for get command."""

    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console, verbose=verbose)

    project_get: ProjectGet = ProjectGet(registry, console, True if verbose else False)
    project_get.get_project(target, proj_specifier, verspec, mql_target_folder)


def register(app):
    """Register the get command with the main Typer app."""

    @app.command()
    def get(
        target: Target = typer.Argument(..., help="Platform target (MQL4, MQL5, ...)."),
        proj_specifier: str = typer.Argument(
            ...,
            help="Specifier of the project to get: @organization/project_name"
        ),
        verspec: Optional[str] = typer.Option(
            '*',
            "--verspec",
            "-v",
            help="Version specifier for the project"
        ),
        mql_data_folder: Optional[Path] = typer.Option(
            None,
            "--mql-data-folder",
            "-m",
            help="MQL data folder path"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Get a project."""

        console: Console = Console(log_path=False)

        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)

        try:
            console_awr.print("")

            mql_target_folder: Path

            if not mql_data_folder:
                if is_valid_target_path(Path.cwd()):
                    mql_target_folder = Path.cwd()
                elif is_valid_target_path(Path.cwd() / target.value):
                    mql_target_folder = Path.cwd() / target.value
                else:
                    candidates = find_mql_paths(target)
                    len_candidates = len(candidates)
                    if len_candidates == 1:
                        mql_target_folder = candidates[0]
                    else:
                        raise InvalidUsageError("Could not determine MQL data folder. Please specify it via -m or --mql-data-folder option.")
            else:
                mql_target_folder = mql_data_folder / target.value
                if not is_valid_target_path(mql_target_folder):
                    raise InvalidUsageError("The specified path is not an MQL data folder.")

            get_command(target.value, proj_specifier, verspec, mql_target_folder,
                       console=console,
                       verbose=True if verbose else False)
            from knitpkg.core.telemetry import print_telemetry_warning
            print_telemetry_warning(Path.cwd())
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Get cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Get failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)