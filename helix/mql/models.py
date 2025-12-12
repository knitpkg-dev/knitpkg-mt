# helix/mql/models.py

"""
MQL-specific manifest extensions for MetaTrader 4/5.

This module extends the base HelixManifest with MQL-specific fields
and validation logic.
"""

from typing import Optional, List, Any
from enum import Enum
from pydantic import Field, field_validator, model_validator

from helix.core.models import HelixManifest

# ==============================================================
# MQL-SPECIFIC ENUMS
# ==============================================================

class Target(str, Enum):
    """MetaTrader target platforms."""
    MQL4 = "MQL4"
    MQL5 = "MQL5"

class ProjectType(str, Enum):
    """MetaTrader project types."""
    PACKAGE = "package"
    MQL_EXPERT = "mql.expert"
    MQL_INDICATOR = "mql.indicator"
    MQL_SCRIPT = "mql.script"
    MQL_LIBRARY = "mql.library"

class IncludeMode(str, Enum):
    """MQL include processing modes."""
    INCLUDE = "include"  # Copy .mqh to helix/include/
    FLAT = "flat"        # Generate self-contained _flat files

# ==============================================================
# MQL HELIX MANIFEST
# ==============================================================

class MQLHelixManifest(HelixManifest):
    """
    MQL-specific manifest extending the base HelixManifest.

    Adds MetaTrader-specific fields: target (MQL4/MQL5), type (project types),
    include_mode, and entrypoints.
    """

    # Override with strict MQL types
    target: Target = Field(
        ...,
        description="Target platform (MQL4 or MQL5)"
    )

    type: ProjectType = Field(
        ...,
        description="Project type"
    )

    # MQL-specific fields
    include_mode: IncludeMode = Field(
        default=IncludeMode.INCLUDE,
        description="Include processing mode. Use 'include' (copy .mqh) or 'flat' (generate _flat files). Forced to 'flat' for type='package'."
    )

    entrypoints: Optional[List[str]] = Field(
        default=None,
        description="Main source files. Required for all types except 'package'"
    )

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: Any) -> ProjectType:
        """Validate type is not None and is a valid ProjectType enum value."""
        if v is None:
            raise ValueError("type cannot be None")
        if isinstance(v, str):
            try:
                return ProjectType(v)
            except ValueError:
                valid_types = [x.value for x in ProjectType]
                raise ValueError(f"type must be one of {valid_types}, got: {v}")
        return v

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, v: Any) -> Target:
        """Validate target is not None and is a valid Target enum value."""
        if v is None:
            raise ValueError("target cannot be None")
        if isinstance(v, str):
            try:
                return Target(v)
            except ValueError:
                valid_targets = [x.value for x in Target]
                raise ValueError(f"target must be one of {valid_targets}, got: {v}")
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
    @classmethod
    def validate_entrypoints_presence(cls, data: Any) -> Any:
        """Ensure non-package projects have at least one entrypoint."""
        if data.type != ProjectType.PACKAGE:
            if not data.entrypoints or len(data.entrypoints) == 0:
                raise ValueError(
                    f"Projects of type '{data.type.value}' must have at least one entrypoint"
                )
        return data
