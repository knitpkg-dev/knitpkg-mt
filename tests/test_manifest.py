# tests/test_manifest.py

import json
from pathlib import Path

import pytest

from knitpkg.mql.models import MQLKnitPkgManifest, MQLProjectType, Target
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.core.exceptions import ManifestLoadError

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a valid knitpkg.json"""
    d = tmp_path / "sample-project"
    d.mkdir()

    manifest_data = {
        "name": "super-rsi-alert",
        "version": "2.4.1",
        "organization": "acme",
        "description": "RSI with visual, sound and Telegram alerts",
        "author": "João Trader <joao@tradingpro.com>",
        "license": "MIT",
        "target": "MQL5",
        "type": "indicator",
        "entrypoints": ["SuperRSI_Alert.mq5"],
        "dependencies": {
            "json": "^1.2.3",
            "telegram": "1.3.4",
            "utils": "~1.2.4"
        }
    }

    manifest_path = d / "knitpkg.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return d

@pytest.fixture
def package_project(tmp_path: Path) -> Path:
    """Package project (reusable library with .mqh files)"""
    d = tmp_path / "package-lib"
    d.mkdir()

    data = {
        "name": "math-advanced",
        "organization": "nullsoft",
        "description": "test",
        "version": "1.0.0",
        "type": "package",
        "target": "MQL5",
        "dependencies": {}
    }

    (d / "knitpkg.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return d

# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_load_valid_manifest(sample_dir: Path):
    """Test loading a complete valid manifest"""
    manifest = load_knitpkg_manifest(sample_dir / "knitpkg.json", manifest_class=MQLKnitPkgManifest)

    assert isinstance(manifest, MQLKnitPkgManifest)
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
    assert manifest.dependencies["json"] == "^1.2.3"
    assert manifest.dependencies["telegram"] == "1.3.4"


def test_package_has_no_entrypoint(package_project: Path):
    """Ensure package projects are accepted without entrypoints"""
    manifest = load_knitpkg_manifest(package_project / "knitpkg.json", manifest_class=MQLKnitPkgManifest)

    assert manifest.target == Target.MQL5
    assert manifest.type == MQLProjectType.PACKAGE
    assert manifest.entrypoints is None or manifest.entrypoints == []

def test_missing_description(tmp_path: Path):
    d = tmp_path / "missing-entrypoint"
    d.mkdir()
    data = {
        "name": "no-entry",
        "organization": "bublesoft",
        "type": "script",
        "version": "1.0.0",
        "include_mode": "flat",
        "target": "MQL5",
    }
    (d / "knitpkg.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ManifestLoadError) as exc:
        load_knitpkg_manifest(d / "knitpkg.json", manifest_class=MQLKnitPkgManifest)

    error = str(exc.value)
    assert "Missing required field" in str(exc.value)
    assert "'description'" in str(exc.value)


def test_invalid_semver(tmp_path: Path):
    """Version not following SemVer"""
    d = tmp_path / "bad-version"
    d.mkdir()
    data = {
        "name": "bad",
        "version": "1.2", 
        "organization": "acme",
        "description": "test",
        "type": "indicator",
        "target": "MQL5",
        "entrypoints": ["X.mq5"],
    }
    (d / "knitpkg.json").write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ManifestLoadError) as exc:
        load_knitpkg_manifest(d / "knitpkg.json", manifest_class=MQLKnitPkgManifest)

    assert "Version must follow SemVer format" in str(exc.value)

def test_file_not_found():
    """knitpkg.json not found"""
    with pytest.raises(FileNotFoundError):
        load_knitpkg_manifest("/path/that/does/not/exist/knitpkg.json", manifest_class=MQLKnitPkgManifest)
