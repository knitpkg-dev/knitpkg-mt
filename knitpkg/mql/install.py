from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Set, Optional

from knitpkg.core.path_helper import navigate_path
from knitpkg.core.file_reading import load_knitpkg_manifest, read_source_file_smart

from knitpkg.mql.constants import FLAT_DIR, INCLUDE_DIR
from knitpkg.mql.models import MQLKnitPkgManifest, MQLProjectType, IncludeMode
from knitpkg.mql.dependency_downloader import MQLDependencyDownloader
from knitpkg.mql.warnings import warn_mql_project_structure
from knitpkg.mql.constants import INCLUDE_DIR
from knitpkg.core.global_config import get_registry_url
from knitpkg.core.dependency_downloader import ProjectNode
from knitpkg.core.console import Console, ConsoleAware

from knitpkg.core.exceptions import KnitPkgError
from knitpkg.mql.exceptions import InvalidDirectiveError, IncludeFileNotFoundError

# ==============================================================
# KNITPKG INCLUDE DIRECTIVES PATTERN CLASS
# ==============================================================

class ResolveKnitPkgIncludePattern:
    """
    Parses KnitPkg include directives from MQL source code.

    Matches patterns like:
    - /* @knitpkg:include "knitpkg/include/AdditionalPath.mqh" */

    Attributes:
        include_path: Original include path from #include statement
        directive: KnitPkg directive type ('include' or 'replace-with')
        replace_path: Replacement path specified in directive
        pattern: Compiled regex pattern for matching
    """

    def __init__(self):
        self.include_path: Optional[str] = None
        self.directive: Optional[str] = None
        self.directive_path: Optional[str] = None

        self.pattern = re.compile(
            r'^\s*#\s*include\s+"(?P<include_path>[^"]+)"\s*$'
            r'|'
            r'^\s*/\*\s*@knitpkg:(?P<directive>\w+(?:-\w+)*)\s+"(?P<directive_path>[^"]+)"\s*\*/\s*$',
            re.MULTILINE
        )

    def extract_groups(self, match: re.Match) -> None:
        """Extract named groups from regex match and store in instance variables."""
        self.include_path = match.group("include_path")
        self.directive = match.group("directive")
        self.directive_path = match.group("directive_path")

# ==============================================================
# INCLUDE MODE PROCESSOR CLASS
# ==============================================================

class IncludeModeDelegate(ConsoleAware):
    """Handles include mode processing."""

    def __init__(self, project_dir: Path, console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console, verbose)

        self.project_dir: Path = project_dir
        self.resolve_include_pattern: ResolveKnitPkgIncludePattern = ResolveKnitPkgIncludePattern()

    def process(self, root_node: ProjectNode) -> None:
        """Process dependencies in include mode."""
        self.log("[bold blue]Resolving dependencies... ('include' mode)[/]")

        include_dir = self.project_dir / INCLUDE_DIR
        include_dir.mkdir(parents=True, exist_ok=True)
        total_copied = 0

        resolved_deps: List[tuple[str, Path]] = root_node.resolved_dependencies()
        self.log(f"[dim]found[/] {len(resolved_deps)} dependency(ies)")

        for dep, dep_path in resolved_deps:
            dep_include_dir = dep_path / "knitpkg" / "include"
            if not dep_include_dir.exists():
                self.log(f"[dim]no include[/] {dep} → no knitpkg/include/")
                continue

            mqh_files = list(dep_include_dir.rglob("*.mqh"))
            if not mqh_files:
                continue

            self.log(f"[dim]copying[/] {dep} → {len(mqh_files)} file(s)")
            for src in mqh_files:
                self._safe_copy_with_conflict_warning(src, include_dir, dep)
                total_copied += 1

        self.log(
            f"[bold green]✔ Include mode:[/] {total_copied} file(s) copied → "
            f"[bold]knitpkg/include/[/]"
        )
        self._process_directives(include_dir)

    def _process_directives(self, include_dir: Path) -> None:
        """Process knitpkg directives in copied files."""
        log_neutralize = True
        for mqh_file in include_dir.rglob("*.mqh"):
            content = mqh_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            modified = False

            for i, line in enumerate(lines):
                match = self.resolve_include_pattern.pattern.match(line)
                if match:
                    self.resolve_include_pattern.extract_groups(match)
                    include_path = self.resolve_include_pattern.include_path
                    directive = self.resolve_include_pattern.directive
                    replace_path = self.resolve_include_pattern.directive_path

                    if directive == 'include' and replace_path is not None:
                        lines[i] = (
                            f'#include "{navigate_path(mqh_file.parent, self.project_dir / INCLUDE_DIR / replace_path).as_posix()}" '
                            f'/*** ← dependence added by KnitPkg ***/'
                        )
                        modified = True
                    elif include_path is not None and '/autocomplete/autocomplete.mqh' in Path(include_path).as_posix():
                        if log_neutralize:
                            self.log(
                                f"[dim]neutralizing[/] autocomplete includes in copied files..."
                            )
                            log_neutralize = False
                        lines[i] = (
                            f"// {line.strip()}  "
                            f"/*** ← disabled by KnitPkg install (dev helper) ***/"
                        )
                        modified = True
                    else:
                        raise InvalidDirectiveError(line)

            if modified:
                mqh_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _safe_copy_with_conflict_warning(
        self,
        src: Path,
        dst_dir: Path,
        dep_name: str
    ) -> None:
        """Copy a header detecting and warning about content conflicts."""
        try:
            for parent in src.parents:
                if parent.name == "include" and parent.parent.name == "knitpkg":
                    rel_path = src.relative_to(parent)
                    break
            else:
                rel_path = src.name
        except Exception:
            rel_path = src.name

        dst = dst_dir / rel_path

        if dst.exists():
            try:
                src_content = read_source_file_smart(src)
                dst_content = read_source_file_smart(dst)
                if src_content.strip() != dst_content.strip():
                    self.print( 
                        f"[bold red]CONFLICT DETECTED:[/] {dst.name} will be "
                        f"overwritten by '{dep_name}'"
                    )
                    self.print(f"    → Different content conflict!")
                else:
                    self.log(
                        f"[dim]duplicate header[/] {dst.name} (same content, skipped)"
                    )
                    return
            except Exception as e:
                self.print( 
                    f"[yellow]Warning:[/] Could not compare content of {dst.name}: {e}"
                )

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

