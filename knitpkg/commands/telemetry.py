# knitpkg/commands/telemetry.py

import typer
from pathlib import Path
from rich.console import Console

from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError
from knitpkg.core.global_config import set_global_telemetry
from knitpkg.core.settings import Settings

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def telemetry_command(state: str, global_setting: bool, project_dir: Path, console: Console):
    """Command wrapper for telemetry command."""
    console_awr = ConsoleAware(console=console, verbose=False)

    enabled = state.lower() == 'on'

    if global_setting:
        set_global_telemetry(enabled)
        status = "enabled" if enabled else "disabled"
        console_awr.print(f"📊 [bold green]Global telemetry {status}[/bold green]")
    else:
        settings = Settings(project_dir)
        settings.save_if_changed("telemetry", enabled)
        status = "enabled" if enabled else "disabled"
        console_awr.print(f"📊 [bold green]Project telemetry {status}[/bold green]")


def register(app):
    """Register the telemetry command with the Typer app."""

    @app.command()
    def telemetry(
        state: str = typer.Argument(..., help="Telemetry state: 'on' or 'off'"),
        global_setting: bool = typer.Option(
            True,
            "--global/--local",
            help="Set global or local telemetry. `global` enables telemetry globally for all projects of this user; `local` means it is enabled only for this project."
        ),
        project_dir: Path = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        )
    ):
        """Configure telemetry settings."""
        console = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=False)

        # Validate state argument
        if state.lower() not in ['on', 'off']:
            console_awr.print(f"[bold red]❌ Invalid state:[/bold red] '{state}'. Must be 'on' or 'off'.")
            raise typer.Exit(code=1)

        project_path = Path(project_dir).resolve() if project_dir else Path.cwd()

        try:
            console_awr.print("")
            telemetry_command(state, global_setting, project_path, console)
            console_awr.print("")
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Telemetry setting cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)

        except KnitPkgError as e:
            console_awr.print(f"\n[bold red]❌ Telemetry setting failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
