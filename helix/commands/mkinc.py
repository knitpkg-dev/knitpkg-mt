# helix/commands/mkinc.py
# HELIX 2025 — mkinc

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Dict

from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

import chardet
import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from helix.core.models import (
    load_helix_manifest,
    HelixManifest,
    MQLProjectType,
    IncludeMode,
)

console = Console()

# ==============================================================
# CONSTANTS
# ==============================================================
INCLUDE_DIR = Path("helix/include")
FLAT_DIR = Path("helix/flat")
CACHE_DIR = Path(".helix/cache")
LOCKFILE = Path("helix/lock.json")

ResolvedDep = Tuple[str, Path]
ResolvedDeps = List[ResolvedDep]


# ==============================================================
# LOCKFILE
# ==============================================================

def load_lockfile() -> Dict:
    """Load the helix/lock.json file. Creates a minimal structure if missing or corrupted."""
    if LOCKFILE.exists():
        try:
            return json.loads(LOCKFILE.read_text(encoding="utf-8"))
        except:
            return {"version": "1", "dependencies": {}}
    return {"version": "1", "dependencies": {}}


def save_lockfile(data: Dict):
    """Write the lockfile with proper formatting and ensure parent directories exist."""
    data.setdefault("version", "1")
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKFILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ==============================================================
# FILE READING
# ==============================================================

def read_file_smart(path: Path) -> str:
    """
    Read any .mqh file with the correct encoding (UTF-8, UTF-16, etc.)
    and safely remove null bytes / line-ending issues common with UTF-16 files.
    """
    raw = path.read_bytes()

    # 1. Try BOM-aware encodings first (most reliable)
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            # Normalize line endings and strip null bytes left by UTF-16
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.replace("\x00", "")
            return text
        except UnicodeDecodeError:
            continue

    # 2. Fallback to chardet detection
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"
    try:
        text = raw.decode(encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        return text
    except:
        pass

    # 3. Last resort: force UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    return text


# ==============================================================
# UTILS
# ==============================================================

def is_local_path(spec: str) -> bool:
    """Return True if the specifier points to a local filesystem path."""
    spec = spec.strip()
    if spec.startswith("file://"):
        return True
    if spec.startswith(("http://", "https://", "git@", "ssh://")):
        return False
    return any(spec.startswith(p) for p in ("./", "../", "/", "~")) or Path(spec).is_absolute()


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


def resolve_includes(
    content: str,
    base_path: Path,
    visited: Set[Path],
    resolved_deps: ResolvedDeps,
) -> str:
    """Recursively resolve all #include directives, preserving #property lines and avoiding cycles."""
    pattern = re.compile(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', re.MULTILINE)

    def replace(match):
        inc_file = match.group(1)
        try:
            inc_path = find_include_file(inc_file, base_path, resolved_deps)
        except FileNotFoundError:
            console.log(f"[red]ERROR:[/] Include not found in {base_path} → {inc_file}")
            return f"// ERROR: Include not found → {inc_file}"

        if inc_path in visited:
            return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
        visited.add(inc_path)

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

    return pattern.sub(replace, content)


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

def _download_from_git(name: str, specifier: str) -> Path:
    """Clone or update a remote git dependency and resolve the correct ref using lockfile when possible."""
    base_url = specifier.split("#")[0].rstrip("/")
    ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
    cache_key = hashlib.sha256(specifier.encode()).hexdigest()[:16]
    dep_path = CACHE_DIR / f"{name}_{cache_key}"

    lock_data = load_lockfile()
    locked = lock_data["dependencies"].get(name, {})

    # Use lockfile when source + specifier match and directory exists
    if (locked.get("source") == base_url and
        locked.get("specifier") == ref_spec and
        dep_path.exists()):
        final_ref = locked.get("resolved", "HEAD")
        console.log(f"[dim]Cache[/] {name} → {final_ref}")
    else:
        if not dep_path.exists():
            console.log(f"[bold blue]Cloning[/] {name} ← {base_url}")
            dep_path.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=50)

        repo = git.Repo(dep_path)
        repo.remotes.origin.fetch(tags=True, prune=True)

        # Resolve the best matching tag/commit
        final_ref = resolve_version_from_spec(name, ref_spec, repo)

        try:
            repo.git.checkout(final_ref, force=True)
        except git.exc.GitCommandError as e:
            console.log(f"[red]Error:[/] Could not checkout '{final_ref}' for {name}")
            console.log(f"    → {e}")
            repo.git.checkout("HEAD", force=True)
            final_ref = "HEAD"

        commit = repo.head.commit.hexsha

        # Update lockfile
        lock_data["dependencies"][name] = {
            "source": base_url,
            "specifier": ref_spec,
            "resolved": final_ref,
            "commit": commit,
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        save_lockfile(lock_data)

    # Strict validation
    if not any((dep_path / f).exists() for f in ("helix.yaml", "helix.json")):
        console.log(f"[red]Fatal error:[/] Remote dependency '{name}' is not a Helix project")
        console.log(f"    → {base_url}#{ref_spec}")
        raise SystemExit(1)

    return dep_path


def _process_recursive_dependencies(dep_path: Path, dep_name: str, resolved_deps: ResolvedDeps):
    """Process recursive dependencies for both local and remote projects."""
    try:
        sub_manifest = load_helix_manifest(dep_path)

        console.log(f"[dim cyan]↳ processing dependency[/] [bold]{dep_name}[/] → {sub_manifest.name} v{sub_manifest.version}")

        validate_include_project_structure(sub_manifest, dep_path, True)

        if sub_manifest.type == MQLProjectType.INCLUDE and sub_manifest.dependencies:
            console.log(f"[dim]Recursive:[/] {dep_name} → {len(sub_manifest.dependencies)} dep(s)")
            for sub_name, sub_spec in sub_manifest.dependencies.items():
                if sub_name.lower() not in {n.lower() for n, _ in resolved_deps}:
                    download_dependency(sub_name, sub_spec, resolved_deps)
    except Exception as e:
        console.log(f"[yellow]Warning:[/] Failed to process dependencies of {dep_name}: {e}")


def download_dependency(name: str, specifier: str, resolved_deps: ResolvedDeps) -> Path:
    """Download (or resolve) a dependency and recursively process its own dependencies."""
    name = name.lower()

    if is_local_path(specifier):
        dep_path = resolve_local_dependency(name, specifier)
    else:
        dep_path = _download_from_git(name, specifier)

    if (name, dep_path) not in resolved_deps:
        resolved_deps.append((name, dep_path))

    # Always process recursive dependencies
    _process_recursive_dependencies(dep_path, name, resolved_deps)

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

def mkinc_command():
    """Main entry point for `helix mkinc` — resolves dependencies and generates output."""
    try:
        manifest = load_helix_manifest()
        
        effective_mode = IncludeMode.FLAT if manifest.type == MQLProjectType.INCLUDE else manifest.include_mode

        console.log(f"[bold magenta]helix mkinc[/] → [bold cyan]{manifest.name}[/] v{manifest.version}")
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
                download_dependency(name, spec, resolved_deps)
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
        console.log(f"\n[bold green]Check mkinc completed![/] → {output_dir.as_posix()}/")

    except Exception as e:
        console.log(f"[red]Error:[/] {e}")

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def mkinc():
        """Prepare the project: resolve recursive includes or generate flat files."""
        mkinc_command()