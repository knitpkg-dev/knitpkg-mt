# knitpkg/config.py (NOVO)

import os
from pathlib import Path
from typing import Optional
import yaml

DEFAULT_PUBLIC_REGISTRY = "https://registry.knitpkg.dev"

def get_registry_url() -> str:
    """
    Get registry URL from:
    1. Environment variable KNITPKG_REGISTRY
    2. Global config ~/.knitpkg/config.yaml
    3. Default public registry
    """

    # 1. Env var (highest priority)
    if env_registry := os.getenv("KNITPKG_REGISTRY"):
        return env_registry

    # 2. Global config
    if config_registry := load_global_config():
        return config_registry

    # 3. Default
    return DEFAULT_PUBLIC_REGISTRY


def load_global_config() -> Optional[str]:
    """Load registry URL from ~/.knitpkg/config.yaml"""
    config_path = Path.home() / ".knitpkg" / "config.yaml"

    if not config_path.exists():
        return None

    try:
        config = yaml.safe_load(config_path.read_text())
        return config.get("registry", {}).get("url")
    except:
        return None


def set_global_registry(url: str):
    """Set global registry URL in ~/.knitpkg/config.yaml"""
    config_path = Path.home() / ".knitpkg" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}
    else:
        config = {}

    # Update registry
    if "registry" not in config:
        config["registry"] = {}
    config["registry"]["url"] = url

    # Save
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    print(f"✓ Default registry set to: {url}")
