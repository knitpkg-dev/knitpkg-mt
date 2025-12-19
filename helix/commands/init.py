import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text
from pathlib import Path
import re
import yaml
from enum import Enum
import subprocess # For git init

from helix.mql.models import MQLProjectType
from helix.mql.models import Target, IncludeMode

# Initialize Rich console
console = Console()

# --- Enums and Models (Simplified for init, actual validation would be in helix/mql/models.py) ---

# --- Helper Functions ---
def validate_project_name(name: str) -> bool:
    """Validates if the project name is suitable for a directory name."""
    # Regex: alphanumeric, hyphen, underscore, dot. No spaces.
    return re.fullmatch(r"^[\w\-\.]+$", name) is not None

def get_gitignore_content(project_type: MQLProjectType) -> str:
    """Returns the appropriate .gitignore content based on project type."""
    package_ignore = """
.helix/
helix/autocomplete/
helix/flat/

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
"""
    others_ignore = """
.helix/
helix/autocomplete/
helix/flat/
helix/include

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
"""
    if project_type == MQLProjectType.PACKAGE:
        return package_ignore.strip()
    else:
        return others_ignore.strip()

def create_example_file(project_root: Path, project_type: MQLProjectType, project_name: str, entrypoints: list[str]):
    """Creates a basic example file based on project type."""
    if project_type == MQLProjectType.PACKAGE:
        # For package, create the first entrypoint if specified, otherwise a generic .mqh
        if entrypoints:
            file_name = entrypoints[0]
        else:
            file_name = f"{project_name}.mqh"
        content = f"""//+------------------------------------------------------------------+
//|                                                      {file_name} |
//|                                          https://www.helix.dev |
//+------------------------------------------------------------------+
#property copyright "No name"
#property link      "https://www.helix.dev"
#property version   "1.00"

// Example function for your package
void OnStart()
{{
    Print("Hello from Helix package: {project_name}!");
}}
"""
        (project_root / file_name).write_text(content.strip())
    elif project_type in [MQLProjectType.EXPERT, MQLProjectType.INDICATOR, MQLProjectType.LIBRARY, MQLProjectType.SERVICE]:
        # For other types, create a main .mq5 file and potentially an entrypoint .mqh
        main_file_name = f"{project_name}.mq5"
        content = f"""//+------------------------------------------------------------------+
//|                                                    {main_file_name} |
//|                                          https://www.helix.dev |
//+------------------------------------------------------------------+
#property copyright "No name"
#property link      "https://www.helix.dev"
#property version   "1.00"
#property strict

// If using 'flat' include mode, your entrypoints will be flattened into helix/flat/
// You might include them like this:
// #include <helix/flat/{entrypoints[0] if entrypoints else 'MyEntrypoint.mqh'}>

//+------------------------------------------------------------------+
//| Program initialization function                                  |
//+------------------------------------------------------------------+
int OnInit()
{{
   //---
   Print("Hello from Helix {project_type.value}: {project_name}!");
   //---
   return(INIT_SUCCEEDED);
}}
//+------------------------------------------------------------------+
//| Program deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
   //---

}}
//+------------------------------------------------------------------+
//| Program tick function (for Expert Advisors)                      |
//+------------------------------------------------------------------+
void OnTick()
{{
   //---

}}
"""
        (project_root / main_file_name).write_text(content.strip())

        if entrypoints:
            for ep_file in entrypoints:
                (project_root / ep_file).write_text(f"// {ep_file} for {project_name}\n// Add your shared code here\n")


