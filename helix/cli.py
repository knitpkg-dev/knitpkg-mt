# helix/cli.py
"""
Main CLI entry point for Helix for MetaTrader.

This module sets up the Typer application and registers all commands.
"""
import typer
from rich.console import Console

from helix.commands import (
    init,
    install,
    autocomplete,
    compile,
    config,
    # build, # Not yet implemented
    # init, # Not yet implemented
    # update, # Not yet implemented
    # package, # Not yet implemented
    # deploy, # Not yet implemented
)

app = typer.Typer(
    name="Helix for MetaTrader", 
    help="Helix for MetaTrader - Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Register commands
init.register(app)
install.register(app)
autocomplete.register(app)
compile.register(app)
config.register(app)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the version of Helix for MetaTrader and exit.",
        callback=lambda value: _version_callback(value),
        is_eager=True,
    )
):
    """
    Helix for MetaTrader CLI.
    """
    pass


def _version_callback(value: bool):
    if value:
        console = Console(log_path=False)
        # TODO: Get version from pyproject.toml
        console.print("[bold green]Helix for MetaTrader[/] version [cyan]0.1.0[/]")
        raise typer.Exit()

if __name__ == "__main__":
    app()
