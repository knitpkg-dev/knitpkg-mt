from pathlib import Path
from typing import Union

# ==============================================================
# UTILS
# ==============================================================

def is_local_path(spec: str) -> bool:
    """Return True if the specifier points to a local filesystem path."""
    spec = spec.strip()
    if spec.startswith("file://"):
        return True
    if spec.startswith(("http://", "https://", "git@", "ssh://")):
        return False
    return any(spec.startswith(p) for p in ("./", "../", "/", "~")) or Path(spec).is_absolute()


def navigate_path(source: Union[str, Path], target: Union[str, Path]) -> Path:
    """
    Return relative path from source directory to target path.
    Works automatically even when source and target are in different branches.
    
    Args:
        source: Starting path (file or directory)
        target: Destination path (file or directory)
    
    Returns:
        Relative path (e.g. '../../../sibling/dir/file')
    """
    src = Path(source).resolve()
    dst = Path(target).resolve()

    # Find deepest common ancestor
    common = next((p for p in src.parents if p in dst.parents), Path(src.root))

    # Count how many levels up from source to reach common ancestor
    up_levels = len(src.parents) - len(common.parents)

    # Build relative path: go up + go down into target
    rel = Path("../" * up_levels) / dst.relative_to(common)

    return rel
