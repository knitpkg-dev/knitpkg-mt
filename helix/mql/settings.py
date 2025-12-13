# helix/mql/settings.py

"""
MQL-specific settings management.

This module handles MetaTrader compiler path configuration.
"""

from helix.core.settings import get_setting, set_setting

# Default compiler paths for MetaTrader
DEFAULT_MQL5_COMPILER = r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"
DEFAULT_MQL4_COMPILER = r"C:\Program Files (x86)\MetaTrader 4\MetaEditor.exe"

def get_mql5_compiler_path() -> str:
    """Get configured MQL5 compiler path or default."""
    return get_setting("mql5-compiler-path", DEFAULT_MQL5_COMPILER)

def get_mql4_compiler_path() -> str:
    """Get configured MQL4 compiler path or default."""
    return get_setting("mql4-compiler-path", DEFAULT_MQL4_COMPILER)

def set_mql5_compiler_path(path: str) -> None:
    """Set MQL5 compiler path."""
    set_setting("mql5-compiler-path", path)

def set_mql4_compiler_path(path: str) -> None:
    """Set MQL4 compiler path."""
    set_setting("mql4-compiler-path", path)
