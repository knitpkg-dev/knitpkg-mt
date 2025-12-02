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
    helix: Optional[HelixSection] = None

    # Lista de entrypoints — obrigatória apenas se type != include
    entrypoints: Optional[List[str]] = Field(
        default=None,
        description="Lista de arquivos .mq4/.mq5. Obrigatório exceto para type='include'"
    )

    # Validação inteligente de entrypoints
    @model_validator(mode="before")
    @classmethod
    def validate_entrypoints_presence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            proj_type = data.get("type")
            has_entrypoints = "entrypoints" in data and data["entrypoints"] is not None

            if proj_type == "include":
                # include: entrypoints deve ser ausente ou vazio
                if has_entrypoints and len(data["entrypoints"]) > 0:
                    raise ValueError("Projetos do tipo 'include' não devem ter entrypoints")
                data["entrypoints"] = []  # garante lista vazia
            else:
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
    def validate_git_urls(cls, v: Any) -> Dict[str, str]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("dependencies deve ser um dicionário")

        # Regex final – aceita tudo real e rejeita EXATAMENTE o caso com ".."
        pattern = re.compile(
            r"^"
            r"(https?://|git@)"
            r"([\w.\-]+)"
            r"[:/]"
            r"([\w.\-~]+/)+"           # pelo menos um / (aceita caminhos profundos)
            r"[\w.\-~]+"
            r"\.git"
            r"#"
            r"(?:"
            r"([a-zA-Z0-9._-]+)"                                      # branch simples, tag, etc.
            r"|(?:tag|branch|commit)[=:]?[a-zA-Z0-9._-]+"
            r"|v?"
            r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
            r"(?:-"
            r"(?=[^\.])"                                           # garante que começa com algo que não é ponto
            r"[0-9a-zA-Z-]+"
            r"(?:\.[0-9a-zA-Z-]+)*"
            r"(?<![\.])"                                           # garante que não termina com ponto
            r")?"
            r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?"               # build metadata
            r")$",
            re.IGNORECASE,
        )

        for name, url in v.items():
            if not isinstance(url, str):
                raise ValueError(f"Dependência '{name}' deve ser string")
            url_clean = url.strip()

            if not pattern.match(url_clean):
                raise ValueError(
                    f"Dependência '{name}' inválida → URL git ou ref mal formada\n"
                    f"Fornecido: {url_clean!r}\n"
                    f"Exemplos válidos:\n"
                    f"  https://github.com/user/lib.git#v1.2.3\n"
                    f"  https://github.com/user/lib.git#v1.2.3+build.123\n"
                    f"  https://github.com/user/lib.git#v1.0.0-alpha.beta\n"
                    f"  git@github.com:user/lib.mql.git#branch=main"
                )

        return v


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