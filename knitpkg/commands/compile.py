# knitpkg/commands/compile.py

"""
KnitPkg for Metatrader compile command — compile MQL source files.

This module handles compilation of MQL4/MQL5 source files using MetaEditor.
The MQLCompiler class raises domain-specific exceptions instead of SystemExit,
allowing proper separation between library code and CLI layer.
"""
from typing import Optional
from pathlib import Path
from rich.console import Console
import typer

from knitpkg.mql.compile import MQLCompiler
from knitpkg.core.exceptions import KnitPkgError

# ==============================================================
# COMMAND WRAPPER
# ==============================================================

def compile_command(project_dir: Path, inplace: bool, entrypoints_only: bool, compile_only: bool, console: Console, verbose: bool):
    """Command wrapper"""

    compiler = MQLCompiler(project_dir, inplace, console, verbose)

    compiler.compile(entrypoints_only, compile_only)

# ==============================================================
# CLI REGISTRATION
# ==============================================================

def register(app):
    @app.command()
    def compile(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir",
            "-d",
            help="Project directory (default: current directory)"
        ),
        inplace: Optional[bool] = typer.Option(
            False,
            "--in-place",
            help="Keeps compiled binaries in place or move those to bin/"
        ),
        entrypoints_only: Optional[bool] = typer.Option(
            False,
            "--entrypoints-only",
            help="Compile only entrypoints (skip compile list)"
        ),
        compile_only: Optional[bool] = typer.Option(
            False,
            "--compile-only",
            help="Compile only files in compile list (skip entrypoints)"
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output"
        )
    ):
        """Compile MQL source files via CLI."""

        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir).resolve()
            
        console = Console(log_path=False)

        from knitpkg.core.console import ConsoleAware
        console_awr = ConsoleAware(console=console, verbose=True if verbose else False)
        
        try:
            console_awr.print("")
            compile_command(project_dir, \
                            True if inplace else False, \
                            True if entrypoints_only else False, \
                            True if compile_only else False, \
                            console, \
                            True if verbose else False, \
                            )
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print("\n[bold yellow]⚠️ Compilation cancelled by user.[/bold yellow]")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except KnitPkgError as e:
            console_awr.print(f"[bold red]❌ Compilation failed:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
        except Exception as e:
            console_awr.print(f"[bold red]❌ Unexpected error:[/bold red] {e}")
            console_awr.print("")
            raise typer.Exit(code=1)
        
