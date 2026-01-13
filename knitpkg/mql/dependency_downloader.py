# knitpkg/mql/dependency_downloader.py

"""
MQL-specific dependency downloader.

Extends the core DependencyDownloader with MQL-specific validation logic.
"""

from pathlib import Path

from knitpkg.core.dependency_downloader import DependencyDownloader
from knitpkg.mql.validators import (
    validate_mql_project_structure,
    validate_mql_dependency_manifest
)

# ==============================================================
# MQL DEPENDENCY DOWNLOADER
# ==============================================================

class MQLDependencyDownloader(DependencyDownloader):
    """
    MQL-specific dependency downloader with validation.

    This class extends the core DependencyDownloader with MQL-specific
    validation for targets (MQL4/MQL5) and project types (only packages
    are allowed as dependencies).
    """

    def validate_manifest(self, manifest, dep_path: Path, target: str) -> bool:
        """Validate MQL-specific manifest constraints."""
        validated = True
        if not validate_mql_dependency_manifest(manifest, self.console):
            validated = False
        
        if manifest.target != target:
            self.console.print(
                f"[red]✗[/red] Dependency target mismatch: [cyan]{manifest.target}[/cyan] != [cyan]{target}[/cyan]",
                style="bold"
            )
            validated = False
        return validated

    def validate_project_structure(
        self,
        manifest,
        project_dir: Path,
        is_dependency: bool = False
    ) -> None:
        """Validate MQL project structure (knitpkg/include/ for packages)."""
        validate_mql_project_structure(
            manifest,
            project_dir,
            is_dependency,
            self.console
        )
