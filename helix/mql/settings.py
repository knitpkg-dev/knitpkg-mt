# helix/mql/settings.py

"""
MQL-specific settings management.

This module provides functions to get and set configuration paths
related to MetaTrader installations, such as compiler paths and
data folder paths.
"""

from helix.core.settings import get_setting, set_setting

# Default compiler paths for MetaTrader
DEFAULT_MQL5_COMPILER = r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
DEFAULT_MQL4_COMPILER = r"C:\Program Files (x86)\MetaTrader 4\MetaEditor.exe"

def get_mql5_compiler_path() -> str:
    """Get configured MQL5 compiler path or default."""
    return get_setting("mql5-compiler-path", DEFAULT_MQL5_COMPILER)

def set_mql5_compiler_path(path: str):
    """Set the MQL5 compiler path."""
    set_setting("mql5-compiler-path", path)

def get_mql4_compiler_path() -> str:
    """Get configured MQL4 compiler path or default."""
    return get_setting("mql4-compiler-path", DEFAULT_MQL4_COMPILER)


def set_mql4_compiler_path(path: str):
    """Set the MQL4 compiler path."""
    set_setting("mql4-compiler-path", path)

# --- MQL5 Data Folder Path (NEW) ---

def get_mql5_data_folder_path() -> str:
    """Get the configured MQL5 data folder path."""
    return get_setting("mql5-data-folder-path", "")

def set_mql5_data_folder_path(path: str):
    """Set the MQL5 data folder path."""
    set_setting("mql5-data-folder-path", path)

# --- MQL4 Data Folder Path (NEW) ---

def get_mql4_data_folder_path() -> str:
    """Get the configured MQL4 data folder path."""
    return get_setting("mql4-data-folder-path", "")

def set_mql4_data_folder_path(path: str):
    """Set the MQL4 data folder path."""
    set_setting("mql4-data-folder-path", path)
