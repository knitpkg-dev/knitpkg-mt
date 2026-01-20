# knitpkg/core/file_reading.py

"""
File reading utilities for KnitPkg manifests.

This module provides functions to read manifest files (knitpkg.yaml/knitpkg.json)
and source code files with proper encoding detection.
"""

import json
import yaml
from pathlib import Path
from typing import Optional, Union, Type, TypeVar
import chardet

from .models import KnitPkgManifest
from .exceptions import ManifestLoadError

T = TypeVar('T', bound=KnitPkgManifest)

def read_source_file_smart(path: Path) -> str:
    """
    Read any source file with the correct encoding (UTF-8, UTF-16, etc.)
    and safely remove null bytes / line-ending issues common with UTF-16 files.

    Args:
        path: Path to file

    Returns:
        File content as string with normalized line endings
    """
    raw = path.read_bytes()

    # Try BOM-aware encodings first (most reliable)
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            # Normalize line endings and strip null bytes left by UTF-16
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.replace("\x00", "")
            return text
        except UnicodeDecodeError:
            continue

    # Fallback to chardet detection
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"
    try:
        text = raw.decode(encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        return text
    except:
        pass

    # Last resort: force UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    return text

def load_knitpkg_manifest(
    path: Optional[Union[str, Path]] = None,
    manifest_class: Type[T] = KnitPkgManifest
) -> T:
    """
    Load knitpkg.json OR knitpkg.yaml (YAML takes precedence if both exist).

    Args:
        path:
            - None: current directory
            - Path to file (knitpkg.yaml/knitpkg.json)
            - Directory (searches for manifest inside it)
        manifest_class: Manifest class to use (defaults to KnitPkgManifest).
            Use MQLKnitPkgManifest for MQL-specific validation.

    Returns:
        KnitPkgManifest or subclass instance (e.g., MQLKnitPkgManifest)

    Raises:
        ValueError: Invalid filename
        FileNotFoundError: No manifest found

    Example:
        >>> from knitpkg.mql.models import MQLKnitPkgManifest
        >>> manifest = load_knitpkg_manifest("path/to/project", MQLKnitPkgManifest)
        >>> print(manifest.target)  # Target.MQL5
    """
    if manifest_class is None:
        manifest_class = KnitPkgManifest
    
    if not issubclass(manifest_class, KnitPkgManifest):
        raise ValueError(f"manifest_class must be KnitPkgManifest or a subclass of it")

    if path is None:
        path = Path.cwd()

    path = Path(path)

    if path.is_file():
        if path.name not in ("knitpkg.yaml", "knitpkg.json"):
            raise ValueError(
                f"Invalid file: {path.name}\n"
                f"Expected: knitpkg.yaml or knitpkg.json"
            )
        yaml_path = path if path.name == "knitpkg.yaml" else None
        json_path = path if path.name == "knitpkg.json" else None
    elif path.is_dir():
        yaml_path = path / "knitpkg.yaml"
        json_path = path / "knitpkg.json"
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    if yaml_path and yaml_path.exists():
        return _load_from_yaml(yaml_path, manifest_class)
    elif json_path and json_path.exists():
        return _load_from_json(json_path, manifest_class)
    else:
        raise FileNotFoundError(
            f"No manifest file found in {path}: knitpkg.yaml or knitpkgkg.json"
        )

def _load_from_yaml(path: Path, manifest_class: Type[T]) -> T:
    """Load and parse a knitpkg.yaml manifest file."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if data is None:
            raise ManifestLoadError(str(path), "knitpkg.yaml is empty")
        return manifest_class(**data)
    except Exception as e:
        raise ManifestLoadError(str(path), str(e))

def _load_from_json(path: Path, manifest_class: Type[T]) -> T:
    """Load and parse a knitpkg.json manifest file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return manifest_class(**data)
    except Exception as e:
        raise ManifestLoadError(str(path), str(e))
