# knitpkg/commands/install.py

"""
KnitPkg for Metatrader install command — dependency resolution and output generation.

This module orchestrates the installation process: downloading dependencies,
processing them in include or flat mode, and generating output files.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from knitpkg.mql.install import ProjectInstaller
from knitpkg.core.exceptions import KnitPkgError, RegistryError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def install_command(project_dir: Path, locked_mode: bool, show_tree: bool, console: Console, verbose: bool):
    """Command wrapper for install command."""
    installer = ProjectInstaller(project_dir, locked_mode, console, verbose)
    installer.install(show_tree)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def install(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        locked: Optional[bool] = typer.Option(
            False,
            "--locked",
            help="Fail if any dependency has local changes or does not match the lockfile. "
            "Enables strict reproducible builds (recommended for CI/CD and production)."
        ),
        no_tree: Optional[bool] = typer.Option(
            False,
            "--no-tree",
            help="Skip displaying dependency tree after resolution."
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output with file/line information"
        )
    ):
        """Prepare the project: resolve recursive includes or generate flat files."""

        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()

        
        console = Console(log_path=False)
        try:
            console.print("")
            install_command(project_dir, locked, not no_tree, console, verbose) # type: ignore
            console.print("")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠ Install cancelled by user.[/bold yellow]")
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
            console.print(f"[bold red]❌ Install failed:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console.print("")
            raise typer.Exit(code=1)
