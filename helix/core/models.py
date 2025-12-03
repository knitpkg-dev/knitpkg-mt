# helix/core/models.py
from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import yaml

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
    AnyUrl,
    model_validator,
)

class MQLTarget(str, Enum):
    MQL4 = "MQL4"
    MQL5 = "MQL5"


class MQLProjectType(str, Enum):
    EXPERT = "expert"
    INDICATOR = "indicator"
    SCRIPT = "script"
    LIBRARY = "library"
    INCLUDE = "include"  # only .mqh headers


class OAuthProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE = "azure"
    GOOGLE = "google"


class IncludeMode(str, Enum):
    INCLUDE = "include"        # default — just copies .mqh to helix/include/
    FLAT = "flat"              # generates self-contained _flat.mq5/.mqh files


# ================================================================
# Dist section
# ================================================================

class DistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dependency_id: Optional[str] = Field(
        default=None,
        alias="dependencyId",
        description="Dependency name or 'this' (or omitted) for the current project"
    )
    src: str = Field(..., description="Relative source file path")
    dst: str = Field(..., description="Relative path in the distribution package")

    @field_validator("dependency_id")
    @classmethod
    def normalize_dependency_id(cls, v: Optional[str]) -> str:
        if v is None or v == "this" or v == "":
            return "this"
        return v.lower()


class DistRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="Unique release ID")
    name: str = Field(..., description="Package name (can contain ${version})")
    items: List[DistItem] = Field(..., min_length=1)


class DistSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dist: List[DistRelease] = Field(
        default_factory=list,
        description="Project distribution configuration"
    )

    def get_release_by_id(self, release_id: str) -> Optional[DistRelease]:
        for r in self.dist:
            if r.id == release_id:
                return r
        return None

    def render_name(self, release_id: str, version: str) -> str:
        release = self.get_release_by_id(release_id)
        if not release:
            return f"{release_id}-{version}.zip"
        return release.name.replace("${version}", version)


# ================================================================
# Helix Pro / Enterprise sections
# ================================================================
class HelixProSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    private: bool = False
    oauth_provider: Optional[OAuthProvider] = None


class HelixEnterpriseSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proxy_url: Optional[AnyUrl] = None


class HelixSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pro: Optional[HelixProSection] = None
    enterprise: Optional[HelixEnterpriseSection] = None


# ================================================================
# HelixManifest — FINAL VERSION
# ================================================================

SEMVER_OR_PREFIXED_REF = re.compile(
    r"^"
    r"(?P<prefix>tag|branch|commit)=[A-Za-z0-9._-]+$"
    r"|"
    r"(?:v|V)?"
    r"(?:0|[1-9]\d*)\."
    r"(?:0|[1-9]\d*)\."
    r"(?:0|[1-9]\d*)"
    r"(?:-[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?"
    r"(?:\+[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?"
    r"$"
)

class HelixManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[\w\-\.]+$")
    version: str = Field(..., description="Required SemVer version")

    description: Optional[str] = Field(default=None, max_length=500)
    author: Optional[str] = Field(default=None)
    license: Optional[str] = Field(default="MIT")

    type: MQLProjectType = Field(..., description="expert, indicator, library, include, etc.")
    target: MQLTarget = Field(default=MQLTarget.MQL5, description="MQL4 or MQL5")

    dependencies: Dict[str, str] = Field(default_factory=dict)

    include_mode: IncludeMode = Field(
        default=IncludeMode.INCLUDE,
        description="Build preparation mode: 'include' (default) or 'flat'"
    )

    entrypoints: Optional[List[str]] = Field(
        default=None,
        description=".mq4/.mq5 file list. Required except for type='include'"
    )

    dist: Optional[DistSection] = Field(default=None)

    helix: Optional[HelixSection] = None


    @model_validator(mode="before")
    @classmethod
    def validate_entrypoints_presence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            proj_type = data.get("type")
            has_entrypoints = "entrypoints" in data and data["entrypoints"] is not None

            if proj_type != "include":
                if not has_entrypoints or len(data["entrypoints"]) == 0:
                    raise ValueError(f"Projects of type '{proj_type}' must have at least one entrypoint")
        return data


    @field_validator("entrypoints", mode="before")
    @classmethod
    def validate_entrypoints_format(cls, v: Any) -> List[str]:
        if v is None or v == []:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise ValueError("entrypoints must be a list of strings")
        for ep in v:
            if not isinstance(ep, str):
                raise ValueError(f"entrypoint must be a string: {ep!r}")
            if not ep.lower().endswith((".mq4", ".mq5", ".mqh")):
                raise ValueError(f"entrypoint must have .mq4, .mq5 or .mqh extension: {ep}")
        return v


    @model_validator(mode="after")
    def check_include_has_no_entrypoints(self) -> "HelixManifest":
        if self.type == MQLProjectType.INCLUDE:
            if self.entrypoints and len(self.entrypoints) > 0:
                raise ValueError("Projects of type 'include' must not have entrypoints")
            self.entrypoints = []
        return self


    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        v = v.strip()
        pattern = re.compile(
            r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
            r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
            r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
        )
        if not pattern.match(v):
            raise ValueError("version must follow SemVer format (e.g. 1.0.0, 2.1.3-beta.1)")
        return v


    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies(cls, v: Any) -> Dict[str, str]:
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

            # 1. file:// → explicit local path
            if spec.startswith("file://"):
                local_path = spec[7:]
                if not Path(local_path).exists():
                    raise ValueError(f"Local dependency '{dep_name}' not found: {local_path}")
                if not (Path(local_path) / "helix.json").exists() and not (Path(local_path) / "helix.yaml").exists():
                    raise ValueError(f"Local dependency '{dep_name}' missing helix.yaml or helix.json: {local_path}")
                continue

            # 2. Relative/absolute path without protocol → also treated as local
            if spec.startswith(("./", "../", "/", "~")):
                continue
            if Path(spec).exists() or (Path.cwd() / spec).exists():
                continue

            # 3. Remote Git → strict rules
            if not any(spec.startswith(p) for p in ("https://", "http://", "git@", "ssh://")):
                raise ValueError(
                    f"Invalid dependency '{dep_name}' → unrecognized format\n"
                    f"Provided: {spec!r}"
                )

            if spec.count("#") != 1:
                raise ValueError(f"Invalid dependency '{dep_name}' → must contain exactly one #ref")
            base_url, ref = spec.split("#", 1)

            if not ref:
                raise ValueError(f"Invalid dependency '{dep_name}' → ref cannot be empty after #")

            if not base_url.endswith(".git"):
                raise ValueError(
                    f"Invalid dependency '{dep_name}' → URL must end with .git\n"
                    f"URL: {base_url}"
                )

            if not SEMVER_OR_PREFIXED_REF.match(ref):
                raise ValueError(
                    f"Invalid dependency '{dep_name}' → unrecognized ref: #{ref}\n"
                    f"Valid examples:\n"
                    f"  v1.2.3\n"
                    f"  1.2.3\n"
                    f"  v1.0.0-alpha.1+build.123\n"
                    f"  branch=main\n"
                    f"  tag=v2.5.0"
                )

        return v


    def get_package_name(self, release_id: str = "release") -> str:
        if not self.dist or not self.dist.dist:
            return f"{self.name}-{self.version}.zip"
        return self.dist.render_name(release_id, self.version)


# ================================================================
# Loading
# ================================================================
from rich.console import Console
console = Console()

def load_helix_manifest(path: Optional[str | Path] = None) -> HelixManifest:
    """
    Loads helix.json OR helix.yaml (yaml takes precedence if both exist)
    
    Args:
        path: None (current dir), path to file (helix.yaml/helix.json),
              or directory (searches helix.yaml/helix.json inside it)
    
    Raises:
        ValueError: If path points to invalid filename
        FileNotFoundError: If no manifest found
    """
    if path is None:
        yaml_path = Path("helix.yaml")
        json_path = Path("helix.json")
    else:
        path = Path(path)
        
        if path.is_file():
            if path.name not in ("helix.yaml", "helix.json"):
                raise ValueError(
                    f"Invalid file: {path.name}\n"
                    f"Expected: helix.yaml or helix.json"
                )
            yaml_path = path if path.name == "helix.yaml" else None
            json_path = path if path.name == "helix.json" else None
        elif path.is_dir():
            yaml_path = path / "helix.yaml"
            json_path = path / "helix.json"
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    if yaml_path and yaml_path.exists():
        return _load_from_yaml(yaml_path)
    elif json_path and json_path.exists():
        return _load_from_json(json_path)
    else:
        raise FileNotFoundError("No manifest file found: helix.yaml or helix.json")

def _load_from_yaml(path: Path) -> HelixManifest:
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if data is None:
            raise ValueError("helix.yaml is empty")
        console.log(f"[bold green]Loaded:[/] {path.name}")
        return HelixManifest(**data)
    except Exception as e:
        raise ValueError(f"Error reading helix.yaml: {e}")

def _load_from_json(path: Path) -> HelixManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        console.log(f"[bold green]Loaded:[/] {path.name}")
        return HelixManifest(**data)
    except Exception as e:
        raise ValueError(f"Error reading helix.json: {e}")