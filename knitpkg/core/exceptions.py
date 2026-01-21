# knitpkg/core/exceptions.py

from typing import Optional
from httpx import HTTPStatusError
import json

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

class LocalDependencyManifestError(DependencyError):
    """Raised when a local dependency's manifest cannot be loaded."""
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        super().__init__(
            f"Cannot load manifest for local dependency '{name}' at {path}"
        )

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
# REGISTRY BASE ERRORS
# ==============================================================

class RegistryBaseError(KnitPkgError):
    """Base class for errors with Registry services"""
    pass


# ==============================================================
# REGISTRY AUTHENTICATION ERRORS
# ==============================================================

class AuthenticationError(RegistryBaseError):
    """Base class for Authentication errors with Registry."""
    pass

class CallbackServerError(AuthenticationError):
    """Raised when callback server fails to start or handle request."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Callback server error: {details}")

class AuthorizationCodeError(AuthenticationError):
    """Raised when authorization code is not received from callback."""
    def __init__(self):
        super().__init__("Failed to obtain authorization code from OAuth callback")

class TokenExchangeError(AuthenticationError):
    """Raised when token exchange fails."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Token exchange failed: {details}")

class AccessTokenError(AuthenticationError):
    """Raised when access token is missing from response."""
    def __init__(self):
        super().__init__("Access token not found in registry response")

class InvalidRegistryError(AuthenticationError):
    """Raised when registry configuration is invalid."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Invalid registry configuration: {details}")

class TokenStorageError(AuthenticationError):
    """Raised when token storage fails."""
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"Failed to store token securely: {details}")

class TokenRemovalError(AuthenticationError):
    """Raised when token removal fails."""
    def __init__(self):
        super().__init__(f"Failed to remove token")

class TokenNotFoundError(AuthenticationError):
    """Raised when access token is not found in keyring."""
    def __init__(self):
        super().__init__("You are not logged in. Please run 'kp login --provider <provider>' first.")


# ==============================================================
# REGISTRY ERRORS
# ==============================================================

class RegistryError(KnitPkgError):
    """Base class for Registry authentication errors."""
    
    def __init__(self, http_error: HTTPStatusError, *args: object) -> None:
        self.reason = http_error.response.reason_phrase
        self.status_code = http_error.response.status_code
        self.request_url = http_error.request.url

        status_class = http_error.response.status_code // 100
        error_types = {
            1: "Informational response",
            3: "Redirect response",
            4: "Client error",
            5: "Server error",
        }
        self.error_type = error_types.get(status_class, "Invalid status code")

        try:
            error_data = json.loads(http_error.response.text)
            detail = error_data.get("detail", str(http_error))
        except (json.JSONDecodeError, AttributeError):
            detail = str(http_error)

        super().__init__(detail)


# ==============================================================
# OTHERS REGISTRY ERRORS
# ==============================================================

class ProviderNotFoundError(RegistryBaseError):
    """Raised when provider is not found in registry config."""
    def __init__(self, provider: str, available_providers: Optional[list[str]] = None):
        self.provider = provider
        self.available_providers = available_providers
        if available_providers:
            super().__init__(
                f"Provider '{provider}' not found in registry configuration. "
                f"Available providers: {', '.join(available_providers)}"
            )
        else:
            super().__init__(f"Provider '{provider}' not found in registry configuration")


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

class ManifestLoadError(ManifestError):
    """Raised when manifest file cannot be loaded or parsed."""
    def __init__(self, file_path: str, details: str):
        self.file_path = file_path
        self.details = details
        super().__init__(f"Error loading {file_path}: {details}")

