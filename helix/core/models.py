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
        description="Dependency name or 'this' (current project). Can be omitted if source is local."
    )
    src: str = Field(..., description="Source path relative to dependency root")
    dst: str = Field(..., description="Destination path in the final package")


class DistRelease(BaseModel):
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
    items: List[DistItem] = Field(..., min_length=1, description="Files to include in this release")


class DistSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dist: List[DistRelease] = Field(
        default_factory=list,
        description="Distribution package definitions (used by `helix dist`)"
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
    private: bool = Field(default=False, description="Set to true for private repositories")
    oauth_provider: Optional[OAuthProvider] = Field(default=None, description="OAuth provider for private repo access")


class HelixEnterpriseSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proxy_url: Optional[AnyUrl] = Field(default=None, description="Proxy URL for enterprise environments")


class HelixSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pro: Optional[HelixProSection] = Field(default=None, description="Helix Pro configuration")
    enterprise: Optional[HelixEnterpriseSection] = Field(default=None, description="Helix Enterprise configuration")


# ================================================================
# HelixManifest — FINAL VERSION
# ================================================================

# === Regex principal: cobre TODOS os casos SemVer + ranges NPM + prefixed refs ===
REF_PATTERN = re.compile(
    r"^"
    r"(?:"                              # Grupo 1: operadores de range (NPM style)
        r"(\^|~|>=|<=|>|<|\s*)"         # ^ ~ >= <= > < (ou espaços
        r"(v?)(\d+\.\d+\.\d+)"          # versão base (com ou sem v)
        r"(-[A-Za-z0-9\.\-]+)?"         # pre-release opcional
        r"(\+[A-Za-z0-9\.\-]+)?"        # build metadata opcional
        r"(?:\s+(<|<=)\s*(v?)(\d+\.\d+\.\d+))?"  # segundo lado do range (< ou <=)
    r")"
    r"|"                                # OU
    r"(branch|tag|commit)=[A-Za-z0-9._-]+$"  # prefixed refs
    r"$",
    re.IGNORECASE
)

# === Regex auxiliar: SemVer puro (para validar versão isolada) ===
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _is_valid_ref(ref: str) -> bool:
    ref = ref.strip()

    # 1. Prefixed: branch=, tag=, commit=
    if "=" in ref and ref.split("=", 1)[0].lower() in ("branch", "tag", "commit"):
        return bool(REF_PATTERN.match(ref))

    # 2. NPM-style ranges: ^ ~ >= <= > < ou intervalos como ">=1.0.0 <2.0.0"
    if any(op in ref for op in ("^", "~", ">=", "<=", ">", "<", " ")):
        return bool(REF_PATTERN.match(ref.replace(" ", "")))  # remove espaços

    # 3. SemVer puro (com ou sem v)
    cleaned = ref.lstrip("vV")
    return bool(SEMVER_PATTERN.match(cleaned))

class HelixManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[\w\-\.]+$",
        description="Project name (alphanumeric, hyphens, underscores, dots only)"
    )
    version: str = Field(..., description="Required Semantic Versioning string (e.g. 1.0.0)")

    description: Optional[str] = Field(default=None, max_length=500, description="Short project description")
    author: Optional[str] = Field(default=None, description="Author or team name")
    license: Optional[str] = Field(default="MIT", description="License identifier (default: MIT)")

    type: MQLProjectType = Field(..., description="Project type: expert, indicator, script, library or include")
    target: MQLTarget = Field(default=MQLTarget.MQL5, description="Target platform: MQL4 or MQL5 (default: MQL5)")

    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Dependencies with Git URLs or local paths and version constraints"
    )

    include_mode: IncludeMode = Field(
        default=IncludeMode.INCLUDE,
        description="Mode: 'include' (copy .mqh) or 'flat' (generate _flat files). Forced to 'flat' for type='include'"
    )

    entrypoints: Optional[List[str]] = Field(
        default=None,
        description="Main source files (.mq4/.mq5/.mqh). Required except for type='include'"
    )

    dist: Optional[DistSection] = Field(default=None, description="Distribution package configuration")

    helix: Optional[HelixSection] = Field(default=None, description="Helix Pro and Enterprise settings")


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
    def validate_include_project_rules(self) -> "HelixManifest":
        if self.type == MQLProjectType.INCLUDE:
            # Biblioteca pura → sempre flat (melhor DX)
            self.include_mode = IncludeMode.FLAT
            
            # Permite scripts de teste locais
            if self.entrypoints is None:
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

            # === 1. Local file:// ===
            if spec.startswith("file://"):
                local_path = spec[7:]
                if not Path(local_path).exists():
                    raise ValueError(f"Local dependency '{dep_name}' not found: {local_path}")
                if not any((Path(local_path) / f).exists() for f in ("helix.yaml", "helix.json")):
                    raise ValueError(f"Local dependency '{dep_name}' missing helix.yaml or helix.json")
                continue

            # === 2. Caminho relativo/absoluto (sem protocolo) ===
            if spec.startswith(("./", "../", "/", "~")) or Path(spec).exists() or (Path.cwd() / spec).exists():
                continue

            # === 3. Remote Git (https, http, git@, ssh://) ===
            if not any(spec.startswith(proto) for proto in ("https://", "http://", "git@", "ssh://")):
                raise ValueError(f"Invalid dependency '{dep_name}': must use https://, git@, ssh://, file:// or local path")

            if spec.count("#") != 1:
                raise ValueError(f"Invalid dependency '{dep_name}': must contain exactly one '#' separator")

            base_url, ref = spec.split("#", 1)

            if not ref:
                raise ValueError(f"Invalid dependency '{dep_name}': version/reference cannot be empty after '#'")

            if not base_url.endswith(".git"):
                raise ValueError(f"Invalid dependency '{dep_name}': Git URL must end with '.git'")

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