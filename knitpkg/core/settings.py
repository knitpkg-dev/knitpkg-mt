# knitpkg/core/settings.py

"""
Settings management for KnitPkg CLI.

This module handles reading and writing user configuration stored in
.knitpkg/settings.yaml
"""

from pathlib import Path
from typing import Any, Dict
import yaml

SETTINGS_FILE = Path(".knitpkg/settings.yaml")

def load_settings(project_path: Path) -> Dict[str, Any]:
    """
    Load settings from .knitpkg/settings.yaml.

    Returns empty dict if file doesn't exist or is corrupted.
    """
    settings_file = project_path / SETTINGS_FILE
    if not settings_file.exists():
        return {}

    try:
        content = settings_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_settings(project_path: Path, settings: Dict[str, Any]) -> None:
    """
    Save settings to .knitpkg/settings.yaml.

    Creates parent directories if needed.
    """
    settings_file = project_path / SETTINGS_FILE
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(settings, default_flow_style=False, sort_keys=False)
    settings_file.write_text(content, encoding="utf-8")

def get_setting(project_path: Path, key: str, default: Any = None) -> Any:
    """Get a specific setting value."""
    settings = load_settings(project_path)
    return settings.get(key, default)

def set_setting(project_path: Path, key: str, value: Any) -> None:
    """
    Set a specific setting value, preserving other settings.
    """
    settings = load_settings(project_path)
    settings[key] = value
    save_settings(project_path, settings)
