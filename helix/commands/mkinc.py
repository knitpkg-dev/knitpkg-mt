# helix/commands/mkinc.py
# Helix 2025 — mkinc definitivo
# Suporte completo a:
# • git + semver (^ ~ >=) + lockfile
# • path local (../minha-lib)
# • build_mode + regra especial para type: include
# • helix-lock.json com commit travado
# • cache inteligente + reproducibilidade total

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Set, Dict

import git
from packaging import version as semver_version, specifiers
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from helix.core.models import load_helix_manifest, BuildMode, MQLProjectType

from typer import Typer
import re

console = Console()
CACHE_DIR = Path(".helix/cache")
INCLUDE_DIR = Path("helix/include")
FLAT_DIR = Path("helix/flat")
LOCKFILE = Path("helix-lock.json")


# ==============================================================
# UTILIDADES
# ==============================================================

import chardet

def detect_encoding(path: Path) -> str:
    """
    Detecta encoding real do arquivo (UTF-8, UTF-16 LE, UTF-16 BE, Windows-1252, etc.)
    """
    try:
        raw = path.read_bytes()
        # Primeiro tenta BOM
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            return "utf-16"
        if raw.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"

        # Se não tiver BOM, usa chardet
        result = chardet.detect(raw[:10000])  # primeiros 10KB bastam
        enc = result["encoding"] or "utf-8"
        confidence = result["confidence"]

        if confidence < 0.7:
            # Fallback seguro para arquivos MQL antigos
            return "windows-1252" if b"\x00" not in raw[:100] else "utf-16"

        return enc.lower()
    except:
        return "utf-8"


def read_file_smart(path: Path) -> str:
    """
    Lê arquivo .mqh/.mq5 com encoding correto → sempre retorna str em UTF-8
    """
    enc = detect_encoding(path)
    try:
        text = path.read_text(encoding=enc, errors="replace")
    except:
        text = path.read_text(encoding="utf-8", errors="replace")

    # Garante que o resultado final seja limpo UTF-8
    return text.encode("utf-8", errors="replace").decode("utf-8")


def is_local_path(spec: str) -> bool:
    """Detecta se a dependência é um caminho local (relativo ou absoluto)"""
    if spec.startswith(("http://", "https://", "git@", "ssh://")):
        return False
    path = Path(spec)
    return path.exists() or (Path.cwd() / path).exists() or (Path.home() / path.relative_to("~") if spec.startswith("~") else Path()).exists()


def resolve_local_dependency(name: str, path_spec: str) -> Path:
    path_spec = path_spec.removeprefix("file://")
    path = Path(path_spec)
    if path_spec.startswith("~"):
        path = Path.home() / path.relative_to("~")
    path = (Path.cwd() / path).resolve()

    if not path.exists():
        raise ValueError(f"Dependência local '{name}' não encontrada: {path}")
    if not (path / "helix.json").exists():
        raise ValueError(f"Dependência local '{name}' não é um projeto Helix (falta helix.json): {path}")

    console.log(f"[bold magenta]Local[/] {name} → {path}")
    return path.resolve()


def resolve_version_from_spec(dep_name: str, full_spec: str, repo: git.Repo) -> str:
    """Resolve ^ ~ >= <= = ou retorna branch/commit/tag direto"""
    if "#" not in full_spec:
        return "HEAD"

    _, ref_spec = full_spec.split("#", 1)

    # Casos diretos
    if ref_spec.startswith(("branch=", "commit=", "tag=")):
        return ref_spec.split("=", 1)[-1]
    if re.match(r"^\d+\.\d+\.\d+$", ref_spec):
        return ref_spec

    # Busca tags semver
    try:
        raw_tags = repo.git.tag("-l").splitlines()
        candidates = []
        for tag in raw_tags:
            clean = tag.lstrip("vV")
            try:
                v = semver_version.parse(clean)
                if isinstance(v, semver_version.Version):
                    candidates.append((tag, v))
            except:
                continue

        if not candidates:
            return "HEAD"

        candidates.sort(key=lambda x: x[1], reverse=True)

        spec_set = specifiers.SpecifierSet(ref_spec)
        for tag, ver in candidates:
            if ver in spec_set:
                console.log(f"[green]Resolvido[/] {dep_name}: {ref_spec} → {tag}")
                return tag

        latest = candidates[0][0]
        console.log(f"[yellow]Sem match exato para {ref_spec}, usando mais recente: {latest}[/]")
        return latest
    except Exception:
        return "HEAD"


def load_lockfile() -> Dict:
    if LOCKFILE.exists():
        try:
            return json.loads(LOCKFILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"version": "1", "dependencies": {}}


def save_lockfile(data: Dict):
    LOCKFILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.log("[bold green]Check[/] helix-lock.json atualizado")


# ==============================================================
# DOWNLOAD / RESOLVE DEPENDÊNCIA
# ==============================================================

