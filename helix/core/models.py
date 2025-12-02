# helix/core/models.py
from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import json

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ConfigDict,
    AnyUrl,
    ValidationError,
    model_validator,
)

from urllib.parse import urlparse
from pathlib import Path


class MQLTarget(str, Enum):
    MQL4 = "MQL4"
    MQL5 = "MQL5"


class MQLProjectType(str, Enum):
    EXPERT = "expert"
    INDICATOR = "indicator"
    SCRIPT = "script"
    LIBRARY = "library"
    INCLUDE = "include"  # apenas headers .mqh


class OAuthProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE = "azure"
    GOOGLE = "google"


class BuildMode(str, Enum):
    INCLUDES = "includes"      # default — só copia .mqh para Includes/
    FLAT = "flat"              # gera arquivos _flat.mq5 autocontidos    


# ================================================================
# Seção dist
# ================================================================
# helix/core/models.py (adicionar esses modelos)

class DistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dependency_id: Optional[str] = Field(
        default=None,
        alias="dependencyId",
        description="Nome da dependência ou 'this' (ou omitido) para o projeto atual"
    )
    src: str = Field(..., description="Caminho relativo do arquivo de origem")
    dst: str = Field(..., description="Caminho relativo no pacote de distribuição")

    @field_validator("dependency_id")
    @classmethod
    def normalize_dependency_id(cls, v: Optional[str]) -> str:
        if v is None or v == "this" or v == "":
            return "this"
        return v.lower()  # normaliza para comparação


class DistRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="ID único do release")
    name: str = Field(..., description="Nome do pacote (pode ter ${version})")
    items: List[DistItem] = Field(..., min_length=1)


class DistSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dist: List[DistRelease] = Field(
        default_factory=list,
        description="Configuração de distribuição do projeto"
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
# Seções helix.pro / enterprise
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
# HelixManifest — FINAL, exatamente como você quer
# ================================================================

# Regex aceita:
# • v1.2.3, 1.2.3
# • v1.0.0-alpha, v1.0.0-alpha.1+build.123
# • tag=v2.5.0, branch=main, commit=abc123
SEMVER_OR_PREFIXED_REF = re.compile(
    r"^"
    r"(?P<prefix>tag|branch|commit)=[A-Za-z0-9._-]+$"
    r"|"
    r"(?:v|V)?"                              # v opcional
    r"(?:0|[1-9]\d*)\."                       # major
    r"(?:0|[1-9]\d*)\."                      # minor
    r"(?:0|[1-9]\d*)"                        # patch
    r"(?:-[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?" # pre-release (permite ponto, hífen, alfanum)
    r"(?:\+[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?" # build metadata
    r"$"
)

class HelixManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[\w\-\.]+$")
    version: str = Field(..., description="SemVer obrigatória")

    description: Optional[str] = Field(default=None, max_length=500)
    author: Optional[str] = Field(default=None)
    license: Optional[str] = Field(default="MIT")

    type: MQLProjectType = Field(..., description="expert, indicator, library, include, etc.")
    target: MQLTarget = Field(default=MQLTarget.MQL5, description="MQL4 ou MQL5")

    dependencies: Dict[str, str] = Field(default_factory=dict)

    build_mode: BuildMode = Field(
        default=BuildMode.INCLUDES,
        description="Modo de preparação para compilação: 'includes' (padrão) ou 'flat'"
    )

    # Lista de entrypoints — obrigatória apenas se type != include
    entrypoints: Optional[List[str]] = Field(
        default=None,
        description="Lista de arquivos .mq4/.mq5. Obrigatório exceto para type='include'"
    )

    dist: Optional[DistSection] = Field(default=None)

    helix: Optional[HelixSection] = None

    # Validação inteligente de entrypoints
    @model_validator(mode="before")
    @classmethod
    def validate_entrypoints_presence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            proj_type = data.get("type")
            has_entrypoints = "entrypoints" in data and data["entrypoints"] is not None

            if proj_type != "include":
                # todos os outros tipos: entrypoints é obrigatório e não vazio
                if not has_entrypoints or len(data["entrypoints"]) == 0:
                    raise ValueError(f"Projetos do tipo '{proj_type}' devem ter pelo menos um entrypoint")
        return data

    # Validação de extensão dos entrypoints (só roda se existirem)
    @field_validator("entrypoints", mode="before")
    @classmethod
    def validate_entrypoints_format(cls, v: Any) -> List[str]:
        if v is None or v == []:
            return []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise ValueError("entrypoints deve ser uma lista de strings")
        for ep in v:
            if not isinstance(ep, str):
                raise ValueError(f"entrypoint deve ser string: {ep!r}")
            if not ep.lower().endswith((".mq4", ".mq5")):
                raise ValueError(f"entrypoint deve ter extensão .mq4 ou .mq5: {ep}")
        return v
    

    # Tipo 'include' → entrypoints vazio
    @model_validator(mode="after")
    def check_include_has_no_entrypoints(self) -> "HelixManifest":
        if self.type == MQLProjectType.INCLUDE:
            if self.entrypoints and len(self.entrypoints) > 0:
                raise ValueError("Projetos do tipo 'include' não devem ter entrypoints")
            self.entrypoints = []
        return self


    # SemVer
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
            raise ValueError("version deve seguir o padrão SemVer (ex: 1.0.0, 2.1.3-beta.1)")
        return v


    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies(cls, v: Any) -> Dict[str, str]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("dependencies deve ser um dicionário")

        for dep_name, spec in v.items():
            if not isinstance(spec, str):
                raise ValueError(f"Dependência '{dep_name}' deve ser string")
            spec = spec.strip()
            if not spec:
                raise ValueError(f"Dependência '{dep_name}' está vazia")

            # 1. file:// → caminho local explícito (novo padrão Helix)
            if spec.startswith("file://"):
                local_path = spec[7:]  # remove file://
                if not Path(local_path).exists():
                    raise ValueError(f"Dependência local '{dep_name}' não encontrada: {local_path}")
                if not (Path(local_path) / "helix.json").exists():
                    raise ValueError(f"Dependência local '{dep_name}' não tem helix.json: {local_path}")
                continue

            # 2. Caminho relativo/absolute sem protocolo → também aceito como local
            if spec.startswith(("./", "../", "/", "~")):
                continue
            if Path(spec).exists() or (Path.cwd() / spec).exists():
                continue

            # 3. Git remoto → regras rígidas
            if not any(spec.startswith(p) for p in ("https://", "http://", "git@", "ssh://")):
                raise ValueError(
                    f"Dependência '{dep_name}' inválida → formato não reconhecido\n"
                    f"Fornecido: {spec!r}"
                )

            # Deve ter exatamente um # e ref não vazia
            if spec.count("#") != 1:
                raise ValueError(f"Dependência '{dep_name}' inválida → deve ter exatamente um #ref")
            base_url, ref = spec.split("#", 1)

            if not ref:
                raise ValueError(f"Dependência '{dep_name}' inválida → ref não pode ser vazia após #")

            # URL deve terminar em .git
            if not base_url.endswith(".git"):
                raise ValueError(
                    f"Dependência '{dep_name}' inválida → URL deve terminar em .git\n"
                    f"URL: {base_url}"
                )

            # Ref deve seguir padrão SemVer completo ou tag/branch/commit
            if not SEMVER_OR_PREFIXED_REF.match(ref):
                raise ValueError(
                    f"Dependência '{dep_name}' inválida → ref não reconhecida: #{ref}\n"
                    f"Exemplos válidos:\n"
                    f"  v1.2.3\n"
                    f"  1.2.3\n"
                    f"  v1.0.0-alpha.1+build.123\n"
                    f"  branch=main\n"
                    f"  tag=v2.5.0"
                )

        return v    

    # Renderiza nome do pacote com versão
    def get_package_name(self, release_id: str = "release") -> str:
        if not self.dist or not self.dist.dist:
            return f"{self.name}-{self.version}.zip"
        return self.dist.render_name(release_id, self.version)

# ================================================================
# Carregamento
# ================================================================
def load_helix_manifest(path: Union[str, Path] = "helix.json") -> HelixManifest:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"helix.json não encontrado em {p.resolve()}")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"helix.json contém JSON inválido: {e}") from e

    try:
        return HelixManifest(**data)
    except ValidationError as e:
        errors = "\n".join(
            f"  • {' → '.join(map(str, err['loc']))}: {err['msg']}"
            for err in e.errors()
        )
        raise ValueError(f"Erro de validação no helix.json:\n{errors}") from e