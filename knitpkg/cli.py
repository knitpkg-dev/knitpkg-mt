# knitpkg/cli.py
"""
Main CLI entry point for KnitPkg for MetaTrader.

This module sets up the Typer application and registers all commands.
"""
import typer
from rich.console import Console

from knitpkg.commands import (
    init,
    install,
    autocomplete,
    compile,
    config,
    login,
    publish,
    # build, # Not yet implemented
    # deploy, # Not yet implemented
)

app = typer.Typer(
    name="KnitPkg for MetaTrader", 
    help="KnitPkg for MetaTrader - Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Register commands
init.register(app)
install.register(app)
autocomplete.register(app)
compile.register(app)
config.register(app)

login.register(app)
publish.register(app)

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
        # TODO: Get version from pyproject.toml
        console.print("[bold green]KnitPkg for MetaTrader[/] version [cyan]0.1.0[/]")
        raise typer.Exit()

if __name__ == "__main__":
    app()
