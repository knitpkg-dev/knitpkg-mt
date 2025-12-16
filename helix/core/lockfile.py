from typing import Dict
import json
from helix.core.constants import LOCK_FILE

# ==============================================================
# LOCKFILE
# ==============================================================

def load_lockfile() -> Dict:
    """Load the helix/lock.json file. Creates a minimal structure if missing or corrupted."""
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