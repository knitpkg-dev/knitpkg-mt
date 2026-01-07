# tests/test_dependency_url.py

import pytest
from pathlib import Path
import json
from knitpkg.core.file_reading import load_helix_manifest
from knitpkg.mql.models import MQLHelixManifest

VALID_URLS = [
    # === SemVer clássico (com e sem v), versão exata ===
    "https://github.com/user/lib.mql.git#v1.2.3",
    "https://github.com/user/lib.mql.git#1.2.3",
    "git@github.com:user/lib.mql.git#v2.0.0",
    "git@github.com:user/lib.mql.git#3.1.4",

    # === SemVer com versão não exata ===
    "https://github.com/knitpkg/core.git#^2.0.0",
    "https://github.com/ai/mql-engine.git#>=3.1.0 <4.0.0",
    "https://github.com/pro/risk-manager.git#~1.8.5",
    "https://github.com/pro/indicators.git#^4.2.0",
    "https://github.com/team/experimental.git#branch=next",

    # === Pré-release ===
    "https://github.com/user/lib.git#v1.0.0-alpha",
    "https://github.com/user/lib.git#v1.0.0-alpha.1",
    "https://github.com/user/lib.git#v1.0.0-beta.2",
    "https://github.com/user/lib.git#v2.0.0-rc.1",
    "https://github.com/user/lib.git#1.5.0-dev.20250330",

    # === Build metadata ===
    "https://github.com/user/lib.git#v1.2.3+build.123",
    "https://github.com/user/lib.git#v1.2.3+sha.abc123def",
    "https://github.com/user/lib.git#v1.2.3+exp.sha.5114f85",

    # === Pré-release + build ===
    "https://github.com/user/lib.git#v1.0.0-alpha.1+build.456",

    # === Formatos com prefixo explícito ===
    "https://github.com/user/lib.git#tag=v2.5.0",
    "https://github.com/user/lib.git#tag=2.5.0",
    "git@github.com:user/lib.git#branch=v1.8.2",
    "git@github.com:user/lib.git#commit=abc123def456",

    # === Casos reais famosos ===
    "https://github.com/fxdss/json.mql.git#v1.8.2",
    "git@github.com:fabiuz/telegram.mql.git#branch=main",
    "https://github.com/dingmaotu/mql-zmq.git#v1.0.4",
    "https://gitlab.com/mql5/libs/utils.git#v3.2.1",

    # === Outros domínios ===
    "git@gitlab.com:group/project.mql.git#v1.0.0",
    "https://bitbucket.org/team/indicators.git#2.1.0",
    "git@bitbucket.org:team/utils.git#branch=stable",
]

INVALID_URLS = [
    # === Faltando .git ===
    "https://github.com/user/lib#v1.2.3",
    "git@github.com:user/lib#1.0.0",

    # === Sem ref após # ===
    "https://github.com/user/lib.git#",
    "git@github.com:user/lib.git#",

    # === Formato errado ===
    "https://github.com/user/lib.git",
    "git@github.com:user/lib.git",
    "ftp://github.com/user/lib.git#v1.0.0",
    "user/lib.git#v1.0.0",
]

@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_dependency_urls(tmp_path: Path, url: str):
    """Test that valid dependency URLs are accepted."""
    d = tmp_path / "valid"
    d.mkdir()
    manifest = {
        "name": "test",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "mylib": url
        }
    }
    (d / "knitpkg.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Should load without error using MQL manifest
    manifest_obj = load_helix_manifest(d / "knitpkg.json", manifest_class=MQLHelixManifest)
    assert manifest_obj.dependencies["mylib"] == url

@pytest.mark.parametrize("url", INVALID_URLS)
def test_invalid_dependency_urls(tmp_path: Path, url: str):
    """Test that invalid dependency URLs raise ValueError."""
    d = tmp_path / "invalid"
    d.mkdir()
    manifest = {
        "name": "test",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "mylib": url
        }
    }
    (d / "knitpkg.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Should raise ValueError with clear message
    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "knitpkg.json", manifest_class=MQLHelixManifest)

    error_msg = str(exc.value)
    assert "Invalid dependency 'mylib'" in error_msg or "Error reading knitpkg." in error_msg

def test_branch_main_is_accepted(tmp_path: Path):
    """Test that branch=main is accepted (real use case)."""
    d = tmp_path / "branch"
    d.mkdir()
    manifest = {
        "name": "test",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Bot.mq5"],
        "dependencies": {
            "telegram": "git@github.com:fabiuz/telegram.mql.git#branch=main"
        }
    }
    (d / "knitpkg.json").write_text(json.dumps(manifest), encoding="utf-8")
    obj = load_helix_manifest(d / "knitpkg.json", manifest_class=MQLHelixManifest)
    assert obj.dependencies["telegram"] == "git@github.com:fabiuz/telegram.mql.git#branch=main"
