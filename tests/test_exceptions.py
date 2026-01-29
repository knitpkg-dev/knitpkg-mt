# tests/test_exceptions.py

"""Tests for custom KnitPkg exceptions."""

import pytest
from pathlib import Path
import json

from knitpkg.core.exceptions import (
    LocalDependencyNotFoundError,
    LockedWithLocalDependencyError,
    ManifestLoadError
)
from knitpkg.core.file_reading import load_knitpkg_manifest
from knitpkg.mql.models import MQLKnitPkgManifest
from knitpkg.mql.dependency_downloader import MQLDependencyDownloader
from rich.console import Console

def test_local_dependency_not_found(tmp_path: Path):
    """Test LocalDependencyNotFoundError is raised for missing local paths."""
    d = tmp_path / "project"
    d.mkdir()

    manifest_data = {
        "name": "test",
        "organization": "acme",
        "description": "blah",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "missing": "./nonexistent/path"
        }
    }
    (d / "knitpkg.json").write_text(json.dumps(manifest_data))

    manifest = load_knitpkg_manifest(d, manifest_class=MQLKnitPkgManifest)
    downloader = MQLDependencyDownloader(d, "http://localhost:8000", False, MQLKnitPkgManifest, Console(), False)

    with pytest.raises(LocalDependencyNotFoundError) as exc:
        downloader.download_all()

    assert exc.value.name == "@acme/missing"
    assert "nonexistent" in str(exc.value)

def test_local_missing_fields(tmp_path: Path):
    """Test LocalDependencyNotFoundError is raised for missing local paths."""
    d = tmp_path / "project"
    d.mkdir()

    manifest_data = {
        "name": "test",
        "description": "blah",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"]
    }
    (d / "knitpkg.json").write_text(json.dumps(manifest_data))

    with pytest.raises(ManifestLoadError) as exc:
        load_knitpkg_manifest(d, manifest_class=MQLKnitPkgManifest)

    assert "Missing required fields" in str(exc.value) and "'organization'" in str(exc.value)

def test_local_dependency_not_git_in_locked_mode(tmp_path: Path):
    """Test LocalDependencyNotGitError is raised for non-git deps with --locked."""
    # Create main project
    main_dir = tmp_path / "main"
    main_dir.mkdir()

    # Create local dependency (no git)
    dep_dir = tmp_path / "local-dep"
    dep_dir.mkdir()
    dep_manifest = {
        "name": "local-dep",
        "organization": "nullsoft",
        "description": "blah",
        "version": "1.0.0",
        "type": "package",
        "target": "MQL5"
    }
    (dep_dir / "knitpkg.json").write_text(json.dumps(dep_manifest))

    # Main project depends on local dep
    main_manifest = {
        "name": "test",
        "organization": "acme",
        "description": "blah",
        "version": "1.0.0",
        "type": "expert",
        "target": "MQL5",
        "entrypoints": ["Test.mq5"],
        "dependencies": {
            "local-dep": f"file://{dep_dir}"
        }
    }
    (main_dir / "knitpkg.json").write_text(json.dumps(main_manifest))

    manifest = load_knitpkg_manifest(main_dir, manifest_class=MQLKnitPkgManifest)
    downloader = MQLDependencyDownloader(main_dir, "http://localhost:8000", True, MQLKnitPkgManifest, Console(), False)

    with pytest.raises(LockedWithLocalDependencyError) as exc:
        downloader.download_all()

    assert exc.value.name == "@acme/local-dep"
    assert "--locked" in str(exc.value)
