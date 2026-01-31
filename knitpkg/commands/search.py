from typing import Optional
from pathlib import Path
import typer
from rich.console import Console

from knitpkg.core.registry import Registry
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError, RegistryError
from knitpkg.mql.models import Target
import datetime

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def search_command(target: str, q: Optional[str], org: Optional[str], type: Optional[str], author: Optional[str], license: Optional[str], page: int, page_size: int, sort_by: str, sort_order: str, console_awr: ConsoleAware, verbose: bool):
    """Command wrapper for search command."""

    registry_url = get_registry_url()
    registry: Registry = Registry(registry_url, console=console_awr.console, verbose=verbose)

    search_results = registry.search_projects(target, q, org, type, author, license, page, page_size, sort_by, sort_order)

    console_awr.print("🔍 [bold cyan]Search Results[/bold cyan]\n")
    console_awr.print(f"  Total results: [cyan]{search_results.get('total_results', 0)}[/cyan]")
    console_awr.print(f"  Page: [cyan]{search_results.get('page', 1)}[/cyan] (Page size: [cyan]{search_results.get('page_size', 20)}[/cyan])\n")

    results = search_results.get('results', [])
    if results:
        for result in results:
            org_name = result.get('organization', {}).get('name', 'Unknown')
            name = result.get('name', 'Unknown')
            description = result.get('description', 'No description')
            keywords = result.get('keywords', 'None')
            author = result.get('author', 'Unknown')
            license = result.get('license', 'Unknown')
            project_type = result.get('type', 'Unknown')
            is_private = result.get('is_private', False)
            published_at = result.get('published_at', '')
            published_at = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S') if published_at else ''

            console_awr.print(f"📦 [bold magenta]@{org_name}/{name}[/bold magenta]")
            console_awr.print(f"  Target: [cyan]{target}[/cyan]")
            console_awr.print(f"  Type: [cyan]{project_type}[/cyan]")
            console_awr.print(f"  Description: [cyan]{description}[/cyan]")
            console_awr.print(f"  Keywords: [cyan]{keywords}[/cyan]")
            console_awr.print(f"  Author: [cyan]{author}[/cyan]")
            console_awr.print(f"  License: [cyan]{license}[/cyan]")
            console_awr.print(f"  Private: {'[yellow]Yes[/yellow]' if is_private else '[cyan]No[/cyan]'}")
            console_awr.print(f"  Published: [cyan]{published_at}[/cyan]")
            if result.get('repo_url'):
                console_awr.print(f"  Repository: [cyan]{result.get('repo_url')}[/cyan]")
            console_awr.print("")
    else:
        console_awr.print("  [cyan]No results found.[/cyan]\n")


def register(app):
    """Register the search command with the main Typer app."""

    @app.command()
    def search(
        target: str = typer.Argument(..., help="Target platform (MQL5, MQL4, ...)."),
        q: Optional[str] = typer.Option(
            None,
            "--query",
            "-q",
            help="General search term (name, description, keywords)"
        ),
        org: Optional[str] = typer.Option(
            None,
            "--organization",
            "-o",
            help="Filter by organization name"
        ),
        type: Optional[str] = typer.Option(
            None,
            "--type",
            "-t",
            help="Filter by project type (e.g., 'expert', 'indicator', 'library', etc)"
        ),
        author: Optional[str] = typer.Option(
            None,
            "--author",
            "-a",
            help="Filter by author name"
        ),
        license: Optional[str] = typer.Option(
            None,
            "--license",
            "-l",
            help="Filter by license type"
        ),
        sortby: Optional[str] = typer.Option(
            "published_at",
            "--sort-by",
            "-S",
            help="Sort by order. Use `relevance` with `q` or any Project field (e.g., 'name', 'published_at', ...)"
        ),
        sortorder: Optional[str] = typer.Option(
            "desc",
            "--sort-order",
            "-O",
            help="Sort order ('asc' or 'desc')"
        ),
        page: int = typer.Option(
            1,
            "--page",
            "-p",
            help="Page number for pagination"
        ),
        page_size: int = typer.Option(
            20,
            "--page-size",
            "-s",
            help="Number of results per page"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Search for projects in the KnitPkg registry."""

        console: Console = Console(log_path=False)

        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)

        try:
            console_awr.print("")
            target_t: Optional[Target] = None
            for t in Target:
                if t.lower() == target.lower():
                    target_t = t
                    break
            if not target_t:
                raise KnitPkgError(f"Unsupported target platform: {target}")
            
            search_command(target_t.value, q, org, type, author, license, page, page_size, sortby or 'published_at', sortorder or 'desc', console_awr, True if verbose else False)
            from knitpkg.core.telemetry import print_telemetry_warning
            print_telemetry_warning(Path.cwd())
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Search cancelled by user.[/bold yellow]")
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
            console_awr.print(f"\n[bold red]❌ Search failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)