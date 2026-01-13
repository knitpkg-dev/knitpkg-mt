# knitpkg/core/dependency_downloader.py

"""
Platform-agnostic dependency downloader.

This module handles Git-based dependency resolution, lockfile management,
and recursive dependency trees. Platform-specific validation logic can be
overridden by subclasses.
"""

from __future__ import annotations

import httpx
from pathlib import Path
from typing import List, Tuple, Set, Optional, Any
from dataclasses import dataclass

import shutil
import git

from rich.console import Console

from knitpkg.core.lockfile import load_lockfile, save_lockfile, is_lock_change
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.core.utils import is_local_path
from knitpkg.core.constants import CACHE_DIR

# Import custom exceptions
from knitpkg.core.exceptions import (
    LocalDependencyNotFoundError,
    LocalDependencyNotGitError,
    DependencyHasLocalChangesError,
    LocalDependencyNotInLockfileError,
    LocalDependencyCommitMismatchError,
    LocalDependencyManifestError,
    RegistryRequestError,
    GitCloneError,
    GitCommitNotFoundError,
)

# ==============================================================
# TYPE DEFINITIONS
# ==============================================================

@dataclass
class DependencyNode:
    """Represents a resolved dependency with hierarchy information."""
    name: str
    path: Path
    resolved_path: Path  # Canonical path for deduplication
    version: str
    children: List['DependencyNode']
    parent: Optional['DependencyNode'] = None

    def __post_init__(self):
        for child in self.children:
            child.parent = self

ResolvedDep = Tuple[str, Path]  # (name, path)
ResolvedDeps = List[ResolvedDep]
DependencyTree = List[DependencyNode]

# ==============================================================
# DEPENDENCY DOWNLOADER CLASS
# ==============================================================

