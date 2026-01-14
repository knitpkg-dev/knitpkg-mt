# knitpkg/commands/install.py

"""
KnitPkg for Metatrader install command — dependency resolution and output generation.

This module orchestrates the installation process: downloading dependencies,
processing them in include or flat mode, and generating output files.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Tuple, Set, Optional

from rich.console import Console
import typer

from knitpkg.core.utils import navigate_path
from knitpkg.core.file_reading import load_knitpkg_manifest, read_file_smart

# Import MQL-specific models and downloader
from knitpkg.mql.constants import FLAT_DIR, INCLUDE_DIR
from knitpkg.mql.models import MQLKnitPkgManifest, MQLProjectType, IncludeMode
from knitpkg.mql.dependency_downloader import MQLDependencyDownloader
from knitpkg.mql.validators import validate_mql_project_structure
from knitpkg.mql.constants import INCLUDE_DIR
from knitpkg.core.global_config import get_registry_url

# Import shared types from core
from knitpkg.core.dependency_downloader import (
    DependencyNode,
    ResolvedDeps,
    DependencyTree
)

# Import custom exceptions
from knitpkg.core.exceptions import (
    LocalDependencyNotFoundError,
    LockedWithLocalDependencyError,
    DependencyHasLocalChangesError,
)

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
        self.include_path = None
        self.directive = None
        self.directive_path = None

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

class IncludeModeProcessor:
    """Handles include mode processing."""

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        self.resolve_include_pattern: ResolveKnitPkgIncludePattern = (
            ResolveKnitPkgIncludePattern()
        )

    def process(self, resolved_deps: ResolvedDeps) -> None:
        """Process dependencies in include mode."""
        self.console.log("[bold blue]Resolving dependencies... ('include' mode)[/]")

        include_dir = self.project_dir / INCLUDE_DIR
        include_dir.mkdir(parents=True, exist_ok=True)
        total_copied = 0

        for dep, dep_path in resolved_deps:
            dep_include_dir = dep_path / "knitpkg" / "include"
            if not dep_include_dir.exists():
                self.console.log(f"[dim]no include[/] {dep} → no knitpkg/include/")
                continue

            mqh_files = list(dep_include_dir.rglob("*.mqh"))
            if not mqh_files:
                continue

            self.console.log(f"[dim]copying[/] {dep} → {len(mqh_files)} file(s)")
            for src in mqh_files:
                self._safe_copy_with_conflict_warning(src, include_dir, dep)
                total_copied += 1

        self.console.log(
            f"[bold green]Check Include mode:[/] {total_copied} file(s) copied → "
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

                    if directive == 'include':
                        lines[i] = (
                            f'#include "{navigate_path(mqh_file.parent, self.project_dir / INCLUDE_DIR / replace_path).as_posix()}" '
                            f'/*** ← dependence added by KnitPkg ***/'
                        )
                        modified = True
                    elif '/autocomplete/autocomplete.mqh' in Path(include_path).as_posix():
                        if log_neutralize:
                            self.console.log(
                                f"[dim]neutralizing[/] autocomplete includes in copied files..."
                            )
                            log_neutralize = False
                        lines[i] = (
                            f"// {line.strip()}  "
                            f"/*** ← disabled by KnitPkg install (dev helper) ***/"
                        )
                        modified = True

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
                src_content = read_file_smart(src)
                dst_content = read_file_smart(dst)
                if src_content.strip() != dst_content.strip():
                    self.console.log(
                        f"[bold red]CONFLICT DETECTED:[/] {dst.name} will be "
                        f"overwritten by '{dep_name}'"
                    )
                    self.console.log(f"    → Different content conflict!")
                else:
                    self.console.log(
                        f"[dim]duplicate header[/] {dst.name} (same content, skipped)"
                    )
                    return
            except Exception as e:
                self.console.log(
                    f"[yellow]Warning:[/] Could not compare content of {dst.name}: {e}"
                )

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

# ==============================================================
# FLAT MODE PROCESSOR CLASS
# ==============================================================

class FlatModeProcessor:
    """Handles flat mode processing."""

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        self.resolve_include_pattern: ResolveKnitPkgIncludePattern = (
            ResolveKnitPkgIncludePattern()
        )

    def process(self, manifest: MQLKnitPkgManifest, resolved_deps: ResolvedDeps) -> None:
        """Process entrypoints in flat mode."""

        self.console.log(f"[bold blue]Resolving dependencies... ('flat' mode)[/]")
        flat_dir = self.project_dir / FLAT_DIR
        flat_dir.mkdir(parents=True, exist_ok=True)

        for entry in manifest.entrypoints or []:
            src = self.project_dir / entry
            if not src.exists():
                self.console.log(f"[red]Error:[/] entrypoint not found: {entry}")
                continue

            content = read_file_smart(src)
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
            self.console.log(f"[green]Check[/] {flat_file.name} generated")

    def _find_include_file_local(
        self,
        inc_file: str,
        base_path: Path,
    ) -> Path:
        """Search for an #include file in the current project."""

        path = (base_path.parent / inc_file).resolve()
        if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
            return path

        raise FileNotFoundError(f"Include not found in the current project: {inc_file}")

    def _find_include_file_deps(
        self,
        inc_file: str,
        resolved_deps: ResolvedDeps
    ) -> Path:
        """Search for an #include file in all resolved dependencies."""

        candidates = [(dep_path / INCLUDE_DIR / inc_file).resolve() for _name, dep_path in resolved_deps]

        for path in candidates:
            if path and path.exists() and path.suffix.lower() in {".mqh", ".mq4", ".mq5"}:
                return path

        raise FileNotFoundError(f"Include not found in any resolved dependencies: {inc_file}")

    def _resolve_includes(
        self,
        content: str,
        base_path: Path,
        visited: Set[Path],
        resolved_deps: ResolvedDeps
    ) -> str:
        """Recursively resolve all #include directives, preserving #property lines and avoiding cycles."""

        def replace(match: re.Match):
            self.resolve_include_pattern.extract_groups(match)
            include_path: str = self.resolve_include_pattern.include_path
            directive: str = self.resolve_include_pattern.directive
            directive_path: str = self.resolve_include_pattern.directive_path

            inc_file = None
            inc_path = None
            try:
                if directive is None:
                    inc_file = include_path.strip()
                    if '/autocomplete/autocomplete.mqh' in Path(inc_file).as_posix():
                        return f"// Ignoring autocomplete.mqh\n"
                    
                    inc_path = self._find_include_file_local(inc_file, base_path)

                elif directive == 'include':
                    inc_file = directive_path.strip()
                    if '/autocomplete/autocomplete.mqh' in Path(inc_file).as_posix():
                        return f"// Ignoring autocomplete.mqh\n"
                    
                    inc_path = self._find_include_file_deps(inc_file, resolved_deps)
                    self.console.log(f"[dim]@knitpkg:include found:[/] '{inc_file}'")

                else:
                    self.console.log(
                        f"[red]ERROR:[/] Invalid @knitpkg:<directive> → '{directive}'"
                    )
                    return f"// ERROR: Invalid @knitpkg:<directive> → '{directive}'"

            except FileNotFoundError:
                self.console.log(
                    f"[red]ERROR:[/] Include not found in {base_path} → {inc_file}"
                )
                return f"// ERROR: Include not found → {inc_file}"

            inc_path_abs = inc_path.absolute()
            if inc_path_abs in visited:
                return f"// RECURSIVE INCLUDE SKIPPED: {inc_file}"
            visited.add(inc_path_abs)

            raw = read_file_smart(inc_path)
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

