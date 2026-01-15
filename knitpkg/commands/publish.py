# knitpkg/commands/publish.py

"""
KnitPkg for MetaTrader publish command — publishes a project to the registry.

This module handles the process of validating a local KnitPkg project,
checking its Git status, creating a tag for the commit hash, pushing the tag to remote,
and submitting its metadata to the KnitPkg registry.

It ensures that only clean, committed repositories can be published,
and that the commit is tagged with 'knitpkg-registry/<commit_hash>' to prevent it from becoming orphaned.
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
from knitpkg.core.global_config import get_registry_url
from knitpkg.mql.models import MQLKnitPkgManifest

# Configurations
CREDENTIALS_SERVICE = "knitpkg-mt"

console = Console()


def get_current_commit_hash(repo: git.Repo) -> str:
    """Get the current commit hash from the Git repo."""
    return repo.head.commit.hexsha


def create_and_push_tag(repo: git.Repo, commit_hash: str) -> None:
    """
    Create a tag 'knitpkg-registry/<commit_hash>' pointing to the current commit
    and push it to the remote origin.

    This tag acts as a safeguard to prevent the commit from becoming orphaned
    if the user performs a force-push or rebase.

    Args:
        repo: Git repository object
        commit_hash: The commit hash to tag

    Raises:
        git.GitCommandError: If tag creation or push fails
    """
    tag_name = f"knitpkg-registry/{commit_hash}"

    # Check if tag already exists locally
    try:
        existing_tag = repo.git.tag("-l", tag_name).strip()
        if existing_tag == tag_name:
            console.print(f"[yellow]⚠[/yellow] Tag '{tag_name}' already exists locally.", style="dim")

            # Verify it points to the correct commit
            tag_commit = repo.git.rev_list("-n", "1", tag_name).strip()
            if tag_commit != commit_hash:
                console.print(f"[red]✗[/red] Local tag '{tag_name}' points to wrong commit: {tag_commit[:12]}", style="bold")
                console.print(f"   Expected: {commit_hash[:12]}", style="dim")
                raise git.GitCommandError(f"Tag '{tag_name}' is corrupted")

            # Check if tag is already on remote
            try:
                repo.git.fetch("--tags")
                remote_tags = repo.git.ls_remote("--tags", "origin", f"refs/tags/{tag_name}").strip()
                if remote_tags:
                    console.print(f"[green]✓[/green] Tag '{tag_name}' already exists on remote.", style="dim")
                    return  # Tag already exists locally and remotely, we're good
            except git.GitCommandError:
                pass  # Tag not on remote, proceed to push
        else:
            # Tag name matches but content differs (shouldn't happen, but handle it)
            console.print(f"[yellow]⚠[/yellow] Deleting corrupted local tag '{tag_name}'...", style="dim")
            repo.git.tag("-d", tag_name)
    except git.GitCommandError:
        pass  # Tag doesn't exist, proceed to create

    # Create the tag locally
    try:
        repo.create_tag(tag_name, ref=commit_hash)
        console.print(f"[green]✓[/green] Created local tag: [cyan]'{tag_name}'[/cyan]", style="dim")
    except git.GitCommandError as e:
        console.print(f"[red]✗[/red] Failed to create tag '{tag_name}': {e}", style="bold")
        raise git.GitCommandError(f"Cannot create tag: {e}")

    # Push the tag to remote
    try:
        console.print(f"[cyan]→[/cyan] Pushing tag to remote origin...", style="dim")
        repo.git.push("origin", tag_name)
        console.print(f"[green]✓[/green] Tag [cyan]'{tag_name}'[/cyan] pushed to remote.", style="dim")
    except git.GitCommandError as e:
        # Clean up local tag if push fails
        try:
            repo.git.tag("-d", tag_name)
            console.print(f"[yellow]⚠[/yellow] Cleaned up local tag after push failure.", style="dim")
        except:
            pass

        console.print(f"[red]✗[/red] Failed to push tag to remote: {e}", style="bold")
        console.print("   [dim]Cannot publish without remote tag (prevents orphaned commits)[/dim]")
        raise git.GitCommandError(f"Tag push failed: {e}")


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
            manifest = load_knitpkg_manifest(project_path, manifest_class=MQLKnitPkgManifest)
        except FileNotFoundError:
            console.print("[red]✗[/red] [bold]knitpkg.yaml[/bold] not found in project directory.", style="bold")
            console.print("   Run [cyan]kp-mt init[/cyan] to create a new project.", style="dim")
            raise typer.Exit(code=1)
        except ValueError as e:
            console.print(f"[red]✗[/red] Error loading manifest: [yellow]{e}[/yellow]", style="bold")
            raise typer.Exit(code=1)

        # Validate Git repository
        try:
            repo = git.Repo(project_path, search_parent_directories=True)
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
        except typer.Exit as e:
            raise e
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Unable to verify sync status: [dim]{e}[/dim]", style="bold")
            console.print("   Halting...", style="dim")
            raise typer.Exit(code=1)

        # Get commit hash
        commit_hash = get_current_commit_hash(repo)

        # ============================================================================
        # CREATE AND PUSH TAG (NEW SAFETY LAYER)
        # ============================================================================
        try:
            console.print(f"\n[cyan]→[/cyan] Creating registry tag for commit [yellow]{commit_hash[:12]}[/yellow]...", style="dim")
            create_and_push_tag(repo, commit_hash)
        except git.GitCommandError as e:
            console.print(f"\n[red]✗[/red] [bold]Failed to create/push tag[/bold]", style="bold")
            console.print(f"   {e}", style="dim")
            console.print("\n   [yellow]Cannot publish without remote tag (prevents orphaned commits)[/yellow]")
            raise typer.Exit(code=1)

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
            console.print(f"\n[red]✗[/red] Not logged in to [cyan]{provider}[/cyan].", style="bold")
            console.print(f"   Login first: [cyan]kp-mt login --provider {provider}[/cyan]", style="dim")
            raise typer.Exit(code=1)

        # Validate manifest fields
        if not all([manifest.organization, manifest.name, manifest.description]):
            console.print("[red]✗[/red] Incomplete manifest.", style="bold")
            console.print("   Required fields: [yellow]organization[/yellow], [yellow]name[/yellow], [yellow]description[/yellow]", style="dim")
            raise typer.Exit(code=1)

        # Prepare payload
        payload = {
            "organization": manifest.organization,
            "name": manifest.name,
            "target": manifest.target,
            "type": manifest.type,
            "description": manifest.description,
            "version": manifest.version,
            "repo_url": repo_url,
            "commit_hash": commit_hash,
            "dependencies": manifest.dependencies,
            "is_private": False
        }

        # Display project info
        console.print()
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="cyan bold", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("Project:", f"[green bold]{manifest.target.value}[/green bold]:@{manifest.organization}/{manifest.name}")
        info_table.add_row("Type:", f"[yellow]{manifest.type.value}[/yellow]")
        info_table.add_row("Version:", f"[yellow]{manifest.version}[/yellow]")
        info_table.add_row("Commit:", f"[dim]{commit_hash[:12]}[/dim]")
        info_table.add_row("Repository:", f"[dim]{repo_url}[/dim]")
        info_table.add_row("Provider:", f"[dim]{provider}[/dim]")

        console.print(Panel(info_table, title="[bold]📦 Publishing Project[/bold]", border_style="cyan"))

        registry_url = get_registry_url()
        # Send publish request
        async def send_publish_request():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{registry_url}/project/publish",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"}
                )
                return response

        with console.status("[cyan]Uploading to registry...", spinner="dots"):
            response = asyncio.run(send_publish_request())

        # Handle response
        if response.status_code == 201:
            console.print()
            console.print("[green]✓[/green] [bold green]Project published successfully![/bold green]")

            response_data = response.json()
            if "project" in response_data:
                pkg = response_data["project"]
                console.print()
                # TODO resolver mensagem abaixo
                console.print(f"   [cyan]→[/cyan] View at: [link]https://registry.knitpkg.dev/packages/{pkg['target']}/@{pkg['organization']}/{pkg['name']}[/link]")

            console.print()
        else:
            console.print()
            try:
                error_data = response.json()

                # Handle validation errors (422)
                if response.status_code == 422:
                    if isinstance(error_data, dict) and "detail" in error_data:
                        # FastAPI validation error format
                        detail = error_data["detail"]
                        if isinstance(detail, list):
                            console.print("[red]✗[/red] [bold]Validation errors:[/bold]")
                            for error in detail:
                                field = " → ".join(str(x) for x in error.get("loc", []))
                                msg = error.get("msg", "Unknown error")
                                console.print(f"   [yellow]{field}[/yellow]: {msg}")
                        else:
                            console.print(f"[red]✗[/red] [bold]Validation error:[/bold] {detail}")
                    else:
                        console.print(f"[red]✗[/red] [bold]Validation error[/bold]")
                        console.print(f"   {error_data}")
                else:
                    # Other errors
                    error_detail = error_data.get("detail", "Unknown error")
                    console.print(f"[red]✗[/red] [bold]Failed to publish project[/bold]")
                    console.print(f"   {error_detail}")
            except:
                console.print(f"[red]✗[/red] [bold]HTTP {response.status_code}[/bold]: Failed to publish project")
                console.print(f"   {response.text[:200]}")

            console.print()
            raise typer.Exit(code=1)
