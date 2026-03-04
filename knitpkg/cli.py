# knitpkg/cli.py
"""
Main CLI entry point for KnitPkg for MetaTrader.

Automatically loads all commands from knitpkg.commands and extensions.
"""

import importlib
import pkgutil
from types import ModuleType

import typer
from rich.console import Console

from knitpkg.core.cli_version import get_package_version


app = typer.Typer(
    name="KnitPkg for MetaTrader",
    help="KnitPkg for MetaTrader - Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

loaded_commands = set()

# -------------------------------------------------------------------
# Dynamic command loading utilities
# -------------------------------------------------------------------
def _load_commands_from_package(package_name: str) -> None:
    """
    Import all submodules from a package and call register(app) on each module that defines it.
    """
    try:
        pkg = importlib.import_module(package_name)
    except ImportError:
        return

    # Register the package itself if it has a register function
    _register_if_available(pkg)

    # Register all submodules
    for finder, mod_name, is_pkg in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if mod_name in loaded_commands:
            continue
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        _register_if_available(mod)
        loaded_commands.add(mod_name)


def _register_if_available(mod: ModuleType) -> None:
    """
    Call register(app) on the module if the function exists.
    """
    register_func = getattr(mod, "register", None)
    if callable(register_func):
        register_func(app)


# -------------------------------------------------------------------
# Load optional PRO commands
# -------------------------------------------------------------------
_load_commands_from_package("knitpkg.commands.pro")

# -------------------------------------------------------------------
# Load standard commands
# -------------------------------------------------------------------
_load_commands_from_package("knitpkg.commands")

# -------------------------------------------------------------------
# Main callback (version)
# -------------------------------------------------------------------
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
        console.print(
            f"[bold green]KnitPkg for MetaTrader[/] version [cyan]{current_version}[/]"
        )
        raise typer.Exit()


if __name__ == "__main__":
    app()