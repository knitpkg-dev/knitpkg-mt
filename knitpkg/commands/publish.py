# knitpkg/commands/publish.py

"""
KnitPkg for MetaTrader publish command — publishes a package to the registry.
This module handles the process of validating a local KnitPkg project,
checking its Git status, and submitting its metadata to the KnitPkg registry.
It ensures that only clean, committed repositories can be published.
"""

import typer
import httpx
import asyncio
import keyring
from typing import Optional
import git
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from knitpkg.core.file_reading import load_knitpkg_manifest

# Configurations
REGISTRY_URL = "http://localhost:8000"
CREDENTIALS_SERVICE = "knitpkg-mt"

console = Console()


def get_current_commit_hash(repo: git.Repo) -> str:
    """Get the current commit hash from the Git repo."""
    return repo.head.commit.hexsha


def register(app):
    """Register the publish command with the main Typer app."""

    @app.command()
    def publish(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        )
    ):
        """Publish the current project to the KnitPkg registry."""

        project_path = Path(project_dir) if project_dir else Path.cwd()

        # Validate project directory
        if not project_path.is_dir():
            console.print(f"[red]✗[/red] Project directory [cyan]{project_dir}[/cyan] not found.", style="bold")
            raise typer.Exit(code=1)

        # Load manifest
        try:
            manifest = load_knitpkg_manifest(project_path)
        except FileNotFoundError:
            console.print("[red]✗[/red] [bold]knitpkg.yaml[/bold] not found in project directory.", style="bold")
            console.print("   Run [cyan]kp-mt init[/cyan] to create a new project.", style="dim")
            raise typer.Exit(code=1)
        except ValueError as e:
            console.print(f"[red]✗[/red] Error loading manifest: [yellow]{e}[/yellow]", style="bold")
            raise typer.Exit(code=1)

        # Validate Git repository
        try:
            repo = git.Repo(Path.cwd(), search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            console.print("[red]✗[/red] Not a Git repository.", style="bold")
            console.print("   Initialize a Git repository first: [cyan]git init[/cyan]", style="dim")
            raise typer.Exit(code=1)

        if repo.bare:
            console.print("[red]✗[/red] Git repository is bare.", style="bold")
            raise typer.Exit(code=1)

        # Check for remote origin
        if not repo.remotes:
            console.print("[red]✗[/red] No remote repository configured.", style="bold")
            console.print("   Add a remote: [cyan]git remote add origin <URL>[/cyan]", style="dim")
            raise typer.Exit(code=1)

        repo_url = repo.remotes.origin.url
        if not repo_url:
            console.print("[red]✗[/red] Remote origin URL not found.", style="bold")
            raise typer.Exit(code=1)

        # Check for uncommitted changes
        if repo.is_dirty():
            console.print("[red]✗[/red] Repository has uncommitted changes.", style="bold")
            console.print("   Commit your changes first: [cyan]git add . && git commit -m 'message'[/cyan]", style="dim")
            raise typer.Exit(code=1)

        # Check for untracked files
        if repo.untracked_files:
            console.print("[red]✗[/red] Repository has untracked files.", style="bold")
            console.print("   Add them to git: [cyan]git add .[/cyan] or add to [cyan].gitignore[/cyan]", style="dim")
            raise typer.Exit(code=1)

        # Check sync status with remote
        try:
            console.print("[cyan]→[/cyan] Checking sync status with remote...", style="dim")
            repo.remotes.origin.fetch()
            local_commit = repo.head.commit
            remote_commit = repo.remotes.origin.refs[repo.active_branch.name].commit

            if local_commit != remote_commit:
                console.print("[red]✗[/red] Local branch is not synced with remote.", style="bold")
                console.print("   Push your changes: [cyan]git push[/cyan]", style="dim")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Unable to verify sync status: [dim]{e}[/dim]", style="bold")
            console.print("   Continuing anyway...", style="dim")

        # Detect Git provider
        if 'github.com/' in repo_url:
            provider = 'github'
        elif 'gitlab.com/' in repo_url:
            provider = 'gitlab'
        elif 'forge.mql5.io/' in repo_url:
            provider = 'mql5forge'
        elif 'bitbucket.org/' in repo_url:
            provider = 'bitbucket'
        else:
            console.print(f"[red]✗[/red] Unsupported Git provider.", style="bold")
            console.print(f"   Repository URL: [cyan]{repo_url}[/cyan]", style="dim")
            console.print("   Supported providers: GitHub, GitLab, MQL5 Forge, Bitbucket", style="dim")
            raise typer.Exit(code=1)

        # Check if logged in
        token = keyring.get_password(CREDENTIALS_SERVICE, provider)
        if not token:
            console.print(f"[red]✗[/red] Not logged in to [cyan]{provider}[/cyan].", style="bold")
            console.print(f"   Login first: [cyan]kp-mt login {provider}[/cyan]", style="dim")
            raise typer.Exit(code=1)

        # Validate manifest fields
        if not all([manifest.organization, manifest.name, manifest.description]):
            console.print("[red]✗[/red] Incomplete manifest.", style="bold")
            console.print("   Required fields: [yellow]organization[/yellow], [yellow]name[/yellow], [yellow]description[/yellow]", style="dim")
            raise typer.Exit(code=1)

        # Get commit hash
        commit_hash = get_current_commit_hash(repo)

        # Prepare payload
        payload = {
            "organization": manifest.organization,
            "name": manifest.name,
            "target": manifest.target,
            "description": manifest.description,
            "version": manifest.version,
            "repo_url": repo_url,
            "commit_hash": commit_hash,
            "is_private": False,
            "dependencies": manifest.dependencies
        }

        # Display package info
        console.print()
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="cyan bold", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("Package:", f"[green bold]{manifest.target}[/green bold] @{manifest.organization}/{manifest.name}")
        info_table.add_row("Version:", f"[yellow]{manifest.version}[/yellow]")
        info_table.add_row("Commit:", f"[dim]{commit_hash[:12]}[/dim]")
        info_table.add_row("Repository:", f"[dim]{repo_url}[/dim]")

        console.print(Panel(info_table, title="[bold]📦 Publishing Package[/bold]", border_style="cyan"))

        # Send publish request
        async def send_publish_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{REGISTRY_URL}/packages/",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"}
                )
                return response

        with console.status("[cyan]Uploading to registry...", spinner="dots"):
            response = asyncio.run(send_publish_request())

        # Handle response
        if response.status_code == 201:
            console.print()
            console.print("[green]✓[/green] [bold green]Package published successfully![/bold green]")

            response_data = response.json()
            if "package" in response_data:
                pkg = response_data["package"]
                console.print()
                console.print(f"   [cyan]→[/cyan] View at: [link]https://registry.knitpkg.dev/packages/{pkg['target']}/@{pkg['organization']}/{pkg['name']}[/link]")

            console.print()
        else:
            console.print()
            try:
                error_data = response.json()

                # Handle validation errors (422)
                if response.status_code == 422 and isinstance(error_data, list):
                    console.print("[red]✗[/red] [bold]Validation errors:[/bold]")
                    for error in error_data:
                        field = " → ".join(str(x) for x in error.get("loc", []))
                        msg = error.get("msg", "Unknown error")
                        console.print(f"   [yellow]{field}[/yellow]: {msg}")
                else:
                    error_detail = error_data.get("detail", "Unknown error")
                    console.print(f"[red]✗[/red] [bold]Failed to publish package[/bold]")
                    console.print(f"   {error_detail}")
            except:
                console.print(f"[red]✗[/red] [bold]HTTP {response.status_code}[/bold]: Failed to publish package")

            console.print()
            raise typer.Exit(code=1)
