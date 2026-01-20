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

    def validate_manifest(self, manifest) -> bool:
        """Validate MQL-specific manifest constraints."""
        validated = True
        if not validate_mql_dependency_manifest(manifest, self.console):
            validated = False
        
        if manifest.target != self._target:
            self.print(
                f"[bold][red]✗[/red] Dependency target mismatch: [cyan]{manifest.target}[/cyan] != [cyan]{self._target}[/cyan][/bold]"
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

#if __name__ == "__main__":
#    from knitpkg.mql.models import MQLKnitPkgManifest
#    from rich.console import Console as RichConsole
#    d = MQLDependencyDownloader(Path("C:\\Users\\dougl\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\MQL5\\Indicators\\knitpkg-mt-ind-sma"), \
#                                "http://localhost:8000", \
#                                manifest_type=MQLKnitPkgManifest, \
#                                console=RichConsole(log_path=False),
#                                verbose=True)
#    node = d.download_all()
#    if not node:
#        print("No nodes downloaded")
#    else:
#        print(node.name)
#        print(node.resolved_names())
#        print(node.resolved_names(True))
