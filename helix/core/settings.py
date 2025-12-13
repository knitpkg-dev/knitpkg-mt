# helix/core/settings.py

"""
Settings management for Helix CLI.

This module handles reading and writing user configuration stored in
.helix/settings.yaml
"""

from pathlib import Path
from typing import Optional, Any, Dict
import yaml

SETTINGS_FILE = Path(".helix/settings.yaml")

def load_settings() -> Dict[str, Any]:
    """
    Load settings from .helix/settings.yaml.

    Returns empty dict if file doesn't exist or is corrupted.
    """
    if not SETTINGS_FILE.exists():
        return {}

    try:
        content = SETTINGS_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_settings(settings: Dict[str, Any]) -> None:
    """
    Save settings to .helix/settings.yaml.

    Creates parent directories if needed.
    """
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(settings, default_flow_style=False, sort_keys=False)
    SETTINGS_FILE.write_text(content, encoding="utf-8")

def get_setting(key: str, default: Any = None) -> Any:
    """Get a specific setting value."""
    settings = load_settings()
    return settings.get(key, default)

def set_setting(key: str, value: Any) -> None:
    """
    Set a specific setting value, preserving other settings.
    """
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