def download_dependency(name: str, specifier: str) -> Path:
    name = name.lower()

    # 1. PATH LOCAL → prioridade máxima
    if is_local_path(specifier):
        return resolve_local_dependency(name, specifier)

    # 2. GIT REMOTO
    base_url = specifier.split("#")[0]
    ref_spec = specifier.split("#", 1)[1] if "#" in specifier else "HEAD"
    cache_key = hashlib.sha256(specifier.encode()).hexdigest()[:16]
    dep_path = CACHE_DIR / f"{name}_{cache_key}"

    lock_data = load_lockfile()
    locked = lock_data["dependencies"].get(name, {})

    # Se já está travado no lock e o commit existe → usa direto
    if dep_path.exists() and locked.get("commit"):
        repo = git.Repo(dep_path)
        if repo.head.commit.hexsha == locked["commit"]:
            console.log(f"[green]Lock[/] {name} → {locked.get('resolved', 'HEAD')} (commit travado)")
            return dep_path

    # Senão: clona ou atualiza
    if not dep_path.exists():
        console.log(f"[bold blue]Clonando[/] {name} ← {base_url}")
        dep_path.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from(base_url, dep_path, single_branch=True, depth=50)

    repo = git.Repo(dep_path)
    repo.remotes.origin.fetch(tags=True)

    resolved_ref = resolve_version_from_spec(name, specifier, repo)
    repo.git.checkout(resolved_ref, force=True)
    final_commit = repo.commit("HEAD").hexsha

    # Atualiza lockfile
    lock_data["dependencies"][name] = {
        "source": base_url,
        "specifier": ref,
        "resolved": resolved_ref,
        "commit": final_commit,
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }
    save_lockfile(lock_data)

    console.log(f"[green]Check[/] {name} → {resolved_ref} @ {final_commit[:8]}")
    return dep_path


# ==============================================================
# FLATTENING (opcional)
# ==============================================================

# ==============================================================
# RESOLVE INCLUDES COM SUPORTE TOTAL A DEPENDÊNCIAS
# ==============================================================

def find_include_file(inc_file: str, base_path: Path, deps_paths: Dict[str, Path]) -> Path:
    candidates = [
        (base_path.parent / inc_file).resolve(),
        (INCLUDE_DIR / inc_file).resolve() if INCLUDE_DIR.exists() else None,
        *( (dep_path / inc_file).resolve() for dep_path in deps_paths.values() )
    ]

    for path in candidates:
        if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
            return path

    raise FileNotFoundError(f"Include não encontrado: {inc_file}")


def resolve_includes(content: str, base_path: Path, visited: Set[Path], deps_paths: Dict[str, Path]) -> str:
    import re
    pattern = re.compile(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', re.MULTILINE)

    def replace(match):
        inc_file = match.group(1)
        try:
            inc_path = find_include_file(inc_file, base_path, deps_paths)
        except FileNotFoundError as e:
            return f"// ERROR: {e}"

        if inc_path in visited:
            return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
        visited.add(inc_path)

        # ← AQUI ESTÁ A MÁGICA: lê com encoding correto
        raw = read_file_smart(inc_path)

        # Preserva #property
        preserved = [l for l in raw.splitlines() if l.strip().startswith(("#property copyright", "#property link", "#property version"))]

        resolved = resolve_includes(raw, inc_path, visited, deps_paths)

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
# COMANDO PRINCIPAL
# ==============================================================

def mkinc_command():
    manifest = load_helix_manifest()

    # Regra de ouro: type=include NUNCA faz flatten
    effective_mode = BuildMode.INCLUDES if manifest.type == MQLProjectType.INCLUDE else manifest.build_mode

    console.log(f"[bold magenta]helix mkinc[/] → {manifest.type.value} | modo: [bold]{effective_mode.value}[/]")

    # Limpa saídas anteriores
    for d in (INCLUDE_DIR, FLAT_DIR):
        if d.exists():
            shutil.rmtree(d)

    # Resolve todas as dependências (locais ou remotas)
    deps_paths: Dict[str, Path] = {}
    with Progress(SpinnerColumn(), TextColumn("[bold blue]Resolvendo dependências...")) as progress:
        task = progress.add_task("", total=len(manifest.dependencies))
        for name, spec in manifest.dependencies.items():
            deps_paths[name] = download_dependency(name, spec)
            progress.update(task, advance=1)

    # MODO FLAT
    # Dentro do mkinc_command(), no modo FLAT:
    if effective_mode == BuildMode.FLAT:
        FLAT_DIR.mkdir(parents=True, exist_ok=True)
        for entry in manifest.entrypoints:
            src = Path(entry)
            if not src.exists():
                console.log(f"[red]Erro:[/red] Entrypoint não encontrado: {entry}")
                continue

            content = read_file_smart(src)
            header = f"""// {'='*70}
// HELIX FLATTEN — DO NOT EDIT
// Project : {manifest.name} v{manifest.version}
// File    : {entry}
// {'='*70}\n\n"""
            content = header + content

            visited: Set[Path] = set()
            try:
                content = resolve_includes(content, src, visited, deps_paths)  # ← deps_paths aqui!
            except Exception as e:
                console.log(f"[red]Erro ao resolver includes em {entry}: {e}[/]")
                continue

            flat_file = FLAT_DIR / f"{src.stem}_flat{src.suffix}"
            flat_file.write_text(content, encoding="utf-8")
            console.log(f"[green]Check[/] {flat_file.name} gerado ({len(content.splitlines())} linhas)")

    # MODO INCLUDES (padrão)
    else:
        INCLUDE_DIR.mkdir(parents=True)
        total = 0
        for dep_name, dep_path in deps_paths.items():
            for mqh in dep_path.rglob("*.mqh"):
                rel = mqh.relative_to(dep_path / INCLUDE_DIR)
                target = INCLUDE_DIR / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(mqh, target)
                total += 1

        console.log(f"\n[bold green]Check mkinc concluído![/] {total} arquivo(s) → [bold]Includes/[/]")


# CLI
def register(app):
    @app.command()
    def mkinc():
        """Prepara o projeto: sincroniza includes ou gera arquivos flat"""
        mkinc_command()