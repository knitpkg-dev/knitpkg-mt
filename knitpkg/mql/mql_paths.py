import os
from typing import List
from pathlib import Path

from knitpkg.mql.models import Target
from knitpkg.core.system import my_system, System

def is_valid_target_path(target_path: Path) -> bool:
    return System.is_valid_target_path(target_path)

def find_mql_paths(target: Target) -> List[Path]:
    """Return a list of valid MQL paths for the given target."""
    return my_system.find_mql_paths(target)