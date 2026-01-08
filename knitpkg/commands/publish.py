import typer
import httpx
import asyncio
import keyring
from typing import Optional
import git
from pathlib import Path

from knitpkg.core.file_reading import load_helix_manifest

app = typer.Typer()

# Configurations (pull from .env or config; adjust for production)
REGISTRY_URL = "http://localhost:8000"  # Registry base URL
CREDENTIALS_SERVICE = "knitpkg-mt"  # Same as in login

def register(app):
    """Register the publish command with the Typer app."""

    @app.command()
    def publish(project_dir: Optional[Path] = typer.Option(
                None,
                "--project-dir",
                "-d",
                help="Project directory (default: current directory)"
            ),
        ):
        """Publish the current project into the registry."""

        project_path = Path(project_dir) if project_dir else Path.cwd()
        if not project_path.is_dir():
            typer.echo(f"Project dir {project_dir} not found.")
            raise typer.Exit(code=1)

        try:
            manifest = load_helix_manifest(project_path)
        except FileNotFoundError:
            typer.echo("Manifest file not found.")
            raise typer.Exit(code=1)
        except ValueError as e: 
            typer.echo(f"Error loading manifest: {e}")
            raise typer.Exit(code=1)
        
        repo = git.Repo(Path.cwd(), search_parent_directories=True)
        if repo.bare:
            typer.echo("Error: Not a git repository.")
            raise typer.Exit(code=1)
        
        repo_url = repo.remotes.origin.url
        if not repo_url:
            typer.echo("Error: Remote origin URL not found.")
            raise typer.Exit(code=1)
        
        if repo.is_dirty():
            typer.echo("Error: There are uncommitted changes in the repository.")
            raise typer.Exit(code=1)
        
        if repo.untracked_files:
            typer.echo("Error: There are untracked files in the repository.")
            raise typer.Exit(code=1)
        
        # Check for pending changes with remote
        try:
            repo.remotes.origin.fetch()
            local_commit = repo.head.commit
            remote_commit = repo.remotes.origin.refs[repo.active_branch.name].commit
            if local_commit != remote_commit:
                typer.echo("Error: There are pending changes to sync with the remote repository.")
                raise typer.Exit(code=1)
        except Exception:
            typer.echo("Error: Unable to verify sync status with remote repository.")
            raise typer.Exit(code=1)
        
        if 'github.com/' in repo_url:
            provider = 'github'
        elif 'gitlab.com/' in repo_url:
            provider = 'gitlab'
        elif 'forge.mql5.io/' in repo_url:
            provider = 'mql5forge'
        else:
            typer.echo(f"Error: Unsupported git provider. Only GitHub, GitLab, and MQL5Forge are supported. Remote URL: {repo_url}")
            raise typer.Exit(code=1)

        # Check if logged in
        token = keyring.get_password(CREDENTIALS_SERVICE, provider)
        if not token:
            typer.echo(f"You need to login to your git provider first. Run `kp-mt login {provider}`.")
            raise typer.Exit(code=1)

        # Extract required fields (adjust keys if your manifest differs)
        org_name = manifest.organization
        name = manifest.name
        description = manifest.description

        if not all([org_name, name, description]):
            typer.echo("Incomplete manifest: organization, name and description are mandatory.")
            raise typer.Exit(code=1)

        commit_hash = repo.head.commit.hexsha

        # Prepare payload
        payload = {
            "org_name": org_name,
            "name": name,
            "description": description,
            "repo_url": repo_url,
            "commit_hash": commit_hash
        }

        typer.echo(f"Publishing @{org_name}/{name} with commit {commit_hash}...")

        # Async POST to /packages
        async def send_publish_request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{REGISTRY_URL}/packages/",
                    json=payload,
                    params={"provider": provider},
                    headers={"Authorization": f"Bearer {token}"}
                )
                return response

        response = asyncio.run(send_publish_request())

        if response.status_code == 200:
            typer.echo("Package published successfully!")
            typer.echo(response.json())
        else:
            error_detail = response.json().get("detail", "Unknown error")
            typer.echo(f"Error: {response.status_code} - {error_detail}")
            raise typer.Exit(code=1)
