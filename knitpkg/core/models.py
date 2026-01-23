# knitpkg/core/models.py

"""
Core models for KnitPkg package manager.

This module contains generic manifest definitions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Dict, Any, List
from knitpkg.core.version_handling import validate_version_specifier, validate_version

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
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


# ==============================================================
# VERSION REFERENCE VALIDATION
# ==============================================================

# Organization and project names
ORGANIZATION_PATTERN = r"^[\w\-\.]+$"
ORGANIZATION_RE = re.compile(ORGANIZATION_PATTERN)
PROJECT_NAME_PATTERN = r"^[\w\-\.]+$"
PROJECT_NAME_RE = re.compile(PROJECT_NAME_PATTERN)

# Validation for dependencies names
DEP_NAME_PATTERN = r"^(@[\w\-\.]+/)?[\w\-\.]+$"
DEP_NAME_RE = re.compile(DEP_NAME_PATTERN)


# ==============================================================
# BASE KNITPKG MANIFEST
# ==============================================================

class KnitPkgManifest(BaseModel):
    """
    KnitPkg base manifest.
    """

    model_config = ConfigDict(extra="allow")

    target: str = Field(
        ...,
        description="Target platform/version"
    )

    organization: str = Field(
        ...,
        max_length=100,
        pattern=ORGANIZATION_PATTERN,
        description="Organization name (alphanumeric, hyphens, underscores, dots only), should match Git repository organization name"
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=PROJECT_NAME_PATTERN,
        description="Project name (alphanumeric, hyphens, underscores, dots only)"
    )

    version: str = Field(
        ...,
        description="Semantic Versioning string (e.g. 1.0.0)"
    )

    # Base project type (only 'package' at this level)
    type: str = Field(
        ...,
        description="Project type"
    )

    keywords: Optional[List[str]] = Field(
        default=None,
        description="List of keywords for package discovery"
    )

    description: str = Field(
        ...,
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

    compile: Optional[List[str]] = Field(
        default=None,
        description="List of source files to compile (relative to project root)"
    )

    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Dependencies with Git URLs or local paths and version constraints"
    )

    overrides: Dict[str, str] = Field(
        default_factory=dict,
        description="Dependency version overrides"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that type is a valid ProjectType value."""
        if v not in [t.value for t in ProjectType]:
            valid_types = ", ".join([t.value for t in ProjectType])
            raise ValueError(f"type must be one of: {valid_types}")
        return v

    @field_validator("version")
    @classmethod
    def validate_manifest_version(cls, v: str) -> str:
        """Strict SemVer validation."""
        v = v.strip()

        if not validate_version(v):
            raise ValueError(
                "Version must follow SemVer format (e.g. 1.0.0, 2.1.3-beta.1)"
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
            
            if not DEP_NAME_RE.fullmatch(dep_name):
                raise ValueError(
                    f"Dependency name '{dep_name}' must follow 'package-name' or '@organization/package-name' format"
                )   

            # Local file:// protocol (path existence checked at install time)
            if spec.startswith("file://"):
                continue

            # Relative or absolute local path (existence checked at install time)
            if spec.startswith(("./", "../", "/", "~")):
                continue

            if not validate_version_specifier(spec):
                raise ValueError(
                    f"Invalid version specifier in dependency '{dep_name}': {spec}\n"
                    "Valid formats:\n"
                    "  1.2.3            v1.2.3           ^1.2.0           ~1.2.3\n"
                    "  >=1.0.0 <2.0.0   >1.5.0           <=3.0.0\n"
                )

        return v

    @field_validator("overrides", mode="before")
    @classmethod
    def validate_overrides(cls, v: Any) -> Dict[str, str]:
        """Validate overrides field with NAME_PATTERN for keys and SEMVER_PATTERN for values."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("overrides must be a dictionary")
        
        for dep_name, version in v.items():
            if not isinstance(version, str):
                raise ValueError(f"Override '{dep_name}' must be a string")
            version = version.strip()
            if not version:
                raise ValueError(f"Override '{dep_name}' is empty")
            
            if not DEP_NAME_RE.fullmatch(dep_name):
                raise ValueError(
                    f"Override name '{dep_name}' must follow 'package-name' or '@organization/package-name' format"
                )
            
            if not validate_version(version):
                raise ValueError(
                    f"Override '{dep_name}' must use SemVer format (e.g. 1.2.3)"
                )
        
        return v
