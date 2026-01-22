import typer
from typing import Optional
from pathlib import Path

from knitpkg.core.exceptions import KnitPkgError, RegistryError
from knitpkg.mql.models import MQLProjectType, Target, IncludeMode
from knitpkg.mql.project_init import ProjectInitializer
from rich.console import Console

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def init_command(project_type: MQLProjectType,
    name: str,
    organization: str,
    version: str,
    description: str,
    author: str,
    license: str,
    target: Target,
    include_mode: IncludeMode,
    entrypoints_str: str,
    location: Path,
    git_init: bool,
    dry_run: bool,
    console: Console
    ):
    """Command wrapper for init command."""

    initializer = ProjectInitializer(console)
    initializer.run(
        dry_run=dry_run,
        project_type=project_type,
        name=name,
        organization=organization,
        version=version,
        description=description,
        author=author,
        license=license,
        target=target,
        include_mode=include_mode,
        entrypoints_str=entrypoints_str,
        location=location,
        git_init=git_init,
    )

def register(app):
    """Register the init command with the Typer app."""

    @app.command(name="init", help="Initializes a new KnitPkg project.")
    def init_project(
        dry_run: bool = typer.Option(
            False, "--dry-run", "-d", help="Show what would be done without making actual changes."
        ),
        project_type: MQLProjectType = typer.Option(
            None, "--type", "-t", help="Project type (package, expert, indicator, library, service)."
        ),
        name: str = typer.Option(
            None,
            "--name",
            "-n",
            help="Project name (alphanumeric, hyphen, underscore, dot; no spaces).",
        ),
        organization: str = typer.Option(
            None,
            "--organization",
            "-o",
            help="Organization name (alphanumeric, hyphen, underscore, dot).",
        ),
        version: str = typer.Option(
            None, "--version", "-v", help="Project version (SemVer, e.g., 1.0.0)."
        ),
        description: str = typer.Option(None, "--description", help="Short project description."),
        author: str = typer.Option(None, "--author", help="Author's name."),
        license: str = typer.Option(None, "--license", help="License identifier (e.g., MIT)."),
        target: Target = typer.Option(None, "--target", help="MetaTrader platform target (MQL4 or MQL5)."),
        include_mode: IncludeMode = typer.Option(
            None, "--include-mode", help="Include resolution mode (include or flat)."
        ),
        entrypoints_str: str = typer.Option(
            None,
            "--entrypoints",
            help="Comma-separated list of entrypoint files (required if include_mode=flat and type!=package).",
        ),
        location: Path = typer.Option(
            None, "--location", "-l", help="Directory where the project will be created."
        ),
        git_init: bool = typer.Option(None, "--git-init", help="Initialize a Git repository."),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output with file/line information"
        )
    ):
        """Initializes a new KnitPkg project interactively."""
    
        console = Console(log_path=False)
        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        try:
            init_command(project_type,
                name,
                organization,
                version,
                description,
                author,
                license,
                target,
                include_mode,
                entrypoints_str,
                location,
                git_init,
                dry_run,
                console
            )
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️ Init cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)

        except KnitPkgError as e:
            console_awr.print(f"[bold red]❌ Init failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
