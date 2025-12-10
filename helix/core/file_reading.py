import json
import yaml
from pathlib import Path
from typing import Optional
import chardet

from .models import HelixManifest


def read_file_smart(path: Path) -> str:
    """
    Read any .mqh file with the correct encoding (UTF-8, UTF-16, etc.)
    and safely remove null bytes / line-ending issues common with UTF-16 files.
    """
    raw = path.read_bytes()

    # 1. Try BOM-aware encodings first (most reliable)
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            # Normalize line endings and strip null bytes left by UTF-16
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.replace("\x00", "")
            return text
        except UnicodeDecodeError:
            continue

    # 2. Fallback to chardet detection
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"
    try:
        text = raw.decode(encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        return text
    except:
        pass

    # 3. Last resort: force UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    return text


def load_helix_manifest(path: Optional[str | Path] = None) -> HelixManifest:
    """
    Load helix.json OR helix.yaml (YAML takes precedence if both exist).
    
    Args:
        path: 
            - None: current directory
            - Path to file (helix.yaml/helix.json)
            - Directory (searches for manifest inside it)
    
    Raises:
        ValueError: Invalid filename
        FileNotFoundError: No manifest found
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
    """Load and parse a helix.yaml manifest file."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if data is None:
            raise ValueError("helix.yaml is empty")
        return HelixManifest(**data)
    except Exception as e:
        raise ValueError(f"Error reading helix.yaml: {e}")


def _load_from_json(path: Path) -> HelixManifest:
    """Load and parse a helix.json manifest file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return HelixManifest(**data)
    except Exception as e:
        raise ValueError(f"Error reading helix.json: {e}")