def register(app):
    """Register the config command with the Typer app."""

    @app.command(name="init", help="Initializes a new Helix project.")
    def init_project(
        dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be done without making actual changes."),
        project_type: MQLProjectType = typer.Option(None, "--type", "-t", help="Project type (package, expert, indicator, library, service)."),
        name: str = typer.Option(None, "--name", "-n", help="Project name (alphanumeric, hyphen, underscore, dot; no spaces)."),
        version: str = typer.Option(None, "--version", "-v", help="Project version (SemVer, e.g., 1.0.0)."),
        description: str = typer.Option(None, "--description", help="Short project description."),
        author: str = typer.Option(None, "--author", help="Author's name."),
        license: str = typer.Option(None, "--license", help="License identifier (e.g., MIT)."),
        target: Target = typer.Option(None, "--target", help="MetaTrader platform target (MQL4 or MQL5)."),
        include_mode: IncludeMode = typer.Option(None, "--include-mode", help="Include resolution mode (include or flat)."),
        entrypoints_str: str = typer.Option(None, "--entrypoints", help="Comma-separated list of entrypoint files (required if include_mode=flat and type!=package)."),
        location: Path = typer.Option(None, "--location", "-l", help="Directory where the project will be created."),
        git_init: bool = typer.Option(False, "--git-init", help="Initialize a Git repository.")
    ):
        """
        Initializes a new Helix project interactively.
        """
        console.print(Text("\n🚀 Initializing a new Helix project...", style="bold blue"))

        # 1. Select project type
        if project_type is None:
            project_type_input = Prompt.ask(
                "What is the project type?",
                choices=[pt.value for pt in MQLProjectType],
                default=MQLProjectType.PACKAGE.value
            )
            project_type = MQLProjectType(project_type_input)
        else:
            try:
                project_type = MQLProjectType(project_type)
            except ValueError:
                console.print(f"[red]Error: Invalid project type '{project_type}'. Choose from {', '.join([pt.value for pt in MQLProjectType])}.[/red]")
                raise typer.Exit(code=1)

        # 2. Project name
        if name is None:
            while True:
                name = Prompt.ask(
                    "Project name (alphanumeric, hyphen, underscore, dot; no spaces)",
                    default="my-project"
                )
                if validate_project_name(name):
                    break
                else:
                    console.print("[red]Invalid project name. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.[/red]")
        else:
            if not validate_project_name(name):
                console.print(f"[red]Error: Invalid project name '{name}'. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.[/red]")
                raise typer.Exit(code=1)

        # 3. Version
        if version is None:
            version = Prompt.ask("Project version (SemVer)", default="1.0.0")
        # TODO: Add SemVer validation here if not relying solely on MQLHelixManifest later

        # 4. Description
        if description is None:
            default_description = f"{project_type.value} for MetaTrader"
            description = Prompt.ask("Project description", default=default_description)

        # 5. Author
        if author is None:
            author = Prompt.ask("Author's name", default="No name")

        # 6. License
        if license is None:
            license = Prompt.ask("License identifier", default="Undefined")

        # 7. Target
        if target is None:
            target_input = Prompt.ask(
                "MetaTrader platform target",
                choices=[t.value for t in Target],
                default=Target.MQL5.value
            )
            target = Target(target_input)
        else:
            try:
                target = Target(target)
            except ValueError:
                console.print(f"[red]Error: Invalid target '{target}'. Choose from {', '.join([t.value for t in Target])}.[/red]")
                raise typer.Exit(code=1)

        # 8. Include mode (conditional)
        chosen_include_mode = None
        entrypoints = []
        if project_type != MQLProjectType.PACKAGE:
            if include_mode is None:
                chosen_include_mode_input = Prompt.ask(
                    "Include resolution mode",
                    choices=[im.value for im in IncludeMode],
                    default=IncludeMode.INCLUDE.value
                )
                chosen_include_mode = IncludeMode(chosen_include_mode_input)
            else:
                try:
                    chosen_include_mode = IncludeMode(include_mode)
                except ValueError:
                    console.print(f"[red]Error: Invalid include mode '{include_mode}'. Choose from {', '.join([im.value for im in IncludeMode])}.[/red]")
                    raise typer.Exit(code=1)

            # 9. Entrypoints (conditional)
            if chosen_include_mode == IncludeMode.FLAT:
                if entrypoints_str is None:
                    while not entrypoints:
                        ep_input = Prompt.ask(
                            "Entrypoint files (comma-separated, e.g., MyHeader.mqh, Another.mqh)",
                            default=f"{name}.mqh"
                        )
                        entrypoints = [ep.strip() for ep in ep_input.split(',') if ep.strip()]
                        if not entrypoints:
                            console.print("[red]Entrypoints cannot be empty when include_mode is 'flat'. Please provide at least one.[/red]")
                else:
                    entrypoints = [ep.strip() for ep in entrypoints_str.split(',') if ep.strip()]
                    if not entrypoints:
                        console.print("[red]Error: Entrypoints cannot be empty when include_mode is 'flat'.[/red]")
                        raise typer.Exit(code=1)
                # TODO: Validate entrypoint files exist or will be created (for now, assume they will be created)

        # 10. Project location
        project_root: Path
        if location is None:
            location_str = Prompt.ask("Directory where the project will be created", default=".")
            # If default is '.', resolve to current working directory, then append project name
            if location_str == ".":
                project_root = Path.cwd() / name
            else:
                project_root = Path(location_str).resolve() / name
        else:
            project_root = location.resolve() / name

        # Check if target directory exists and handle warnings
        if project_root.exists():
            console.print(f"[yellow]Warning: Directory '{project_root}' already exists.[/yellow]")
            existing_files = list(project_root.iterdir())
            if existing_files:
                console.print(f"[yellow]It contains {len(existing_files)} files/directories. Listing up to 5:[/yellow]")
                for i, item in enumerate(existing_files[:5]):
                    console.print(f"  - {item.name}")

                mqproj_files = list(project_root.glob("*.mqproj"))
                if mqproj_files:
                    console.print("[yellow]Found existing .mqproj files. It's recommended to remove them for Helix projects.[/yellow]")
                    if Confirm.ask("Do you want to remove existing .mqproj files?", default=True):
                        for mqproj in mqproj_files:
                            if not dry_run:
                                mqproj.unlink()
                            console.print(f"  [green]Removed '{mqproj.name}'.[/green]" if not dry_run else f"  [yellow]Would remove '{mqproj.name}'.[/yellow]")
        else:
            console.print(f"[blue]Directory '{project_root}' will be created.[/blue]")

        # 11. Git Init
        if not git_init: # Only ask if not provided via option
            git_init = Confirm.ask("Do you want to initialize a Git repository?", default=True)

        # 12. Confirmation
        console.print(Text("\n--- Project Summary ---", style="bold magenta"))
        console.print(f"  Type: [cyan]{project_type.value}[/cyan]")
        console.print(f"  Name: [cyan]{name}[/cyan]")
        console.print(f"  Version: [cyan]{version}[/cyan]")
        console.print(f"  Description: [cyan]{description}[/cyan]")
        console.print(f"  Author: [cyan]{author}[/cyan]")
        console.print(f"  License: [cyan]{license}[/cyan]")
        console.print(f"  Target: [cyan]{target.value}[/cyan]")
        if chosen_include_mode:
            console.print(f"  Include Mode: [cyan]{chosen_include_mode.value}[/cyan]")
        if entrypoints:
            console.print(f"  Entrypoints: [cyan]{', '.join(entrypoints)}[/cyan]")
        console.print(f"  Location: [cyan]{project_root}[/cyan]")
        console.print(f"  Initialize Git: [cyan]{'Yes' if git_init else 'No'}[/cyan]")
        console.print(Text("-----------------------", style="bold magenta"))

        if not Confirm.ask("Proceed with project creation?", default=True):
            console.print("[red]Project creation cancelled.[/red]")
            raise typer.Exit()

        if dry_run:
            console.print(Text("\n[yellow]Dry run complete. No changes were made.[/yellow]", style="bold"))
            raise typer.Exit()

        # --- Create Artifacts ---
        try:
            project_root.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created project directory: {project_root}[/green]")

            # Create helix.yaml
            manifest_data = {
                "name": name,
                "version": version,
                "description": description,
                "author": author,
                "license": license,
                "target": target.value,
                "type": project_type.value,
            }
            if chosen_include_mode:
                manifest_data["include_mode"] = chosen_include_mode.value
            if entrypoints:
                manifest_data["entrypoints"] = entrypoints

            # Add compile section based on project type
            if project_type in [MQLProjectType.EXPERT, MQLProjectType.INDICATOR, MQLProjectType.LIBRARY, MQLProjectType.SERVICE]:
                manifest_data["compile"] = [f"{name}.mq5"] # Automatically add main file to compile
            else:
                manifest_data["compile"] = [] # Empty for package or if not specified

            # Add empty dependencies section
            manifest_data["dependencies"] = {}

            with open(project_root / "helix.yaml", "w") as f:
                yaml.dump(manifest_data, f, sort_keys=False)
            console.print(f"[green]Created {project_root / 'helix.yaml'}[/green]")

            # Create .gitignore
            gitignore_content = get_gitignore_content(project_type)
            with open(project_root / ".gitignore", "w") as f:
                f.write(gitignore_content)
            console.print(f"[green]Created {project_root / '.gitignore'}[/green]")

            # Create helix/ directories
            helix_dir = project_root / "helix"
            helix_dir.mkdir(exist_ok=True)
            (helix_dir / "flat").mkdir(exist_ok=True)
            (helix_dir / "autocomplete").mkdir(exist_ok=True)
            if project_type != MQLProjectType.PACKAGE:
                (helix_dir / "include").mkdir(exist_ok=True)
            console.print(f"[green]Created Helix internal directories under {helix_dir}[/green]")

            # Create example file(s)
            create_example_file(project_root, project_type, name, entrypoints)
            console.print(f"[green]Created initial example file(s) for {project_type.value} project.[/green]")

            # Initialize Git repository
            if git_init:
                try:
                    subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)
                    console.print(f"[green]Initialized Git repository in {project_root}[/green]")
                except FileNotFoundError:
                    console.print("[yellow]Warning: Git command not found. Skipping Git initialization.[/yellow]")
                except subprocess.CalledProcessError as e:
                    console.print(f"[red]Error initializing Git: {e.stderr.decode().strip()}[/red]")

            console.print(Text(f"\n🎉 Project '{name}' created successfully in {project_root}", style="bold green"))
            console.print(Text("Next steps:", style="bold blue"))
            console.print(f"  cd {project_root.name}")
            console.print(f"  Start coding your {project_type.value}!")

        except Exception as e:
            console.print(f"[red]An error occurred during project creation: {e}[/red]")
            raise typer.Exit(code=1)

