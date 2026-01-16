# knitpkg/core/exceptions.py

"""
KnitPkg domain-specific exceptions.

This module contains custom exceptions for the KnitPkg package manager,
providing clear error messages and separating concerns between library
code (which raises exceptions) and CLI code (which handles them).
"""

class KnitPkgError(Exception):
    """Base exception for all KnitPkg errors."""
    pass

# ==============================================================
# DEPENDENCY RESOLUTION ERRORS
# ==============================================================

class DependencyError(KnitPkgError):
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

class LockedWithLocalDependencyError(DependencyError):
    """Raised when --locked is used with a local dependency."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Cannot use --locked with local dependency '{name}'"
        )

class DependencyHasLocalChangesError(DependencyError):
    """Raised when --locked is used but a dependency has uncommitted changes."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Cannot proceed with --locked: dependency '{name}' has local changes"
        )

class LocalDependencyNotInLockfileError(DependencyError):
    """Raised when --locked is used but dependency is not in lockfile."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Cannot proceed with --locked: dependency '{name}' not found in lockfile"
        )

class LocalDependencyCommitMismatchError(DependencyError):
    """Raised when --locked is used but local commit doesn't match lockfile."""
    def __init__(self, name: str, current_commit: str, locked_commit: str):
        self.name = name
        self.current_commit = current_commit
        self.locked_commit = locked_commit
        super().__init__(
            f"Cannot proceed with --locked: dependency '{name}' commit mismatch\n"
            f"    Current: {current_commit[:8]}\n"
            f"    Locked:  {locked_commit[:8]}"
        )

class LocalDependencyManifestError(DependencyError):
    """Raised when a local dependency's manifest cannot be loaded."""
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        super().__init__(
            f"Cannot load manifest for local dependency '{name}' at {path}"
        )

class RegistryRequestError(DependencyError):
    """Raised when registry request fails."""
    def __init__(self, url: str, status_code: int, response_text: str):
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(
            f"Registry request failed: {status_code} - {url}\n{response_text}"
        )

class ProviderNotFoundError(DependencyError):
    """Raised when provider is not found in registry config."""
    def __init__(self, provider: str, available_providers: list[str] = None):
        self.provider = provider
        self.available_providers = available_providers
        if available_providers:
            super().__init__(
                f"Provider '{provider}' not found in registry configuration. "
                f"Available providers: {', '.join(available_providers)}"
            )
        else:
            super().__init__(f"Provider '{provider}' not found in registry configuration")

class CallbackServerError(KnitPkgError):
    """Raised when callback server fails to start or handle request."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Callback server error: {details}")

class AuthorizationCodeError(KnitPkgError):
    """Raised when authorization code is not received from callback."""
    def __init__(self):
        super().__init__("Failed to obtain authorization code from OAuth callback")

class TokenExchangeError(KnitPkgError):
    """Raised when token exchange fails."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Token exchange failed: {details}")

class AccessTokenError(KnitPkgError):
    """Raised when access token is missing from response."""
    def __init__(self):
        super().__init__("Access token not found in registry response")

class InvalidRegistryError(KnitPkgError):
    """Raised when registry configuration is invalid."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Invalid registry configuration: {details}")

class TokenStorageError(KnitPkgError):
    """Raised when token storage fails."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Failed to store token securely: {details}")

class TokenRemovalError(KnitPkgError):
    """Raised when token removal fails."""
    def __init__(self):
        super().__init__(f"Failed to remove token")

class TokenNotFoundError(KnitPkgError):
    """Raised when access token is not found in keyring."""
    def __init__(self):
        super().__init__(f"No access token found")

class GitOperationError(DependencyError):
    """Raised when git operations fail."""
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(f"Git {operation} failed: {details}")

class GitCloneError(DependencyError):
    """Raised when git clone fails."""
    def __init__(self, git_url: str, details: str):
        self.git_url = git_url
        self.details = details
        super().__init__(f"Git clone failed for {git_url}: {details}")

class GitCommitNotFoundError(DependencyError):
    """Raised when commit hash doesn't exist or checkout fails."""
    def __init__(self, commit_hash: str, details: str):
        self.commit_hash = commit_hash
        self.details = details
        super().__init__(f"Commit {commit_hash[:8]} not found or checkout failed: {details}")

# ==============================================================
# MANIFEST ERRORS
# ==============================================================

class ManifestError(KnitPkgError):
    """Base exception for manifest-related errors."""
    pass

class ManifestNotFoundError(ManifestError):
    """Raised when knitpkg.yaml/knitpkg.json is not found."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"No manifest file found in {path}")
