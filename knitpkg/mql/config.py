# knitpkg/mql/config.py
from typing import Optional, Any
from pathlib import Path
import os

from knitpkg.core.global_config import get_global_default

"""
MQL-specific configuration options management.

This module provides functions to get and set configuration paths
related to MetaTrader installations, such as compiler paths and
data folder paths.
"""

from knitpkg.core.config import ProjectConfig
from knitpkg.mql.models import Target
from knitpkg.mql.exceptions import UnsupportedTargetError

# Default compiler paths for MetaTrader
DEFAULT_MQL5_COMPILER = r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
DEFAULT_MQL4_COMPILER = r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe"

class MQLProjectConfig(ProjectConfig):
    """MQL-specific configuration options handler."""

    def __init__(self, project_path: Path):
        super().__init__(project_path)
        self.global_config_default: dict = get_global_default()
    
    def get_final(self, env_key: str, config_key: str, default: Optional[str]=None) -> Any:
        """Get configuration value from environment variable, config file, or default."""

        # Env has the highest priority
        v = os.environ.get(env_key, None)
        if v is not None:
            return v
        
        # Then project-specific config file
        v = self.get(config_key, None)
        if v is not None:
            return v
        
        # Finally global config or default value
        v = self.global_config_default.get(config_key, default)
        return v

    def get_compiler_path(self, target: Target) -> str:
        """Get compiler path for specified MQL version."""
        if target == Target.mql4:
            return self.get_final("MQL4_COMPILER_PATH", "mql4-compiler-path", DEFAULT_MQL4_COMPILER)
        elif target == Target.mql5:
            return self.get_final("MQL5_COMPILER_PATH", "mql5-compiler-path", DEFAULT_MQL5_COMPILER)
        else:
            raise UnsupportedTargetError(target)
    
    def set_compiler_path(self, path: str, target: Target):
        """Set compiler path for specified MQL version."""
        if target == Target.mql4:
            compiler_path: Path = Path(path)
            if compiler_path.is_dir():
                compiler_path = compiler_path / "metaeditor.exe"
            if not compiler_path.exists():
                raise FileNotFoundError(f"Compiler not found at {compiler_path}")
            self.save_if_changed("mql4-compiler-path", str(compiler_path))
        
        elif target == Target.mql5:
            compiler_path: Path = Path(path)
            if compiler_path.is_dir():
                compiler_path = compiler_path / "MetaEditor64.exe"
            if not compiler_path.exists():
                raise FileNotFoundError(f"Compiler not found at {compiler_path}")
            self.save_if_changed("mql5-compiler-path", str(compiler_path))
        
        else:
            raise UnsupportedTargetError(target)

    def get_data_folder_path(self, target: Target) -> Optional[str]:
        """Get compiler path for specified MQL version."""
        if target == Target.mql4:
            return self.get_final("MQL4_DATA_FOLDER_PATH", "mql4-data-folder-path")
        
        elif target == Target.mql5:
            return self.get_final("MQL5_DATA_FOLDER_PATH", "mql5-data-folder-path")
        
        else:
            raise UnsupportedTargetError(target)
    
    def set_data_folder_path(self, path: str, target: Target):
        """Set compiler path for specified MQL version."""
        if target == Target.mql4:
            self.save_if_changed("mql4-data-folder-path", str(path))
        
        elif target == Target.mql5:
            self.save_if_changed("mql5-data-folder-path", str(path))
        
        else:
            raise UnsupportedTargetError(target)
