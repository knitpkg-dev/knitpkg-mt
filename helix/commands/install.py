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

from helix.commands.autocomplete import navigate_path

from helix.core.models import (
    load_helix_manifest,
    HelixManifest,
    MQLProjectType,
    IncludeMode,
)

from helix.core.constants import LOCKFILE, CACHE_DIR, FLAT_DIR, INCLUDE_DIR
from helix.core.lockfile import load_lockfile, save_lockfile
from helix.core.file_reading import read_file_smart
from helix.core.utils import is_local_path

console: Console = None

ResolvedDep = Tuple[str, Path]
ResolvedDeps = List[ResolvedDep]


# ==============================================================
# UTILS
# ==============================================================

def resolve_local_dependency(name: str, specifier: str) -> Path:
    """Resolve a local dependency path and validate it contains a helix manifest."""

    if specifier.startswith("file://"):
        path = Path(specifier[7:])
    else:
        path = (Path.cwd() / specifier).resolve()

    if not path.exists():
        console.log(f"[red]Error:[/] Local dependency '{name}' not found: {path}")
        raise SystemExit(1)

    if not (path / "helix.yaml").exists() and not (path / "helix.json").exists():
        console.log(f"[red]Fatal error:[/] Local dependency '{name}' is not a Helix project")
        console.log(f"    → {path}")
        console.log("    Reason: missing helix.yaml or helix.json")
        raise SystemExit(1)

        # Tenta o melhor caminho relativo possível
    try:
        rel = path.relative_to(Path.cwd())
        if str(rel) == ".":
            rel_str = "."
        else:
            rel_str = f"./{rel}"
    except ValueError:
        try:
            rel = path.relative_to(Path.cwd().parent)
            rel_str = f"../{rel}"
        except ValueError:
            rel_str = path.name  # último recurso

    console.log(f"[bold magenta]Local[/] {name} → [dim]{rel_str}[/]")

    return path.resolve()


# ==============================================================
# INCLUDE RESOLUTION
# ==============================================================

def find_include_file(inc_file: str, base_path: Path, resolved_deps: ResolvedDeps) -> Path:
    """Search for an #include file in the current project and all resolved dependencies."""
    candidates = [
        (base_path.parent / inc_file).resolve(),
        (INCLUDE_DIR / inc_file).resolve() if INCLUDE_DIR.exists() else None,
        *[(dep_path / inc_file).resolve() for _name, dep_path in resolved_deps]
    ]

    for path in candidates:
        if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
            return path

    raise FileNotFoundError(f"Include not found: {inc_file}")


_resolve_includes_pattern = re.compile(
    r'^\s*#\s*include\s+"(?P<include>[^"]+)"'
    r'(?:\s*/\*\s*@helix:(?P<directive1>\w+(?:-\w+)*)\s+"(?P<path1>[^"]+)"\s*\*/)?\s*$'
    r'|'
    r'^\s*/\*\s*@helix:(?P<directive2>\w+(?:-\w+)*)\s+"(?P<path2>[^"]+)"\s*\*/\s*$',
    re.MULTILINE
)

def resolve_includes(
    content: str,
    base_path: Path,
    visited: Set[Path],
    resolved_deps: ResolvedDeps,
) -> str:
    """Recursively resolve all #include directives, preserving #property lines and avoiding cycles."""

    def replace(match: re.Match):
        # Extract values safely
        include_path: str = match.group('include')
        directive: str    = match.group('directive1') or match.group('directive2')
        replace_path: str = match.group('path1') or match.group('path2')

        if directive is None: # normal include
            inc_file = include_path.strip()
        
        elif directive == 'include': # /* @helix:include "path" */
            inc_file = replace_path.strip()
            console.log(f"[dim]@helix:include found:[/] '{inc_file}'")
        
        elif directive == 'replace-with': # #include "../../autocomplete.mqh" /* @helix:replace-with "helix/include/Bar/Bar.mqh" */
            inc_file = replace_path.strip()
            console.log(f"[dim]@helix:replace-with found:[/] '{inc_file}'")
        
        else:
            console.log(f"[red]ERROR:[/] Invalid @helix:<directive> → '{directive}'")
            return f"// ERROR: Invalid @helix:<directive> → '{directive}'"

        try:
            inc_path = find_include_file(inc_file, base_path, resolved_deps)
        except FileNotFoundError:
            console.log(f"[red]ERROR:[/] Include not found in {base_path} → {inc_file}")
            return f"// ERROR: Include not found → {inc_file}"

        inc_path_abs = inc_path.absolute()
        if inc_path_abs in visited:
            return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
        visited.add(inc_path_abs)

        raw = read_file_smart(inc_path)
        preserved = [l for l in raw.splitlines() if l.strip().startswith(("#property copyright", "#property link", "#property version"))]

        resolved = resolve_includes(raw, inc_path, visited, resolved_deps)
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

    return _resolve_includes_pattern.sub(replace, content)


