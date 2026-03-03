import importlib.metadata
import pathlib
import sys
import tomllib

# Auxiliary function to get the version of the package
def get_package_version():
    package_name = "knitpkg-mt" # The name of your package as per pyproject.toml

    # 1. Try to get the version from an installed package
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        pass # The package is not installed, try reading from pyproject.toml

    # 2. If not installed, try reading directly from pyproject.toml
    # Assume that cli.py is in knitpkg/cli.py and pyproject.toml is in the project root
    project_root = pathlib.Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    if pyproject_path.exists() and tomllib:
        try:
            with open(pyproject_path, "rb") as f: # "rb" for tomllib
                pyproject_data = tomllib.load(f)
            # The version is in [tool.poetry] for Poetry projects
            return pyproject_data.get("tool", {}).get("poetry", {}).get("version", "unknown")
        except Exception as e:
            # In case of error reading the TOML
            print(f"Warning: Could not read version from pyproject.toml: {e}", file=sys.stderr)
            return "unknown"

    return "unknown" # Final fallback if nothing works
