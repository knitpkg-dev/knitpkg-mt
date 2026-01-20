from typing import Dict
from pathlib import Path
import json
from knitpkg.core.constants import LOCK_FILE

# ==============================================================
# LOCKFILE
# ==============================================================

def load_lockfile(project_dir: str | Path) -> Dict:
    """Load the knitpkg/lock.json file. Creates a minimal structure if missing or corrupted."""
    if LOCK_FILE.exists():
        try:
            lockfile = (Path(project_dir) / LOCK_FILE)
            return json.loads(lockfile.read_text(encoding="utf-8"))
        except:
            return {"version": "1", "dependencies": {}}
    return {"version": "1", "dependencies": {}}


def save_lockfile(project_dir: str | Path, data: Dict):
    """Write the lockfile with proper formatting and ensure parent directories exist."""
    data.setdefault("version", "1")
    lockfile = (Path(project_dir) / LOCK_FILE)
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def is_lock_change(lock_data: Dict, dep_name: str, ref_spec: str, final_ref: str, registry_url: str) -> bool:
    dep_saved = lock_data["dependencies"].get(dep_name, {})
    specifier_saved = dep_saved.get("specifier")
    resolved_saved = dep_saved.get("resolved")
    registry_url_saved = dep_saved.get("registry_url")
    
    return \
        specifier_saved != ref_spec or \
        resolved_saved != final_ref or \
        registry_url_saved != registry_url