# ==============================================================
# FLAT MODE PROCESSOR CLASS
# ==============================================================

class FlatModeDelegate(ConsoleAware):
    """Handles flat mode processing."""

    def __init__(self, project_dir: Path, console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console, verbose)

        self.project_dir = project_dir
        self.resolve_include_pattern: ResolveKnitPkgIncludePattern = ResolveKnitPkgIncludePattern()

    def process(self, manifest: MQLKnitPkgManifest, root_node: ProjectNode) -> None:
        """Process entrypoints in flat mode."""

        self.log(f"[bold blue]Resolving dependencies... ('flat' mode)[/]")
        flat_dir = self.project_dir / FLAT_DIR
        flat_dir.mkdir(parents=True, exist_ok=True)

        resolved_deps: List[tuple[str, Path]] = root_node.resolved_dependencies()

        for entry in manifest.entrypoints or []:
            src = self.project_dir / entry
            if not src.exists():
                self.print(f"[red]Error:[/] entrypoint not found: {entry}") 
                continue

            content = read_source_file_smart(src)
            header = (
                f"// {'='*70}\n"
                f"// KNITPKG FLAT — DO NOT EDIT\n"
                f"// Project: {manifest.name} v{manifest.version}\n"
                f"// File: {entry}\n"
                f"// {'='*70}\n\n"
            )
            content = header + content

            visited = set()
            content = self._resolve_includes(content, src, visited, resolved_deps)

            flat_file = flat_dir / f"{src.stem}_flat{src.suffix}"
            flat_file.write_text(content, encoding="utf-8")
            self.log(f"[green]✔[/] {flat_file.name} generated")

    def _find_include_file_local(
        self,
        inc_file: str,
        base_path: Path,
    ) -> Path:
        """Search for an #include file in the current project."""

        path = (base_path.parent / inc_file).resolve()
        if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
            return path

        raise IncludeFileNotFoundError(inc_file, "the current project")

    def _find_include_file_deps(
        self,
        inc_file: str,
        resolved_deps: List[tuple[str, Path]]
    ) -> Path:
        """Search for an #include file in all resolved dependencies."""

        candidates = [(dep_path / INCLUDE_DIR / inc_file).resolve() for _name, dep_path in resolved_deps]

        for path in candidates:
            if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
                return path

        raise IncludeFileNotFoundError(inc_file, "any resolved dependencies")

    def _resolve_includes(
        self,
        content: str,
        base_path: Path,
        visited: Set[Path],
        resolved_deps: List[tuple[str, Path]]
    ) -> str:
        """Recursively resolve all #include directives, preserving #property lines and avoiding cycles."""

        def replace(match: re.Match):
            self.resolve_include_pattern.extract_groups(match)
            include_path: Optional[str] = self.resolve_include_pattern.include_path
            directive: Optional[str] = self.resolve_include_pattern.directive
            directive_path: Optional[str] = self.resolve_include_pattern.directive_path

            inc_file = None
            inc_path = None
            if directive is None and include_path is not None:
                inc_file = include_path.strip()
                if '/autocomplete/autocomplete.mqh' in Path(inc_file).as_posix():
                    return f"// Ignoring autocomplete.mqh\n"
                
                inc_path = self._find_include_file_local(inc_file, base_path)

            elif directive == 'include' and directive_path is not None:
                inc_file = directive_path.strip()
                if '/autocomplete/autocomplete.mqh' in Path(inc_file).as_posix():
                    return f"// Ignoring autocomplete.mqh\n"
                
                inc_path = self._find_include_file_deps(inc_file, resolved_deps)
                self.log(f"[dim]@knitpkg:include found:[/] '{inc_file}'")

            else:
                raise InvalidDirectiveError(match.group(0))

            inc_path_abs = inc_path.absolute()
            if inc_path_abs in visited:
                return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
            visited.add(inc_path_abs)

            raw = read_source_file_smart(inc_path)
            preserved = [
                l for l in raw.splitlines()
                if l.strip().startswith((
                    "#property copyright",
                    "#property link",
                    "#property version"
                ))
            ]

            resolved = self._resolve_includes(raw, inc_path, visited, resolved_deps)
            lines = [
                f"// {l.strip()}" if l.strip().startswith("#include") else l
                for l in resolved.splitlines()
            ]

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
# KNITPKG INSTALLER CLASS
# ==============================================================

