# knitpkg/commands/compile.py

"""
KnitPkg for Metatrader compile command — compile MQL source files.

This module handles compilation of MQL4/MQL5 source files using MetaEditor.
The MQLCompiler class raises domain-specific exceptions instead of SystemExit,
allowing proper separation between library code and CLI layer.
"""
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.table import Table
import typer

from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.mql.models import MQLKnitPkgManifest, Target
from knitpkg.mql.constants import FLAT_DIR
from knitpkg.mql.constants import COMPILE_LOGS_DIR
from knitpkg.mql.mql_paths import find_mql_paths
from knitpkg.mql.settings import MQLSettings

# Import MQL-specific exceptions
from knitpkg.mql.exceptions import (
    CompilerNotFoundError,
    UnsupportedTargetError,
    NoFilesToCompileError,
    CompilationFailedError,
    IncludePathNotFoundError
)


# ==============================================================
# COMPILATION RESULT TYPES
# ==============================================================

class CompilationStatus(str, Enum):
    """Compilation result status."""
    SUCCESS = "success"
    SUCCESS_WITH_WARNINGS = "warning"
    ERROR = "error"


@dataclass
class CompilationResult:
    """Result of a single file compilation."""
    file_path: Path
    status: CompilationStatus
    error_count: int = 0
    warning_count: int = 0
    messages: Optional[List[str]] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


