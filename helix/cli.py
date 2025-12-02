# helix/cli.py
from typer import Typer
from helix.commands.mkinc import register as register_mkinc

app = Typer(
    name="helix",
    help="Gerenciador profissional de projetos MQL5/MQL4",
    add_completion=False,
    no_args_is_help=True,
)

# Registra todos os comandos
register_mkinc(app)
# (você vai adicionando mais conforme criar: build, dist, etc.)

def main():
    app()

if __name__ == "__main__":
    main()