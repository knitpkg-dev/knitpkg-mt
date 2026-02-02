# knitpkg/mql/validators.py

"""
MQL-specific validation logic.

This module contains validation functions for MQL projects, including
project structure validation and manifest constraints.
"""

from pathlib import Path
from knitpkg.core.console import ConsoleAware

from typing import Optional
from knitpkg.mql.models import MQLProjectType, Target
from knitpkg.mql.constants import INCLUDE_DIR

# ==============================================================
# MQL PROJECT STRUCTURE VALIDATION
# ==============================================================

def warn_mql_project_structure(
    manifest,
    project_dir: Path,
    is_dependency: bool = False,
    console: Optional[ConsoleAware] = None
) -> None:
    """
    Warn log if include-type projects do not have their .mqh files 
    in the correct location: inside knitpkg/include/.

    Called for both the main project and recursive dependencies.
    Emits friendly warnings only (does not break the build).

    Args:
        manifest: MQLKnitPkgManifest object
        project_dir: Path to project root
        is_dependency: True if validating a dependency
        console: Rich console for logging
    """
    if manifest.type != MQLProjectType.PACKAGE:
        return
    if not console:
        return

    include_dir = project_dir / INCLUDE_DIR
    prefix = "[dep]" if is_dependency else "[project]"

    if not include_dir.exists():
        console.log(
            f"[bold yellow]WARNING {prefix}:[/] Include-type project missing "
            f"'{INCLUDE_DIR.as_posix()}' folder"
        )
        console.log(f"    → {project_dir}")
        console.log(
            "    Your .mqh files will not be exported to projects that depend on this one!"
        )
        console.log("    Create the folder and move the files:")
        console.log(f"       mkdir -p {INCLUDE_DIR.as_posix()}")
        console.log(f"       git mv *.mqh {INCLUDE_DIR.as_posix()} 2>/dev/null || true")
        console.log("")
        return

    mqh_files = list(include_dir.rglob("*.mqh"))
    if not mqh_files:
        console.log(
            f"[bold yellow]WARNING {prefix}:[/] '{INCLUDE_DIR.as_posix()}' "
            f"folder exists but is empty!"
        )
        console.log(f"    → {project_dir}")
        console.log("    No .mqh files will be exported. Move your headers there.")
        console.log("")
    else:
        console.log(
            f"[green]✔ {prefix}[/] {len(mqh_files)} .mqh file(s) found in "
            f"{INCLUDE_DIR.as_posix()}"
        )

# ==============================================================
# MQL MANIFEST VALIDATION
# ==============================================================

def warn_mql_dependency_manifest(manifest, console: Optional[ConsoleAware] = None) -> bool:
    """
    Warn log if MQL-specific manifest constraints for dependencies are violated.

    Args:
        manifest: MQLKnitPkgManifest object
        console: Rich console for logging

    Returns:
        True if dependency is accepted, False to skip
    """
    accept = True

    # Check target
    accept_target = manifest.target in (Target.mql4, Target.mql5)
    accept = accept and accept_target
    if not accept_target and console:
        console.log(
            f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}"
        )
        console.log(
            f"    → target is '{manifest.target.value}', but `kp install` only "
            f"supports '{Target.mql4.value}' or '{Target.mql5.value}' projects."
        )

    # Check type
    accept_project_type = manifest.type == MQLProjectType.PACKAGE
    accept = accept and accept_project_type
    if not accept_project_type and console:
        console.log(
            f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}"
        )
        console.log(
            f"    → type is '{manifest.type.value}', but `kp install` only "
            f"supports 'package' projects."
        )

    return accept