# ==============================================================
# MQL COMPILER CLASS
# ==============================================================
class MQLCompiler:
    """Handles MQL4/MQL5 source code compilation."""

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        self.manifest: MQLKnitPkgManifest
        self.results: List[CompilationResult] = []
        self.compile_logs_dir = project_dir / COMPILE_LOGS_DIR

    def compile(
        self,
        entrypoints_only: bool = False,
        compile_only: bool = False
    ) -> None:
        """
        Compile MQL source files.

        Args:
            entrypoints_only: If True, compile only entrypoints
            compile_only: If True, compile only files in compile list

        Raises:
            CompilerNotFoundError: If MetaEditor executable is not found
            UnsupportedTargetError: If manifest target is not supported
            NoFilesToCompileError: If no files are available for compilation
            CompilationFailedError: If one or more files fail to compile
        """
        # Load manifest
        self.manifest = load_knitpkg_manifest(
            self.project_dir,
            manifest_class=MQLKnitPkgManifest
        )

        # Determine compiler path based on target
        compiler_path = self._get_compiler_path()

        # Collect files to compile
        files_to_compile = self._collect_files(entrypoints_only, compile_only)

        if not files_to_compile:
            self.console.log(
                "[yellow]Warning:[/] No files to compile. "
                "Check your manifest's 'compile' and 'entrypoints' fields."
            )
            raise NoFilesToCompileError()

        self.console.log(
            f"[bold magenta]compile[/] → "
            f"[cyan]{self.manifest.name}[/] v{self.manifest.version}"
        )
        self.console.log(
            f"[dim]Files to compile:[/] {len(files_to_compile)}"
        )

        # Prepare compile logs directory (remove old logs)
        self._prepare_compile_logs_dir()

        # Compile each file
        for file_path in files_to_compile:
            result = self._compile_file(compiler_path, file_path)
            self.results.append(result)

        # Print summary
        self._print_summary()

    def _prepare_compile_logs_dir(self) -> None:
        """
        Prepare compile logs directory by removing old logs.
        Creates fresh .knitpkg/compile-logs directory.
        """
        if self.compile_logs_dir.exists():
            shutil.rmtree(self.compile_logs_dir)
        self.compile_logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self, source_file: Path) -> Path:
        """
        Get log file path for a source file.

        Args:
            source_file: Absolute path to source file

        Returns:
            Path to log file in .knitpkg/compile-logs/relative/path/file.log

        Example:
            knitpkg/include/Arquivo.mqh -> .knitpkg/compile-logs/knitpkg/include/Arquivo.mqh.log
        """
        rel_path = source_file.relative_to(self.project_dir)
        log_file = self.compile_logs_dir / f"{rel_path}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        return log_file

    def _get_compiler_path(self) -> Path:
        """
        Get compiler path based on manifest target.

        Returns:
            Path to the MetaEditor executable

        Raises:
            UnsupportedTargetError: If manifest target is not MQL4 or MQL5
            CompilerNotFoundError: If the compiler executable does not exist
        """
        settings: MQLSettings = MQLSettings(self.project_dir)
        try:
            compiler_path: Path = Path(settings.get_compiler_path(Target(self.manifest.target)))
        except ValueError:
            self.console.log(
                f"[red]Error:[/] Invalid target in manifest: {self.manifest.target}"
            )
            raise UnsupportedTargetError(self.manifest.target)

        if not compiler_path.exists():
            self.console.log(
                f"[red]Error:[/] Compiler not found: {compiler_path}"
            )
            self.console.log(
                f"[yellow]Hint:[/] Configure compiler path with:"
            )
            if self.manifest.target == Target.MQL5:
                self.console.log(
                    f"  kp-mt config --mql5-compiler-path <path-to-MetaEditor64.exe>"
                )
            else:
                self.console.log(
                    f"  kp-mt config --mql4-compiler-path <path-to-MetaEditor.exe>"
                )
            raise CompilerNotFoundError(
                str(compiler_path),
                self.manifest.target
            )

        return compiler_path

    def _collect_files(
        self,
        entrypoints_only: bool,
        compile_only: bool
    ) -> List[Path]:
        """
        Collect files to compile based on flags.
        Returns list of absolute paths to compile.
        """
        files = []

        # Collect from entrypoints (unless compile_only)
        if not compile_only and self.manifest.entrypoints:
            # Only compile entrypoints if include_mode is 'flat'
            if self.manifest.include_mode == "flat":
                # Transform entrypoints to _flat versions
                for file_str in self.manifest.entrypoints:
                    file_name_str = Path(file_str).name
                    if file_name_str.endswith(".mqh"):
                        file_name_str = file_name_str.removesuffix(".mqh") + "_flat.mqh"
                    elif file_name_str.endswith(".mq5"):
                        file_name_str = file_name_str.removesuffix(".mq5") + "_flat.mq5"
                    elif file_name_str.endswith(".mq4"):
                        file_name_str = file_name_str.removesuffix(".mq4") + "_flat.mq4"
                    else:
                        self.console.log(
                            f"[yellow]Warning:[/] Invalid file name to compile: {file_str}"
                        )
                        continue
                    file_path = self.project_dir / FLAT_DIR / file_name_str
                    if file_path.exists():
                        files.append(file_path)
                    else:
                        self.console.log(
                            f"[yellow]Warning:[/] File not found (flat from entrypoints): {(FLAT_DIR / file_name_str).as_posix()}"
                        )
            else:
                # include_mode is not 'flat', warn user
                self.console.log(
                    f"[yellow]Warning:[/] Entrypoints defined in manifest but include_mode is not 'flat'. "
                    f"Entrypoints will not be compiled. Set include_mode to 'flat' or use 'compile' field."
                )

        # Collect from compile list (unless entrypoints_only)
        if not entrypoints_only and self.manifest.compile:
            for file_str in self.manifest.compile:
                file_path = self.project_dir / file_str
                if file_path.exists():
                    files.append(file_path)
                else:
                    self.console.log(
                        f"[yellow]Warning:[/] File not found (compile): {file_str}"
                    )

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    
    def _get_mql_include_path(self) -> Path:
        """
        Determine the MQL include path for the current target.

        First, checks if a custom data folder path is configured.
        If not, it attempts to auto-detect the path within the MetaQuotes
        Terminal folders.

        Returns:
            Path to the MQL include directory (e.g., MQL5/Include or MQL4/Include)

        Raises:
            IncludePathNotFoundError: If the MQL include directory cannot be located.
        """
        settings: MQLSettings = MQLSettings(self.project_dir)
        mql_data_folder_path_str: Optional[str] = settings.get_data_folder_path(Target(self.manifest.target))

        # 1. Check for configured data folder path
        if mql_data_folder_path_str:
            configured_path = Path(mql_data_folder_path_str)
            configured_path_include = configured_path / self.manifest.target / "Include"
            if configured_path_include.exists() and configured_path_include.is_dir():
                return configured_path_include.parent
            else:
                self.console.log(
                    f"[yellow]Warning:[/] Configured MQL data folder "
                    f"'{configured_path.as_posix()}' does not exist or is not a valid MQL directory. "
                    f"Attempting auto-detection."
                )

        # 2. Fallback to auto-detection logic
        found_mql_paths: List[Path] = find_mql_paths(Target(self.manifest.target))
        target_folder_name = self.manifest.target # MQL5 or MQL4

        if not found_mql_paths:
            self.console.log(
                f"[red]Error:[/] Could not find MQL {target_folder_name} "
                f"include path automatically. "
                f"Please configure it manually using 'kp-mt config --mql{target_folder_name[3:]}-data-folder-path <path>'."
            )
            # Raise the new exception instead of SystemExit(1)
            raise IncludePathNotFoundError(target_folder_name)

        if len(found_mql_paths) > 1:
            self.console.log(
                f"[yellow]Warning:[/] Multiple MQL {target_folder_name} "
                f"data folders found. Using the first one detected: "
                f"{found_mql_paths[0].parent.as_posix()}"
            )
            self.console.log(
                f"[yellow]Hint:[/] To specify a particular data folder, "
                f"use 'kp-mt config --mql{target_folder_name[3:]}-data-folder-path <path>'."
            )

        return found_mql_paths[0]

    def _parse_compilation_log(self, log_path: Path) -> CompilationResult:
        """Parse MetaEditor compilation log."""
        if not log_path.exists():
            return CompilationResult(
                file_path=log_path,
                status=CompilationStatus.ERROR,
                error_count=1,
                messages=["Log file not found"]
            )

        try:
            # MetaEditor logs are UTF-16 LE
            log_content = log_path.read_text(encoding="utf-16-le", errors="ignore")
        except Exception:
            try:
                log_content = log_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                return CompilationResult(
                    file_path=log_path,
                    status=CompilationStatus.ERROR,
                    error_count=1,
                    messages=[f"Failed to read log: {e}"]
                )

        # Remove BOM if present
        if log_content.startswith('\ufeff'):
            log_content = log_content[1:]

        # Parse final Result line - accepts both formats:
        # "Result: 0 errors, 0 warnings" and "result 0 errors, 0 warnings"
        # Also matches when preceded by other text like ": information: result ..."
        result_pattern = re.compile(
            r'\bresult:?\s*(\d+)\s+errors?,\s*(\d+)\s+warnings?',
            re.IGNORECASE
        )

        result_match = result_pattern.search(log_content)
        if not result_match:
            return CompilationResult(
                file_path=log_path,
                status=CompilationStatus.ERROR,
                error_count=1,
                messages=["Could not parse compilation result"]
            )

        error_count = int(result_match.group(1))
        warning_count = int(result_match.group(2))

        # Determine status
        if error_count > 0:
            status = CompilationStatus.ERROR
        elif warning_count > 0:
            status = CompilationStatus.SUCCESS_WITH_WARNINGS
        else:
            status = CompilationStatus.SUCCESS

        # Collect error/warning lines
        error_lines = []
        warning_lines = []

        for line in log_content.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for error/warning with simple substring search
            if re.search(r' : error \d+: ', line):
                error_lines.append(line)
            elif re.search(r' : warning \d+: ', line):
                warning_lines.append(line)

        # Format messages
        messages = []
        for line in error_lines:
            formatted = self._format_log_line(line)
            messages.append(f"[red]{formatted}[/]")

        for line in warning_lines:
            formatted = self._format_log_line(line)
            messages.append(f"[yellow]{formatted}[/]")

        return CompilationResult(
            file_path=log_path,
            status=status,
            error_count=error_count,
            warning_count=warning_count,
            messages=messages
        )

    def _format_log_line(self, line: str) -> str:
        r"""
        Format a compiler log line to show path relative to project directory.

        Finds (line,col) pattern and extracts file path before it.
        Uses simple string search instead of regex for better reliability.

        Input:  C:\...\knitpkg-test\src\TestScript.mq5(20,16) : warning 44: message
        Output: src/TestScript.mq5(20,16) : warning 44: message

        Args:
            line: Full compiler log line with absolute path

        Returns:
            Formatted line with relative POSIX path from project root
        """
        # Find last occurrence of '(' followed by digits
        idx = -1
        for i in range(len(line) - 1, -1, -1):
            if line[i] == '(' and i + 1 < len(line) and line[i + 1].isdigit():
                # Check if pattern matches (digits,digits)
                j = i + 1
                while j < len(line) and line[j].isdigit():
                    j += 1
                if j < len(line) and line[j] == ',':
                    j += 1
                    if j < len(line) and line[j].isdigit():
                        k = j
                        while k < len(line) and line[k].isdigit():
                            k += 1
                        if k < len(line) and line[k] == ')':
                            idx = i
                            break

        if idx == -1:
            return line

        # Extract file path (everything before the '(')
        file_path_str = line[:idx].strip()
        # Extract rest (from '(' onwards)
        rest_of_line = line[idx:]

        if not file_path_str:
            return line

        try:
            file_path = Path(file_path_str)

            # Try to make relative to project directory
            if file_path.is_absolute():
                try:
                    rel_path = file_path.relative_to(self.project_dir)
                    # Convert to POSIX format (forward slashes)
                    return f"{rel_path.as_posix()}{rest_of_line}"
                except ValueError:
                    # File is outside project directory (system includes)
                    return f"{file_path.name}{rest_of_line}"
            else:
                # Already relative
                return line
        except Exception:
            # If anything fails, return original line
            return line

    def _compile_file(self, compiler_path: Path, file_path: Path) -> CompilationResult:
        """
        Compile a single file using MetaEditor.
        Returns CompilationResult with status and messages.
        """
        rel_path = file_path.relative_to(self.project_dir)
        self.console.log(f"[dim]Compiling:[/] {rel_path.as_posix()}")

        # Get individual log file path for this source file
        log_file = self._get_log_file_path(file_path)

        try:
            # NOTE: The MetaEditor compiler does not handle file paths with spaces correctly 
            # when invoked via os.subprocess.run(). Workaround: navigate to the compiler 
            # directory and invoke via os.system() instead.

            cmd = f'{compiler_path.name} /compile:"{file_path}" /log:"{log_file}"'

            inc_path = self._get_mql_include_path()
            if inc_path:
                cmd = cmd + f' /inc:"{inc_path}"'
                
            os.chdir(compiler_path.parent)
            os.system(cmd)

            # Parse log to determine actual result
            result = self._parse_compilation_log(log_file)
            result.file_path = file_path

            # Show immediate feedback
            if result.status == CompilationStatus.SUCCESS:
                self.console.log(f"  [green]✓[/] {rel_path.as_posix()}")
            elif result.status == CompilationStatus.SUCCESS_WITH_WARNINGS:
                self.console.log(
                    f"  [yellow]⚠[/] {rel_path.as_posix()} "
                    f"({result.warning_count} warning{'s' if result.warning_count > 1 else ''})"
                )
            else:
                self.console.log(
                    f"  [red]✗[/] {rel_path.as_posix()} "
                    f"({result.error_count} error{'s' if result.error_count > 1 else ''})"
                )

            # Show error/warning messages
            if result.messages:
                for msg in result.messages:
                    self.console.log(f"    {msg}")

            return result

        except Exception as e:
            self.console.log(
                f"  [red]✗[/] {rel_path} (error: {e})"
            )
            return CompilationResult(
                file_path=file_path,
                status=CompilationStatus.ERROR,
                error_count=1,
                messages=[str(e)]
            )


    def _print_summary(self) -> None:
        """Print compilation summary table."""
        if not self.results:
            return

        success_count = sum(1 for r in self.results if r.status == CompilationStatus.SUCCESS)
        warning_count = sum(1 for r in self.results if r.status == CompilationStatus.SUCCESS_WITH_WARNINGS)
        error_count = sum(1 for r in self.results if r.status == CompilationStatus.ERROR)

        if warning_count > 0 or error_count > 0:
            self.console.log("")
            table = Table(title="Compilation Summary", show_header=True, header_style="bold cyan")
            table.add_column("File", style="dim")
            table.add_column("Status", justify="center")
            table.add_column("Errors", justify="right")
            table.add_column("Warnings", justify="right")

            for result in self.results:
                rel_path = result.file_path.relative_to(self.project_dir).as_posix()
                if result.status == CompilationStatus.SUCCESS:
                    status = "[green]✓ Success[/]"
                elif result.status == CompilationStatus.SUCCESS_WITH_WARNINGS:
                    status = "[yellow]⚠ Warning[/]"
                else:
                    status = "[red]✗ Error[/]"
                table.add_row(
                    str(rel_path),
                    status,
                    str(result.error_count) if result.error_count > 0 else "—",
                    str(result.warning_count) if result.warning_count > 0 else "—"
                )
            self.console.print(table)

        self.console.log("")
        if error_count == 0 and warning_count == 0:
            self.console.log(
                f"[bold green]✓ All files compiled successfully![/] "
                f"({success_count}/{len(self.results)})"
            )
        elif error_count == 0:
            self.console.log(
                f"[bold yellow]⚠ Compilation completed with warnings:[/] "
                f"{success_count} succeeded, {warning_count} with warnings"
            )
        else:
            self.console.log(
                f"[bold red]✗ Compilation failed:[/] "
                f"{success_count} succeeded, {warning_count} with warnings, {error_count} failed"
            )

        if warning_count > 0 or error_count > 0:
            self.console.log("")
            self.console.log(
                f"[dim]Compilation logs saved to:[/] {self.compile_logs_dir.relative_to(self.project_dir).as_posix()}"
            )
        self.console.log("")

        # Raise exception instead of SystemExit
        if error_count > 0:
            raise CompilationFailedError(error_count, warning_count, len(self.results))


# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def compile_command(project_dir: Path, entrypoints_only: bool, compile_only: bool, verbose: bool):
    """Command wrapper"""
    console = Console(log_path=False)

    if entrypoints_only and compile_only:
        console.log(
            "[red]Error:[/] --entrypoints-only and --compile-only "
            "are mutually exclusive"
        )
        raise SystemExit(1)

    compiler = MQLCompiler(console, project_dir)

    try:
        compiler.compile(entrypoints_only, compile_only)
    except (CompilerNotFoundError, 
            UnsupportedTargetError, 
            NoFilesToCompileError,
            CompilationFailedError):
        # All errors already logged by MQLCompiler
        # Just exit with error code
        raise SystemExit(1)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def compile(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        entrypoints_only: Optional[bool] = typer.Option(
            False,
            "--entrypoints-only",
            help="Compile only entrypoints (skip compile list)"
        ),
        compile_only: Optional[bool] = typer.Option(
            False,
            "--compile-only",
            help="Compile only files in compile list (skip entrypoints)"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Compile MQL source files via CLI."""

        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()

        compile_command(project_dir, \
                        True if entrypoints_only else False, \
                        True if compile_only else False, \
                        True if verbose else False)
        
