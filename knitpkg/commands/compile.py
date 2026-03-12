# knitpkg/commands/compile.py

"""
KnitPkg compile command — compile MQL source files via MetaEditor compiler.

Before invoking the MetaEditor compiler, this command automatically generates
``knitpkg/build/BuildInfo.mqh`` from the project manifest and any
``--define`` / ``-D`` flags supplied on the command line.

Usage examples::

    kp compile
    kp compile --define FEATURE_X_ENABLED --define BUILD_TYPE=release
    kp compile -D MAX_BARS=500 -D NIGHTLY
    kp compile --verbose --define MY_FLAG
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict

import typer
from rich.console import Console

from knitpkg.core.console import ConsoleAware
from knitpkg.core.exceptions import KnitPkgError
from knitpkg.mql.compile import MQLProjectCompiler, parse_defines_cli

# Command wrapper (called by the CLI registration below)

def compile_command(
    project_dir: Path,
    inplace: bool,
    entrypoints_only: bool,
    compile_only: bool,
    cli_defines: Optional[Dict],
    console: Console,
    verbose: bool,
) -> None:
    """
    Orchestrates the full compile flow:

    1. Generate ``knitpkg/build/BuildInfo.mqh``  ← NEW STEP
    2. Invoke MetaEditor via :class:`~knitpkg.mql.compile.MQLProjectCompiler`
    """
    compiler = MQLProjectCompiler(project_dir, inplace, console, verbose)
    compiler.compile(entrypoints_only, compile_only, cli_defines)


# CLI registration

def register(app: typer.Typer) -> None:

    @app.command()
    def compile(
        project_dir: Optional[Path] = typer.Option(
            None,
            "--project-dir", "-d",
            help="Project directory (default: current directory).",
        ),
        inplace: Optional[bool] = typer.Option(
            False,
            "--in-place",
            help="Keep compiled binaries in place instead of moving them to bin/.",
        ),
        entrypoints_only: Optional[bool] = typer.Option(
            False,
            "--entrypoints-only",
            help="Compile only entrypoints (skip the compile list).",
        ),
        compile_only: Optional[bool] = typer.Option(
            False,
            "--compile-only",
            help="Compile only files in the compile list (skip entrypoints).",
        ),
        raw_defines: Optional[List[str]] = typer.Option(
            None,
            "--define", "-D",
            help=(
                "Add a constant to BuildInfo in addition to those declared in the manifest with `defines`. "
                "Accepted formats: NAME (flag, no value) or NAME=value. "
                "Can be repeated: -D FEATURE_X -D BUILD_TYPE=release"
            ),
        ),
        verbose: Optional[bool] = typer.Option(
            False,
            "--verbose",
            help="Show detailed output.",
        ),
    ):
        """Compile MQL source files via MetaEditor."""

        # resolve project dir 
        resolved_dir = Path(project_dir).resolve() if project_dir else Path.cwd()

        # set up console 
        console     = Console(log_path=False)
        console_awr = ConsoleAware(console=console, verbose=bool(verbose))

        # run 
        try:
            console_awr.print("")

            # parse --define / -D arguments 
            cli_defines: Optional[dict] = parse_defines_cli(raw_defines)

            compile_command(
                project_dir      = resolved_dir,
                inplace          = bool(inplace),
                entrypoints_only = bool(entrypoints_only),
                compile_only     = bool(compile_only),
                cli_defines      = cli_defines,
                console          = console,
                verbose          = bool(verbose),
            )
            console_awr.print("")

        except KeyboardInterrupt:
            console_awr.print(
                "\n[bold yellow]⚠️  Compilation cancelled by user.[/bold yellow]"
            )
            console_awr.print("")
            raise typer.Exit(code=1)

        except KnitPkgError as exc:
            console_awr.print(
                f"\n[bold red]❌ Compilation failed:[/bold red] {exc}"
            )
            console_awr.print("")
            raise typer.Exit(code=1)

        except Exception as exc:
            console_awr.print(
                f"\n[bold red]❌ Unexpected error:[/bold red] {exc}"
            )
            console_awr.print("")
            raise typer.Exit(code=1)