class ProjectInstaller(ConsoleAware):
    """
    Encapsulates KnitPkg install functionality for dependency resolution
    and output generation.
    """

    def __init__(self, project_dir: Path, locked_mode: bool, console: Console, verbose: bool):
        super().__init__(console, verbose)

        self.project_dir = project_dir
        registry_url = get_registry_url()
        self.downloader = MQLDependencyDownloader(project_dir, registry_url, locked_mode,
                                                  MQLKnitPkgManifest, console, verbose)
        self.locked_mode: bool = locked_mode

    def install(self, show_tree: bool = True) -> None:
        """
        Main entry point for install — resolves dependencies and generates output.

        Raises:
            SystemExit: On fatal errors (dependency not found, locked mode violations, etc.)
        """
        manifest: MQLKnitPkgManifest = load_knitpkg_manifest(
            self.project_dir,
            manifest_class=MQLKnitPkgManifest
        )

        effective_mode = (
            IncludeMode.FLAT
            if manifest.type == MQLProjectType.PACKAGE
            else manifest.include_mode
        )

        self._log_install_start(manifest, effective_mode)

        # Validate main project structure
        warn_mql_project_structure(
            manifest,
            self.project_dir,
            is_dependency=False,
            console=self
        )

        self._prepare_output_directories(manifest)

        self.print("📦 Downloading dependencies...") 
        root_node: ProjectNode = self.downloader.download_all()
        
        if not root_node:
            self.log("[dim]No dependencies to install[/]")
        else:
            self.log("[green]✔[/] All dependencies downloaded")

        if show_tree and root_node:
            self._log_dependency_tree(root_node)

        if effective_mode == IncludeMode.INCLUDE:
            self.print("📝 Generating include files...") 
            include_delegate = IncludeModeDelegate(self.project_dir, self.console, self.verbose)
            include_delegate.process(root_node)
        else:
            self.print("📝 Generating flat files...") 
            flat_processor = FlatModeDelegate(self.project_dir, self.console, self.verbose)
            flat_processor.process(manifest, root_node)

        self._log_completion(root_node, effective_mode)


    def _log_install_start(
        self,
        manifest: MQLKnitPkgManifest,
        effective_mode: IncludeMode
    ) -> None:
        self.print(  
            f"📦 [bold magenta]Install[/] → [cyan]@{manifest.organization}/{manifest.name}[/] : "
            f"{manifest.version} ({manifest.type})"
        )
        if effective_mode != manifest.include_mode:
            self.log(
                f"       (project type '{manifest.type}' enforces "
                f"[bold yellow]'{effective_mode.value}'[/] mode)"
            )

    def _prepare_output_directories(self, manifest: MQLKnitPkgManifest) -> None:
        self.print("📁 Preparing knitpkg package directories...")  
        flat_dir = self.project_dir / FLAT_DIR
        include_dir = self.project_dir / INCLUDE_DIR

        shutil.rmtree(flat_dir, ignore_errors=True)
        if manifest.type != MQLProjectType.PACKAGE:
            shutil.rmtree(include_dir, ignore_errors=True)
        elif include_dir.exists():
            self.log(
                f"[dim]Preserving[/] {INCLUDE_DIR.as_posix()} "
                f"(project type is 'package')"
            )

    def _log_dependency_tree(self, root_node: ProjectNode) -> None:
        """Log the dependency tree in a readable format."""
        self.print("\n🌳 [bold cyan]Dependency Tree:[/]") 
        self._log_tree_node(root_node, "")
        self.print("")

    def _log_tree_node(self, node: ProjectNode, prefix: str) -> None:
        """Recursively log a dependency tree node."""
        current_prefix = " ├── " if not node.is_root else " └── "

        self.print(f"{prefix}{current_prefix}[bold]{node.name}[/] : {node.version}")

        child_prefix = prefix + (" │   " if not node.is_root else "     ")
        for child in node.dependencies:
            self._log_tree_node(child, child_prefix)

    def _log_completion(
        self,
        node: ProjectNode,
        effective_mode: IncludeMode
    ) -> None:
        resolved_deps_len = len(node.resolved_names(add_root=False))
        self.log(
            f"[green]✔[/] Resolved {resolved_deps_len} "
            f"dependenc{'y' if resolved_deps_len==1 else 'ies'}"
        )
        output_dir = INCLUDE_DIR if effective_mode == IncludeMode.INCLUDE else FLAT_DIR
        self.print( 
            f"\n✅ [bold green]Install completed![/] → {output_dir.as_posix()}/"
        )
