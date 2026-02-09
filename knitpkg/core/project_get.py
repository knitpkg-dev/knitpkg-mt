from typing import Optional, TypeVar
from pathlib import Path
import git

from knitpkg.core.console import Console, ConsoleAware
from knitpkg.core.registry import Registry
from knitpkg.core.models import KnitPkgManifest
from knitpkg.core.resolve_helper import parse_project_name, normalize_dep_name
from knitpkg.core.exceptions import InvalidUsageError, KnitPkgError, GitCloneError, GitCommitNotFoundError
from knitpkg.core.version_handling import validate_version_specifier
from knitpkg.mql.models import MQLProjectType
from knitpkg.mql.models import MQLKnitPkgManifest
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.mql.autocomplete import AutocompleteTools
from knitpkg.mql.install import ProjectInstaller
from knitpkg.mql.compile import MQLProjectCompiler
from git.exc import GitCommandError
from knitpkg.mql.settings import MQLSettings
from knitpkg.mql.models import Target

T = TypeVar('T', bound=KnitPkgManifest)

class ProjectGet(ConsoleAware):
    
    def __init__(self, registry: Registry, console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console, verbose)
        self.registry: Registry = registry

    def get_project(self, target: str, proj_specifier: str, verspec: Optional[str], mql_target_folder: Path):
        self.log(f"Getting project data → {proj_specifier} : {verspec} into {mql_target_folder}")

        if not verspec:
            verspec = "*"
        else:
            if not validate_version_specifier(verspec):
                raise InvalidUsageError(f'Invalid version specifier: `{verspec}`')
        
        org, name = parse_project_name(proj_specifier.lower())
        if not org:
            org: str = manifest.get('organization') # type: ignore
            org = org.lower()

        dep_info = self.registry.resolve_package(target, org, name, verspec)

        project_type = dep_info.get('type')
        if not project_type:
            raise KnitPkgError("Registry did not return a project type for the package.")
        project_dir: Optional[Path] = {
            MQLProjectType.PACKAGE.value: mql_target_folder / 'Scripts',
            MQLProjectType.INDICATOR.value: mql_target_folder / 'Indicators',
            MQLProjectType.EXPERT.value: mql_target_folder / 'Experts',
            MQLProjectType.SCRIPT.value: mql_target_folder / 'Scripts',
            MQLProjectType.LIBRARY.value: mql_target_folder / 'Libraries',
            MQLProjectType.SERVICE.value: mql_target_folder / 'Services',
        }.get(project_type)

        if not project_dir:
            raise InvalidUsageError(f"Unsupported target: {target}")
        
        if not project_dir.exists():
            raise KnitPkgError(f"Invalid MQL target folder: {project_dir}")
        
        project_dir = project_dir / name
        if project_dir.exists():
            raise KnitPkgError(f"Project directory already exists: {project_dir}")
        
        resolved_version = dep_info.get('resolved_version')
        if not resolved_version:
            dep_spec_normalized = normalize_dep_name(name, org)
            raise InvalidUsageError(f"Could not resolve to any version `{verspec}` for package {dep_spec_normalized}")
        self.log(f"Resolved {proj_specifier} to version {resolved_version}")

        commit_hash = dep_info.get('commit_hash')
        if not commit_hash:
            raise KnitPkgError("Registry did not return a commit hash for the package.")

        repo_url = dep_info.get('repo_url')
        if not repo_url:
            raise KnitPkgError("Registry did not return a repository URL for the package.")
                
        project_dir.mkdir(parents=True, exist_ok=True)

        
        self.log(f"Cloning project...")
        try:
            repo = git.Repo.clone_from(repo_url, project_dir)
        except GitCommandError as e:
            if 'forge.mql5.io/' in repo_url and 'Retry your command' in e.stderr and e.status==128:
                try:
                    repo = git.Repo.clone_from(repo_url, project_dir)
                except Exception as e:
                    raise GitCloneError(repo_url, str(e))
            else:
                raise GitCloneError(repo_url, str(e))
        except Exception as e:
            raise GitCloneError(repo_url, str(e))
        
        try:
            repo.git.checkout(commit_hash)
        except Exception as e:
            raise GitCommitNotFoundError(commit_hash, str(e))
        
        settings: MQLSettings = MQLSettings(project_dir)
        settings.set_data_folder_path(str(mql_target_folder.parent), Target(target))
        
        self.print(f"[green]✓[/] Got [bold]{proj_specifier}[/] : {resolved_version}\n")

        manifest: MQLKnitPkgManifest = load_knitpkg_manifest(project_dir, manifest_class=MQLKnitPkgManifest)
        self.print(
            f"🚀 [bold][green]Build[/green] → "
            f"[cyan]@{manifest.organization}/{manifest.name}[/cyan] : {manifest.version}[/bold]"
            )

        # Execute commands based on project type
        project_type = MQLProjectType(manifest.type) # Assumes `manifest.type` is an Enum and has `.value`
        if project_type == MQLProjectType.PACKAGE:
            self.print("\n[cyan]▶️  Generating autocomplete...[/cyan]")
            generator = AutocompleteTools(project_dir, self.console, self.verbose)
            generator.generate_autocomplete()
        else:
            self.print("\n[cyan]▶️  Installing dependencies...[/cyan]")
            installer = ProjectInstaller(project_dir, True, self.console, self.verbose)
            installer.install(True)

        self.print("\n[cyan]▶️  Compiling project...[/cyan]")
        compiler = MQLProjectCompiler(project_dir, False, self.console, self.verbose)
        compiler.compile(False, False)

        self.print("[bold green]✅ Build completed successfully![/bold green]")        