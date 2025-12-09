from pathlib import Path

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
