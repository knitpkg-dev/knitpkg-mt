# helix/commands/install.py
# HELIX 2025 — install

from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Optional

from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer

from helix.core.utils import navigate_path

from helix.core.models import (
    HelixManifest,
    ProjectType,
    IncludeMode,
    Target
)

from helix.core.file_reading import load_helix_manifest
from helix.core.constants import CACHE_DIR, FLAT_DIR, INCLUDE_DIR
from helix.core.lockfile import load_lockfile, save_lockfile
from helix.core.file_reading import read_file_smart
from helix.core.utils import is_local_path

from dataclasses import dataclass

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

ResolvedDep = Tuple[str, Path, Path]  # name, path, resolved_path
ResolvedDeps = List[ResolvedDep]
DependencyTree = List[DependencyNode]

# ==============================================================
# HELIX INCLUDE DIRECTIVES PATTERN CLASS
# ==============================================================

class ResolveHelixIncludePattern:
    """Parses Helix include directives from MQL source code.
    
    Matches patterns like:
    - #include "autocomplete/autocomplete.mqh" /* @helix:replace-with "new/path.mqh" */
    - /* @helix:include "helix/include/AdditionalPath.mqh" */
    
    Attributes:
        include_path: Original include path from #include statement
        directive: Helix directive type ('include' or 'replace-with')
        replace_path: Replacement path specified in directive
        pattern: Compiled regex pattern for matching
    """

    def __init__(self):
        self.include_path = None
        self.directive = None
        self.replace_path = None

        self.pattern = re.compile(
            r'^\s*#\s*include\s+"(?P<include>[^"]+)"'
            r'(?:\s*/\*\s*@helix:(?P<directive1>\w+(?:-\w+)*)\s+"(?P<path1>[^"]+)"\s*\*/)?\s*$'
            r'|'
            r'^\s*/\*\s*@helix:(?P<directive2>\w+(?:-\w+)*)\s+"(?P<path2>[^"]+)"\s*\*/\s*$',
            re.MULTILINE
        )

    def extract_groups(self, match: re.Match) -> None:
        """Extract named groups from regex match and store in instance variables."""
        self.include_path = match.group("include")
        self.directive = match.group("directive1") or match.group("directive2")
        self.replace_path = match.group("path1") or match.group("path2")


# ==============================================================
# Include project validation (centralized)
# ==============================================================

def validate_include_project_structure(
    manifest: HelixManifest,
    project_dir: Path,
    is_dependency: bool = False,
    console: Console = None
) -> None:
    """
    Ensure include-type projects have their .mqh files inside helix/include/.
    
    Called for both the main project and recursive dependencies.
    Emits friendly warnings only (does not break the build).
    """
    if manifest.type != ProjectType.PACKAGE:
        return

    include_dir = project_dir / INCLUDE_DIR
    prefix = "[dep]" if is_dependency else "[project]"

    if not include_dir.exists():
        console.log(f"[bold yellow]WARNING {prefix}:[/] Include-type project missing '{Path(INCLUDE_DIR).as_posix()}' folder")
        console.log(f"    → {project_dir}")
        console.log("    Your .mqh files will not be exported to projects that depend on this one!")
        console.log("    Create the folder and move the files:")
        console.log(f"       mkdir -p {Path(INCLUDE_DIR).as_posix()}")
        console.log(f"       git mv *.mqh {Path(INCLUDE_DIR).as_posix()} 2>/dev/null || true")
        console.log("")
        return

    mqh_files = list(include_dir.rglob("*.mqh"))
    if not mqh_files:
        console.log(f"[bold yellow]WARNING {prefix}:[/] '{Path(INCLUDE_DIR).as_posix()}' folder exists but is empty!")
        console.log(f"    → {project_dir}")
        console.log("    No .mqh files will be exported. Move your headers there.")
        console.log("")
    else:
        console.log(f"[green]Check {prefix}[/] {len(mqh_files)} .mqh file(s) found in {Path(INCLUDE_DIR).as_posix()}")

# ==============================================================
# DEPENDENCY DOWNLOADER CLASS
# ==============================================================

