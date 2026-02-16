# knitpkg/core/config.py

"""
Configuration options management for KnitPkg CLI.

This module handles reading and writing user configuration stored in
.knitpkg/config.yaml
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

CONFIG_FILE = Path(".knitpkg/config.yaml")

# ==============================================================
# PROJECT CONFIGURATION MANAGER CLASS
# ==============================================================

class ProjectConfig:
    """Manages configuration settings and file operations for a project."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.config_file = self.project_path / CONFIG_FILE
        self._data: Optional[Dict[str, Any]] = None
    
    def load(self) -> Dict[str, Any]:
        """Load config data and cache it."""
        if not self.config_file.exists():
            self._data = {}
            return self._data
        
        try:
            content = self.config_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            self._data = data if isinstance(data, dict) else {}
        except:
            self._data = {}
        return self._data
    
    def save(self) -> None:
        """Save cached data to config file."""
        if self._data is None:
            return
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.dump(self._data, default_flow_style=False, sort_keys=False)
        self.config_file.write_text(content, encoding="utf-8")
    
    def save_if_changed(self, key: str, value: Any) -> None:
        """Save config if key/value has changed."""
        if self._data is None:
            self.load()

        data: Dict[str, Any] = self._data # type: ignore
        
        if data.get(key) != value:
            data[key] = value
            self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        if self._data is None:
            self.load()

        data: Dict[str, Any] = self._data # type: ignore

        return data.get(key, default)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        if self._data is None:
            self.load()

        data: Dict[str, Any] = self._data # type: ignore

        return data.copy()
