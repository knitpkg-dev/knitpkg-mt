# knitpkg/core/dependency_downloader.py

"""
Platform-agnostic dependency downloader.

This module handles Git-based dependency resolution, lockfile management,
and recursive dependency trees. Platform-specific validation logic can be
overridden by subclasses.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Any, Dict
from dataclasses import dataclass

import shutil
import git

from knitpkg.core.registry import Registry
from knitpkg.core.lockfile import LockFile
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.core.path_helper import is_local_path
from knitpkg.core.constants import CACHE_DIR
from knitpkg.core.models import ProjectType, KnitPkgManifest
from knitpkg.core.console import ConsoleAware, Console
from knitpkg.core.resolve_helper import normalize_dep_name

# Import custom exceptions
from knitpkg.core.exceptions import (
    DependencyError,
    LocalDependencyNotFoundError,
    LockedWithLocalDependencyError,
    DependencyHasLocalChangesError,
    LocalDependencyManifestError,
    GitCloneError,
    GitCommitNotFoundError,
    KnitPkgError
)

# ==============================================================
# TYPE DEFINITIONS
# ==============================================================

@dataclass
class ProjectNode:
    """Represents a resolved dependency with hierarchy information."""
    name: str
    path: Path
    resolved_path: Path  # Canonical path for deduplication
    version: str
    is_root: bool
    dependencies: List['ProjectNode']
    parent: Optional['ProjectNode'] = None

    def __post_init__(self):
        for child in self.dependencies:
            child.parent = self

    def add_dependency(self, dependency: 'ProjectNode' ):
        """Add a child node and set parent reference."""
        dependency.parent = self
        self.dependencies.append(dependency)

    def is_resolved(self, name: str) -> bool:
        """Check if name is resolved in this node or any children recursively."""
        if name == self.name:
            return True
        return any(child.is_resolved(name) for child in self.dependencies)

    def _collect_post_order(self, add_root: bool, collector_func) -> List[Any]:
        """Visit all children recursively and return objects collected by function, ordered from leafs to root."""
        result = []
        for child in self.dependencies:
            result.extend(child._collect_post_order(add_root, collector_func))
        if not self.is_root or add_root:
            result.append(collector_func(self))
        return result
    
    def resolved_names(self, add_root: bool = False) -> List[str]:
        """Get all resolved dependency names in tree (including self)."""
        return self._collect_post_order(add_root, lambda x: x.name)
    
    def resolved_dependencies(self, add_root: bool = False) -> List[tuple[str, Path]]:
        """Get all resolved canonical paths in tree (including self)."""
        return self._collect_post_order(add_root, lambda x: (x.name, x.resolved_path))

# ==============================================================
# DEPENDENCY DOWNLOADER CLASS
# ==============================================================

class DependencyDownloader(ConsoleAware):
    """
    Platform-agnostic dependency resolver.

    This class handles Git-based dependency resolution, lockfile management,
    and recursive dependency processing. Platform-specific validation can be
    implemented by overriding validate_manifest() and validate_project_structure().

    Raises custom exceptions instead of SystemExit to allow better reusability.

    Attributes:
        console: Rich console for logging
        resolved_deps: List of (name, path) tuples for resolved dependencies
        dependency_tree: Hierarchical tree of dependencies
        resolved_paths: Set of resolved canonical paths (for deduplication)
        locked_mode: Whether to enforce strict lockfile mode
    """

    def __init__(self, project_dir: Path, registry_base_url: str, 
                 locked_mode: bool = False, manifest_type: type[KnitPkgManifest] = KnitPkgManifest,
                 console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console=console, verbose=verbose)
        self.project_dir: Path = project_dir
        self.default_registry_base_url: str = registry_base_url.rstrip('/')
        self.locked_mode: bool = locked_mode
        self.manifest_type: type[KnitPkgManifest] = manifest_type

    def download_all(
        self
    ) -> ProjectNode:
        """
        Download all dependencies and return resolved list and dependency tree.

        Args:
            dependencies: Dict of {name: spec} from manifest
            locked_mode: If True, enforce strict lockfile matching

        Returns:
            Tuple of (resolved_deps, dependency_tree)

        Raises:
            LocalDependencyNotFoundError: Local path does not exist
            LocalDependencyNotGitError: --locked used with non-git local dep
            DependencyHasLocalChangesError: --locked used but dep has changes
        """

        try:
            manifest = load_knitpkg_manifest(self.project_dir, self.manifest_type)
        except Exception as e:
            raise KnitPkgError(f"Failed to load manifest: {e}. Location: {self.project_dir}")

        self._target: str = manifest.target
        dependencies = manifest.dependencies or {}

        root: ProjectNode = ProjectNode(
            name=f"@{manifest.organization.lower()}/{manifest.name.lower()}",
            path=self.project_dir,
            resolved_path=self.project_dir.resolve(),
            version=manifest.version,
            is_root=True,
            dependencies=[]
        )
        self._root_node: ProjectNode = root
        
        overrides: dict[str, str]
        if manifest.overrides:
            overrides = {normalize_dep_name(name, manifest.organization): spec for name, spec in manifest.overrides.items()}
        else:
            overrides = {}

        for name, spec in dependencies.items():
            name = normalize_dep_name(name, manifest.organization)
            self._download_dependency(name, spec, overrides, root)

        return root
    
    def _get_package_resolve_dist(self, registry_base_url: str, dep_name: str, version_spec: str) -> dict:
        """Resolve project distribution info from registry.
        
        Args:
            name: Package name (may include @org/project format)
            version_spec: Version specifier
            
        Returns:
            Dict containing project distribution info
            
        Raises:
            RegistryRequestError: If registry request fails
        """
        org, pack_name = self._parse_project_name(dep_name)

        registry: Registry = Registry(registry_base_url, self.console, self.verbose)
        response_json = registry.resolve_package(self._target, org, pack_name, version_spec)
        project_type = response_json.get('type', None)
        
        if not project_type:
            raise DependencyError(f"Project type not found in registry response for dependency '{dep_name}'.")

        if project_type != ProjectType.PACKAGE.value:
            raise DependencyError(
                f"Unsupported project type '{project_type}' for dependency '{dep_name}'. "
                f"Only 'package' type is supported."
            )
        
        return response_json

    def _clone_shallow_to_commit(self, git_url: str, commit_hash: str, cache_path: Path) -> None:
        """Clone repository shallow to specific commit.
        
        Args:
            git_url: Git repository URL
            commit_hash: Target commit hash
            cache_path: Local path to clone to
            
        Raises:
            GitCloneError: If clone fails
            GitCommitNotFoundError: If commit hash doesn't exist or checkout fails
        """
        try:
            cache_path.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(git_url, cache_path, depth=1, no_checkout=True)
        except Exception as e:
            raise GitCloneError(git_url, str(e))
        
        try:
            repo.git.fetch('origin', commit_hash, depth=1)
            repo.git.checkout(commit_hash)
        except Exception as e:
            raise GitCommitNotFoundError(commit_hash, str(e))

    def _checkout_shallow_to_commit(self, commit_hash: str, cache_path: Path) -> None:
        """Checkout existing repository to specific commit (shallow).
        
        Args:
            commit_hash: Target commit hash
            cache_path: Path to existing git repository
            
        Raises:
            GitCommitNotFoundError: If commit hash doesn't exist or checkout fails
        """
        try:
            repo = git.Repo(cache_path)
            repo.git.fetch('origin', commit_hash, depth=1)
            repo.git.checkout(commit_hash)
        except Exception as e:
            raise GitCommitNotFoundError(commit_hash, str(e))

    # ==============================================================
    # EXTENSIBILITY POINTS — Override in platform-specific subclasses
    # ==============================================================

    def validate_manifest(self, manifest: Any) -> bool:
        """
        Validate a dependency manifest.

        Override this method in platform-specific downloaders to enforce
        platform-specific constraints (e.g., MQL5 can only depend on MQL5 packages).

        Args:
            manifest: Loaded KnitPkgManifest object
            dep_path: Path to the dependency

        Returns:
            True if dependency is accepted, False to skip
        """
        # Base implementation: always accept
        return True

    def validate_project_structure(
        self,
        manifest: Any,
        project_dir: Path,
        is_dependency: bool = False
    ) -> None:
        """
        Validate project structure.

        Override this method for platform-specific checks
        (e.g., MQL requires knitpkg/include/ for packages).

        Args:
            manifest: Loaded KnitPkgManifest object
            project_dir: Path to the project/dependency
            is_dependency: True if validating a dependency, False for main project
        """
        # Base implementation: no-op
        pass

    # ==============================================================
    # CORE RESOLUTION LOGIC (Platform-agnostic)
    # ==============================================================

    def _download_dependency(self, dep_name: str, specifier: str, overrides: Dict[str, str], parent: ProjectNode):
        """
        Resolve and download a dependency (local or remote).

        Args:
            name: Dependency name
            specifier: Version spec or local path

        Returns:
            Resolved path or None if already resolved
        """
        if self._root_node.is_resolved(dep_name):
            self.log(f"[dim]Skip[/] {dep_name} (already resolved)")
            return

        if is_local_path(specifier):
            self._handle_local_dependency(dep_name, specifier, overrides, parent)
        else:
            self._handle_remote_dependency(dep_name, specifier, overrides, parent)

    def _handle_local_dependency(self, dep_name: str, specifier: str, overrides: Dict[str, str], parent: ProjectNode):
        """
        Handle local dependency resolution.

        Raises:
            LocalDependencyNotFoundError: If path doesn't exist
            LocalDependencyNotGitError: If --locked with non-git dependency
        """
        if dep_name in overrides:
            raise DependencyError("Overrides cannot be local dependencies: {dep_name}")
        if self.locked_mode:
            raise LockedWithLocalDependencyError(dep_name)

        if specifier.startswith("file://"):
            dep_path = Path(specifier[7:])
        else:
            dep_path = Path(specifier)

        if not dep_path.exists():
            raise LocalDependencyNotFoundError(dep_name, str(dep_path))
        
        resolved_path = dep_path.resolve()

        self.log(f"[bold magenta]Local[/] {dep_name}")

        # Load manifest to get version
        try:
            manifest = load_knitpkg_manifest(dep_path, self.manifest_type)
            version = manifest.version
        except Exception:
            raise LocalDependencyManifestError(dep_name, str(dep_path))

        # Create dependency node
        dep_node = ProjectNode(
            name=dep_name,
            path=dep_path,
            resolved_path=resolved_path,
            version=version,
            is_root=False,
            dependencies=[]
        )

        if self._process_recursive_dependencies(resolved_path, dep_name, dep_node, overrides):
            parent.add_dependency(dep_node)
            self.log(f"[green]✔[/] {dep_name}")

        return resolved_path

    def _handle_remote_dependency(self, dep_name: str, specifier: str, overrides: Dict[str, str], parent: ProjectNode):
        """Handle remote dependency resolution."""
        if dep_name in overrides:
            self.print(f"[bold][yellow]Override[/yellow] {dep_name} → {overrides[dep_name]}")
            resolved_path = self._download_from_git_remote(dep_name, overrides[dep_name])    
        else:
            resolved_path = self._download_from_git_remote(dep_name, specifier)

        # Load manifest to get version
        try:
            manifest = load_knitpkg_manifest(resolved_path, self.manifest_type)
            version = manifest.version
        except Exception:
            raise DependencyError(f"Failed to load manifest for dependency '{dep_name}#{specifier}' at {resolved_path}")

        # Create dependency node
        dep_node = ProjectNode(
            name=dep_name,
            path=resolved_path,
            resolved_path=resolved_path,
            version=version,
            is_root=False,
            dependencies=[]
        )

        if self._process_recursive_dependencies(resolved_path, dep_name, dep_node, overrides):
            parent.add_dependency(dep_node)
            self.log(f"[green]✔[/] {dep_name}")

        return resolved_path

    def _download_from_git_remote(
        self,
        dep_name: str,
        specifier: str
    ) -> Path:
        """
        Download a remote Git dependency.

        Raises:
            DependencyHasLocalChangesError: If dependency has local changes in locked mode
        """
        lockfile: LockFile = LockFile(self.project_dir)

        if self.locked_mode and lockfile.is_dependency(dep_name):
            self.log(f"[dim]Locked[/] {dep_name}")
            registry_base_url = lockfile.get(dep_name, "registry_url", self.default_registry_base_url)
            version_spec = lockfile.get(dep_name, "resolved")
        else:
            registry_base_url = self.default_registry_base_url
            version_spec = specifier

        dist_info = self._get_package_resolve_dist(registry_base_url, dep_name, version_spec)

        dep_resolved_path = self.project_dir / CACHE_DIR / f"{dep_name.strip().lower().replace('/', '_')}"
        if dep_resolved_path.exists():
            status = self._check_repo_integrity(dist_info['repo_url'], dep_resolved_path)

            if status == "dirty":
                if self.locked_mode:
                    raise DependencyHasLocalChangesError(dep_name)
                self.print(
                    f"[bold yellow]Warning:[/] Local changes in '{dep_name}' "
                    f"— using modified version"
                )
            
            elif status == "invalid_remote_url":
                # Repository exists in cache but remote URL is invalid; clean and download again
                shutil.rmtree(str(dep_resolved_path.resolve()))
                self._clone_shallow_to_commit(dist_info['repo_url'], dist_info['commit_hash'], dep_resolved_path)
                if not self.locked_mode or not lockfile.is_dependency(dep_name):
                    lockfile.update_if_changed(dep_name, specifier, dist_info["resolved_version"], self.default_registry_base_url)

            else:
                # Repository exists in cache and remote URL is correct
                if not self.locked_mode:
                    self.log(
                        f"[dim]Cache drifted[/] {dep_name} — re-resolving..."
                    )
                self._checkout_shallow_to_commit(dist_info["commit_hash"], dep_resolved_path)
                if not self.locked_mode or not lockfile.is_dependency(dep_name):
                    lockfile.update_if_changed(dep_name, specifier, dist_info["resolved_version"], self.default_registry_base_url)
                
        else:
            # Repo cache directory does not exist
            self._clone_shallow_to_commit(dist_info['repo_url'], dist_info['commit_hash'], dep_resolved_path)
            if not self.locked_mode or not lockfile.is_dependency(dep_name):
                lockfile.update_if_changed(dep_name, specifier, dist_info["resolved_version"], self.default_registry_base_url)
        
        return dep_resolved_path

    def _check_repo_integrity(self, repo_url: str, dep_resolved_path: Path) -> str:
        """Check the state of a local repository dependency."""
        try:
            repo: git.Repo = git.Repo(dep_resolved_path, search_parent_directories=True)
            if repo.bare:
                raise git.InvalidGitRepositoryError

            if not repo.remotes.origin.url or repo.remotes.origin.url != repo_url:
                return "invalid_remote_url"

            if repo.is_dirty(untracked_files=True):
                return "dirty"
            
            return "drifted"

        except git.InvalidGitRepositoryError:
            return "not-git"
        except Exception:
            return "invalid"

    def _process_recursive_dependencies(
        self,
        resolved_path: Path,
        dep_name: str,
        dep_node: ProjectNode,
        overrides: Dict[str, str]
    ) -> bool:
        """
        Process recursive dependencies. Return True if accepted, False if skipped.

        This method calls validate_manifest() and validate_project_structure()
        which can be overridden by platform-specific subclasses.
        """
        sub_manifest = load_knitpkg_manifest(resolved_path, self.manifest_type)

        # Platform-specific validation (overridable)
        if not self.validate_manifest(sub_manifest):
            self.print(
                f"[yellow]Warning:[/] Invalid manifest for {dep_name}. Dependency ignored."
            )
            return False

        expected_dep_name = f"@{sub_manifest.organization.strip().lower()}/{sub_manifest.name.strip().lower()}"

        if dep_name != expected_dep_name:
            self.print(
                f"[yellow]Warning:[/] Dependency name mismatch: "
                f"'{dep_name}'. Expected: '{expected_dep_name}'."
            )
            self.print(
                f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] → "
                f"{sub_manifest.name} : {sub_manifest.version}"
            )
        else:
            self.print(
                f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] : "
                f"{sub_manifest.version}"
            )

        # Platform-specific structure validation (overridable)
        self.validate_project_structure(sub_manifest, resolved_path, is_dependency=True)

        if sub_manifest.dependencies:
            self.log(
                f"[dim]Recursive:[/] {dep_name} → "
                f"{len(sub_manifest.dependencies)} dep(s)"
            )

            # Merge overrides (parent overrides take precedence)
            overrides_dep = overrides.copy()
            for sub_ovr_name, sub_ovr_version in sub_manifest.overrides.items():
                sub_ovr_name = normalize_dep_name(sub_ovr_name, sub_manifest.organization)
                if sub_ovr_name not in overrides_dep:
                    overrides_dep[sub_ovr_name] = sub_ovr_version

            # Process recursive sub-dependencies
            for sub_dep_name, sub_dep_spec in sub_manifest.dependencies.items():
                sub_dep_name = normalize_dep_name(sub_dep_name, sub_manifest.organization)
                self._download_dependency(sub_dep_name, sub_dep_spec, overrides_dep, dep_node)

        return True

