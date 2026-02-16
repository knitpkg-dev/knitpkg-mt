# knitpkg/commands/global_config.py

from typing import Optional
from pathlib import Path
import typer
from rich.console import Console

from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError
from knitpkg.core.global_config import (
    get_registry_url,
    set_global_registry,
    get_global_default,
    set_global_default,
)

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def globalconfig_command(
        set_registry: str,
        mql5_compiler_path: Optional[Path],
        mql4_compiler_path: Optional[Path],
        mql5_data_folder_path: Optional[Path],
        mql4_data_folder_path: Optional[Path],
        console: Console
    ):
    """Command wrapper for install command."""
    console_awr = ConsoleAware(console=console, verbose=False)

    if set_registry:
        set_global_registry(set_registry)
        console_awr.print(f"⚙️ [bold green]Registry set[/bold green] → [cyan]{set_registry}[/cyan]")
    
    if mql5_compiler_path:
        set_global_default('mql5-compiler-path', str(mql5_compiler_path))
        console_awr.print(f"🔧 [green]MQL5 compiler path set[/green] → [cyan]{mql5_compiler_path}[/cyan]")

    if mql4_compiler_path:
        set_global_default('mql4-compiler-path', str(mql4_compiler_path))
        console_awr.print(f"🔧 [green]MQL5 compiler path set[/green] → [cyan]{mql4_compiler_path}[/cyan]")
    
    if mql5_data_folder_path:
        set_global_default('mql5-data-folder-path', str(mql5_data_folder_path))
        console_awr.print(f"📁 [green]MQL5 data folder path set[/green] → [cyan]{mql5_data_folder_path}[/cyan]")
    
    if mql4_data_folder_path:
        set_global_default('mql4-data-folder-path', str(mql4_data_folder_path))
        console_awr.print(f"📁 [green]MQL4 data folder path set[/green] → [cyan]{mql4_data_folder_path}[/cyan]")

    console_awr.print("")
    current_registry = get_registry_url()
    console_awr.print(f"📋 [bold cyan]Registry[/bold cyan] → [cyan]{current_registry}[/cyan]")
    global_default = get_global_default()
    console_awr.print("⚙️  [bold cyan]Projects Defaults[/]:")
    console_awr.print(f"   → MQL5 Compiler Path: [cyan]{global_default.get('mql5-compiler-path', 'Not set')}[/cyan]")
    console_awr.print(f"   → MQL4 Compiler Path: [cyan]{global_default.get('mql4-compiler-path', 'Not set')}[/cyan]")
    console_awr.print(f"   → MQL5 Data Folder Path: [cyan]{global_default.get('mql5-data-folder-path', 'Not set')}[/cyan]")
    console_awr.print(f"   → MQL4 Data Folder Path: [cyan]{global_default.get('mql4-data-folder-path', 'Not set')}[/cyan]")


def register(app: typer.Typer):

    @app.command()
    def globalconfig(
        mql5_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql5-compiler-path",
            help="Set the default path to MetaEditor64.exe (MQL5 compiler)"
        ),
        mql4_compiler_path: Optional[Path] = typer.Option(
            None,
            "--mql4-compiler-path",
            help="Set the default path to MetaEditor.exe (MQL4 compiler)"
        ),
        mql5_data_folder_path: Optional[Path] = typer.Option(
            None,
            "--mql5-data-folder-path",
            help="Set the default custom data folder path for MQL5 (e.g., C:\\Users\\User\\AppData\\Roaming\\MetaQuotes\\Terminal\\<hash>)"
        ),
        mql4_data_folder_path: Optional[Path] = typer.Option(
            None,
            "--mql4-data-folder-path",
            help="Set the default custom data folder path for MQL4 (e.g., C:\\Users\\User\\AppData\\Roaming\\MetaQuotes\\Terminal\\<hash>)"
        ),
        set_registry: str = typer.Option(None, "--set-registry", help="Set default registry URL")
    ):
        """Configure KnitPkg CLI options."""
        console = Console(log_path=False)

        console_awr = ConsoleAware(console=console, verbose=False)

        try:
            console_awr.print("")
            globalconfig_command(
                set_registry, 
                mql5_compiler_path,
                mql4_compiler_path,
                mql5_data_folder_path,
                mql4_data_folder_path,
                console
            )
            console_awr.print("")
        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️  Global config setting cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"\n[bold red]❌ Global config setting failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"\n[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