class KnitPkgInstaller:
    """
    Encapsulates KnitPkg install functionality for dependency resolution
    and output generation.
    """

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        
        registry_url = get_registry_url()
        # Use MQL-specific downloader
        self.downloader = MQLDependencyDownloader(console, project_dir, registry_url)
        self.include_processor = IncludeModeProcessor(console, project_dir)
        self.flat_processor = FlatModeProcessor(console, project_dir)

    def install(self, locked_mode: bool = False, show_tree: bool = True) -> None:
        """
        Main entry point for install — resolves dependencies and generates output.

        Raises:
            SystemExit: On fatal errors (dependency not found, locked mode violations, etc.)
        """
        try:
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
            validate_mql_project_structure(
                manifest,
                self.project_dir,
                is_dependency=False,
                console=self.console
            )

            self._prepare_output_directories(manifest)

            resolved_deps = self._resolve_dependencies(manifest, locked_mode, show_tree)

            if effective_mode == IncludeMode.INCLUDE:
                self.include_processor.process(resolved_deps)
            else:
                self.flat_processor.process(manifest, resolved_deps)

            self._log_completion(resolved_deps, effective_mode)

        except (LocalDependencyNotFoundError, LockedWithLocalDependencyError, DependencyHasLocalChangesError) as e:
            # Handle dependency errors with clear messages
            self.console.log(f"[red]Fatal error:[/] {e}")
            raise SystemExit(1)
        except Exception as e:
            self.console.log(f"[red]Error:[/] {e}")
            raise SystemExit(1)

    def _log_install_start(
        self,
        manifest: MQLKnitPkgManifest,
        effective_mode: IncludeMode
    ) -> None:
        self.console.log(
            f"[bold magenta]knitpkg install[/] → [bold cyan]{manifest.name}[/] "
            f"v{manifest.version} {manifest.type.value}"
        )
        if effective_mode != manifest.include_mode:
            self.console.log(
                f"       (project type '{manifest.type.value}' enforces "
                f"[bold yellow]'{effective_mode.value}'[/] mode)"
            )

    def _prepare_output_directories(self, manifest: MQLKnitPkgManifest) -> None:
        flat_dir = self.project_dir / FLAT_DIR
        include_dir = self.project_dir / INCLUDE_DIR

        shutil.rmtree(flat_dir, ignore_errors=True)
        if manifest.type != MQLProjectType.PACKAGE:
            shutil.rmtree(include_dir, ignore_errors=True)
        elif include_dir.exists():
            self.console.log(
                f"[dim]Preserving[/] {INCLUDE_DIR.as_posix()} "
                f"(project type is 'package')"
            )

    def _resolve_dependencies(
        self,
        manifest: MQLKnitPkgManifest,
        locked_mode: bool,
        show_tree: bool
    ) -> ResolvedDeps:
        """
        Resolve dependencies using downloader.

        Raises:
            LocalDependencyNotFoundError: If local dependency path doesn't exist
            LocalDependencyNotGitError: If --locked with non-git local dependency
            DependencyHasLocalChangesError: If --locked but dependency has changes
        """
        self.console.log("[bold blue]Downloading dependencies...[/]")

        # This may raise custom exceptions - let them propagate
        resolved_deps, dependency_tree = self.downloader.download_all(
            manifest.dependencies or {}, 
            manifest.target.value,
            locked_mode
        )

        # Log dependency tree by default unless --no-tree flag is used
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

    def _log_completion(
        self,
        resolved_deps: ResolvedDeps,
        effective_mode: IncludeMode
    ) -> None:
        self.console.log(
            f"[green]Check[/] Resolved {len(resolved_deps)} "
            f"dependenc{'y' if len(resolved_deps)==1 else 'ies'}"
        )
        output_dir = INCLUDE_DIR if effective_mode == IncludeMode.INCLUDE else FLAT_DIR
        self.console.log(
            f"\n[bold green]Check install completed![/] → {output_dir.as_posix()}/"
        )

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def install_command(project_dir: Path, locked_mode: bool, show_tree: bool, verbose: bool):
    """Command wrapper for KnitPkgInstaller."""
    console = Console(log_path=verbose)
    installer = KnitPkgInstaller(console, project_dir)
    installer.install(locked_mode, show_tree)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def install(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        locked: Optional[bool] = typer.Option(
            False,
            "--locked",
            help="Fail if any dependency has local changes or does not match the lockfile. "
            "Enables strict reproducible builds (recommended for CI/CD and production)."
        ),
        no_tree: Optional[bool] = typer.Option(
            False,
            "--no-tree",
            help="Skip displaying dependency tree after resolution."
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output with file/line information"
        )
    ):
        """Prepare the project: resolve recursive includes or generate flat files."""

        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()

        install_command(project_dir, locked, not no_tree, verbose)