def resolve_version_from_spec(name: str, specifier: str, repo: git.Repo) -> str:
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
        console.log(f"[yellow]Warning:[/] Invalid specifier '{specifier}' for {name}. Accepting any version.")
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
        console.log(f"[yellow]Warning:[/] No valid SemVer tags in {name}. Using HEAD.")
        return "HEAD"

    # === 4. Sort: newest version first, build-metadata wins on ties ===
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # === 5. Find first matching version ===
    for version, tag_name in candidates:
        if version in spec:
            return tag_name

    # === 6. Fallback ===
    console.log(f"[yellow]Warning:[/] No compatible version for '{specifier}' in {name}. Falling back to HEAD.")
    return "HEAD"


# ==============================================================
# REMOTE DOWNLOAD (GIT)
# ==============================================================

def _download_from_git(name: str, specifier: str, *, force_lock: bool = False) -> Path:
    """
    Download a remote Git dependency.
    
    Respects helix.lock.json completely:
      - If lock exists and directory exists → verify integrity
      - If lock exists and directory missing → checkout exact commit from lock
      - Otherwise → resolve version normally
    """
    base_url = specifier.split("#")[0].rstrip("/")
    ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
    cache_key = hashlib.sha256(specifier.encode()).hexsha[:16]
    dep_path = CACHE_DIR / f"{name}_{cache_key}"

    lock_data = load_lockfile()
    locked = lock_data["dependencies"].get(name, {})

    # CASE 1: lock + directory exist → check integrity
    if dep_path.exists() and locked.get("source") == base_url and locked.get("specifier") == ref_spec:
        status = _check_local_dep_integrity(dep_path, locked)

        if status == "clean":
            console.log(f"[dim]Cache hit[/] {name} → {locked.get('resolved', 'HEAD')[:8]}")
            return dep_path

        if force_lock:
            console.log(f"[red]Error:[/] Cannot proceed with --locked: dependency '{name}' has local changes")
            raise SystemExit(1)

        console.log(f"[bold yellow]Warning:[/] Local changes in '{name}' — using modified version")
        console.log(f"    Locked commit: {locked.get('commit', '?')[:8]}")
        console.log("    Use --locked to enforce lockfile integrity")
        return dep_path

    # CASE 2: lock exists, directory missing → force exact commit from lock
    elif locked.get("source") == base_url and locked.get("specifier") == ref_spec:
        commit = locked.get("commit")
        if not commit:
            console.log(f"[bold blue]Resolving[/] {name} ← {specifier}")
            return _download_and_resolve(name, specifier, dep_path)

        console.log(f"[bold green]Lockfile[/] {name} → {locked.get('resolved','HEAD')[:8]} ({commit[:8]})")
        dep_path.mkdir(parents=True, exist_ok=True)
        repo = git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=1)
        repo.git.checkout(commit)
        return dep_path

    # CASE 3: no lock or incompatible → normal resolution
    else:
        console.log(f"[bold blue]Resolving[/] {name} ← {specifier}")
        return _download_and_resolve(name, specifier, dep_path)
    

def _download_and_resolve(name: str, specifier: str, dep_path: Path) -> Path:
    """
    Download a remote Git dependency and resolve the best matching version/tag
    according to the specifier (SemVer ranges, ^, ~, branch=, tag=, commit=).

    This function is only called when:
      - No lockfile entry exists, or
      - The lockfile is being ignored (e.g. during `helix update`)

    Steps performed:
      1. Clone the repository (shallow, single-branch)
      2. Fetch tags
      3. Use resolve_version_from_spec() to find the best matching ref
      4. Checkout the resolved ref
      5. Update the lockfile with resolved version and commit SHA

    Args:
        name (str): Dependency name (for logging and lockfile)
        specifier (str): Full dependency specifier (e.g. "https://github.com/user/lib.git#^1.2.0")
        dep_path (Path): Local cache directory where the repo will be cloned

    Returns:
        Path: Path to the checked-out dependency
    """
    base_url = specifier.split("#")[0].rstrip("/")
    ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"

    console.log(f"[bold blue]Cloning[/] {name} ← {base_url}")
    dep_path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=50)

    console.log(f"[dim]Fetching tags[/] for {name}...")
    repo.remotes.origin.fetch(tags=True, prune=True)

    # Resolve the best matching version/tag/commit
    final_ref = resolve_version_from_spec(name, ref_spec, repo)

    try:
        console.log(f"[dim]Checking out[/] {name} → {final_ref}")
        repo.git.checkout(final_ref, force=True)
    except git.exc.GitCommandError as e:
        console.log(f"[red]Error:[/] Failed to checkout '{final_ref}' for {name}")
        console.log(f"    → Falling back to HEAD")
        repo.git.checkout("HEAD", force=True)
        final_ref = "HEAD"

    commit = repo.head.commit.hexsha

    # Update lockfile with resolved information
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


