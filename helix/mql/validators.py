# helix/mql/validators.py

"""
MQL-specific validation logic.

This module contains validation functions for MQL projects, including
project structure validation and manifest constraints.
"""

from pathlib import Path
from rich.console import Console

from helix.mql.models import ProjectType, Target
from helix.core.constants import INCLUDE_DIR

# ==============================================================
# MQL PROJECT STRUCTURE VALIDATION
# ==============================================================

def validate_mql_project_structure(
    manifest,
    project_dir: Path,
    is_dependency: bool = False,
    console: Console = None
) -> None:
    """
    Ensure include-type projects have their .mqh files inside helix/include/.

    Called for both the main project and recursive dependencies.
    Emits friendly warnings only (does not break the build).

    Args:
        manifest: HelixManifest object
        project_dir: Path to project root
        is_dependency: True if validating a dependency
        console: Rich console for logging
    """
    if manifest.type != ProjectType.PACKAGE:
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
            f"[green]Check {prefix}[/] {len(mqh_files)} .mqh file(s) found in "
            f"{INCLUDE_DIR.as_posix()}"
        )

# ==============================================================
# MQL MANIFEST VALIDATION
# ==============================================================

def validate_mql_dependency_manifest(manifest, console: Console) -> bool:
    """
    Validate MQL-specific manifest constraints for dependencies.

    Args:
        manifest: HelixManifest object
        console: Rich console for logging

    Returns:
        True if dependency is accepted, False to skip
    """
    accept = True

    # Check target
    accept_target = manifest.target in (Target.MQL4, Target.MQL5)
    accept = accept and accept_target
    if not accept_target:
        console.log(f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}")
        console.log(
            f"    → target is '{manifest.target.value}', but `helix install` only "
            f"supports '{Target.MQL4.value}' or '{Target.MQL5.value}' projects."
        )

    # Check type
    accept_project_type = manifest.type == ProjectType.PACKAGE
    accept = accept and accept_project_type
    if not accept_project_type:
        console.log(f"[red]Error:[/] Invalid dependency {manifest.name} v{manifest.version}")
        console.log(
            f"    → type is '{manifest.type.value}', but `helix install` only "
            f"supports 'package' projects."
        )

    return accept
