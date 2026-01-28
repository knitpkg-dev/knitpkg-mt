# knitpkg/commands/info.py

import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError, RegistryError
from knitpkg.mql.models import Target
from knitpkg.core.resolve_helper import parse_project_name
import datetime

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def info_command(target: str, organization: str, project_name: str, console_awr: ConsoleAware, verbose: bool):
    """Command wrapper for info command."""
    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console_awr.console, verbose=verbose)

    project_info = registry.get_project_info(target, organization, project_name)

    console_awr.print("🔍 [bold cyan]Project Information[/bold cyan]\n")

    console_awr.print(f"📦 [bold magenta]@{project_info.get('organization')}/{project_info.get('name')}[/bold magenta]")
    console_awr.print(f"  Target: [cyan]{project_info.get('target')}[/cyan]")
    console_awr.print(f"  Type: [cyan]{project_info.get('type')}[/cyan]")
    console_awr.print(f"  Description: [cyan]{project_info.get('description') or 'No description'}[/cyan]")
    keywords = project_info.get('keywords')
    if keywords:
        console_awr.print(f"  Keywords: [cyan]{[k.strip() for k in keywords.split(',') if k.strip()]}[/cyan]")
    console_awr.print(f"  Private: {'[yellow]Yes[/]' if project_info.get('is_private') else '[cyan]No[/]'}")
    published_at = project_info.get('published_at')
    published_at = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S') if published_at else ''
    console_awr.print(f"  Published: [cyan]{published_at}[/cyan]")
    if project_info.get('repo_url'):
        console_awr.print(f"  Repository: [cyan]{project_info.get('repo_url')}[/cyan]")

    versions = project_info.get('versions', [])
    if versions:
        console_awr.print(f"\n📋 [bold cyan]Versions ({len(versions)} total)[/bold cyan]")
        for version in versions:
            yanked_status = " (yanked)" if version.get('yanked') else ""
            description = f"{' - '+version.get('description') if version.get('description') else ''}"
            created_at = version.get('created_at')
            created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S') if created_at else ''
            console_awr.print(f"  • [cyan]{version.get('version')}[/cyan]"
                              f"{yanked_status}{description} - {created_at} - {version.get('commit_hash')[:16]}")
    else:
        console_awr.print("\n📋 [bold cyan]Versions: None[/bold cyan]")


def register(app):
    """Register the info command with the Typer app."""

    @app.command()
    def info(
        target: Target = typer.Argument(..., help="MetaTrader platform target (MQL4 or MQL5)."),
        specifier: str = typer.Argument(..., help="@organization/project_name"),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Show detailed information about a project."""
        console = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=verbose)
        try:
            console_awr.print("")
            organization, name = parse_project_name(specifier)
            if not organization:
                raise KnitPkgError("No organization specified")
            
            info_command(target.value, organization, name, console_awr, verbose)
            from knitpkg.core.telemetry import print_telemetry_warning
            from pathlib import Path
            print_telemetry_warning(Path.cwd())
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Info cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Info failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)