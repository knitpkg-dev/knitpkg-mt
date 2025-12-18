# helix/core/exceptions.py

"""
Helix domain-specific exceptions.

This module contains custom exceptions for the Helix package manager,
providing clear error messages and separating concerns between library
code (which raises exceptions) and CLI code (which handles them).
"""

class HelixError(Exception):
    """Base exception for all Helix errors."""
    pass

# ==============================================================
# DEPENDENCY RESOLUTION ERRORS
# ==============================================================

class DependencyError(HelixError):
    """Base exception for dependency-related errors."""
    pass

class CorruptGitDependencyCacheError(DependencyError):
    """Raised when a cached git dependency is corrupt."""
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        super().__init__(
            f"Cached git dependency '{name}' is corrupt:\n    → {path}"
        )

class LocalDependencyNotFoundError(DependencyError):
    """Raised when a local dependency path does not exist."""
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        super().__init__(
            f"Local dependency '{name}' points to missing path:\n    → {path}"
        )

class LocalDependencyNotGitError(DependencyError):
    """Raised when --locked is used with a non-git local dependency."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Cannot use --locked with non-git local dependency '{name}'"
        )

class DependencyHasLocalChangesError(DependencyError):
    """Raised when --locked is used but a dependency has uncommitted changes."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Cannot proceed with --locked: dependency '{name}' has local changes"
        )

# ==============================================================
# MANIFEST ERRORS
# ==============================================================

class ManifestError(HelixError):
    """Base exception for manifest-related errors."""
    pass

class ManifestNotFoundError(ManifestError):
    """Raised when helix.yaml/helix.json is not found."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"No manifest file found in {path}")
