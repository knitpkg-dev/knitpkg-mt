# helix/core/models.py

"""
Core models for Helix package manager.

This module contains generic manifest definitions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
    AnyUrl,
)

# ==============================================================
# COMMON ENUMS 
# ==============================================================

class ProjectType(str, Enum):
    """
    Base project type (platform-agnostic).

    Platform-specific types should inherit from this enum.
    """
    PACKAGE = "package"  # Reusable library/components

class OAuthProvider(str, Enum):
    """OAuth providers for Helix Pro private repository access."""
    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE = "azure"
    GOOGLE = "google"

# ==============================================================
# DISTRIBUTION SECTION 
# ==============================================================

class DistItem(BaseModel):
    """Individual file to include in a distribution package."""
    model_config = ConfigDict(extra="forbid")

    dependency_id: Optional[str] = Field(
        default=None,
        alias="dependencyId",
        description="Dependency name or 'this' (current project). Can be omitted if source is local."
    )
    src: str = Field(..., description="Source path relative to dependency root")
    dst: str = Field(..., description="Destination path in the final package")

class DistRelease(BaseModel):
    """Distribution release configuration."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for this release configuration"
    )
    name: str = Field(
        ...,
        description="Final package filename. Supports ${version} placeholder"
    )
    items: List[DistItem] = Field(
        ...,
        min_length=1,
        description="Files to include in this release"
    )

class DistSection(BaseModel):
    """Distribution package definitions (used by `helix package`)."""
    model_config = ConfigDict(extra="forbid")

    dist: List[DistRelease] = Field(
        default_factory=list,
        description="Distribution package definitions"
    )

    def get_release_by_id(self, release_id: str) -> Optional[DistRelease]:
        """Return the DistRelease with the given id, or None if not found."""
        for r in self.dist:
            if r.id == release_id:
                return r
        return None

    def render_name(self, release_id: str, version: str) -> str:
        """Render the final package filename, replacing ${version} placeholder."""
        release = self.get_release_by_id(release_id)
        if not release:
            return f"{release_id}-{version}.zip"
        return release.name.replace("${version}", version)

# ==============================================================
# HELIX PRO / ENTERPRISE SECTIONS
# ==============================================================

class HelixProSection(BaseModel):
    """Helix Pro configuration for private repositories."""
    model_config = ConfigDict(extra="forbid")

    private: bool = Field(
        default=False,
        description="Set to true for private repositories"
    )
    oauth_provider: Optional[OAuthProvider] = Field(
        default=None,
        description="OAuth provider for private repo access"
    )

class HelixEnterpriseSection(BaseModel):
    """Helix Enterprise configuration for corporate environments."""
    model_config = ConfigDict(extra="forbid")

    proxy_url: Optional[AnyUrl] = Field(
        default=None,
        description="Proxy URL for enterprise environments"
    )

class HelixSection(BaseModel):
    """Helix Pro and Enterprise settings."""
    model_config = ConfigDict(extra="forbid")

    pro: Optional[HelixProSection] = Field(
        default=None,
        description="Helix Pro configuration"
    )
    enterprise: Optional[HelixEnterpriseSection] = Field(
        default=None,
        description="Helix Enterprise configuration"
    )

# ==============================================================
# VERSION REFERENCE VALIDATION
# ==============================================================

# Main regex: covers all SemVer + NPM-style ranges + prefixed refs (branch=, tag=, commit=)
REF_PATTERN = re.compile(
    r"^"
    r"(?:"
        r"(\^|~|>=|<=|>|<|\s*)"         # ^ ~ >= <= > < (or spaces)
        r"(v?)(\d+\.\d+\.\d+)"          # base version (with or without v)
        r"(-[A-Za-z0-9\.\-]+)?"         # optional pre-release
        r"(\+[A-Za-z0-9\.\-]+)?"        # optional build metadata
        r"(?:\s+(<|<=)\s*(v?)(\d+\.\d+\.\d+))?"  # second side of range (< or <=)
    r")"
    r"|"
    r"(branch|tag|commit)=[A-Za-z0-9._-]+$"  # prefixed references
    r"$",
    re.IGNORECASE
)

# Auxiliary regex: pure SemVer
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

