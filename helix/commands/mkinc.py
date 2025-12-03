# helix/commands/mkinc.py
# HELIX 2025 — mkinc

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
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

# ==============================================================
# CONSTANTES
# ==============================================================
INCLUDE_DIR = Path("helix/include")
FLAT_DIR = Path("helix/flat")
CACHE_DIR = Path(".helix/cache")
LOCKFILE = Path("helix/lock.json")

console = Console()

ResolvedDep = Tuple[str, Path]
ResolvedDeps = List[ResolvedDep]


# ==============================================================
# LOCKFILE
# ==============================================================

def load_lockfile() -> Dict:
    if LOCKFILE.exists():
        try:
            return json.loads(LOCKFILE.read_text(encoding="utf-8"))
        except:
            return {"version": "1", "dependencies": {}}
    return {"version": "1", "dependencies": {}}


def save_lockfile(data: Dict):
    data.setdefault("version", "1")
    LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    LOCKFILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ==============================================================
# LEITURA DE ARQUIVOS
# ==============================================================

def read_file_smart(path: Path) -> str:
    """
    Lê qualquer .mqh com encoding correto (UTF-8, UTF-16, etc.)
    e REMOVE O PROBLEMA DAS LINHAS EM BRANCO DO UTF-16!
    """
    raw = path.read_bytes()

    # 1. Tenta decodificar com BOM (o mais seguro)
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            # CRÍTICO: normaliza quebras de linha e remove \x00 residual do UTF-16
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.replace("\x00", "")  # remove null bytes do UTF-16
            return text
        except UnicodeDecodeError:
            continue

    # 2. Fallback com chardet
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"
    try:
        text = raw.decode(encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        return text
    except:
        pass

    # 3. Último recurso: força UTF-8 com replace
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    return text


# ==============================================================
# UTILS
# ==============================================================

def is_local_path(spec: str) -> bool:
    spec = spec.strip()
    if spec.startswith("file://"):
        return True
    if spec.startswith(("http://", "https://", "git@", "ssh://")):
        return False
    return any(spec.startswith(p) for p in ("./", "../", "/", "~")) or Path(spec).is_absolute()


def resolve_local_dependency(name: str, specifier: str) -> Path:
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

    console.log(f"[bold magenta]Local[/] {name} → {path}")
    return path.resolve()


# ==============================================================
# RESOLVE INCLUDES
# ==============================================================

def find_include_file(inc_file: str, base_path: Path, resolved_deps: ResolvedDeps) -> Path:
    candidates = [
        (base_path.parent / inc_file).resolve(),
        (INCLUDE_DIR / inc_file).resolve() if INCLUDE_DIR.exists() else None,
        *[(dep_path / inc_file).resolve() for _name, dep_path in resolved_deps]
    ]

    for path in candidates:
        if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
            return path

    raise FileNotFoundError(f"Include não encontrado: {inc_file}")


def resolve_includes(
    content: str,
    base_path: Path,
    visited: Set[Path],
    resolved_deps: ResolvedDeps,
) -> str:
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

# ==============================================================
# DOWNLOAD DEPENDENCY — RECURSIVO + VALIDAÇÃO RÍGIDA
# ==============================================================

# ==============================================================
# RESOLVE VERSION FROM SPECIFIER (A MÁGICA DO HELIX)
# ==============================================================

def resolve_version_from_spec(name: str, specifier: str, repo: git.Repo) -> str:
    """
    Resolve o que o usuário pediu em specifier → retorna o commit/tag exato
    Suporta: v1.8.2, ^1.8.0, branch=main, tag=v2.0.0, commit=abc123
    """
    if specifier.startswith(("branch=", "tag=", "commit=")):
        prefix, value = specifier.split("=", 1)
        if prefix == "commit":
            return value[:7]  # aceita parcial
        return value

    # Extrai versão semver (com ou sem v)
    clean_spec = specifier.lstrip("vV")
    try:
        version = Version(clean_spec)
        spec = SpecifierSet(f"=={version}")
    except InvalidVersion:
        spec = SpecifierSet(specifier)

    # Lista todas as tags
    tags = {}
    for tag in repo.tags:
        tag_name = tag.name.lstrip("vV")
        try:
            tags[Version(tag_name)] = tag.name
        except InvalidVersion:
            continue

    # Encontra a melhor versão compatível
    for version in sorted(tags.keys(), reverse=True):
        if str(version) in spec:
            return tags[version]

    # Fallback: HEAD
    console.log(f"[yellow]Warning:[/] No version compatible with '{specifier}' found in {name}. Falling back to HEAD.")
    return "HEAD"


# ==============================================================
# DOWNLOAD REMOTO (GIT)
# ==============================================================

def _download_from_git(name: str, specifier: str) -> Path:
    base_url = specifier.split("#")[0].rstrip("/")
    ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
    cache_key = hashlib.sha256(specifier.encode()).hexdigest()[:16]
    dep_path = CACHE_DIR / f"{name}_{cache_key}"

    lock_data = load_lockfile()
    locked = lock_data["dependencies"].get(name, {})

    # Usa lock se for o mesmo source + specifier
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

        # AQUI ESTÁ A MÁGICA: resolve_version_from_spec
        final_ref = resolve_version_from_spec(name, ref_spec, repo)

        try:
            repo.git.checkout(final_ref, force=True)
        except git.exc.GitCommandError as e:
            console.log(f"[red]Error:[/] Could not checkout '{final_ref}' for {name}")
            console.log(f"    → {e}")
            repo.git.checkout("HEAD", force=True)
            final_ref = "HEAD"

        commit = repo.head.commit.hexsha

        # Atualiza lockfile
        lock_data["dependencies"][name] = {
            "source": base_url,
            "specifier": ref_spec,
            "resolved": final_ref,
            "commit": commit,
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        save_lockfile(lock_data)

    # Validação rígida
    if not any((dep_path / f).exists() for f in ("helix.yaml", "helix.json")):
        console.log(f"[red]Fatal error:[/] Remote dependency '{name}' is not a Helix project")
        console.log(f"    → {base_url}#{ref_spec}")
        raise SystemExit(1)

    return dep_path


def _process_recursive_dependencies(dep_path: Path, dep_name: str, resolved_deps: ResolvedDeps):
    """Processa dependências recursivas — usado tanto para local quanto remoto"""
    try:
        sub_manifest = load_helix_manifest(dep_path)

        validate_include_project_structure(sub_manifest, dep_path, True)

        if sub_manifest.type == MQLProjectType.INCLUDE and sub_manifest.dependencies:
            console.log(f"[dim]Recursive:[/] {dep_name} → {len(sub_manifest.dependencies)} dep(s)")
            for sub_name, sub_spec in sub_manifest.dependencies.items():
                if sub_name.lower() not in {n.lower() for n, _ in resolved_deps}:
                    download_dependency(sub_name, sub_spec, resolved_deps)
    except Exception as e:
        console.log(f"[yellow]Warning:[/] Failed to process dependencies of {dep_name}: {e}")


def download_dependency(name: str, specifier: str, resolved_deps: ResolvedDeps) -> Path:
    name = name.lower()

    if is_local_path(specifier):
        dep_path = resolve_local_dependency(name, specifier)
    else:
        dep_path = _download_from_git(name, specifier)  # sua lógica git

    if (name, dep_path) not in resolved_deps:
        resolved_deps.append((name, dep_path))

    # RECURSÃO ACONTECE SEMPRE
    _process_recursive_dependencies(dep_path, name, resolved_deps)

    console.log(f"[green]Check[/] {name} → {dep_path.name}")
    return dep_path

# ==============================================================
# VALIDAÇÃO DE PROJETO INCLUDE (centralizada e reutilizável)
# ==============================================================

def validate_include_project_structure(
    manifest: HelixManifest,
    project_dir: Path,
    is_dependency: bool = False,
) -> None:
    """
    Valida que projetos do tipo 'include' tenham seus .mqh em helix/include/
    
    Chamada em:
    - mkinc_command() → projeto principal
    - _process_recursive_dependencies() → dependências recursivas
    
    Nível 1: apenas AVISO amigável (não quebra o build)
    """
    if manifest.type != MQLProjectType.INCLUDE:
        return  # só valida projetos include

    include_dir = project_dir / "helix" / "include"
    prefix = "[dep]" if is_dependency else "[projeto]"

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
# DETECÇÃO DE CONFLITOS NO MODO INCLUDE (SEGURANÇA PROFISSIONAL)
# ==============================================================

def safe_copy_with_conflict_warning(src: Path, dst_dir: Path, dep_name: str) -> None:
    """
    Copia arquivo do helix/include/ da dependência → helix/include/ do projeto principal
    com detecção de conflito inteligente.
    """
    # O src SEMPRE vem de dentro de um helix/include/ (de uma dependência)
    # Vamos extrair apenas o caminho relativo a partir do helix/include/
    try:
        # Encontra o helix/include mais próximo na árvore do src
        for parent in src.parents:
            if parent.name == "include" and parent.parent.name == "helix":
                rel_path = src.relative_to(parent)  # remove helix/include/
                break
        else:
            # Fallback seguro: usa apenas o nome do arquivo (raro)
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

    # Copia
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

# ==============================================================
# COMANDO PRINCIPAL
# ==============================================================

def mkinc_command():
    try:
        manifest = load_helix_manifest()
        effective_mode = (
            "include"
            if manifest.type == MQLProjectType.INCLUDE
            else "flat"
        )

        console.log(f"[bold magenta]helix mkinc[/] → {manifest.type.value} | mode: [bold]{effective_mode}[/]")

        # Validação do projeto principal
        validate_include_project_structure(manifest, Path.cwd(), False)

        for d in (INCLUDE_DIR, FLAT_DIR):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

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

            console.log(f"[bold green]Check Include mode completed![/] {total_copied} file(s) → helix/include/")
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

        console.log(f"\n[bold green]Check mkinc (flat) completed![/] → {FLAT_DIR}/")
    except Exception as e:
        console.log(f"[red]Error:[/] {e}")

# ==============================================================
# CLI
# ==============================================================

def register(app):
    @app.command()
    def mkinc():
        """Prepara o projeto: sincroniza includes recursivamente ou gera arquivos flat"""
        mkinc_command()