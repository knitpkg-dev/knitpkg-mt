# helix/cli.py
from typer import Typer
from helix.commands.install import register as register_install
from helix.commands.autocomplete import register as register_autocomplete
from helix.commands.config import register as register_config
from helix.commands.compile import register as register_compile

app = Typer(
    name="helix",
    help="Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Register all commands
register_install(app)
register_autocomplete(app)
register_config(app)
register_compile(app)

def main():
    app()

if __name__ == "__main__":
    main()
