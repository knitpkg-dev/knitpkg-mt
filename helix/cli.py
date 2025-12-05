# helix/cli.py
from typer import Typer
from helix.commands.mkinc import register as register_mkinc
from helix.commands.autocomplete import register as register_autocomplete

app = Typer(
    name="helix",
    help="Professional package manager for MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Registra todos os comandos
register_mkinc(app)
register_autocomplete(app)
# (você vai adicionando mais conforme criar: build, dist, etc.)

def main():
    app()

if __name__ == "__main__":
    main()