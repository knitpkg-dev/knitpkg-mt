# knitpkg/core/dependency_downloader.py

"""
Platform-agnostic dependency downloader.

This module handles Git-based dependency resolution, lockfile management,
and recursive dependency trees. Platform-specific validation logic can be
overridden by subclasses.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Set, Optional, Any
from dataclasses import dataclass

from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

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
    CorruptGitDependencyCacheError,
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

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        self.resolved_deps: ResolvedDeps = []
        self.dependency_tree: DependencyTree = []
        self.resolved_paths: Set[Path] = set()
        self.locked_mode: bool = False
        self._current_parent: Optional[DependencyNode] = None

    def download_all(
        self,
        dependencies: dict,
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
        self.resolved_deps = []
        self.dependency_tree = []
        self.resolved_paths = set()
        self.locked_mode = locked_mode
        self._current_parent = None

        for name, spec in dependencies.items():
            self._download_dependency(name, spec)

        return self.resolved_deps, self.dependency_tree

    # ==============================================================
    # EXTENSIBILITY POINTS — Override in platform-specific subclasses
    # ==============================================================

    def validate_manifest(self, manifest: Any, dep_path: Path) -> bool:
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

        has_git, current_commit = self._check_git_status(dep_path)

        if self.locked_mode and not has_git:
            raise LocalDependencyNotGitError(name)

        if not has_git:
            self.console.log(
                f"[bold yellow]Warning:[/] Local dependency '{name}' has no Git history"
            )

        if has_git and current_commit:
            self._update_lockfile_local(name, specifier, dep_path, current_commit)

        self.console.log(f"[bold magenta]Local{'-git' if has_git else ''}[/] {name}")

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

    def _handle_remote_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """Handle remote dependency resolution."""
        dep_path = self._download_from_git(name, specifier)
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

    def _check_git_status(self, dep_path: Path) -> tuple[bool, str | None]:
        """Check if path is a git repository and return commit hash."""
        try:
            repo = git.Repo(dep_path, search_parent_directories=True)
            if not repo.bare:
                return True, repo.head.commit.hexsha
        except Exception:
            pass
        return False, None

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

    def _download_from_git(
        self,
        name: str,
        specifier: str
    ) -> Path:
        """
        Download a remote Git dependency.

        Raises:
            DependencyHasLocalChangesError: If dependency has local changes in locked mode
        """
        base_url = specifier.split("#")[0].rstrip("/")
        ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
        dep_path = CACHE_DIR / f"{name.strip().lower().replace('/', '_')}"

        lock_data = load_lockfile()
        locked = lock_data["dependencies"].get(name, {})

        if (
            dep_path.exists()
            and locked.get("source") == base_url
            and locked.get("specifier") == ref_spec
        ):
            status = self._check_local_dep_integrity(name, dep_path, locked)

            if status == "clean":
                self.console.log(
                    f"[dim]Cache hit[/] {name} → {locked.get('resolved', 'HEAD')[:8]}"
                )
                return dep_path
            
            if status == "drifted":
                self.console.log(
                    f"[dim]Cache drifted[/] {name} — re-resolving..."
                )
                if not self.locked_mode:
                    return self._fetch_tags_and_resolve(name, specifier, dep_path)
                else:
                    commit = locked.get("commit")
                    if not commit:
                        return self._fetch_tags_and_resolve(name, specifier, dep_path)

                    repo = git.Repo(dep_path, search_parent_directories=True)
                    repo.git.checkout(commit)
                    return dep_path

            if status == "dirty":
                if self.locked_mode:
                    raise DependencyHasLocalChangesError(name)
                self.console.log(
                    f"[bold yellow]Warning:[/] Local changes in '{name}' "
                    f"— using modified version"
                )
                return dep_path
            
            else:
                raise CorruptGitDependencyCacheError(name, dep_path)

        elif locked.get("source") == base_url and locked.get("specifier") == ref_spec:
            commit = locked.get("commit")
            if not commit:
                return self._clone_and_resolve(name, specifier, dep_path)
            self.console.log(
                f"[bold green]Lockfile[/] {name} → "
                f"{locked.get('resolved','HEAD')[:8]} ({commit[:8]})"
            )
            dep_path.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=1)
            repo.git.checkout(commit)
            return dep_path
        else:
            if dep_path.exists():
                return self._fetch_tags_and_resolve(name, specifier, dep_path)
            else:
                return self._clone_and_resolve(name, specifier, dep_path)

    def _clone_and_resolve(self, name: str, specifier: str, dep_path: Path) -> Path:
        """Download and resolve the best matching version/tag."""
        base_url = specifier.split("#")[0].rstrip("/")
        ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"

        self.console.log(f"[bold blue]Cloning[/] {name} ← {base_url}")
        dep_path.mkdir(parents=True, exist_ok=True)
        repo = git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=50)

        self.console.log(f"[dim]Fetching tags[/] for {name}...")
        repo.remotes.origin.fetch(tags=True, prune=True)

        final_ref = self._resolve_version_from_spec(name, ref_spec, repo)

        try:
            self.console.log(f"[dim]Checking out[/] {name} → {final_ref}")
            repo.git.checkout(final_ref, force=True)
        except git.exc.GitCommandError:
            self.console.log(f"[red]Error:[/] Failed to checkout '{final_ref}' for {name}")
            repo.git.checkout("HEAD", force=True)
            final_ref = "HEAD"

        commit = repo.head.commit.hexsha
        lock_data = load_lockfile()
        if is_lock_change(lock_data, name, base_url, ref_spec, final_ref, commit):
            lock_data["dependencies"][name] = {
                "source": base_url,
                "specifier": ref_spec,
                "resolved": final_ref,
                "commit": commit,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
            save_lockfile(lock_data)
        return dep_path

    def _fetch_tags_and_resolve(self, name: str, specifier: str, dep_path: Path) -> Path:
        """Download and resolve the best matching version/tag."""
        base_url = specifier.split("#")[0].rstrip("/")
        ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"

        repo = git.Repo(dep_path, search_parent_directories=True)

        self.console.log(f"[dim]Fetching tags[/] for {name}...")
        repo.remotes.origin.fetch(tags=True, prune=True)

        final_ref = self._resolve_version_from_spec(name, ref_spec, repo)

        try:
            self.console.log(f"[dim]Checking out[/] {name} → {final_ref}")
            repo.git.checkout(final_ref, force=True)
        except git.exc.GitCommandError:
            self.console.log(f"[red]Error:[/] Failed to checkout '{final_ref}' for {name}")
            repo.git.checkout("HEAD", force=True)
            final_ref = "HEAD"

        commit = repo.head.commit.hexsha
        lock_data = load_lockfile()
        if is_lock_change(lock_data, name, base_url, ref_spec, final_ref, commit):
            lock_data["dependencies"][name] = {
                "source": base_url,
                "specifier": ref_spec,
                "resolved": final_ref,
                "commit": commit,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
            save_lockfile(lock_data)
        return dep_path
    
    def _check_local_dep_integrity(self, name: str, dep_path: Path, locked: dict) -> str:
        """Check if a local dependency is clean and reproducible."""
        try:
            repo = git.Repo(dep_path, search_parent_directories=True)
            if repo.bare:
                raise git.InvalidGitRepositoryError
            if repo.is_dirty(untracked_files=True):
                return "dirty"
            
            if self.locked_mode:
                if locked.get("commit") and repo.head.commit.hexsha == locked["commit"]:
                    return "clean"
            
            # Pull latest changes before checking commit
            try:
                self.console.log(f"[dim]Pull latest changes[/] for {name}...")
                repo.remotes.origin.pull()
            except Exception:
                pass  # Ignore pull errors, continue with existing state
            
            if locked.get("commit") and repo.head.commit.hexsha != locked["commit"]:
                return "drifted"
            return "clean"
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
            if not self.validate_manifest(sub_manifest, dep_path):
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
                    f"{sub_manifest.name} v{sub_manifest.version}"
                )
            else:
                self.console.log(
                    f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] "
                    f"v{sub_manifest.version}"
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

    def _resolve_version_from_spec(self, name: str, specifier: str, repo: git.Repo) -> str:
        """
        Resolve a version specifier (SemVer ranges, ^, ~, exact versions,
        branch=, tag=, commit=) against available git tags.

        Tags with build metadata (+xxx) are preferred when versions are equal.
        """
        specifier = specifier.strip()

        # === 1. Direct references ===
        if specifier.startswith(("branch=", "tag=", "commit=")):
            prefix, value = specifier.split("=", 1)
            return value[:7] if prefix == "commit" else value

        # === 2. Normalize specifier ===
        clean = specifier.lstrip("vV")

        try:
            if clean.startswith("^"):
                base = Version(clean[1:].split("+", 1)[0])
                spec = SpecifierSet(f">={base},<{base.major + 1}.0.0")
            elif clean.startswith("~"):
                base = Version(clean[1:].split("+", 1)[0])
                spec = SpecifierSet(f">={base},<{base.major}.{base.minor + 1}.0")
            elif not any(op in clean for op in (">", "<", "=", " ", ",", "^", "~")):
                clean_ver = clean.split("+", 1)[0]
                spec = SpecifierSet(f"=={clean_ver}")
            else:
                normalized = clean.replace(" ", "")
                normalized = re.sub(r'([0-9])([<>]=?)', r'\1,\2', normalized)
                normalized = re.sub(r'([0-9])([<>])', r'\1,\2', normalized)
                normalized = normalized.replace(",,", ",").lstrip(",")
                spec = SpecifierSet(normalized)
        except Exception:
            self.console.log(
                f"[yellow]Warning:[/] Invalid specifier '{specifier}' for {name}. "
                f"Accepting any version."
            )
            spec = SpecifierSet()

        # === 3. Collect candidate tags ===
        candidates = []
        for tag in repo.tags:
            tag_name = tag.name
            version_str = tag_name.lstrip("vV").split("+", 1)[0]
            try:
                version = Version(version_str)
                candidates.append((version, tag_name))
            except InvalidVersion:
                continue

        if not candidates:
            self.console.log(
                f"[yellow]Warning:[/] No valid SemVer tags in {name}. Using HEAD."
            )
            return "HEAD"

        # === 4. Sort: newest version first, build-metadata wins on ties ===
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # === 5. Find first matching version ===
        for version, tag_name in candidates:
            if version in spec:
                return tag_name

        # === 6. Fallback ===
        self.console.log(
            f"[yellow]Warning:[/] No compatible version for '{specifier}' in {name}. "
            f"Falling back to HEAD."
        )
        return "HEAD"