def _process_recursive_dependencies(dep_path: Path, dep_name: str, resolved_deps: ResolvedDeps) -> bool:
    """
    Process recursive dependencies.
    Return True if the dependency was accepted (is 'include'), False if skipped.
    """
    try:
        sub_manifest = load_helix_manifest(dep_path)

        # mkinc accepts dependencies of type 'include' only
        if sub_manifest.type != MQLProjectType.INCLUDE:
            console.log(
                f"[bold yellow]Skipping dependency[/] '{dep_name}' → {sub_manifest.name} v{sub_manifest.version}\n"
                f"    → type is '{sub_manifest.type.value}', but `helix install` only supports 'include' projects.\n"
                f"    Use `helix build` (Pro) to bundle experts, indicators, etc."
            )
            return False  # ← rejeitada

        console.log(f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] → {sub_manifest.name} v{sub_manifest.version}")

        validate_include_project_structure(sub_manifest, dep_path, True)

        if sub_manifest.dependencies:
            console.log(f"[dim]Recursive:[/] {dep_name} → {len(sub_manifest.dependencies)} dep(s)")
            for sub_name, sub_spec in sub_manifest.dependencies.items():
                if sub_name.lower() not in {n.lower() for n, _ in resolved_deps}:
                    download_dependency(sub_name, sub_spec, resolved_deps)

        return True  # ← aceita

    except Exception as e:
        console.log(f"[yellow]Warning:[/] Failed to process dependencies of {dep_name}: {e}")
        return False

# ==============================================================
# HELPER: Check integrity of a local dependency
# ==============================================================

def _check_local_dep_integrity(dep_path: Path, locked: dict) -> str:
    """
    Check if a local dependency is clean and reproducible.
    
    Returns:
        "clean"   — matches lockfile commit and no uncommitted changes
        "dirty"   — uncommitted changes
        "drifted" — current commit differs from locked commit
        "not-git" — not a Git repository
        "invalid" — error accessing repository
    """
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


# ==============================================================
# download_dependency — handles local and remote deps with full lock support
# ==============================================================

def download_dependency(
    name: str,
    specifier: str,
    resolved_deps: ResolvedDeps,
    *,
    locked_mode: bool = False,
) -> Path:
    """
    Resolve and download a dependency (local or remote).
    
    When --locked is active:
      - Local non-git dependencies → fail
      - Local git dependencies → use current commit
      - Remote dependencies → use exact commit from lockfile
    """
    name = name.lower()

    # ------------------------------------------------------------------
    # Local dependency (file:// or relative path)
    # ------------------------------------------------------------------
    if is_local_path(specifier):
        if specifier.startswith("file://"):
            dep_path = Path(specifier[7:])
        else:
            dep_path = (Path.cwd() / specifier).resolve()

        # Fatal: local path in helix.yaml but directory missing
        if not dep_path.exists():
            console.log(f"[red]Fatal error:[/] Local dependency '{name}' points to missing path:")
            console.log(f"    → {dep_path}")
            console.log("    Local paths in helix.yaml are not portable between machines.")
            console.log("    Use Git URLs for shared dependencies.")
            raise SystemExit(1)

        # Check if it's a Git repository
        has_git = False
        current_commit = None
        try:
            repo = git.Repo(dep_path, search_parent_directories=True)
            if not repo.bare:
                has_git = True
                current_commit = repo.head.commit.hexsha
        except Exception:
            pass

        # --locked + local non-git → fail
        if locked_mode and not has_git:
            console.log(f"[red]Error:[/] Cannot use --locked with non-git local dependency '{name}'")
            console.log(f"    → {dep_path}")
            console.log("    Add a Git repository or remove --locked for development only.")
            raise SystemExit(1)

        # Warn if local and not under Git
        if not has_git:
            console.log(f"[bold yellow]Warning:[/] Local dependency '{name}' has no Git history")
            console.log(f"    → {dep_path}")
            console.log("    This dependency is not reproducible across machines.")

        # Record exact commit in lockfile if it's a Git repo
        if has_git and current_commit:
            lock_data = load_lockfile()
            lock_data["dependencies"][name] = {
                "source": str(dep_path.resolve()),
                "specifier": specifier,
                "resolved": f"commit:{current_commit}",
                "commit": current_commit,
                "type": "local-git",
            }
            save_lockfile(lock_data)

        console.log(f"[bold magenta]Local{'-git' if has_git else ''}[/] {name} → {dep_path.name}")

        if _process_recursive_dependencies(dep_path, name, resolved_deps):
            if (name, dep_path) not in resolved_deps:
                resolved_deps.append((name, dep_path))
            console.log(f"[green]Check[/] {name} → {dep_path.name}")

        return dep_path.resolve()

    # ------------------------------------------------------------------
    # Remote dependency (Git URL)
    # ------------------------------------------------------------------
    else:
        dep_path = _download_from_git(name, specifier, force_lock=locked_mode)

        if _process_recursive_dependencies(dep_path, name, resolved_deps):
            if (name, dep_path) not in resolved_deps:
                resolved_deps.append((name, dep_path))
            console.log(f"[green]Check[/] {name} → {dep_path.name}")

        return dep_path

