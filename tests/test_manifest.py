# tests/test_manifest.py
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from helix.core.models import HelixManifest, load_helix_manifest


# --------------------------------------------------------------------------- #
# Fixtures e helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Cria um diretório temporário com um helix.json válido"""
    d = tmp_path / "sample-project"
    d.mkdir()

    manifest_data = {
        "name": "super-rsi-alert",
        "version": "2.4.1",
        "description": "RSI com alertas visuais, sonoros e Telegram",
        "author": "João Trader <joao@tradingpro.com>",
        "license": "MIT",
        "target": "MQL5",
        "type": "indicator",

        "entrypoints": ["SuperRSI_Alert.mq5"],
        
        "dependencies": {
            "json.mql": "https://github.com/fxdss/json.mql.git#v1.8.2",
            "telegram": "git@github.com:fabiuz/telegram.mql.git#branch=main",
            "utils": "https://gitlab.com/mql-libs/utils.git#v3.1.0"
        },
        "helix": {
            "pro": {
                "private": True,
                "oauth_provider": "github"
            },
            "enterprise": {
                "proxy_url": "https://helix-proxy.bankcorp.com"
            }
        }
    }

    manifest_path = d / "helix.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return d


@pytest.fixture
def include_only_project(tmp_path: Path) -> Path:
    """Projeto do tipo 'include' (só .mqh)"""
    d = tmp_path / "include-lib"
    d.mkdir()

    data = {
        "name": "math-advanced",
        "version": "1.0.0",
        "type": "include",
        "target": "MQL5",


        "dependencies": {}
    }

    (d / "helix.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# Testes
# --------------------------------------------------------------------------- #
def test_load_valid_manifest(sample_dir: Path):
    """Testa carregamento completo de um manifesto válido"""
    manifest = load_helix_manifest(sample_dir / "helix.json")

    assert isinstance(manifest, HelixManifest)
    assert manifest.name == "super-rsi-alert"
    assert manifest.version == "2.4.1"
    assert manifest.description == "RSI com alertas visuais, sonoros e Telegram"
    assert manifest.author == "João Trader <joao@tradingpro.com>"
    assert manifest.license == "MIT"
    assert manifest.target.value == "MQL5"

    # mql section
    assert manifest.type.value == "indicator"
    assert manifest.entrypoints == ["SuperRSI_Alert.mq5"]

    # dependencies
    assert len(manifest.dependencies) == 3
    assert manifest.dependencies["json.mql"] == "https://github.com/fxdss/json.mql.git#v1.8.2"
    assert manifest.dependencies["telegram"] == "git@github.com:fabiuz/telegram.mql.git#branch=main"

    # helix section
    assert manifest.helix is not None
    assert manifest.helix.pro is not None
    assert manifest.helix.pro.private is True
    assert manifest.helix.pro.oauth_provider.value == "github"
    assert manifest.helix.enterprise is not None
    assert str(manifest.helix.enterprise.proxy_url) == "https://helix-proxy.bankcorp.com/"


def test_include_type_has_no_entrypoint(include_only_project: Path):
    """Garante que projetos 'include' são aceitos sem entrypoint"""
    manifest = load_helix_manifest(include_only_project / "helix.json")

    assert manifest.target.value == "MQL5"

    assert manifest.type.value == "include"
    assert manifest.entrypoints == []


def test_invalid_entrypoint_for_include(tmp_path: Path):
    d = tmp_path / "invalid-include"
    d.mkdir()
    data = {
        "name": "bad-lib",
        "version": "1.0.0",
        "type": "include",
        "entrypoints": ["Bad.mq5"]
    }
    (d / "helix.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json")

    assert "Projetos do tipo 'include' não devem ter entrypoints" in str(exc.value)


def test_missing_entrypoint_for_indicator(tmp_path: Path):
    d = tmp_path / "missing-entrypoint"
    d.mkdir()
    data = {
        "name": "no-entry",
        "version": "1.0.0",
        "type": "indicator"
    }
    (d / "helix.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json")

    assert "Projetos do tipo 'indicator' devem ter pelo menos um entrypoint" in str(exc.value)


def test_invalid_git_url(tmp_path: Path):
    """URL de dependência mal formada deve falhar"""
    d = tmp_path / "bad-dep"
    d.mkdir()
    data = {
        "name": "bad",
        "version": "1.0.0",
        "type": "script", 
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "badlib": "https://github.com/user/lib"  # ← sem .git
        }
    }
    (d / "helix.json").write_text(json.dumps(data))

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json")

    error_msg = str(exc.value)
    assert "Dependência 'badlib' inválida" in error_msg
    assert "Erro de validação no helix.json" in error_msg


def test_invalid_semver(tmp_path: Path):
    """Versão fora do padrão SemVer"""
    d = tmp_path / "bad-version"
    d.mkdir()
    data = {
        "name": "bad",
        "version": "1.2",  # ← faltou patch
        "type": "indicator", 
        "entrypoints": ["X.mq5"],
    }
    (d / "helix.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json")

    assert "version deve seguir o padrão SemVer" in str(exc.value)


def test_file_not_found():
    """helix.json inexistente"""
    with pytest.raises(FileNotFoundError):
        load_helix_manifest("/caminho/que/nao/existe/helix.json")