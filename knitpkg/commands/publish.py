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
from rich.console import Console # Import Console for colored output

from .login import REGISTRY_URL, CREDENTIALS_SERVICE
from knitpkg.core.file_reading import load_helix_manifest # Renamed to load_knitpkg_manifest if applicable

# Initialize Typer app (if this file is meant to be a standalone Typer app, otherwise remove)
# app = typer.Typer() # This line might be redundant if 'register' function is used to add command to a main app

def register(app):
    """Register the publish command with the main Typer app."""

    @app.command()
    def publish(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """
        Publishes the current KnitPkg project to the registry.

        This command performs several checks:
        1. Validates the project directory and manifest file.
        2. Ensures the project is a clean Git repository (no uncommitted changes, no untracked files).
        3. Verifies that local changes are synced with the remote origin.
        4. Determines the Git provider (GitHub, GitLab, MQL5Forge, Bitbucket).
        5. Checks for an active login token for the identified provider.
        6. Extracts package metadata from the manifest.
        7. Sends the package metadata and commit hash to the KnitPkg registry.
        """
        console = Console(log_path=verbose) # Initialize Console for colored output

        project_path = Path(project_dir) if project_dir else Path.cwd()
        if not project_path.is_dir():
            console.log(f"[red]Error:[/] Project directory '[cyan]{project_dir}[/]' not found.")
            raise typer.Exit(code=1)

        try:
            # Assuming load_helix_manifest will be renamed to load_knitpkg_manifest eventually
            manifest = load_helix_manifest(project_path)
        except FileNotFoundError:
            console.log("[red]Error:[/] KnitPkg manifest file (e.g., knitpkg.yaml) not found in the project directory.")
            raise typer.Exit(code=1)
        except ValueError as e:
            console.log(f"[red]Error:[/] Invalid manifest file: {e}")
            raise typer.Exit(code=1)

        try:
            repo = git.Repo(project_path, search_parent_directories=True)
            if repo.bare:
                console.log("[red]Error:[/] Not a valid Git repository. Initialize Git or run from a Git repository.")
                raise typer.Exit(code=1)
        except git.InvalidGitRepositoryError:
            console.log("[red]Error:[/] Not a valid Git repository. Initialize Git or run from a Git repository.")
            raise typer.Exit(code=1)


        repo_url = None
        if repo.remotes:
            try:
                repo_url = repo.remotes.origin.url
            except Exception:
                pass # Will be handled by the check below

        if not repo_url:
            console.log("[red]Error:[/] Git remote 'origin' URL not found. Please configure your remote origin.")
            raise typer.Exit(code=1)

        if repo.is_dirty(untracked_files=True): # Check for both dirty and untracked files in one go
            console.log("[red]Error:[/] There are uncommitted changes or untracked files in the repository. Please commit or stash them before publishing.")
            raise typer.Exit(code=1)

        # Check for pending changes with remote
        try:
            console.log("[bold yellow]Checking remote synchronization...[/]")
            repo.remotes.origin.fetch()
            local_commit = repo.head.commit
            remote_commit = repo.remotes.origin.refs[repo.active_branch.name].commit
            if local_commit != remote_commit:
                console.log("[red]Error:[/] There are pending changes to sync with the remote repository. Please push your local commits.")
                raise typer.Exit(code=1)
            console.log("[green]Repository is synchronized with remote.[/]")
        except Exception as e:
            console.log(f"[red]Error:[/] Unable to verify sync status with remote repository: {e}. Ensure you have network access and the remote is reachable.")
            raise typer.Exit(code=1)

        provider = None
        if 'github.com/' in repo_url:
            provider = 'github'
        elif 'gitlab.com/' in repo_url:
            provider = 'gitlab'
        elif 'forge.mql5.io/' in repo_url:
            provider = 'mql5forge'
        elif 'bitbucket.org/' in repo_url:
            provider = 'bitbucket'
        else:
            console.log(f"[red]Error:[/] Unsupported Git provider. Only GitHub, GitLab, Bitbucket, and MQL5Forge are currently supported. Remote URL: [cyan]{repo_url}[/]")
            raise typer.Exit(code=1)

        # Check if logged in
        token = keyring.get_password(CREDENTIALS_SERVICE, provider)
        if not token:
            console.log(f"[red]Error:[/] You need to log in to your [cyan]{provider.capitalize()}[/] account first. Run `kp login --provider {provider}`.")
            raise typer.Exit(code=1)

        # Extract required fields from manifest
        # Assuming manifest attributes are directly accessible or via a method
        org_name = getattr(manifest, 'organization', None)
        name = getattr(manifest, 'name', None)
        description = getattr(manifest, 'description', None)
        version = getattr(manifest, 'version', None) # Added version as it's crucial for packages

        missing_fields = []
        if not org_name: missing_fields.append("organization")
        if not name: missing_fields.append("name")
        if not description: missing_fields.append("description")
        if not version: missing_fields.append("version")

        if missing_fields:
            console.log(f"[red]Error:[/] Incomplete manifest. The following fields are mandatory: [yellow]{', '.join(missing_fields)}[/].")
            raise typer.Exit(code=1)

        commit_hash = repo.head.commit.hexsha

        # Prepare payload
        payload = {
            "org_name": org_name,
            "name": name,
            "description": description,
            "version": version, # Include version in payload
            "repo_url": repo_url,
            "commit_hash": commit_hash
        }

        console.log(f"[bold magenta]Publishing[/] package [cyan]@{org_name}/{name} v{version}[/] with commit [yellow]{commit_hash[:7]}[/]...")

        # Async POST to /packages
        async def send_publish_request():
            """Sends the package metadata to the KnitPkg registry."""
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{REGISTRY_URL}/packages/",
                        json=payload,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    response.raise_for_status() # Raise an exception for bad status codes
                    return response
                except httpx.HTTPStatusError as e:
                    console.log(f"[red]Error:[/] HTTP error during publish: {e.response.status_code} - {e.response.text}")
                    raise typer.Exit(code=1)
                except httpx.RequestError as e:
                    console.log(f"[red]Error:[/] Network error during publish request: {e}")
                    raise typer.Exit(code=1)

        response = asyncio.run(send_publish_request())

        if response.status_code == 200 or response.status_code == 201: # 201 Created is also a success for new resources
            console.log("[bold green]Package published successfully![/]")
            console.log(response.json())
        else:
            error_detail = response.json().get("detail", "Unknown error")
            console.log(f"[red]Error:[/] Failed to publish package: {response.status_code} - {error_detail}")
            raise typer.Exit(code=1)