# ==============================================================
# INCLUDE PROJECT VALIDATION (centralized)
# ==============================================================

def validate_include_project_structure(
    manifest: HelixManifest,
    project_dir: Path,
    is_dependency: bool = False,
) -> None:
    """
    Ensure include-type projects have their .mqh files inside helix/include/.
    
    Called for both the main project and recursive dependencies.
    Emits friendly warnings only (does not break the build).
    """
    if manifest.type != MQLProjectType.INCLUDE:
        return

    include_dir = project_dir / "helix" / "include"
    prefix = "[dep]" if is_dependency else "[project]"

    if not include_dir.exists():
        console.log(f"[bold yellow]WARNING {prefix}:[/] Include-type project missing 'helix/include/' folder")
        console.log(f"    → {project_dir}")
        console.log("    Your .mqh files will not be exported to projects that depend on this one!")
        console.log("    Create the folder and move the files:")
        console.log("       mkdir -p helix/include")
        console.log("       git mv *.mqh helix/include/ 2>/dev/null || true")
        console.log("")
        return

    mqh_files = list(include_dir.rglob("*.mqh"))
    if not mqh_files:
        console.log(f"[bold yellow]WARNING {prefix}:[/] 'helix/include/' folder exists but is empty!")
        console.log(f"    → {project_dir}")
        console.log("    No .mqh files will be exported. Move your headers there.")
        console.log("")
    else:
        console.log(f"[green]Check {prefix}[/] {len(mqh_files)} .mqh file(s) found in helix/include/")

# ==============================================================
# SAFE COPY WITH CONFLICT DETECTION
# ==============================================================