def _is_valid_ref(ref: str) -> bool:
    """Validate a dependency reference (version range or prefixed ref)."""
    ref = ref.strip()

    # Prefixed refs: branch=, tag=, commit=
    if "=" in ref and ref.split("=", 1)[0].lower() in ("branch", "tag", "commit"):
        return bool(REF_PATTERN.match(ref))

    # NPM-style ranges: ^ ~ >= <= > < or intervals
    if any(op in ref for op in ("^", "~", ">=", "<=", ">", "<", " ")):
        return bool(REF_PATTERN.match(ref.replace(" ", "")))

    # Pure SemVer
    cleaned = ref.lstrip("vV")
    return bool(SEMVER_PATTERN.match(cleaned))

# ==============================================================
# BASE HELIX MANIFEST
# ==============================================================

class HelixManifest(BaseModel):
    """
    Helix base manifest.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[\w\-\.]+$",
        description="Project name (alphanumeric, hyphens, underscores, dots only)"
    )

    version: str = Field(
        ...,
        description="Semantic Versioning string (e.g. 1.0.0)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Short project description"
    )

    author: Optional[str] = Field(
        default=None,
        description="Author or team name"
    )

    license: Optional[str] = Field(
        default="MIT",
        description="License identifier"
    )

    organization: Optional[str] = Field(
        default=None,
        max_length=100,
        pattern=r"^[\w\-\.]+$",
        description="Organization or company ID (alphanumeric, hyphens, underscores, dots only)"
    )

    # Generic target (string - platform-specific subclasses will use enums)
    target: str = Field(
        ...,
        description="Target platform/version"
    )

    # Base project type (only PACKAGE at this level)
    type: ProjectType = Field(
        ...,
        description="Project type"
    )

    compile: Optional[List[str]] = Field(
        default=None,
        description="List of source files to compile (relative to project root)"
    )

    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Dependencies with Git URLs or local paths and version constraints"
    )

    dist: Optional[DistSection] = Field(
        default=None,
        description="Distribution package configuration"
    )

    helix: Optional[HelixSection] = Field(
        default=None,
        description="Helix Pro and Enterprise settings"
    )

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Strict SemVer validation."""
        v = v.strip()
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                "version must follow SemVer format (e.g. 1.0.0, 2.1.3-beta.1)"
            )
        return v

    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies(cls, v: Any) -> Dict[str, str]:
        """
        Comprehensive validation of dependency specifications.

        Note: This validator does NOT check if local paths exist on disk.
        Path existence validation is deferred to runtime (install command).
        """
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("dependencies must be a dictionary")

        for dep_name, spec in v.items():
            if not isinstance(spec, str):
                raise ValueError(f"Dependency '{dep_name}' must be a string")
            spec = spec.strip()
            if not spec:
                raise ValueError(f"Dependency '{dep_name}' is empty")

            # Local file:// protocol (path existence checked at install time)
            if spec.startswith("file://"):
                continue

            # Relative or absolute local path (existence checked at install time)
            if spec.startswith(("./", "../", "/", "~")):
                continue

            # Remote Git dependency
            if not any(spec.startswith(proto) for proto in ("https://", "http://", "git@", "ssh://")):
                raise ValueError(
                    f"Invalid dependency '{dep_name}': must use https://, git@, "
                    f"ssh://, file:// or local path"
                )

            if spec.count("#") != 1:
                raise ValueError(
                    f"Invalid dependency '{dep_name}': must contain exactly one '#' separator"
                )

            base_url, ref = spec.split("#", 1)

            if not ref:
                raise ValueError(
                    f"Invalid dependency '{dep_name}': version/reference cannot be empty after '#'"
                )

            if not base_url.endswith(".git"):
                raise ValueError(
                    f"Invalid dependency '{dep_name}': Git URL must end with '.git'"
                )

            if not _is_valid_ref(ref):
                raise ValueError(
                    f"Invalid version/reference in dependency '{dep_name}': #{ref}\n"
                    "Valid formats:\n"
                    "  1.2.3           v1.2.3           ^1.2.0           ~1.2.3\n"
                    "  >=1.0.0 <2.0.0   >1.5.0           <=3.0.0\n"
                    "  branch=main      tag=v2.0.0       commit=abc123"
                )

        return v

    def get_package_name(self, release_id: str = "release") -> str:
        """Return the final package name for a given release configuration."""
        if not self.dist or not self.dist.dist:
            return f"{self.name}-{self.version}.zip"
        return self.dist.render_name(release_id, self.version)
