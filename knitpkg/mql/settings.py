# knitpkg/mql/settings.py

from pathlib import Path

"""
MQL-specific settings management.

This module provides functions to get and set configuration paths
related to MetaTrader installations, such as compiler paths and
data folder paths.
"""

from knitpkg.core.settings import get_setting, set_setting

# Default compiler paths for MetaTrader
DEFAULT_MQL5_COMPILER = r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
DEFAULT_MQL4_COMPILER = r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe"

def get_mql5_compiler_path(project_path: str) -> str:
    """Get configured MQL5 compiler path or default."""
    return get_setting(Path(project_path), "mql5-compiler-path", DEFAULT_MQL5_COMPILER)

def set_mql5_compiler_path(project_path: str, path: str):
    """Set the MQL5 compiler path."""
    compiler_path: Path = Path(path)
    if compiler_path.is_dir():
        compiler_path = compiler_path / "MetaEditor64.exe"
    if not compiler_path.exists():
        raise FileNotFoundError(f"Compiler not found at {compiler_path}")
    
    set_setting(Path(project_path), "mql5-compiler-path", str(compiler_path.absolute()))

def get_mql4_compiler_path(project_path: str) -> str:
    """Get configured MQL4 compiler path or default."""
    return get_setting(Path(project_path), "mql4-compiler-path", DEFAULT_MQL4_COMPILER)


def set_mql4_compiler_path(project_path: str, path: str):
    """Set the MQL4 compiler path."""
    compiler_path: Path = Path(path)
    if compiler_path.is_dir():
        compiler_path = compiler_path / "metaeditor.exe"
    if not compiler_path.exists():
        raise FileNotFoundError(f"Compiler not found at {compiler_path}")
    
    set_setting(Path(project_path), "mql4-compiler-path", str(compiler_path.absolute()))

# --- MQL5 Data Folder Path (NEW) ---

def get_mql5_data_folder_path(project_path: str) -> str:
    """Get the configured MQL5 data folder path."""
    return get_setting(Path(project_path), "mql5-data-folder-path", "")

def set_mql5_data_folder_path(project_path: str, path: str):
    """Set the MQL5 data folder path."""
    set_setting(Path(project_path), "mql5-data-folder-path", path)

# --- MQL4 Data Folder Path (NEW) ---

def get_mql4_data_folder_path(project_path: str) -> str:
    """Get the configured MQL4 data folder path."""
    return get_setting(Path(project_path), "mql4-data-folder-path", "")

def set_mql4_data_folder_path(project_path: str, path: str):
    """Set the MQL4 data folder path."""
    set_setting(Path(project_path), "mql4-data-folder-path", path)
