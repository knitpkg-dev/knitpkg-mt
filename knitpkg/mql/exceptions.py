# knitpkg/mql/exceptions.py

"""
MQL-specific exceptions.

These exceptions are raised by MQL compilation and processing subsystems.
The CLI layer catches them and translates into appropriate exit codes.
"""

from knitpkg.core.exceptions import KnitPkgError

# ==============================================================
# DEPENDENCY INSTALL ERRORS
# ==============================================================

class InstallError(KnitPkgError):
    """Base exception for all MQL install failures."""
    pass


class InvalidDirectiveError(InstallError):
    """Raised when an invalid KnitPkg directive is encountered during install."""
    
    def __init__(self, line: str):
        self.line = line
        super().__init__(f"Invalid directive: {line}")


class IncludeFileNotFoundError(InstallError):
    """Raised when an include file cannot be found during flat mode processing."""
    
    def __init__(self, inc_file: str, search_location: str):
        self.inc_file = inc_file
        self.search_location = search_location
        super().__init__(f"Include not found in {search_location}: {inc_file}")

# ==============================================================
# MQL COMPILATION ERRORS
# ==============================================================

class MQLCompilationError(KnitPkgError):
    """Base exception for all MQL compilation failures."""
    pass


class CompilerNotFoundError(MQLCompilationError):
    """Raised when the configured MetaEditor executable does not exist."""

    def __init__(self, compiler_path: str, target: str):
        self.compiler_path = compiler_path
        self.target = target
        super().__init__(f"Compiler not found: {compiler_path}. Hint: configure compiler path with `kp config --{target.lower()}-compiler-path <path-to-MetaEditor.exe>`")


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
            f"{error_count} error{'' if error_count == 1 else 's'}, "
            f"{warning_count if warning_count > 0 else 'no'} warning{'' if warning_count == 1 else 's'}, "
            f"{total} file{'' if total == 1 else 's'} total"
        )

class MQLIncludePathNotFoundError(MQLCompilationError): # NEW
    """Raised when the MetaTrader include directory cannot be located."""

    def __init__(self, target_folder: str):
        self.target_folder = target_folder
        super().__init__(
            f"MetaTrader include directory for '{target_folder}' not found. "
            "Ensure MetaTrader is installed and the data folder exists."
        )


class CompilationLogParseError(MQLCompilationError):
    """Raised when parsing the MetaEditor compilation log fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Compilation log parse error: {message}")


class CompilationExecutionError(MQLCompilationError):
    """Raised when the MetaEditor compiler execution fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Compilation execution error: {message}")


class CompilationLogNotFoundError(MQLCompilationError):
    """Raised when the compilation log file is not found."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        super().__init__(f"Compilation log file not found: {log_path}")


class CompilationFileNotFoundError(MQLCompilationError):
    """Raised when a file specified for compilation cannot be found."""

    def __init__(self, file_path: str, context: str = ""):
        self.file_path = file_path
        self.context = context
        message = f"Compilation file not found: {file_path}"
        if context:
            message += f" ({context})"
        super().__init__(message)


class CompilationInvalidEntrypointError(MQLCompilationError):
    """Raised when an entrypoint file has an invalid extension."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Invalid entrypoint file extension: {file_path}. Supported extensions: .mq4, .mq5, .mqh")


