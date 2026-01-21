from typing import Dict, Optional
from pathlib import Path
import json
import datetime as dt
from knitpkg.core.constants import LOCK_FILE

# ==============================================================
# LOCKFILE CLASS
# ==============================================================

class LockFile:
    """Manages lockfile operations for a project."""
    
    def __init__(self, project_dir: str | Path):
        self.project_dir: Path = Path(project_dir)
        self.lockfile_path: Path = self.project_dir / LOCK_FILE
        self._data: Optional[Dict] = None
    
    def load(self) -> Dict:
        """Load lockfile data and cache it."""
        data = {"version": "1", "dependencies": {}}
        try:
            json_data = json.loads(self.lockfile_path.read_text(encoding="utf-8"))
            json_data_version = json_data.get("version")
            if json_data_version == "1":
                data = json_data
            else:
                raise ValueError("Unsupported lockfile version or lockfile missing.")
        except:
            ...
        self._data = data
        return data
    
    def save(self) -> None:
        """Save cached data to lockfile."""
        if self._data is None:
            return
        self._data.setdefault("version", "1")
        self.lockfile_path.parent.mkdir(parents=True, exist_ok=True)
        self.lockfile_path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def update_if_changed(
        self, dep_name: str, ref_spec: str, final_ref: str, registry_url: str
    ) -> None:
        """Update lockfile for git dependency."""
        if self._is_changed(dep_name, ref_spec, final_ref, registry_url):
            self._put(dep_name, "registry_url", registry_url)
            self._put(dep_name, "specifier", ref_spec)
            self._put(dep_name, "resolved", final_ref)
            self._put(dep_name, "resolved_at", dt.datetime.now(dt.timezone.utc).isoformat())
            self.save()

    def get(self, dep_name: str, key: str, default=None):
        """Get a specific value for a dependency from the lockfile."""
        if self._data is None:
            self.load()

        return self._data["dependencies"].get(dep_name, {}).get(key, default) # type: ignore
    
    def is_dependency(self, dep_name):
        """Check if a dependency exists in the lockfile."""
        if self._data is None:
            self.load()
        
        return (
             self.get(dep_name, "registry_url") is not None and
             self.get(dep_name, "specifier") is not None and
             self.get(dep_name, "resolved") is not None and
             self.get(dep_name, "resolved_at") is not None
        )
    
    def _is_changed(self, dep_name: str, ref_spec: str, final_ref: str, registry_url: str) -> bool:
        """Check if dependency has changed compared to lockfile."""
        if self._data is None:
            self.load()
        
        dep_saved = self._data["dependencies"].get(dep_name, {}) # type: ignore
        specifier_saved = dep_saved.get("specifier")
        resolved_saved = dep_saved.get("resolved")
        registry_url_saved = dep_saved.get("registry_url")
        
        return (
            specifier_saved != ref_spec or
            resolved_saved != final_ref or
            registry_url_saved != registry_url
        )

    def _put(self, dep_name: str, key: str, value: str): 
        """Update a specific dependency entry in the lockfile."""
        if self._data is None:
            self.load()

        data: Dict = self._data # type: ignore
        
        if "dependencies" not in data: 
            data["dependencies"] = {} 
        
        if dep_name not in data["dependencies"]:
            data["dependencies"][dep_name] = {}
        
        data["dependencies"][dep_name][key] = value 

