# knitpkg/commands/build.py
from typing import Optional
from pathlib import Path
from rich.console import Console
import typer

# Import functions from existing commands that will be invoked
from knitpkg.commands.install import install_command
from knitpkg.commands.autocomplete import autocomplete_command
from knitpkg.commands.compile import compile_command

# Import utility function to load the manifest
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.mql.models import MQLKnitPkgManifest # Import the manifest model

# ==============================================================
# COMMAND WRAPPER
# ==============================================================
def build_command(project_dir: Path, locked_mode: bool, show_tree: bool, entrypoints_only: bool, compile_only: bool, verbose: bool) -> None:
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
    console = Console(log_path=False)

    console.print(f"[bold green]🚀 Starting build for project in[/bold green] [cyan]{project_dir}[/cyan]")

    # 1. Load the project manifest
    manifest_path_json = project_dir / "knitpkg.json"
    manifest_path_yaml = project_dir / "knitpkg.yaml"

    if manifest_path_json.is_file():
        manifest_path = manifest_path_json
    elif manifest_path_yaml.is_file():
        manifest_path = manifest_path_yaml
    else:
        console.print(f"[red]❌ Error: Manifest (knitpkg.json or knitpkg.yaml) not found in[/red] [cyan]{project_dir}[/cyan]")
        raise FileNotFoundError(f"Manifest not found in directory {project_dir}")

    try:
        manifest: MQLKnitPkgManifest = load_knitpkg_manifest(
            manifest_path, manifest_class=MQLKnitPkgManifest
        )
    except Exception as e:
        console.print(f"[red]❌ Error loading manifest:[/red] {e}")
        raise typer.Exit(code=1)

    project_type = manifest.type.value # Assumes `manifest.type` is an Enum and has `.value`
    console.print(f"   [bold]Project Name:[/bold] [yellow]{manifest.name}[/yellow]")
    console.print(f"   [bold]Project Type:[/bold] [magenta]{project_type}[/magenta]")
    console.print(f"   [bold]Version:[/bold] [magenta]{manifest.version}[/magenta]")

    # 2. Execute commands based on project type
    if project_type == "package":
        console.print("\n[bold blue]→ 'package' type detected. Executing autocomplete and compile...[/bold blue]")

        console.print("[cyan]   ▶️   Generating autocomplete...[/cyan]")
        autocomplete_command(project_dir, verbose) # Invokes the function directly
    else:
        console.print(f"\n[bold blue]→ '{project_type}' type detected. Executing install and compile...[/bold blue]")

        console.print("[cyan]   ▶️   Installing dependencies...[/cyan]")
        install_command(project_dir, locked_mode, show_tree, verbose)

    console.print("[cyan]   ▶️   Compiling project...[/cyan]")
    compile_command(project_dir, entrypoints_only, compile_only, verbose)

    console.print("\n[bold green]✅   Build completed successfully![/bold green]")


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

        build_command(project_dir, \
                    True if locked else False, \
                    False if no_tree else True, \
                    True if entrypoints_only else False, 
                    True if compile_only else False, \
                    True if verbose else False)

