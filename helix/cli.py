# helix/cli.py
from typer import Typer
from helix.commands.install import register as register_install
from helix.commands.autocomplete import register as register_autocomplete

app = Typer(
    name="helix",
    help="Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Registra todos os comandos
register_install(app)
register_autocomplete(app)
# (você vai adicionando mais conforme criar: build, dist, etc.)

def main():
    app()

if __name__ == "__main__":
    main()