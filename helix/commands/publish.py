import typer
import httpx
import asyncio
import subprocess
import os
import keyring
from typing import Optional
import git
from pathlib import Path

from helix.core.file_reading import load_helix_manifest

app = typer.Typer()

# Configurations (pull from .env or config; adjust for production)
REGISTRY_URL = "http://localhost:8000"  # Registry base URL
CREDENTIALS_SERVICE = "helix-mt"  # Same as in login
DEFAULT_PROVIDER = "github"  # Default provider

def get_stored_token(provider: str) -> Optional[str]:
    """Retrieve stored token from keyring."""
    return keyring.get_password(CREDENTIALS_SERVICE, provider)

def get_current_commit_hash() -> str:
    """Get the current commit hash from the local Git repo."""
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        raise typer.BadParameter("Não foi possível obter o commit hash. Certifique-se de estar em um repositório Git.")

def register(app):
    """Register the login command with the Typer app."""

    @app.command()
    def publish(manifest_path: str = typer.Option("helix.yaml", "--manifest", help="Caminho para o arquivo helix.yaml")):
        """Publish the current project into the registry."""
        # Check if logged in
        token = get_stored_token(DEFAULT_PROVIDER)
        if not token:
            typer.echo("You need to login to your git provider first. Run `helix-mt login`.")
            raise typer.Exit(code=1)

        # Load manifest
        if not os.path.exists(manifest_path):
            typer.echo(f"Manifest file {manifest_path} not found.")
            raise typer.Exit(code=1)

        manifest = load_helix_manifest(Path.cwd())

        repo = git.Repo(Path.cwd(), search_parent_directories=True)
        if repo.bare:
            typer.echo("Error: Not a git repository.")
            raise typer.Exit(code=1)
        
        repo_url = repo.remotes.origin.url
        if not repo_url:
            typer.echo("Error: Remote origin URL not found.")
            raise typer.Exit(code=1)

        # Extract required fields (adjust keys if your manifest differs)
        org_name = manifest.organization
        name = manifest.name
        description = manifest.description

        if not all([org_name, name, description]):
            typer.echo("Incomplete manifest: organization and name are mandatory.")
            raise typer.Exit(code=1)

        commit_hash = get_current_commit_hash()

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
                    f"{REGISTRY_URL}/packages",
                    json=payload,
                    params={"provider": DEFAULT_PROVIDER},
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
