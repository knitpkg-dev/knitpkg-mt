from typing import Optional, TypeVar, Type, Union
from pathlib import Path
import json
from ruamel.yaml import YAML
yaml = YAML()
yaml.preserve_quotes = True

from knitpkg.core.console import Console, ConsoleAware
from knitpkg.core.registry import Registry
from knitpkg.core.models import KnitPkgManifest
from knitpkg.core.resolve_helper import parse_project_name, normalize_dep_name
from knitpkg.core.exceptions import InvalidUsageError, ManifestLoadError

T = TypeVar('T', bound=KnitPkgManifest)

class ProjectManager(ConsoleAware):
    
    def __init__(self, project_dir: Optional[Path],  registry: Registry, console: Optional[Console] = None, verbose: bool = False):
        super().__init__(console, verbose)
        self.project_dir: Path = project_dir if project_dir else Path.cwd()
        self.registry: Registry = registry
        
        self.resolved_manifest_path: Optional[Path] = None
        self.loaded_manifest: Optional[dict] = None

    def add_dependency(self, dep_spec: str, verspec: str):
        self.log(f"Adding dependency: {dep_spec} : {verspec}")
        
        self._load_knitpkg_manifest()
        manifest: dict = self.loaded_manifest # type: ignore

        target: str = manifest.get('target') # type: ignore
        org, name = parse_project_name(dep_spec.lower())
        if not org:
            org: str = manifest.get('organization') # type: ignore
            org = org.lower()

        dependencies = manifest.get('dependencies')
        if not dependencies:
            dependencies = {}
        if normalize_dep_name(dep_spec.lower(), org) in [normalize_dep_name(dep_name, org) for dep_name in dependencies.keys()]:
            self.print(f"⚠️  [bold yellow]Dependency already exists:[/] {dep_spec.lower()}")
            return

        dep_info = self.registry.resolve_package(target, org, name, verspec)

        resolved_version = dep_info.get('resolved_version')
        dep_spec_normalized = normalize_dep_name(name, org)
        if not resolved_version:
            raise InvalidUsageError(f"Could not resolve version {verspec} for package {dep_spec_normalized}")
        
        dependencies[dep_spec.lower()] = f"^{resolved_version}"
        manifest['dependencies'] = dependencies

        self._save_knitpkg_manifest()

        self.print(f"✅ [bold green]Added dependency[/] → {dep_spec.lower()} : {resolved_version}")
        

    def _save_knitpkg_manifest(self):
        if not self.resolved_manifest_path:
            raise InvalidUsageError("No manifest file loaded to save changes to.")
        
        if self.resolved_manifest_path.name.endswith('.yaml') or self.resolved_manifest_path.name.endswith('.yml'):
            with self.resolved_manifest_path.open("w", encoding="utf-8") as fp:
                yaml.dump(self.loaded_manifest, fp)
        elif self.resolved_manifest_path.name.endswith('.json'):
            with self.resolved_manifest_path.open("w", encoding="utf-8") as fp:
                json.dump(self.loaded_manifest, fp, indent=2)
        else:
            raise InvalidUsageError("Unknown manifest format")

    def _load_knitpkg_manifest(self):
        path = self.project_dir
        if path is None:
            path = Path.cwd()

        path = Path(path)

        if path.is_file():
            if path.name not in ("knitpkg.yaml", "knitpkg.yml", "knitpkg.json"):
                raise ValueError(
                    f"Invalid file: {path.name}\n"
                    f"Expected: knitpkg.yaml, knitpkg.yml or knitpkg.json"
                )
            yaml_path = path if path.name == "knitpkg.yaml" else None
            yml_path = path if path.name == "knitpkg.yml" else None
            json_path = path if path.name == "knitpkg.json" else None
        elif path.is_dir():
            yaml_path = path / "knitpkg.yaml"
            yml_path = path / "knitpkg.yml"
            json_path = path / "knitpkg.json"
        else:
            raise FileNotFoundError(f"Path not found: {path}")

        self.resolved_manifest_path = None
        if yaml_path and yaml_path.exists():
            self.loaded_manifest = self._load_from_yaml(yaml_path)
            self.resolved_manifest_path = yaml_path

        elif yml_path and yml_path.exists():
            self.loaded_manifest = self._load_from_yaml(yml_path)
            self.resolved_manifest_path = yml_path

        elif json_path and json_path.exists():
            self.loaded_manifest = self._load_from_json(json_path)
            self.resolved_manifest_path = json_path

        else:
            raise FileNotFoundError(
                f"No manifest file found in {path}"
            )
        
        if not self.loaded_manifest:
            raise ManifestLoadError(str(self.resolved_manifest_path), "Manifest file is empty")

        # Basic validation
        if not self.loaded_manifest.get('target'):
            raise ManifestLoadError(str(self.resolved_manifest_path), "Manifest must contain a target")
        if not self.loaded_manifest.get('organization'):
            raise ManifestLoadError(str(self.resolved_manifest_path), "Manifest must contain an organization")
        if not self.loaded_manifest.get('name'):
            raise ManifestLoadError(str(self.resolved_manifest_path), "Manifest must contain a name")
        
    def _load_from_yaml(self, path: Path) -> Optional[dict]:
        try:
            with open(path, 'r') as yaml_file:
                data = yaml.load(yaml_file)
                if data is None:
                    raise ManifestLoadError(str(path), "Manifest file is empty")
                return data
        except Exception as e:
            raise ManifestLoadError(str(path), str(e))

    def _load_from_json(self, path: Path) -> Optional[dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data is None:
                raise ManifestLoadError(str(path), "Manifest file is empty")
            return data
        except Exception as e:
            raise ManifestLoadError(str(path), str(e))
