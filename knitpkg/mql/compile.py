import os
import re
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from knitpkg.core.exceptions import InvalidUsageError
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.core.console import Console, ConsoleAware
from knitpkg.mql.models import MQLKnitPkgManifest, Target
from knitpkg.mql.constants import FLAT_DIR, COMPILE_LOGS_DIR, BIN_DIR
from knitpkg.mql.mql_paths import find_mql_paths
from knitpkg.mql.config import MQLProjectConfig

# Import MQL-specific exceptions
from knitpkg.mql.exceptions import (
    MQLCompilationError,
    CompilerNotFoundError,
    NoFilesToCompileError,
    CompilationFailedError,
    MQLIncludePathNotFoundError,
    CompilationLogParseError,
    CompilationExecutionError,
    CompilationLogNotFoundError,
    CompilationFileNotFoundError,
    CompilationInvalidEntrypointError
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
# MQL PROJECT COMPILER CLASS
# ==============================================================
class MQLProjectCompiler(ConsoleAware):
    """Handles MQL4/MQL5 source code compilation."""

    def __init__(self, project_dir: Path, inplace: bool, console: Optional[Console], verbose: bool):
        super().__init__(console, verbose)

        self.project_dir: Path = project_dir
        self.inplace: bool = inplace
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

        if entrypoints_only and compile_only:
            raise InvalidUsageError("Both --entrypoints-only and --compile-only are mutually exclusive")

        # Load manifest
        self.manifest = load_knitpkg_manifest(
            self.project_dir,
            manifest_class=MQLKnitPkgManifest
        )

        self.print(
            f"📦 [bold magenta]Compile[/] → "
            f"[cyan]@{self.manifest.organization}/{self.manifest.name}[/] : {self.manifest.version}"
        )

        # Determine compiler path based on target
        compiler_path = self._get_compiler_path()

        # Collect files to compile
        files_to_compile = self._collect_files(entrypoints_only, compile_only)

        if not files_to_compile:
            raise NoFilesToCompileError()

        self.print(
            f"[dim]Files to compile:[/] {len(files_to_compile)}"
        )

        # Prepare compile logs directory (remove old logs)
        self._prepare_compile_logs_dir()

        # Compile each file
        moved_files: List[str] = []
        inc_path = self._get_mql_include_path()
        for file_path in files_to_compile:
            result = self._compile_file(compiler_path, file_path, inc_path)
            self.results.append(result)
            self._move_to_bin_if_not_inplace(result, moved_files)

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
            UnsupportedTargetError: If manifest target is not mql4 or mql5
            CompilerNotFoundError: If the compiler executable does not exist
        """
        config: MQLProjectConfig = MQLProjectConfig(self.project_dir)
        compiler_path: Path = Path(config.get_compiler_path(Target(self.manifest.target)))

        if not compiler_path.exists():
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
                        raise CompilationInvalidEntrypointError(file_str)
                        
                    file_path = self.project_dir / FLAT_DIR / file_name_str
                    if file_path.exists():
                        files.append(file_path)
                    else:
                        raise CompilationFileNotFoundError(str(file_path), "flat from entrypoints")
            else:
                # include_mode is not 'flat', warn user
                self.print(
                    f"[yellow]⚠️  Warning:[/] Entrypoints defined in manifest but include_mode is not 'flat'. "
                    f"Entrypoints will not be compiled. Set include_mode to 'flat' or use 'compile' field."
                )

        # Collect from compile list (unless entrypoints_only)
        if not entrypoints_only and self.manifest.compile:
            for file_str in self.manifest.compile:
                file_path = self.project_dir / file_str
                if file_path.exists():
                    files.append(file_path)
                else:
                    raise CompilationFileNotFoundError(file_str, "compile")

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
        config: MQLProjectConfig = MQLProjectConfig(self.project_dir)
        mql_data_folder_path_str: Optional[str] = config.get_data_folder_path(Target(self.manifest.target))

        # 1. Check for configured data folder path
        if mql_data_folder_path_str:
            configured_path = Path(mql_data_folder_path_str)
            configured_path_include = configured_path / self.manifest.target / "Include"
            if configured_path_include.exists() and configured_path_include.is_dir():
                return configured_path_include.parent
            else:
                self.print(
                    f"[yellow]⚠️  Warning:[/] Configured MQL data folder "
                    f"'{configured_path}' does not exist or is not a valid MQL directory. "
                    f"Attempting auto-detection."
                )

        # 2. Fallback to auto-detection logic
        found_mql_paths: List[Path] = find_mql_paths(Target(self.manifest.target))
        target_folder_name = self.manifest.target.upper() # MQL5 or MQL4

        if not found_mql_paths:
            raise MQLIncludePathNotFoundError(target_folder_name)

        if len(found_mql_paths) > 1:
            self.print(
                f"[yellow]⚠️  Warning:[/] Multiple {target_folder_name} "
                f"data folders found. Using the first one detected: "
                f"{found_mql_paths[0].parent}"
            )
            self.print(
                f"[yellow]💡 Hint:[/] To specify a particular data folder, "
                f"use 'kp config --{self.manifest.target.lower()}-data-folder-path <path>'."
            )

        return found_mql_paths[0]

    def _parse_compilation_log(self, log_path: Path, src_file_path: Path) -> CompilationResult:
        """Parse MetaEditor compilation log."""
        if not log_path.exists():
            raise CompilationLogNotFoundError(str(log_path))

        try:
            # MetaEditor logs are UTF-16 LE
            log_content = log_path.read_text(encoding="utf-16-le", errors="ignore")
        except Exception:
            try:
                log_content = log_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                raise CompilationLogParseError(f"Failed to read compilation log file: {e}")

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
            raise CompilationLogParseError("Failed to parse compilation result from log")

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
            file_path=src_file_path,
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

    def _compile_file(self, compiler_path: Path, src_file_path: Path, inc_path: Path) -> CompilationResult:
        """
        Compile a single file using MetaEditor.
        Returns CompilationResult with status and messages.
        """
        rel_path = src_file_path.relative_to(self.project_dir)
        self.print(f"🔨 [dim]Compiling:[/] {rel_path.as_posix()}")

        # Get individual log file path for this source file
        log_file = self._get_log_file_path(src_file_path)

        # NOTE: The MetaEditor compiler does not handle file paths with spaces correctly 
        # when invoked via os.subprocess.run(). Workaround: navigate to the compiler 
        # directory and invoke via os.system() instead.

        cmd = f'{compiler_path.name} /compile:"{src_file_path}" /log:"{log_file}"'

        if inc_path:
            cmd += f' /inc:"{inc_path}"'
            
        try:
            os.chdir(compiler_path.parent)
            os.system(cmd)
        except Exception as e:
            raise CompilationExecutionError(f"Failed to execute compilation command: {e}")

        # Parse log to determine actual result
        result = self._parse_compilation_log(log_file, src_file_path)

        # Show immediate feedback
        if result.status == CompilationStatus.SUCCESS:
            self.log(f"  [green]✓[/] {rel_path.as_posix()}")
        elif result.status == CompilationStatus.SUCCESS_WITH_WARNINGS:
            self.print(
                f"  [yellow]⚠[/] {rel_path.as_posix()} "
                f"({result.warning_count} warning{'s' if result.warning_count > 1 else ''})"
            )
        else:
            self.print(
                f"  [red]✗[/] {rel_path.as_posix()} "
                f"({result.error_count} error{'s' if result.error_count > 1 else ''})"
            )

        # Show error/warning messages
        if result.messages:
            for msg in result.messages:
                self.print(f"    {msg}")

        return result


    def _move_to_bin_if_not_inplace(self, result: CompilationResult, moved_files: List[str]):
        if self.inplace:
            return
        
        bin_dir = self.project_dir / BIN_DIR
        bin_dir.mkdir(exist_ok=True)

        if not result.file_path:
            return

        compiled_file_ext = ".ex5" if self.manifest.target == Target.mql5 else ".ex4"

        # Only move files that were actually compiled (not skipped)
        if result.status in (CompilationStatus.SUCCESS, CompilationStatus.SUCCESS_WITH_WARNINGS):
            compiled_file = result.file_path.with_suffix(compiled_file_ext)
            if compiled_file.exists():
                dst_file_name = compiled_file.name

                if dst_file_name in moved_files:
                    dst_file_name = f"{compiled_file.stem}_{len(moved_files)}{compiled_file.suffix}"
                    self.print(
                        f"[yellow]⚠️  Warning:[/] {(result.file_path.relative_to(self.project_dir)).as_posix()} "
                        f"compiled file name conflict, renaming to {dst_file_name}"
                    )

                shutil.move(
                    str(compiled_file),
                    str(bin_dir / dst_file_name)
                )
                moved_files.append(dst_file_name)
                self.print(f"  📁 [dim]Moved:[/] bin/{dst_file_name}")

    def _print_summary(self) -> None:
        """Print compilation summary."""
        if not self.results:
            return

        success_count = sum(1 for r in self.results if r.status == CompilationStatus.SUCCESS)
        warning_count = sum(1 for r in self.results if r.status == CompilationStatus.SUCCESS_WITH_WARNINGS)
        error_count = sum(1 for r in self.results if r.status == CompilationStatus.ERROR)

        if warning_count > 0 or error_count > 0:
            self.print("")
            self.print("[bold cyan]📊 Compilation Summary:[/]")
            self.print("")
            
            for result in self.results:
                if not result.file_path:
                    continue
                rel_path = result.file_path.relative_to(self.project_dir).as_posix()
                if result.status == CompilationStatus.SUCCESS:
                    status = "[green]✓[/]"
                elif result.status == CompilationStatus.SUCCESS_WITH_WARNINGS:
                    status = "[yellow]⚠[/]"
                else:
                    status = "[red]✗[/]"
                
                result_print = f"  {status:<5} {rel_path:<40}"
                if result.error_count > 0:
                    result_print += f" Errors: {result.error_count}"
                
                if result.warning_count > 0:
                    result_print += f" Warnings: {result.warning_count}"
                
                self.print(result_print)

        self.print("")
        if error_count == 0 and warning_count == 0:
            self.print(
                f"[bold green]✅ All files compiled successfully![/] "
                f"({success_count}/{len(self.results)})"
            )
        elif error_count == 0:
            self.print(
                f"[bold yellow]⚠️ Compilation completed with warnings:[/] "
                f"{success_count} succeeded, {warning_count} with warnings"
            )

        if warning_count > 0 or error_count > 0:
            self.print("")
            self.print(
                f"[dim]📝 Compilation logs saved to:[/] {self.compile_logs_dir.relative_to(self.project_dir).as_posix()}"
            )
        self.print("")

        # Raise exception instead of SystemExit
        if error_count > 0:
            raise CompilationFailedError(error_count, warning_count, len(self.results))
