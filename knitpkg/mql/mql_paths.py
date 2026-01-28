import os
from typing import List, Optional
from knitpkg.mql.models import Target
from pathlib import Path

def is_valid_target_path(target_path: Path) -> bool:
    """Check if a path is a valid MQL path with all required subdirectories."""
    required_dirs = ["Include", "Experts", "Indicators", "Scripts", "Libraries"]
    return all((target_path / dir_name).is_dir() for dir_name in required_dirs)

def get_mql_target_paths(target: Target, base_path: Path) -> List[Path]:
    target_paths = []
    if not base_path.exists():
        return target_paths

    # Iterate through subfolders (e.g., "D0E8209F77C15E0B37B07412A6190423")
    # Using os.walk to ensure we only go one level deep in the terminal folders
    for root, dirs, _ in os.walk(base_path):
        for d in dirs:
            terminal_id_path = Path(root) / d
            mql_path = terminal_id_path / target.value
            if is_valid_target_path(mql_path):
                target_paths.append(mql_path)
        # Only search one level deep in Terminal folders
        break

    return target_paths

def find_mql_paths(target: Target) -> List[Path]:
    """
    Locates MetaTrader data directories (MQL5 or MQL4) containing essential
    sub-folders (Include, Experts, Indicators, Scripts, Libraries).

    It searches common base locations like AppData roaming and default
    Program Files installations. For each base path, it inspects
    terminal-specific sub-folders (e.g., hash-named) to confirm the presence
    of all required MQL directories.

    Parameters
    ----------
    target : Target
        The MetaTrader target platform (Target.MQL5 or Target.MQL4).

    Returns
    -------
    List[Path]
        A list of absolute Path objects, each pointing to a valid MQL5 or MQL4
        data folder. The list may be empty if no suitable directories are found.

    Notes
    -----
    * Does not raise an exception if no paths are found; returns an empty list.
    * Used by commands like `kp-mt compile` and `kp-mt init` for auto-detection.
    """
    possible_paths = [
        Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal",
    ]

    if target == Target.MQL5:
        possible_paths.append(
            Path("C:/Program Files/MetaTrader 5/Terminal"), # Common default for MQL5
        )
    elif target == Target.MQL4:
        possible_paths.append(
            Path("C:/Program Files (x86)/MetaTrader 4/Terminal"),
        )

    found_mql_paths: List[Path] = []

    for base_path in possible_paths:
        target_path = get_mql_target_paths(target, base_path)
        if target_path:
            found_mql_paths.extend(target_path)

    return found_mql_paths

if __name__ == '__main__':
    print(find_mql_paths(Target.MQL5))