from typing import Dict
import json
from knitpkg.core.constants import LOCK_FILE

# ==============================================================
# LOCKFILE
# ==============================================================

def load_lockfile() -> Dict:
    """Load the knitpkg/lock.json file. Creates a minimal structure if missing or corrupted."""
    if LOCK_FILE.exists():
        try:
            return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        except:
            return {"version": "1", "dependencies": {}}
    return {"version": "1", "dependencies": {}}


def save_lockfile(data: Dict):
    """Write the lockfile with proper formatting and ensure parent directories exist."""
    data.setdefault("version", "1")
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def is_lock_change(lock_data: Dict, dep_name: str, ref_spec: str, final_ref: str, registry_url: str) -> bool:
    dep_saved = lock_data["dependencies"].get(dep_name, {})
    specifier_saved = dep_saved.get("specifier")
    resolved_saved = dep_saved.get("resolved")
    registry_url_saved = dep_saved.get("registry_url")
    
    return \
        specifier_saved != ref_spec or \
        resolved_saved != final_ref or \
        registry_url_saved != registry_url