class DependencyDownloader:
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

    def __init__(self, console: Console, project_dir: Path, registry_base_url: str = "http://localhost:8000"):
        self.console = console
        self.project_dir = project_dir
        self.registry_base_url = registry_base_url.rstrip('/')
        self.resolved_deps: ResolvedDeps = []
        self.dependency_tree: DependencyTree = []
        self.resolved_paths: Set[Path] = set()
        self.locked_mode: bool = False
        self._current_parent: Optional[DependencyNode] = None

    def download_all(
        self,
        dependencies: dict,
        target: str,
        locked_mode: bool = False
    ) -> tuple[ResolvedDeps, DependencyTree]:
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
        self.target: str = target
        self.resolved_deps = []
        self.dependency_tree = []
        self.resolved_paths = set()
        self.locked_mode = locked_mode
        self._current_parent = None

        for name, spec in dependencies.items():
            self._download_dependency(name, spec)

        return self.resolved_deps, self.dependency_tree

    def _get_package_resolve_dist(self, name: str, version_spec: str) -> dict:
        """Resolve package distribution info from registry.
        
        Args:
            name: Package name (may include @org/package format)
            version_spec: Version specifier
            
        Returns:
            Dict containing package distribution info
            
        Raises:
            RegistryRequestError: If registry request fails
        """
        org, pack_name = self._parse_package_name(name)
        url = f"{self.registry_base_url}/package/{self.target}/{org}/{pack_name}/{version_spec}"
        
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code != 200:
                raise RegistryRequestError(url, response.status_code, response.text)
            return response.json()
        except httpx.RequestError as e:
            raise RegistryRequestError(url, 0, str(e))

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

    def validate_manifest(self, manifest: Any, dep_path: Path, target: str) -> bool:
        """
        Validate a dependency manifest.

        Override this method in platform-specific downloaders to enforce
        platform-specific constraints (e.g., MQL can only depend on packages).

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

    def _download_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """
        Resolve and download a dependency (local or remote).

        Args:
            name: Dependency name
            specifier: Version spec or local path

        Returns:
            Resolved path or None if already resolved
        """
        name = name.lower()

        if is_local_path(specifier):
            return self._handle_local_dependency(name, specifier)
        else:
            return self._handle_remote_dependency(name, specifier)

    def _handle_local_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """
        Handle local dependency resolution.

        Raises:
            LocalDependencyNotFoundError: If path doesn't exist
            LocalDependencyNotGitError: If --locked with non-git dependency
        """
        if specifier.startswith("file://"):
            dep_path = Path(specifier[7:])
        else:
            dep_path = (self.project_dir / specifier).resolve()

        if not dep_path.exists():
            raise LocalDependencyNotFoundError(name, str(dep_path))

        resolved_path = dep_path.resolve()

        # Check if already resolved by path
        if resolved_path in self.resolved_paths:
            self.console.log(f"[dim]Already resolved by path:[/] {name} → {resolved_path}")
            return None

        repo_status, current_commit = self._check_local_repo_status(dep_path)

        if self.locked_mode:
            if repo_status == 'not-git':
                raise LocalDependencyNotGitError(name)
            if repo_status == 'dirty':
                raise DependencyHasLocalChangesError(name)
            
            lock_data = load_lockfile()
            lock_data_dep = lock_data["dependencies"].get(name, {})
            if not lock_data_dep:
                raise LocalDependencyNotInLockfileError(name)
            if lock_data_dep.get("commit") != current_commit:
                raise LocalDependencyCommitMismatchError(name, current_commit or "unknown", lock_data_dep.get("commit", "unknown"))

        else:
            if repo_status == 'clean' and current_commit:
                self._update_lockfile_local(name, specifier, dep_path, current_commit)
            elif repo_status == 'not-git':
                self.console.log(
                    f"[bold yellow]Warning:[/] Local dependency '{name}' has no Git history"
                )
            else:
                self.console.log(
                f"[bold yellow]Warning:[/] Local dependency '{name}' is a Git repository but it is not clean"
            )

        self.console.log(f"[bold magenta]Local{'-git' if repo_status != 'no-git' else ''}[/] {name}")

        # Load manifest to get version
        try:
            manifest = load_knitpkg_manifest(dep_path)
            version = manifest.version
        except Exception:
            raise LocalDependencyManifestError(name, str(dep_path))

        # Create dependency node
        dep_node = DependencyNode(
            name=name,
            path=dep_path,
            resolved_path=resolved_path,
            version=version,
            children=[]
        )

        if self._process_recursive_dependencies(dep_path, name, dep_node):
            self.resolved_paths.add(resolved_path)
            self.resolved_deps.append((name, dep_path))

            if self._current_parent is None:
                self.dependency_tree.append(dep_node)
            else:
                self._current_parent.children.append(dep_node)
                dep_node.parent = self._current_parent

            self.console.log(f"[green]Check[/] {name}")

        return resolved_path

    def _handle_remote_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """Handle remote dependency resolution."""
        dep_path = self._download_from_git_remote(name, specifier)
        resolved_path = dep_path.resolve()

        # Check if already resolved by path
        if resolved_path in self.resolved_paths:
            self.console.log(f"[dim]Already resolved by path:[/] {name} → {resolved_path}")
            return None

        # Load manifest to get version
        try:
            manifest = load_knitpkg_manifest(dep_path)
            version = manifest.version
        except Exception:
            version = "unknown"

        # Create dependency node
        dep_node = DependencyNode(
            name=name,
            path=dep_path,
            resolved_path=resolved_path,
            version=version,
            children=[]
        )

        if self._process_recursive_dependencies(dep_path, name, dep_node):
            self.resolved_paths.add(resolved_path)
            self.resolved_deps.append((name, dep_path))

            if self._current_parent is None:
                self.dependency_tree.append(dep_node)
            else:
                self._current_parent.children.append(dep_node)
                dep_node.parent = self._current_parent

            self.console.log(f"[green]Check[/] {name}")

        return resolved_path

    def _update_lockfile_local(
        self,
        name: str,
        specifier: str,
        dep_path: Path,
        commit: str
    ) -> None:
        """Update lockfile for local git dependency."""
        lock_data = load_lockfile()
        if is_lock_change(lock_data, name, str(dep_path.resolve()), specifier, f"commit:{commit}", commit):
            lock_data["dependencies"][name] = {
                "source": str(dep_path.resolve()),
                "specifier": specifier,
                "resolved": f"commit:{commit}",
                "commit": commit,
                "type": "local-git",
            }
            save_lockfile(lock_data)

    def _update_lockfile_remote(
        self, name: str, base_url: str, ref_spec: str, final_ref: str, commit: str
    ) -> None:
        """Update lockfile for local git dependency."""
        lock_data = load_lockfile()
        if is_lock_change(lock_data, name, base_url, ref_spec, final_ref, commit):
            lock_data["dependencies"][name] = {
                "source": base_url,
                "specifier": ref_spec,
                "resolved": final_ref,
                "commit": commit,
                "type": "resolved-git",
            }
            save_lockfile(lock_data)

    def _download_from_git_remote(
        self,
        name: str,
        specifier: str
    ) -> Path:
        """
        Download a remote Git dependency.

        Raises:
            DependencyHasLocalChangesError: If dependency has local changes in locked mode
        """
        dep_path = CACHE_DIR / f"{name.strip().lower().replace('/', '_')}"

        lock_data = load_lockfile()
        lock_data_dep = lock_data["dependencies"].get(name, {})

        if dep_path.exists():
            repo: git.Repo = git.Repo(dep_path, search_parent_directories=True)

            status = self._check_repo_integrity(repo, lock_data_dep)

            if status == "invalid_remote_url":
                # Repository exists in cache but remote URL is invalid; clean and download again
                shutil.rmtree(str(dep_path))
                resolved_commit_hash = lock_data_dep.get("commit", None)
                is_resolved_git = lock_data_dep.get("type", None) == "resolved-git"
                if self.locked_mode and is_resolved_git and resolved_commit_hash:
                    self._clone_shallow_to_commit(lock_data_dep['source'], lock_data_dep['commit'], dep_path)
                else:
                    dist_info = self._get_package_resolve_dist(name, specifier)

                    git_url = dist_info["repo_url"]
                    resolved_commit_hash = dist_info["commit_hash"]
                    self._clone_shallow_to_commit(git_url, resolved_commit_hash, dep_path)
                    self._update_lockfile_remote(name, git_url, specifier, dist_info["resolved_version"], resolved_commit_hash)

            elif status == "clean" and self.locked_mode:
                self.console.log(
                    f"[dim]Cache hit[/] {name} → {lock_data_dep.get('resolved', 'HEAD')[:8]}"
                )
            
            elif status == "dirty":
                if self.locked_mode:
                    raise DependencyHasLocalChangesError(name)
                self.console.log(
                    f"[bold yellow]Warning:[/] Local changes in '{name}' "
                    f"— using modified version"
                )
            
            else:
            
                # Repository exists in cache and remote URL is correct
                resolved_commit_hash = lock_data_dep.get("commit", None)
                is_resolved_git = lock_data_dep.get("type", None) == "resolved-git"
                if self.locked_mode and is_resolved_git and resolved_commit_hash:
                    self._checkout_shallow_to_commit(lock_data_dep['commit'], dep_path)
                else:
                    self.console.log(
                        f"[dim]Cache drifted[/] {name} — re-resolving..."
                    )
                    dist_info = self._get_package_resolve_dist(name, specifier)

                    git_url = dist_info["repo_url"]
                    resolved_commit_hash = dist_info["commit_hash"]
                    self._checkout_shallow_to_commit(resolved_commit_hash, dep_path)
                    self._update_lockfile_remote(name, git_url, specifier, dist_info["resolved_version"], resolved_commit_hash)
                
        else:
            # Repo cache directory does not exist
            resolved_commit_hash = lock_data_dep.get("commit", None)
            is_resolved_git = lock_data_dep.get("type", None) == "resolved-git"
            if self.locked_mode and is_resolved_git and resolved_commit_hash:
                self._clone_shallow_to_commit(lock_data_dep['source'], lock_data_dep['commit'], dep_path)
            else:
                dist_info = self._get_package_resolve_dist(name, specifier)

                git_url = dist_info["repo_url"]
                resolved_commit_hash = dist_info["commit_hash"]
                self._clone_shallow_to_commit(git_url, resolved_commit_hash, dep_path)
                self._update_lockfile_remote(name, git_url, specifier, dist_info["resolved_version"], resolved_commit_hash)
        
        return dep_path


    def _check_local_repo_status(self, dep_path: Path) -> tuple[str, str | None]:
        """Check if path is a git repository and return commit hash."""
        try:
            repo = git.Repo(dep_path, search_parent_directories=True)
            if not repo.bare:
                if repo.is_dirty(untracked_files=True):
                    return "dirty", None
                return "clean", repo.head.commit.hexsha
        except Exception:
            pass
        return "not-git", None


    def _parse_package_name(self, name: str) -> tuple[str, str]:
        """Parse package name format @org/package-name into (org, pack_name) tuple."""
        if name.startswith('@') and '/' in name:
            parts = name[1:].split('/', 1)
            return parts[0], parts[1]
        return '', name

    def _check_repo_integrity(self, repo: git.Repo, lock_data_dep: dict) -> str:
        """Check the state of a local repository dependency."""
        try:
            if repo.bare:
                raise git.InvalidGitRepositoryError

            if not repo.remotes.origin.url or repo.remotes.origin.url != lock_data_dep["source"]:
                return "invalid_remote_url"

            if repo.is_dirty(untracked_files=True):
                return "dirty"
            
            if (
                lock_data_dep.get("commit") and 
                repo.head.commit.hexsha == lock_data_dep["commit"] 
            ):
                return "clean"

            return "drifted"

        except git.InvalidGitRepositoryError:
            return "not-git"
        except Exception:
            return "invalid"

    def _process_recursive_dependencies(
        self,
        dep_path: Path,
        dep_name: str,
        dep_node: DependencyNode
    ) -> bool:
        """
        Process recursive dependencies. Return True if accepted, False if skipped.

        This method calls validate_manifest() and validate_project_structure()
        which can be overridden by platform-specific subclasses.
        """
        try:
            sub_manifest: dict = load_knitpkg_manifest(dep_path)

            # Platform-specific validation (overridable)
            if not self.validate_manifest(sub_manifest, dep_path, self.target):
                self.console.log(
                    f"[yellow]Warning:[/] Invalid manifest for {dep_name}. Dependency ignored."
                )
                return False

            if sub_manifest.organization:
                expected_dep_name = f"@{sub_manifest.organization.strip()}/{sub_manifest.name.strip()}"
            else:
                expected_dep_name = sub_manifest.name

            if dep_name != expected_dep_name:
                self.console.log(
                    f"[yellow]Warning:[/] Dependency name mismatch: "
                    f"'{dep_name}'. Expected: '{expected_dep_name}'."
                )
                self.console.log(
                    f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] → "
                    f"{sub_manifest.name} {sub_manifest.version}"
                )
            else:
                self.console.log(
                    f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] "
                    f"{sub_manifest.version}"
                )

            # Platform-specific structure validation (overridable)
            self.validate_project_structure(sub_manifest, dep_path, is_dependency=True)

            if sub_manifest.dependencies:
                self.console.log(
                    f"[dim]Recursive:[/] {dep_name} → "
                    f"{len(sub_manifest.dependencies)} dep(s)"
                )

                # Set current node as parent for recursive calls
                previous_parent = self._current_parent
                self._current_parent = dep_node

                for sub_name, sub_spec in sub_manifest.dependencies.items():
                    self._download_dependency(sub_name, sub_spec)

                # Restore previous parent
                self._current_parent = previous_parent

            return True
        except Exception as e:
            self.console.log(
                f"[yellow]Warning:[/] Failed to process dependencies of {dep_name}: {e}"
            )
            return False

