# knitpkg/cli.py
"""
Main CLI entry point for KnitPkg for MetaTrader.

This module sets up the Typer application and registers all commands.
"""
import typer
from rich.console import Console

from knitpkg.commands import (
    add,
    init,
    install,
    autocomplete,
    checkinstall,
    compile,
    build,
    get,
    config,
    login,
    logout,
    global_config,
    register,
    search,
    whoami,
    yank,
    info,
    status,
    telemetry,
    # deploy, # Not yet implemented
)

import importlib.metadata
import pathlib
import sys
import tomllib

app = typer.Typer(
    name="KnitPkg for MetaTrader",
    help="KnitPkg for MetaTrader - Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Register commands
add.register(app)
init.register(app)
install.register(app)
autocomplete.register(app)
checkinstall.register(app)
compile.register(app)
build.register(app)
get.register(app)
config.register(app)
global_config.register(app)

login.register(app)
register.register(app)
search.register(app)
status.register(app)
logout.register(app)
whoami.register(app)
yank.register(app)
info.register(app)
telemetry.register(app)

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

@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the version of KnitPkg for MetaTrader and exit.",
        callback=lambda value: _version_callback(value),
        is_eager=True,
    )
):
    """
    KnitPkg for MetaTrader CLI.
    """
    pass

def _version_callback(value: bool):
    if value:
        console = Console(log_path=False)
        current_version = get_package_version()
        console.print(f"[bold green]KnitPkg for MetaTrader[/] version [cyan]{current_version}[/]")
        raise typer.Exit()

if __name__ == "__main__":
    app()
