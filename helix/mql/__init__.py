# helix/mql/__init__.py

"""
MQL-specific modules for MetaTrader 4/5.

This package contains MQL-specific functionality including dependency
downloaders, validators, and utilities.
"""

from helix.mql.dependency_downloader import MQLDependencyDownloader
from helix.mql.validators import (
    validate_mql_project_structure,
    validate_mql_dependency_manifest
)

__all__ = [
    'MQLDependencyDownloader',
    'validate_mql_project_structure',
    'validate_mql_dependency_manifest',
]
