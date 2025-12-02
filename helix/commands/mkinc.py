# helix/commands/mkinc.py
import hashlib
import shutil
from pathlib import Path
from typing import Set

import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from helix.core.models import load_helix_manifest, BuildMode, MQLProjectType

console = Console()
CACHE_DIR = Path(".helix/cache")
INCLUDES_DIR = Path("helix/includes")   # padrão do MetaTrader
FLAT_DIR = Path("helix/flat")           # arquivos _flat.mq5


def download_dependency(name: str, url: str) -> Path:
    ref = url.split("#")[-1] if "#" in url else "HEAD"
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:16]
    dep_path = CACHE_DIR / f"{name}_{cache_key}"

    if dep_path.exists():
        repo = git.Repo(dep_path)
        repo.remotes.origin.fetch(tags=True)
        repo.git.checkout(ref, force=True)
        console.log(f"[green]Cache[/] {name} → {ref}")
    else:
        console.log(f"[bold blue]Clonando[/] {name} → {ref}")
        dep_path.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from(url.split("#")[0], dep_path, single_branch=True)
        repo = git.Repo(dep_path)
        repo.git.checkout(ref)
    return dep_path


def resolve_includes(content: str, base_path: Path, visited: Set[Path]) -> str:
    import re
    pattern = re.compile(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', re.MULTILINE)

    def replace(match):
        inc_file = match.group(1)
        inc_path = (base_path.parent / inc_file).resolve()

        if inc_path in visited:
            return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
        if not inc_path.exists():
            return f"// MISSING INCLUDE: {inc_file}"

        visited.add(inc_path)
        raw = inc_path.read_text(encoding="utf-8", errors="ignore")

        # Preserva #property copyright, link, version
        preserved = [
            line for line in raw.splitlines()
            if line.strip().startswith(("#property copyright", "#property link", "#property version"))
        ]

        resolved = resolve_includes(raw, inc_path, visited)
        lines = [f"// {line.strip()}" if line.strip().startswith("#include") else line
                 for line in resolved.splitlines()]

        result = []
        if preserved:
            result.extend(preserved)
            result.append("")
        result.extend(lines)
        if preserved:
            result.append("")
            result.append("// " + "="*60)
        return "\n".join(result)

    return pattern.sub(replace, content)


def mkinc_command():
    manifest = load_helix_manifest()

    # Regra de ouro: projetos tipo "include" SEMPRE usam "includes"
    effective_mode = BuildMode.INCLUDES if manifest.type == MQLProjectType.INCLUDE else manifest.build_mode

    console.log(f"[bold magenta]helix mkinc[/] → tipo: [bold]{manifest.type.value}[/] → modo: [bold]{effective_mode.value}[/]")

    # Limpa saídas anteriores
    if INCLUDES_DIR.exists():
        shutil.rmtree(INCLUDES_DIR)
    if FLAT_DIR.exists() and any(FLAT_DIR.iterdir()):
        shutil.rmtree(FLAT_DIR)

    # Baixa todas as dependências
    deps_paths = {}
    with Progress(SpinnerColumn(), TextColumn("[bold blue]Baixando dependências..."), transient=True) as p:
        for name, url in manifest.dependencies.items():
            deps_paths[name] = download_dependency(name, url)
            p.update(0, advance=1)

    if effective_mode == BuildMode.FLAT:
        FLAT_DIR.mkdir(parents=True)
        for entry in manifest.entrypoints:
            src = Path(entry)
            if not src.exists():
                console.log(f"[red]Erro:[/red] Entrypoint não encontrado: {entry}")
                continue

            content = src.read_text(encoding="utf-8", errors="ignore")
            header = f"""// {'='*70}
// HELIX FLATTEN — DO NOT EDIT
// Project : {manifest.name} v{manifest.version}
// Target  : {manifest.target.value}
// File    : {entry}
// {'='*70}\n\n"""
            content = header + content

            visited: Set[Path] = set()
            content = resolve_includes(content, src, visited)

            flat_file = FLAT_DIR / f"{src.stem}_flat{src.suffix}"
            flat_file.write_text(content, encoding="utf-8")
            console.log(f"[green]Check[/] {flat_file.name} gerado")

        console.log(f"\n[bold green]Check mkinc (flat) concluído![/] Arquivos em {FLAT_DIR}/")

    else:  # build_mode == "includes" → padrão
        INCLUDES_DIR.mkdir(parents=True)
        total = 0
        for dep_name, dep_path in deps_paths.items():
            console.log(f"[cyan]Copiando[/] {dep_name} → Includes/")
            for mqh in dep_path.rglob("*.mqh"):
                rel = mqh.relative_to(dep_path)
                target = INCLUDES_DIR / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(mqh, target)
                total += 1

        console.log(f"\n[bold green]Check mkinc concluído![/] {total} arquivo(s) .mqh copiados → [bold]Includes/[/]")
        console.log("   Agora compile normalmente com MetaEditor ou `helix build`")


# Registro no CLI
def register(app):
    @app.command()
    def mkinc():
        """Prepara includes para compilação (sincroniza .mqh ou gera arquivos flat)"""
        mkinc_command()