def safe_copy_with_conflict_warning(src: Path, dst_dir: Path, dep_name: str) -> None:
    """
    Copy a header from a dependency's helix/include/ into the main project,
    detecting and warning about content conflicts.
    """
    # Extract path relative to the dependency's helix/include/
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
                console.log(
                    f"[bold red]CONFLICT DETECTED:[/] {dst.name} "
                    f"will be overwritten by '{dep_name}'"
                )
                console.log(f"    → Different content conflict!")
                console.log(f"       From: {dep_name}")
                console.log("       Already exists from another dependency")
                console.log("")
            else:
                console.log(f"[dim]duplicate header[/] {dst.name} (same content, skipped)")
                return
        except Exception as e:
            console.log(f"[yellow]Warning:[/] Could not compare content of {dst.name}: {e}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

# ==============================================================
# MAIN COMMAND
# ==============================================================

def install_command(locked_mode: bool):
    """Main entry point for `helix install` — resolves dependencies and generates output."""
    try:
        manifest = load_helix_manifest()

        effective_mode = IncludeMode.FLAT if manifest.type == MQLProjectType.INCLUDE else manifest.include_mode

        console.log(f"[bold magenta]helix install[/] → [bold cyan]{manifest.name}[/] v{manifest.version}")
        console.log(f"   ├─ type: {manifest.type.value}")
        console.log(f"   └─ mode: [bold]{effective_mode.value}[/] {'[bold yellow]FORCED[/]' if effective_mode != manifest.include_mode else ''}")

        # Validate main project structure
        validate_include_project_structure(manifest, Path.cwd(), False)

        shutil.rmtree(FLAT_DIR, ignore_errors=True)
        if manifest.type != MQLProjectType.INCLUDE:
            shutil.rmtree(INCLUDE_DIR, ignore_errors=True)
        else:
            if INCLUDE_DIR.exists():
                console.log(f"[dim]Preserving[/] helix/include/ (project type is 'include')")

        resolved_deps: ResolvedDeps = []

        with Progress(SpinnerColumn(), TextColumn("[bold blue]Solving dependencies...")) as progress:
            task = progress.add_task("", total=len(manifest.dependencies or {}))
            for name, spec in (manifest.dependencies or {}).items():
                download_dependency(name, spec, resolved_deps, locked_mode=locked_mode)
                progress.update(task, advance=1)

        if effective_mode == IncludeMode.INCLUDE:
            INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
            total_copied = 0

            for dep, dep_path in resolved_deps:
                dep_include_dir = dep_path / "helix" / "include"
                if not dep_include_dir.exists():
                    console.log(f"[dim]no include[/] {dep} → no helix/include/")
                    continue

                mqh_files = list(dep_include_dir.rglob("*.mqh"))
                if not mqh_files:
                    continue

                console.log(f"[dim]copying[/] {dep} → {len(mqh_files)} file(s)")
                for src in mqh_files:
                    safe_copy_with_conflict_warning(src, INCLUDE_DIR, dep)
                    total_copied += 1

            console.log(f"[bold green]Check Include mode:[/] {total_copied} file(s) copied → [bold]helix/include/[/]")

            log_neutralize = True
            for mqh_file in INCLUDE_DIR.rglob("*.mqh"):
                content = mqh_file.read_text(encoding="utf-8")
                lines = content.splitlines()
                modified = False

                for i, line in enumerate(lines):
                    match = _resolve_includes_pattern.match(line)
                    if match:
                        include_path = match.group('include')
                        directive    = match.group('directive1') or match.group('directive2')
                        replace_path = match.group('path1') or match.group('path2')

                        if directive is not None:
                            if directive == 'include': # /* @helix:include "path" */
                                lines[i] = f'#include "{navigate_path(mqh_file.parent,replace_path).as_posix()}" /*** ← dependence added by Helix ***/'

                            elif directive == 'replace-with': # #include "../../autocomplete.mqh" /* @helix:replace-with "helix/include/Bar/Bar.mqh" */
                                lines[i] = f'#include "{navigate_path(mqh_file.parent,replace_path).as_posix()}" /*** ← dependence resolved by Helix. Original include: "{include_path}" ***/'

                            modified = True

                        else: # directive is None, check if it is nedded to neutralize autocomplete includes (dev time only)
                            if '/autocomplete/autocomplete.mqh' in Path(include_path).as_posix():
                                if log_neutralize:
                                    console.log(f"[dim]neutralizing[/] autocomplete includes in copied files...")
                                    log_neutralize = False                                
                                lines[i] = f"// {line.strip()}  /*** ← disabled by Helix install (dev helper) ***/"
                                modified = True

                if modified:
                    mqh_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        else:
            FLAT_DIR.mkdir(parents=True, exist_ok=True)
            for entry in manifest.entrypoints or []:
                src = Path(entry)
                if not src.exists():
                    console.log(f"[red]Error:[/] entrypoint not found: {entry}")
                    continue

                content = read_file_smart(src)
                header = f"// {'='*70}\n// HELIX FLAT — DO NOT EDIT\n// Project: {manifest.name} v{manifest.version}\n// File: {entry}\n// {'='*70}\n\n"
                content = header + content

                visited = set()
                content = resolve_includes(content, src, visited, resolved_deps)

                flat_file = FLAT_DIR / f"{src.stem}_flat{src.suffix}"
                flat_file.write_text(content, encoding="utf-8")
                console.log(f"[green]Check[/] {flat_file.name} generated")

        console.log(f"[green]Check[/] Resolved {len(resolved_deps)} dependenc{'y' if len(resolved_deps)==1 else 'ies'}")

        output_dir = INCLUDE_DIR if effective_mode == IncludeMode.INCLUDE else FLAT_DIR
        console.log(f"\n[bold green]Check install completed![/] → {output_dir.as_posix()}/")

    except Exception as e:
        console.log(f"[red]Error:[/] {e}")

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def install(locked: Optional[bool] = typer.Option(False, "--locked", help="Fail if any dependency has local changes or does not match the lockfile. "
                    "Enables strict reproducible builds (recommended for CI/CD and production)."),
                verbose: Optional[bool] = typer.Option(False, "--verbose", "-v", help="Show detailed output with file/line information")):
        """Prepare the project: resolve recursive includes or generate flat files."""

        global console
        console = Console(log_path=verbose)
        install_command(locked)