# knitpkg/mql/settings.py
from typing import Optional
from pathlib import Path

"""
MQL-specific settings management.

This module provides functions to get and set configuration paths
related to MetaTrader installations, such as compiler paths and
data folder paths.
"""

from knitpkg.core.settings import Settings
from knitpkg.mql.models import Target
from knitpkg.mql.exceptions import UnsupportedTargetError

# Default compiler paths for MetaTrader
DEFAULT_MQL5_COMPILER = r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
DEFAULT_MQL4_COMPILER = r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe"

class MQLSettings(Settings):
    """MQL-specific settings handler."""

    def __init__(self, project_path: Path):
        super().__init__(project_path)
    
    def get_compiler_path(self, target: Target) -> str:
        """Get compiler path for specified MQL version."""
        if target == Target.mql4:
            return self.get("mql4-compiler-path", DEFAULT_MQL4_COMPILER)
        elif target == Target.mql5:
            return self.get("mql5-compiler-path", DEFAULT_MQL5_COMPILER)
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
            return self.get("mql4-data-folder-path")
        
        elif target == Target.mql5:
            return self.get("mql5-data-folder-path")
        
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
