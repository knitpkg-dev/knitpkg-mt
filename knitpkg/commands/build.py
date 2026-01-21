# knitpkg/commands/build.py
from typing import Optional
from pathlib import Path
from rich.console import Console
import typer

from knitpkg.commands.install import install_command
from knitpkg.commands.autocomplete import autocomplete_command
from knitpkg.commands.compile import compile_command

from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.mql.models import MQLKnitPkgManifest, MQLProjectType
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================
def build_command(project_dir: Path, locked_mode: bool, show_tree: bool, entrypoints_only: bool, compile_only: bool, console: Console, verbose: bool) -> None:
    """
    Main logic for the `kp-mt build` command.

    Loads the project manifest and executes the correct sequence of commands
    (autocomplete, install, compile) based on the `manifest.type`.

    Parameters
    ----------
    console:
        An instance of `rich.console.Console` for displaying messages.
    project_dir:
        The path to the project's root directory (where the manifest is located).
    """

    console.print(f"[bold green]🚀 Starting build for project in[/bold green] [cyan]{project_dir}[/cyan]")

    # 1. Load the project manifest
    manifest: MQLKnitPkgManifest = load_knitpkg_manifest(project_dir, manifest_class=MQLKnitPkgManifest)

    console.print(f"   [bold]Project Name:[/bold] [yellow]{manifest.name}[/yellow]")
    console.print(f"   [bold]Project Type:[/bold] [magenta]{manifest.type}[/magenta]")
    console.print(f"   [bold]Version:[/bold] [magenta]{manifest.version}[/magenta]")

    # 2. Execute commands based on project type
    project_type = MQLProjectType(manifest.type) # Assumes `manifest.type` is an Enum and has `.value`
    if project_type == MQLProjectType.PACKAGE:
        console.print("\n[cyan]▶️  Generating autocomplete...[/cyan]")
        autocomplete_command(project_dir, console, verbose) # Invokes the function directly
    else:
        console.print("\n[cyan]▶️  Installing dependencies...[/cyan]")
        install_command(project_dir, locked_mode, show_tree, console, verbose)

    console.print("\n[cyan]▶️  Compiling project...[/cyan]")
    compile_command(project_dir, entrypoints_only, compile_only, console, verbose)

    console.print("\n[bold green]✅ Build completed successfully![/bold green]")


# ----------------------------------------------------------------------
# Command Registration for Typer
# ----------------------------------------------------------------------
def register(app):
    """
    Registers the `build` sub-command with the main Typer application.
    """
    @app.command(
        name="build",
        help="Builds the current KnitPkg project, installing dependencies and compiling.",
    )
    def build(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        locked: Optional[bool] = typer.Option(
            True,
            "--locked",
            help="Fail if any dependency has local changes or does not match the lockfile. "
            "Enables strict reproducible builds (recommended for CI/CD and production)."
        ),
        no_tree: Optional[bool] = typer.Option(
            False,
            "--no-tree",
            help="Skip displaying dependency tree after resolution."
        ),
        entrypoints_only: Optional[bool] = typer.Option(
            False,
            "--entrypoints-only",
            help="Compile only entrypoints (skip compile list)"
        ),
        compile_only: Optional[bool] = typer.Option(
            False,
            "--compile-only",
            help="Compile only files in compile list (skip entrypoints)"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output with file/line information"
        )
    ):
        
        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()
        console = Console(log_path=False)

        try:
            console.print("")
            build_command(project_dir, \
                        True if locked else False, \
                        False if no_tree else True, \
                        True if entrypoints_only else False, 
                        True if compile_only else False, \
                        console,
                        True if verbose else False)
            console.print("")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠ Build cancelled by user.[/bold yellow]")
            console.print("")
            raise typer.Exit(code=1)

        except RegistryError as e:
            console.print(f"[bold red]❌ Registry error:[/bold red] {e}. Reason: {e.reason} ")
            if verbose:
                console.log(f"  Status Code: {e.status_code}")
                console.log(f"  Error type: {e.error_type}")
                console.log(f"  Request URL: {e.request_url}")
            console.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console.print(f"[bold red]❌ Build failed:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)

