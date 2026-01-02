from pathlib import Path
import os
from .models import Target
from typing import List

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
    * Used by commands like `helix compile` and `helix init` for auto-detection.
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
    target_folder_name = target.value # MQL5 or MQL4

    for base_path in possible_paths:
        if not base_path.exists():
            continue

        # Iterate through subfolders (e.g., "D0E8209F77C15E0B37B07412A6190423")
        # Using os.walk to ensure we only go one level deep in the terminal folders
        for root, dirs, _ in os.walk(base_path):
            for d in dirs:
                terminal_id_path = Path(root) / d
                mql_path = terminal_id_path / target_folder_name
                include_path = mql_path / "Include"
                experts_path = mql_path / "Experts"
                indicators_path = mql_path / "Indicators"
                scripts_path = mql_path / "Scripts"
                libraries_path = mql_path / "Libraries"
                if include_path.is_dir() and \
                    experts_path.is_dir() and \
                    indicators_path.is_dir() and \
                    scripts_path.is_dir() and \
                    libraries_path.is_dir():
                    
                    found_mql_paths.append(mql_path)
            # Only search one level deep in Terminal folders
            break 

    return found_mql_paths