class DependencyDownloader:
    """Handles downloading and resolving dependencies."""
    
    def __init__(self, console: Console):
        self.console = console
        self.resolved_deps: ResolvedDeps = []
        self.dependency_tree: DependencyTree = []
        self.resolved_paths: Set[Path] = set()  # Track resolved paths for deduplication
        self.locked_mode: bool = False
        self._current_parent: Optional[DependencyNode] = None
    
    def download_all(self, dependencies: dict, locked_mode: bool = False) -> tuple[ResolvedDeps, DependencyTree]:
        """Download all dependencies and return both resolved list and dependency tree."""
        self.resolved_deps = []
        self.dependency_tree = []
        self.resolved_paths = set()
        self.locked_mode = locked_mode
        self._current_parent = None
        
        for name, spec in dependencies.items():
            self._download_dependency(name, spec)
        
        return self.resolved_deps, self.dependency_tree
    
    def _download_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """Resolve and download a dependency (local or remote)."""
        name = name.lower()
        
        if is_local_path(specifier):
            return self._handle_local_dependency(name, specifier)
        else:
            return self._handle_remote_dependency(name, specifier)
    
    def _handle_local_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """Handle local dependency resolution."""
        if specifier.startswith("file://"):
            dep_path = Path(specifier[7:])
        else:
            dep_path = (Path.cwd() / specifier).resolve()
        
        if not dep_path.exists():
            self.console.log(f"[red]Fatal error:[/] Local dependency '{name}' points to missing path:")
            self.console.log(f"    → {dep_path}")
            raise SystemExit(1)
        
        resolved_path = dep_path.resolve()
        
        # Check if already resolved by path
        if resolved_path in self.resolved_paths:
            self.console.log(f"[dim]Already resolved by path:[/] {name} → {resolved_path}")
            return None
        
        has_git, current_commit = self._check_git_status(dep_path)
        
        if self.locked_mode and not has_git:
            self.console.log(f"[red]Error:[/] Cannot use --locked with non-git local dependency '{name}'")
            raise SystemExit(1)
        
        if not has_git:
            self.console.log(f"[bold yellow]Warning:[/] Local dependency '{name}' has no Git history")
        
        if has_git and current_commit:
            self._update_lockfile_local(name, specifier, dep_path, current_commit)
        
        self.console.log(f"[bold magenta]Local{'-git' if has_git else ''}[/] {name}")
        
        # Load manifest to get version
        try:
            manifest = load_helix_manifest(dep_path)
            version = manifest.version
        except Exception:
            version = "unknown"
        
        # Create dependency node
        dep_node = DependencyNode(name=name, path=dep_path, resolved_path=resolved_path, version=version, children=[])
        
        if self._process_recursive_dependencies(dep_path, name, dep_node):
            self.resolved_paths.add(resolved_path)
            self.resolved_deps.append((name, dep_path, resolved_path))
            
            if self._current_parent is None:
                self.dependency_tree.append(dep_node)
            else:
                self._current_parent.children.append(dep_node)
                dep_node.parent = self._current_parent
            
            self.console.log(f"[green]Check[/] {name}")
        
        return resolved_path
    
    def _handle_remote_dependency(self, name: str, specifier: str) -> Optional[Path]:
        """Handle remote dependency resolution."""
        dep_path = self._download_from_git(name, specifier, force_lock=self.locked_mode)
        resolved_path = dep_path.resolve()
        
        # Check if already resolved by path
        if resolved_path in self.resolved_paths:
            self.console.log(f"[dim]Already resolved by path:[/] {name} → {resolved_path}")
            return None
        
        # Load manifest to get version
        try:
            manifest = load_helix_manifest(dep_path)
            version = manifest.version
        except Exception:
            version = "unknown"
        
        # Create dependency node
        dep_node = DependencyNode(name=name, path=dep_path, resolved_path=resolved_path, version=version, children=[])
        
        if self._process_recursive_dependencies(dep_path, name, dep_node):
            self.resolved_paths.add(resolved_path)
            self.resolved_deps.append((name, dep_path, resolved_path))
            
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
    
    def _update_lockfile_local(self, name: str, specifier: str, dep_path: Path, commit: str) -> None:
        """Update lockfile for local git dependency."""
        lock_data = load_lockfile()
        lock_data["dependencies"][name] = {
            "source": str(dep_path.resolve()),
            "specifier": specifier,
            "resolved": f"commit:{commit}",
            "commit": commit,
            "type": "local-git",
        }
        save_lockfile(lock_data)
    
    def _download_from_git(self, name: str, specifier: str, *, force_lock: bool = False) -> Path:
        """Download a remote Git dependency."""
        base_url = specifier.split("#")[0].rstrip("/")
        ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
        cache_key = hashlib.sha256(specifier.encode()).hexsha[:16]
        dep_path = CACHE_DIR / f"{name}_{cache_key}"
        
        lock_data = load_lockfile()
        locked = lock_data["dependencies"].get(name, {})
        
        if dep_path.exists() and locked.get("source") == base_url and locked.get("specifier") == ref_spec:
            status = self._check_local_dep_integrity(dep_path, locked)
            if status == "clean":
                self.console.log(f"[dim]Cache hit[/] {name} → {locked.get('resolved', 'HEAD')[:8]}")
                return dep_path
            if force_lock:
                self.console.log(f"[red]Error:[/] Cannot proceed with --locked: dependency '{name}' has local changes")
                raise SystemExit(1)
            self.console.log(f"[bold yellow]Warning:[/] Local changes in '{name}' — using modified version")
            return dep_path
        elif locked.get("source") == base_url and locked.get("specifier") == ref_spec:
            commit = locked.get("commit")
            if not commit:
                return self._download_and_resolve(name, specifier, dep_path)
            self.console.log(f"[bold green]Lockfile[/] {name} → {locked.get('resolved','HEAD')[:8]} ({commit[:8]})")
            dep_path.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=1)
            repo.git.checkout(commit)
            return dep_path
        else:
            return self._download_and_resolve(name, specifier, dep_path)
    
    def _download_and_resolve(self, name: str, specifier: str, dep_path: Path) -> Path:
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
        lock_data["dependencies"][name] = {
            "source": base_url,
            "specifier": ref_spec,
            "resolved": final_ref,
            "commit": commit,
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        save_lockfile(lock_data)
        return dep_path
    
    def _check_local_dep_integrity(self, dep_path: Path, locked: dict) -> str:
        """Check if a local dependency is clean and reproducible."""
        try:
            repo = git.Repo(dep_path, search_parent_directories=True)
            if repo.bare:
                raise git.InvalidGitRepositoryError
            if repo.is_dirty(untracked_files=True):
                return "dirty"
            if locked.get("commit") and repo.head.commit.hexsha != locked["commit"]:
                return "drifted"
            return "clean"
        except git.InvalidGitRepositoryError:
            return "not-git"
        except Exception:
            return "invalid"
    
    def _process_recursive_dependencies(self, dep_path: Path, dep_name: str, dep_node: DependencyNode) -> bool:
        """Process recursive dependencies. Return True if accepted, False if skipped."""
        try:
            sub_manifest = load_helix_manifest(dep_path)
            
            if not self._accept_dependency(sub_manifest):
                return False
            
            if dep_name != sub_manifest.name:
                self.console.log(f"[yellow]Warning:[/] Dependency name mismatch: '{dep_name}' != '{sub_manifest.name}'")
                self.console.log(f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] → {sub_manifest.name} v{sub_manifest.version}")
            else:
                self.console.log(f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] v{sub_manifest.version}")

            validate_include_project_structure(sub_manifest, dep_path, True, self.console)
            
            if sub_manifest.dependencies:
                self.console.log(f"[dim]Recursive:[/] {dep_name} → {len(sub_manifest.dependencies)} dep(s)")
                
                # Set current node as parent for recursive calls
                previous_parent = self._current_parent
                self._current_parent = dep_node
                
                for sub_name, sub_spec in sub_manifest.dependencies.items():
                    self._download_dependency(sub_name, sub_spec)
                
                # Restore previous parent
                self._current_parent = previous_parent
            
            return True
        except Exception as e:
            self.console.log(f"[yellow]Warning:[/] Failed to process dependencies of {dep_name}: {e}")
            return False
        
    def _accept_dependency(self, manifest: HelixManifest):
        """Decide whether to accept a dependency based on its manifest."""
        accept = True

        accept_target = manifest.target in (Target.MQL4, Target.MQL5)
        accept = accept and accept_target
        if not accept_target:
            self.console.log(f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}")
            self.console.log(f"    → target is '{manifest.target.value}', but `helix install` only supports '{Target.MQL4}' or '{Target.MQL5}' projects.")

        accept_project_type = manifest.type == ProjectType.PACKAGE
        accept = accept and accept_project_type
        if not accept_project_type:
            self.console.log(f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}")
            self.console.log(f"    → type is '{manifest.type.value}', but `helix install` only supports 'package' projects.")
        
        return accept
        
    def _resolve_version_from_spec(self, name: str, specifier: str, repo: git.Repo) -> str:
        """
        Resolve a version specifier (SemVer ranges, ^, ~, exact versions, branch=, tag=, commit=)
        against available git tags. Tags with build metadata (+xxx) are preferred when versions are equal.
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
            self.console.log(f"[yellow]Warning:[/] Invalid specifier '{specifier}' for {name}. Accepting any version.")
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
            self.console.log(f"[yellow]Warning:[/] No valid SemVer tags in {name}. Using HEAD.")
            return "HEAD"

        # === 4. Sort: newest version first, build-metadata wins on ties ===
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        # === 5. Find first matching version ===
        for version, tag_name in candidates:
            if version in spec:
                return tag_name

        # === 6. Fallback ===
        self.console.log(f"[yellow]Warning:[/] No compatible version for '{specifier}' in {name}. Falling back to HEAD.")
        return "HEAD"


# ==============================================================
# INCLUDE MODE PROCESSOR CLASS
# ==============================================================

class IncludeModeProcessor:
    """Handles include mode processing."""
    
    def __init__(self, console: Console):
        self.console = console
        self.resolve_include_pattern: ResolveHelixIncludePattern = ResolveHelixIncludePattern()
    
    def process(self, resolved_deps: ResolvedDeps) -> None:
        """Process dependencies in include mode."""
        INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
        total_copied = 0
        
        for dep, dep_path, _ in resolved_deps:
            dep_include_dir = dep_path / "helix" / "include"
            if not dep_include_dir.exists():
                self.console.log(f"[dim]no include[/] {dep} → no helix/include/")
                continue
            
            mqh_files = list(dep_include_dir.rglob("*.mqh"))
            if not mqh_files:
                continue
            
            self.console.log(f"[dim]copying[/] {dep} → {len(mqh_files)} file(s)")
            for src in mqh_files:
                self._safe_copy_with_conflict_warning(src, INCLUDE_DIR, dep)
                total_copied += 1
        
        self.console.log(f"[bold green]Check Include mode:[/] {total_copied} file(s) copied → [bold]helix/include/[/]")
        self._process_directives()
    
    def _process_directives(self) -> None:
        """Process helix directives in copied files."""
        log_neutralize = True
        for mqh_file in INCLUDE_DIR.rglob("*.mqh"):
            content = mqh_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            modified = False
            
            for i, line in enumerate(lines):
                match = self.resolve_include_pattern.pattern.match(line)
                if match:
                    self.resolve_include_pattern.extract_groups(match)
                    include_path = self.resolve_include_pattern.include_path
                    directive = self.resolve_include_pattern.directive
                    replace_path = self.resolve_include_pattern.replace_path
                    
                    if directive == 'include':
                        lines[i] = f'#include "{navigate_path(mqh_file.parent,replace_path).as_posix()}" /*** ← dependence added by Helix ***/'
                        modified = True
                    elif directive == 'replace-with':
                        lines[i] = f'#include "{navigate_path(mqh_file.parent,replace_path).as_posix()}" /*** ← dependence resolved by Helix. Original include: "{include_path}" ***/'
                        modified = True
                    elif '/autocomplete/autocomplete.mqh' in Path(include_path).as_posix():
                        if log_neutralize:
                            self.console.log(f"[dim]neutralizing[/] autocomplete includes in copied files...")
                            log_neutralize = False
                        lines[i] = f"// {line.strip()}  /*** ← disabled by Helix install (dev helper) ***/"
                        modified = True
            
            if modified:
                mqh_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    def _safe_copy_with_conflict_warning(self, src: Path, dst_dir: Path, dep_name: str) -> None:
        """Copy a header detecting and warning about content conflicts."""
        try:
            for parent in src.parents:
                if parent.name == "include" and parent.parent.name == "helix":
                    rel_path = src.relative_to(parent)
                    break
            else:
                rel_path = src.name
        except Exception:
            rel_path = src.name
        
        dst = dst_dir / rel_path
        
        if dst.exists():
            try:
                src_content = read_file_smart(src)
                dst_content = read_file_smart(dst)
                if src_content.strip() != dst_content.strip():
                    self.console.log(f"[bold red]CONFLICT DETECTED:[/] {dst.name} will be overwritten by '{dep_name}'")
                    self.console.log(f"    → Different content conflict!")
                else:
                    self.console.log(f"[dim]duplicate header[/] {dst.name} (same content, skipped)")
                    return
            except Exception as e:
                self.console.log(f"[yellow]Warning:[/] Could not compare content of {dst.name}: {e}")
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

# ==============================================================
# FLAT MODE PROCESSOR CLASS
# ==============================================================

class FlatModeProcessor:
    """Handles flat mode processing."""
    
    def __init__(self, console: Console):
        self.console = console
        self.resolve_include_pattern: ResolveHelixIncludePattern = ResolveHelixIncludePattern()
    
    def process(self, manifest: HelixManifest, resolved_deps: ResolvedDeps) -> None:
        """Process entrypoints in flat mode."""
        FLAT_DIR.mkdir(parents=True, exist_ok=True)
        for entry in manifest.entrypoints or []:
            src = Path(entry)
            if not src.exists():
                self.console.log(f"[red]Error:[/] entrypoint not found: {entry}")
                continue
            
            content = read_file_smart(src)
            header = f"// {'='*70}\n// HELIX FLAT — DO NOT EDIT\n// Project: {manifest.name} v{manifest.version}\n// File: {entry}\n// {'='*70}\n\n"
            content = header + content
            
            visited = set()
            content = self._resolve_includes(content, src, visited, resolved_deps)
            
            flat_file = FLAT_DIR / f"{src.stem}_flat{src.suffix}"
            flat_file.write_text(content, encoding="utf-8")
            self.console.log(f"[green]Check[/] {flat_file.name} generated")
    
    def _find_include_file(self, inc_file: str, base_path: Path, resolved_deps: ResolvedDeps) -> Path:
        """Search for an #include file in the current project and all resolved dependencies."""
        candidates = [
            (base_path.parent / inc_file).resolve(),
            (INCLUDE_DIR / inc_file).resolve() if INCLUDE_DIR.exists() else None,
            *[(dep_path / inc_file).resolve() for _name, dep_path, _ in resolved_deps]
        ]
        
        for path in candidates:
            if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
                return path
        
        raise FileNotFoundError(f"Include not found: {inc_file}")
    
    def _resolve_includes(self, content: str, base_path: Path, visited: Set[Path], resolved_deps: ResolvedDeps) -> str:
        """Recursively resolve all #include directives, preserving #property lines and avoiding cycles."""
        
        def replace(match: re.Match):
            self.resolve_include_pattern.extract_groups(match)
            include_path: str = self.resolve_include_pattern.include_path
            directive: str = self.resolve_include_pattern.directive
            replace_path: str = self.resolve_include_pattern.replace_path
            
            if directive is None:
                inc_file = include_path.strip()
            elif directive == 'include':
                inc_file = replace_path.strip()
                self.console.log(f"[dim]@helix:include found:[/] '{inc_file}'")
            elif directive == 'replace-with':
                inc_file = replace_path.strip()
                self.console.log(f"[dim]@helix:replace-with found:[/] '{inc_file}'")
            else:
                self.console.log(f"[red]ERROR:[/] Invalid @helix:<directive> → '{directive}'")
                return f"// ERROR: Invalid @helix:<directive> → '{directive}'"
            
            try:
                inc_path = self._find_include_file(inc_file, base_path, resolved_deps)
            except FileNotFoundError:
                self.console.log(f"[red]ERROR:[/] Include not found in {base_path} → {inc_file}")
                return f"// ERROR: Include not found → {inc_file}"
            
            inc_path_abs = inc_path.absolute()
            if inc_path_abs in visited:
                return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
            visited.add(inc_path_abs)
            
            raw = read_file_smart(inc_path)
            preserved = [l for l in raw.splitlines() if l.strip().startswith(("#property copyright", "#property link", "#property version"))]
            
            resolved = self._resolve_includes(raw, inc_path, visited, resolved_deps)
            lines = [f"// {l.strip()}" if l.strip().startswith("#include") else l for l in resolved.splitlines()]
            
            result = []
            if preserved:
                result.extend(preserved)
                result.append("")
            result.extend(lines)
            if preserved:
                result.append("")
                result.append("// " + "="*70)
            return "\n".join(result)
        
        return self.resolve_include_pattern.pattern.sub(replace, content)

# ==============================================================
# HELIX INSTALLER CLASS
# ==============================================================

class HelixInstaller:
    """Encapsulates Helix install functionality for dependency resolution and output generation."""
    
    def __init__(self, console: Console):
        self.console = console
        self.downloader = DependencyDownloader(console)
        self.include_processor = IncludeModeProcessor(console)
        self.flat_processor = FlatModeProcessor(console)
    
    def install(self, locked_mode: bool = False, show_tree: bool = False) -> None:
        """Main entry point for install — resolves dependencies and generates output."""
        try:
            manifest = load_helix_manifest()
            effective_mode = IncludeMode.FLAT if manifest.type == ProjectType.PACKAGE else manifest.include_mode
            
            self._log_install_start(manifest, effective_mode)
            validate_include_project_structure(manifest, Path.cwd(), False, self.console)
            self._prepare_output_directories(manifest)
            
            resolved_deps = self._resolve_dependencies(manifest, locked_mode, show_tree)
            
            if effective_mode == IncludeMode.INCLUDE:
                self.include_processor.process(resolved_deps)
            else:
                self.flat_processor.process(manifest, resolved_deps)
            
            self._log_completion(resolved_deps, effective_mode)
            
        except Exception as e:
            self.console.log(f"[red]Error:[/] {e}")
    
    def _log_install_start(self, manifest: HelixManifest, effective_mode: IncludeMode) -> None:
        self.console.log(f"[bold magenta]helix install[/] → [bold cyan]{manifest.name}[/] v{manifest.version}")
        self.console.log(f"   ├─ type: {manifest.type.value}")
        self.console.log(f"   └─ mode: [bold]{effective_mode.value}[/] {'[bold yellow]FORCED[/]' if effective_mode != manifest.include_mode else ''}")
    
    def _prepare_output_directories(self, manifest: HelixManifest) -> None:
        shutil.rmtree(FLAT_DIR, ignore_errors=True)
        if manifest.type != ProjectType.PACKAGE:
            shutil.rmtree(INCLUDE_DIR, ignore_errors=True)
        elif INCLUDE_DIR.exists():
            self.console.log(f"[dim]Preserving[/] {INCLUDE_DIR.as_posix()} (project type is 'package')")
    
    def _resolve_dependencies(self, manifest: HelixManifest, locked_mode: bool, show_tree: bool) -> ResolvedDeps:
        with Progress(SpinnerColumn(), TextColumn("[bold blue]Solving dependencies...")) as progress:
            task = progress.add_task("", total=len(manifest.dependencies or {}))
            resolved_deps, dependency_tree = self.downloader.download_all(manifest.dependencies or {}, locked_mode)
            progress.update(task, advance=len(manifest.dependencies or {}))
        
        # Log dependency tree only if --tree flag is used and there are dependencies
        if show_tree and dependency_tree:
            self._log_dependency_tree(dependency_tree)
        
        return resolved_deps
    
    def _log_dependency_tree(self, dependency_tree: DependencyTree) -> None:
        """Log the dependency tree in a readable format."""
        self.console.log("\n[bold cyan]Dependency Tree:[/]")
        for node in dependency_tree:
            self._log_tree_node(node, "")
        self.console.log("")
    
    def _log_tree_node(self, node: DependencyNode, prefix: str) -> None:
        """Recursively log a dependency tree node."""
        is_last = node.parent is None or node == node.parent.children[-1]
        current_prefix = "├── " if not is_last else "└── "
        
        self.console.log(f"{prefix}{current_prefix}[bold]{node.name}[/] v{node.version}")
        
        child_prefix = prefix + ("│   " if not is_last else "    ")
        for child in node.children:
            self._log_tree_node(child, child_prefix)
    
    def _log_completion(self, resolved_deps: ResolvedDeps, effective_mode: IncludeMode) -> None:
        self.console.log(f"[green]Check[/] Resolved {len(resolved_deps)} dependenc{'y' if len(resolved_deps)==1 else 'ies'}")
        output_dir = INCLUDE_DIR if effective_mode == IncludeMode.INCLUDE else FLAT_DIR
        self.console.log(f"\n[bold green]Check install completed![/] → {output_dir.as_posix()}/")

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def install_command(locked_mode: bool, show_tree: bool):
    """Command wrapper for HelixInstaller."""
    installer = HelixInstaller(console)
    installer.install(locked_mode, show_tree)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def install(locked: Optional[bool] = typer.Option(False, "--locked", help="Fail if any dependency has local changes or does not match the lockfile. "
                    "Enables strict reproducible builds (recommended for CI/CD and production)."),
                tree: Optional[bool] = typer.Option(False, "--tree", help="Display dependency tree after resolution."),
                verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="Show detailed output with file/line information")):
        """Prepare the project: resolve recursive includes or generate flat files."""

        global console
        console = Console(log_path=verbose)
        install_command(locked, tree)