# knitpkg/commands/yank.py

import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError, RegistryError
from knitpkg.mql.models import Target
from knitpkg.core.resolve_helper import parse_project_name

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def yank_command(target: str, organization: str, project_name: str, version: str, console_awr: ConsoleAware, verbose: bool):
    """Command wrapper for yank command."""
    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console_awr.console, verbose=verbose)

    result = registry.yank(target, organization, project_name, version)

    message = result.get('message', f"Successfully yanked {organization}/{project_name}@{version} for target {target}")

    console_awr.print(f"✅ [bold green]{message}[/bold green]")


def register(app):
    """Register the yank command with the Typer app."""

    @app.command()
    def yank(
        target: Target = typer.Argument(..., help="MetaTrader platform target (MQL4 or MQL5)."),
        specifier: str = typer.Argument(..., help="@organization/project_name"),
        version: str = typer.Argument(..., help="Version to yank"),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Yank a package version from the registry."""
        console = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=verbose)
        try:
            console_awr.print("")
            organization, name = parse_project_name(specifier)
            if not organization:
                raise KnitPkgError("No organization specified")
            
            yank_command(target.value, organization, name, version, console_awr, verbose)
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Yank cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Yank failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
