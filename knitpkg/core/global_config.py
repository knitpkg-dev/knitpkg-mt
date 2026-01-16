# knitpkg/config.py (NOVO)

import os
from pathlib import Path
from typing import Optional
import yaml

DEFAULT_PUBLIC_REGISTRY = "https://registry.knitpkg.dev"
DEFAULT_AUTH_CALLBACK_PORT = 8789

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
    config = load_global_config()
    if config and "registry" in config and "url" in config["registry"]:
        return config["registry"]["url"]

    # 3. Default
    return DEFAULT_PUBLIC_REGISTRY


def load_global_config() -> Optional[dict]:
    """Load config from ~/.knitpkg/config.yaml"""
    config_path = Path.home() / ".knitpkg" / "config.yaml"

    if not config_path.exists():
        return None

    try:
        return yaml.safe_load(config_path.read_text())
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


def get_auth_callback_port() -> int:
    """Get auth callback port from config or default."""
    config = load_global_config()
    if config and "auth" in config and "callback_port" in config["auth"]:
        return config["auth"]["callback_port"]
    return DEFAULT_AUTH_CALLBACK_PORT


def set_auth_callback_port(port: int):
    """Set auth callback port in ~/.knitpkg/config.yaml"""
    config_path = Path.home() / ".knitpkg" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}
    else:
        config = {}

    # Update auth callback port
    if "auth" not in config:
        config["auth"] = {}
    config["auth"]["callback_port"] = port

    # Save
    config_path.write_text(yaml.dump(config, default_flow_style=False))
