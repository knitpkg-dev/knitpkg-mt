# knitpkg/cli.py
"""
Main CLI entry point for KnitPkg for MetaTrader.

This module sets up the Typer application and registers all commands.
"""
import typer
from rich.console import Console

from knitpkg.core.cli_version import get_package_version

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
