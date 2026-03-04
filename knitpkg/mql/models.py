# knitpkg/mql/models.py

"""
MQL-specific manifest extensions for MetaTrader 4/5.

This module extends the base KnitPkgManifest with MQL-specific fields
and validation logic.
"""

from typing import Optional, List, Any, ClassVar, Dict
from enum import Enum
from pydantic import Field, field_validator, model_validator, BaseModel
from typing_extensions import Self
import re

from knitpkg.core.models import KnitPkgManifest, ProjectType

# ==============================================================
# MQL-SPECIFIC ENUMS
# ==============================================================

class Target(str, Enum):
    """MetaTrader target platforms."""
    mql4 = "mql4"
    mql5 = "mql5"

class MQLProjectType(str, Enum):
    """
    MQL-specific project types.

    Inherits PACKAGE from base ProjectType and adds MQL-specific types.
    """
    PACKAGE = "package"  # Inherited from base ProjectType
    EXPERT = "expert"
    INDICATOR = "indicator"
    SCRIPT = "script"
    LIBRARY = "library"
    SERVICE = "service"

class IncludeMode(str, Enum):
    """MQL include processing modes."""
    INCLUDE = "include"  # Copy .mqh to knitpkg/include/
    FLAT = "flat"        # Generate self-contained _flat files


_VALID_CONSTANT_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def _check_constant_identifier(value: str, context: str) -> str:
    """Raise ValueError if *value* is not a valid C identifier."""
    if not _VALID_CONSTANT_IDENTIFIER.match(value):
        raise ValueError(
            f"{context}: '{value}' is not a valid C/MQL identifier. "
            "Use only letters, digits and underscores; "
            "must not start with a digit."
        )
    return value


class ManifestDefines(BaseModel):
    """
    The 'defines' section of knitpkg.yaml / knitpkg.json.

    Example (YAML):

        defines:
          from_manifest:
            version:      MANIFEST_VERSION   # manifest field → constant name
            organization: MANIFEST_ORG
            name:         PROJECT_NAME
          extra:
            - name: FEATURE_X_ENABLED         # flag — no value
            - name: BUILD_TIMESTAMP
              value: "20260304"

    Rules
    -----
    * Keys in *from_manifest* must be fields listed in EXPORTABLE_MANIFEST_FIELDS.
    * Values in *from_manifest* and every *name* in *extra* must be valid C identifiers.
    * At least one of *from_manifest* or *extra* must be present.

    Priority during generation (highest → lowest):
        1. CLI  --define / -D  flags
        2. extra
        3. from_manifest
    If the same constant name appears more than once, the highest-priority
    definition wins and lower-priority ones are silently discarded.
    """

    EXPORTABLE_MANIFEST_FIELDS: ClassVar[set[str]] = {
        "version",
        "organization",
        "name",
        "description",
        "author",
        "license",
        "type",
        "target",
    }

    from_manifest: Optional[Dict[str, str]] = None
    # key   = C constant name      (e.g. "MANIFEST_VERSION")
    # value = manifest field name  (e.g. "version")

    extra: Optional[Dict[str, str]] = None

    @field_validator("from_manifest")
    @classmethod
    def validate_from_manifest_keys_and_values(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        if v is None:
            return v
        for const_name, field_name in v.items():
            if field_name not in ManifestDefines.EXPORTABLE_MANIFEST_FIELDS:
                raise ValueError(
                    f"'from_manifest': '{field_name}' is not an exportable "
                    f"manifest field. Valid fields: "
                    f"{sorted(ManifestDefines.EXPORTABLE_MANIFEST_FIELDS)}"
                )
            _check_constant_identifier(const_name, f"from_manifest['{field_name}']")
        return v

    @model_validator(mode="after")
    def at_least_one_section_present(self) -> "ManifestDefines":
        if not self.from_manifest and not self.extra:
            raise ValueError(
                "'defines' section is present but empty. "
                "Provide at least 'from_manifest' or 'extra'."
            )
        return self

# ==============================================================
# MQL KNITPKG MANIFEST
# ==============================================================

class MQLKnitPkgManifest(KnitPkgManifest):
    """
    MQL-specific manifest extending the base KnitPkgManifest.

    Adds MetaTrader-specific fields: target (mql4/mql5), type (project types),
    include_mode, and entrypoints.
    """

    # MQL-specific fields
    include_mode: IncludeMode = Field(
        default=IncludeMode.INCLUDE,
        description="Include processing mode. Use 'include' (copy .mqh) or 'flat' (generate _flat files)."
    )

    entrypoints: Optional[List[str]] = Field(
        default=None,
        description="Main source files. Required for all types except 'package'"
    )

    defines: Optional[ManifestDefines] = None

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> str:
        """Override inherited validator to accept MQLProjectType values."""
        if v is None:
            raise ValueError("type cannot be None")
        if v not in [t.value for t in MQLProjectType]:
            valid_types = ", ".join([t.value for t in ProjectType])
            raise ValueError(f"type must be one of: {valid_types}")
        return v

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, v: Any) -> str:
        """Validate target is not None and is a valid Target enum value."""
        if v is None:
            raise ValueError("target cannot be None")
        if v not in [t.value for t in Target]:
            valid_types = ", ".join([t.value for t in Target])
            raise ValueError(f"target must be one of: {valid_types}")
        return v

    @field_validator("entrypoints", mode="before")
    @classmethod
    def validate_entrypoints_format(cls, v: Any) -> List[str]:
        """Normalize and validate entrypoints list."""
        if v is None or v == []:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise ValueError("entrypoints must be a list of strings")
        for ep in v:
            if not isinstance(ep, str):
                raise ValueError(f"entrypoint must be a string: {ep!r}")
        return v

    @model_validator(mode="after")
    def validate_entrypoints_presence(self) -> Self:
        """Ensure projects with flat include mode have at least one entrypoint."""
        if self.include_mode and self.include_mode == IncludeMode.FLAT:
            if not self.entrypoints or len(self.entrypoints) == 0:
                raise ValueError(
                    f"Include mode 'flat' requires at least one entrypoint"
                )
        return self
