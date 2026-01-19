# knitpkg/commands/register.py
from typing import Optional
import typer
from pathlib import Path
import git
import httpx
import json
from rich.console import Console

from knitpkg.core.console import ConsoleAware
from knitpkg.core.registry import Registry
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.core.exceptions import KnitPkgError
from knitpkg.core.models import KnitPkgManifest
from knitpkg.mql.models import MQLKnitPkgManifest
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.utils import is_local_path

class RegisterProject(ConsoleAware):
    """
    Encapsulates the comprehensive steps required to register a project in the registry.
    This class handles local Git repository validations, manifest loading, tag creation,
    and delegates the final registration to the `Registry` service. It ensures that
    projects meet pre-registration criteria before attempting to publish.

    It inherits from `ConsoleAware` to provide consistent console output.
    """

    def __init__(self, project_path: Path, registry_service: Registry, console=None, verbose:bool=False):
        """
        Initializes the RegisterProject command with an optional Rich Console instance.
        """
        super().__init__(console, verbose)
        self.registry_service: Registry = registry_service
        self.project_root: str = str(project_path.resolve())
        self.project_path: Path = project_path
        self.repo: git.Repo = git.Repo(self.project_root)
        self.manifest: Optional[KnitPkgManifest] = None
        self.current_commit_hash: Optional[str] = None
        self.remote_url: Optional[str] = None

    def _load_manifest_and_initialize_repo(self):
        """
        Loads and validates the manifest file. Initializes Git repository.
        """
        self.log(f"📦 Loading manifest...")
        try:
            self.manifest = load_knitpkg_manifest(self.project_path, manifest_class=MQLKnitPkgManifest)
            self.log("✔ Manifest loaded successfully.")
        except Exception as e:
            self.print(f"[bold red]✖ Error loading manifest:[/bold red] {e}")
            raise KnitPkgError(f"Failed to load manifest: {e}")

        try:
            self.repo = git.Repo(self.project_root)
            self.log("✔ Directory is a Git repository.")
        except git.InvalidGitRepositoryError:
            raise KnitPkgError(f"The directory '{self.project_root}' is not a Git repository. "
                               "KnitPkg requires projects to be managed by Git for registration.")
        except Exception as e:
            raise KnitPkgError(f"Failed to initialize Git repository: {e}")

    def _validate_manifest_fields(self):
        """
        Validates specific fields within the loaded manifest.
        """
        if not self.manifest:
            raise KnitPkgError("Manifest not loaded. Cannot validate fields.")

        self.log("🔍 Validating manifest fields...")
        # Normalizar nomes de pacotes para minúsculas e impedir publicação se dependências usarem caminhos locais
        if self.manifest.name != self.manifest.name.lower():
            raise KnitPkgError(f"Package name '{self.manifest.name}' must be lowercase. Please update your manifest.")
        
        if not self.manifest.organization:
            raise KnitPkgError("Manifest must specify an 'organization' field.")
        
        if self.manifest.organization != self.manifest.organization.lower():
            raise KnitPkgError(f"Organization name '{self.manifest.organization}' must be lowercase. Please update your manifest.")

        for dep_name, dep_spec in self.manifest.dependencies.items():
            if is_local_path(dep_spec):
                raise KnitPkgError(f"Dependency '{dep_name}' uses a local path. Local path dependencies are not allowed for registration. Please specify a registered version.")
        self.log("✔ Manifest name and dependencies validated.")

    def _check_for_remote_origin(self):
        """
        Checks if the Git repository has a remote named 'origin'.
        """
        if not self.repo:
            raise KnitPkgError("Git repository not initialized.")

        self.log("🔍 Checking for remote 'origin'...")
        try:
            self.remote_url = self.repo.remotes.origin.url
            self.log(f"✔ Remote 'origin' found: [bold blue]{self.remote_url}[/bold blue]")
        except AttributeError:
            raise KnitPkgError("No remote 'origin' found for this Git repository. "
                               "A remote 'origin' is required to link your project to a source control host.")

    def _check_for_uncommitted_changes(self):
        """
        Checks if there are any uncommitted changes in the Git repository.
        """
        if not self.repo:
            raise KnitPkgError("Git repository not initialized.")

        self.log("🔍 Checking for uncommitted changes...")
        if self.repo.is_dirty(untracked_files=True):
            raise KnitPkgError("You have uncommitted changes or untracked files in your Git repository. "
                               "Please commit or stash your changes before registering your project.")
        self.log("✔ No uncommitted changes or untracked files detected.")

    def _check_sync_status_with_remote(self):
        """
        Checks if the local branch is in sync with its remote tracking branch.
        """
        if not self.repo:
            raise KnitPkgError("Git repository not initialized.")

        self.log("🔍 Checking sync status with remote...")
        try:
            # Fetch to ensure local remote-tracking branches are up-to-date
            self.repo.remotes.origin.fetch()

            active_branch = self.repo.active_branch
            if not active_branch.tracking_branch():
                raise KnitPkgError(f"Local branch '{active_branch.name}' is not tracking a remote branch. "
                                   "Please set an upstream branch (e.g., 'git push -u origin {active_branch.name}') "
                                   "before registering your project.")

            local_commit = active_branch.commit
            remote_commit = self.repo.remotes.origin.refs[self.repo.active_branch.name].commit

            if local_commit != remote_commit:
                raise KnitPkgError(f"Local branch '{active_branch.name}' is not in sync with its remote tracking branch. "
                                   "Please push your local commits or pull remote changes before registering.")
            self.log("✔ Local branch is in sync with remote.")
        except Exception as e:
            raise KnitPkgError(f"Failed to check sync status with remote: {e}")

    def get_current_commit_hash(self) -> str:
        """
        Gets the current commit hash of the Git repository.
        This method is now part of RegisterProject.
        """
        if not self.repo:
            raise KnitPkgError("Git repository not initialized.")
        self.current_commit_hash = self.repo.head.commit.hexsha
        self.log(f"✔ Current commit hash: [bold cyan]{self.current_commit_hash}[/bold cyan]")
        return self.current_commit_hash

    def create_and_push_tag(self, tag_name: str):
        """
        Creates a new Git tag and pushes it to the remote origin.
        This method is now part of RegisterProject.
        """
        if not self.repo:
            raise KnitPkgError("Git repository not initialized.")
        if not self.manifest:
            raise KnitPkgError("Manifest not loaded. Cannot create tag.")

        self.log(f"🏷️ Creating and pushing Git tag '[bold magenta]{tag_name}[/bold magenta]'...")
        try:
            # Check if tag already exists locally or remotely
            if tag_name in self.repo.tags:
                self.log(f"ℹ️ Tag '{tag_name}' already exists locally. Skipping creation.")
            else:
                self.repo.create_tag(tag_name, message=f"Reserved for KnitPkg Registry use")
                self.log(f"✔ Tag '{tag_name}' created locally.")

            # Push the tag
            self.repo.remotes.origin.push(tag_name)
            self.log(f"✔ Tag '[bold magenta]{tag_name}[/bold magenta]' pushed to remote origin.")
        except git.GitCommandError as e:
            raise KnitPkgError(f"Failed to create or push Git tag: {e.stderr.strip()}")
        except Exception as e:
            raise KnitPkgError(f"An unexpected error occurred during tag operation: {e}")

    def _display_project_info(self):
        """
        Displays key project information before final registration.
        """
        if not self.manifest:
            raise KnitPkgError("Manifest not loaded. Cannot display project info.")

        self.print("\n--- Project Information for Registration ---")
        self.print(f"  [bold]Name:[/bold] {self.manifest.name}")
        self.print(f"  [bold]Version:[/bold] {self.manifest.version}")
        self.print(f"  [bold]Description:[/bold] {self.manifest.description or 'N/A'}")
        self.print(f"  [bold]Author:[/bold] {self.manifest.author or 'N/A'}")
        self.print(f"  [bold]License:[/bold] {self.manifest.license or 'N/A'}")
        self.print(f"  [bold]Target:[/bold] {self.manifest.target or 'N/A'}")
        self.print(f"  [bold]Git Remote:[/bold] {self.remote_url}")
        self.print(f"  [bold]Commit Hash:[/bold] {self.current_commit_hash}")
        self.print("------------------------------------------\n")


    def run(self, is_private: bool):
        """
        Main entry point for the project registration process.

        This method orchestrates all steps:
        1. Validates the project directory and initializes Git.
        2. Loads the manifest.
        3. Validates Git repository state (remote, uncommitted changes, sync status).
        4. Gets the current commit hash.
        5. Creates and pushes a Git tag.
        6. Validates manifest fields.
        7. Displays project information.
        8. Delegates the final registration to the `Registry` service.

        Args:
            manifest_path (str): The file path to the knitpkg.json/yaml manifest.
            user (User): The authenticated user attempting to register the project.
            is_private (bool): Flag indicating if the project should be registered as private.
            organization_name (Optional[str]): The name of the organization if registering a private project.

        Returns:
            Project: The newly registered project object.

        Raises:
            KnitPkgError: If any step in the registration process fails.
        """
        try:
            self.log(f"Starting registration process for project at '{self.project_root}'...")


            # Step 1: Validate project directory and initialize Git
            self._load_manifest_and_initialize_repo()
            if not self.manifest: # Should not happen if _load_manifest raises on error
                raise KnitPkgError("Manifest could not be loaded.")

            # Step 2: Validate Git repository (remote origin, uncommitted changes, sync status)
            self._check_for_remote_origin()
            self._check_for_uncommitted_changes()
            self._check_sync_status_with_remote()

            # Step 3: Create and push tag (NEW SAFETY LAYER)
            commit_hash = self.get_current_commit_hash()
            self.create_and_push_tag(f'knitpkg-registry/{commit_hash[:16]}')

            # Step 4: Validate manifest fields (e.g., lowercase name, no local path dependencies)
            self._validate_manifest_fields()

            # Step 5: Display project info
            self._display_project_info()

            # Step 6: Delegate registration to the registry service
            self.log("🚀 Initiating project registration with the registry service...")
            payload = {
                "organization": self.manifest.organization,
                "name": self.manifest.name,
                "target": self.manifest.target,
                "type": self.manifest.type,
                "description": self.manifest.description,
                "version": self.manifest.version,
                "repo_url": self.remote_url,
                "commit_hash": commit_hash,
                "dependencies": self.manifest.dependencies,
                "is_private": is_private
            }

            
            response_data = self.registry_service.register(payload)
            if "message" in response_data:
                self.print(f"✅  [bold green]{response_data['message']}[/bold green]")
            else:
                self.print("✅  [bold green]Project registered successfully![/bold green]")
            if "project" in response_data:
                pkg = response_data["project"]
                self.print(pkg)

            return response_data
        except httpx.HTTPStatusError as e:
            try:
                error_data = json.loads(e.response.text)
                detail = error_data.get("detail", str(e))
                self.print(f"[red]✗[/red] Failed to register project: {detail}")
            except (json.JSONDecodeError, AttributeError):
                self.print(f"[red]✗[/red] Failed to register project: {e}")
            raise typer.Exit(code=1)
        except KnitPkgError as e:
            self.print(f"[bold red]✖ Registration failed:[/bold red] {e}")
            raise
        except Exception as e:
            self.print(f"[bold red]✖ An unexpected error occurred during registration:[/bold red] {e}")
            raise


def register(app):
    """Register the register command with the main Typer app."""

    @app.command()
    def register(
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
        """Register the current project to the KnitPkg registry."""

        project_path = Path(project_dir).resolve() if project_dir else Path.cwd()

        console: Console = Console(log_path=verbose) # type: ignore

        registry_url = get_registry_url()
        registry: Registry = Registry(registry_url, console=console, verbose=verbose) # type: ignore

        register: RegisterProject = RegisterProject(project_path, registry, console, True if verbose else False)
        register.run(is_private=False)
