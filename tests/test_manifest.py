# tests/test_manifest.py

import json
from pathlib import Path

import pytest

from helix.mql.models import MQLHelixManifest, MQLProjectType, Target
from helix.core.file_reading import load_helix_manifest

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a valid helix.json"""
    d = tmp_path / "sample-project"
    d.mkdir()

    manifest_data = {
        "name": "super-rsi-alert",
        "version": "2.4.1",
        "description": "RSI with visual, sound and Telegram alerts",
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
def package_project(tmp_path: Path) -> Path:
    """Package project (reusable library with .mqh files)"""
    d = tmp_path / "package-lib"
    d.mkdir()

    data = {
        "name": "math-advanced",
        "version": "1.0.0",
        "type": "package",
        "target": "MQL5",
        "dependencies": {}
    }

    (d / "helix.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return d

# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_load_valid_manifest(sample_dir: Path):
    """Test loading a complete valid manifest"""
    manifest = load_helix_manifest(sample_dir / "helix.json", manifest_class=MQLHelixManifest)

    assert isinstance(manifest, MQLHelixManifest)
    assert manifest.name == "super-rsi-alert"
    assert manifest.version == "2.4.1"
    assert manifest.description == "RSI with visual, sound and Telegram alerts"
    assert manifest.author == "João Trader <joao@tradingpro.com>"
    assert manifest.license == "MIT"
    assert manifest.target == Target.MQL5

    # MQL-specific fields
    assert manifest.type == MQLProjectType.INDICATOR
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

def test_package_has_no_entrypoint(package_project: Path):
    """Ensure package projects are accepted without entrypoints"""
    manifest = load_helix_manifest(package_project / "helix.json", manifest_class=MQLHelixManifest)

    assert manifest.target == Target.MQL5
    assert manifest.type == MQLProjectType.PACKAGE
    assert manifest.entrypoints is None or manifest.entrypoints == []

def test_missing_entrypoint_for_indicator(tmp_path: Path):
    """Non-package projects must have entrypoints"""
    d = tmp_path / "missing-entrypoint"
    d.mkdir()
    data = {
        "name": "no-entry",
        "version": "1.0.0",
        "type": "indicator",
        "target": "MQL5"
    }
    (d / "helix.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json", manifest_class=MQLHelixManifest)

    assert "Projects of type 'indicator' must have at least one entrypoint" in str(exc.value)

def test_invalid_git_url(tmp_path: Path):
    """Malformed dependency URL should fail"""
    d = tmp_path / "bad-dep"
    d.mkdir()
    data = {
        "name": "bad",
        "version": "1.0.0",
        "type": "script",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "badlib": "https://github.com/user/lib"  # ← missing .git
        }
    }
    (d / "helix.json").write_text(json.dumps(data))

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json", manifest_class=MQLHelixManifest)

    error_msg = str(exc.value)
    assert "Invalid dependency 'badlib'" in error_msg or "Error reading helix." in error_msg

def test_invalid_semver(tmp_path: Path):
    """Version not following SemVer"""
    d = tmp_path / "bad-version"
    d.mkdir()
    data = {
        "name": "bad",
        "version": "1.2",  # ← missing patch
        "type": "indicator",
        "target": "MQL5",
        "entrypoints": ["X.mq5"],
    }
    (d / "helix.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_helix_manifest(d / "helix.json", manifest_class=MQLHelixManifest)

    assert "version must follow SemVer format" in str(exc.value)

def test_file_not_found():
    """helix.json not found"""
    with pytest.raises(FileNotFoundError):
        load_helix_manifest("/path/that/does/not/exist/helix.json", manifest_class=MQLHelixManifest)
