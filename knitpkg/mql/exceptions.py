# knitpkg/mql/exceptions.py

"""
MQL-specific exceptions.

These exceptions are raised by MQL compilation and processing subsystems.
The CLI layer catches them and translates into appropriate exit codes.
"""

from knitpkg.core.exceptions import HelixError


class MQLCompilationError(HelixError):
    """Base exception for all MQL compilation failures."""
    pass


class CompilerNotFoundError(MQLCompilationError):
    """Raised when the configured MetaEditor executable does not exist."""

    def __init__(self, compiler_path: str, target: str):
        self.compiler_path = compiler_path
        self.target = target
        super().__init__(f"Compiler not found: {compiler_path}")


class UnsupportedTargetError(MQLCompilationError):
    """Raised when manifest specifies an unsupported compilation target."""

    def __init__(self, target):
        self.target = target
        super().__init__(f"Unsupported target: {target}")


class NoFilesToCompileError(MQLCompilationError):
    """Raised when no files are available for compilation."""

    def __init__(self):
        super().__init__(
            "No files to compile. Check 'compile' and 'entrypoints' fields in manifest."
        )


class CompilationFailedError(MQLCompilationError):
    """Raised when one or more files fail to compile."""

    def __init__(self, error_count: int, warning_count: int, total: int):
        self.error_count = error_count
        self.warning_count = warning_count
        self.total = total
        super().__init__(
            f"Compilation failed: {error_count} error(s), "
            f"{warning_count} warning(s), {total} file(s) total"
        )

class IncludePathNotFoundError(MQLCompilationError): # NEW
    """Raised when the MetaTrader include directory cannot be located."""

    def __init__(self, target_folder: str):
        self.target_folder = target_folder
        super().__init__(
            f"MetaTrader include directory for '{target_folder}' not found. "
            "Ensure MetaTrader is installed and the data folder exists."
        )