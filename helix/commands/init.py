import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text
from pathlib import Path
import re
import yaml
from enum import Enum

from git import Repo
from git.exc import InvalidGitRepositoryError

from helix.mql.models import MQLProjectType, Target, IncludeMode
from rich.console import Console


class ProjectInitializer:
    """Encapsulates the logic for initializing a new Helix project."""

    def __init__(self, console: Console):
        """Initialize the ProjectInitializer with a Rich console instance."""
        self.console = console

        # Project attributes
        self.project_type: MQLProjectType | None = None
        self.name: str | None = None
        self.organization: str | None = None
        self.version: str | None = None
        self.description: str | None = None
        self.author: str | None = None
        self.license: str | None = None
        self.target: Target | None = None
        self.include_mode: IncludeMode | None = None
        self.entrypoints: list[str] = []
        self.project_root: Path | None = None
        self.git_init: bool = False
        self.dry_run: bool = False

    def validate_project_name(self, name: str) -> bool:
        """Validates if the project name is suitable for a directory name."""
        return re.fullmatch(r"^[\w\-\.]+$", name) is not None

    def validate_organization_name(self, name: str) -> bool:
        """Validates organization name. Accepts empty or alphanumeric pattern."""
        if name == "":
            return True
        return re.fullmatch(r"^[\w\-\.]+$", name) is not None

    def get_gitignore_content(self) -> str:
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
        if self.project_type == MQLProjectType.PACKAGE:
            return package_ignore.strip()
        else:
            return others_ignore.strip()

    def create_example_file(self):
        """Creates a basic example file based on project type."""
        if self.project_type == MQLProjectType.PACKAGE:
            if self.entrypoints:
                file_name = self.entrypoints[0]
            else:
                file_name = f"{self.name}.mqh"
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
    Print("Hello from Helix package: {self.name}!");
}}
"""
            (self.project_root / file_name).write_text(content.strip())

        elif self.project_type in [
            MQLProjectType.EXPERT,
            MQLProjectType.INDICATOR,
            MQLProjectType.LIBRARY,
            MQLProjectType.SERVICE,
        ]:
            main_file_name = f"{self.name}.mq5"
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
// #include <helix/flat/{self.entrypoints[0] if self.entrypoints else 'MyEntrypoint.mqh'}>

//+------------------------------------------------------------------+
//| Program initialization function                                  |
//+------------------------------------------------------------------+
int OnInit()
{{
   //---
   Print("Hello from Helix {self.project_type.value}: {self.name}!");
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
            (self.project_root / main_file_name).write_text(content.strip())

            if self.entrypoints:
                for ep_file in self.entrypoints:
                    (self.project_root / ep_file).write_text(
                        f"// {ep_file} for {self.name}\n// Add your shared code here\n"
                    )

    def select_project_type(self, project_type: MQLProjectType | None) -> None:
        """Step 1: Select project type."""
        if project_type is None:
            project_type_input = Prompt.ask(
                "What is the project type?",
                choices=[pt.value for pt in MQLProjectType],
                default=MQLProjectType.PACKAGE.value,
            )
            self.project_type = MQLProjectType(project_type_input)
        else:
            try:
                self.project_type = MQLProjectType(project_type)
            except ValueError:
                self.console.print(
                    f"[red]Error: Invalid project type '{project_type}'. Choose from {', '.join([pt.value for pt in MQLProjectType])}.[/red]"
                )
                raise typer.Exit(code=1)

    def prompt_project_name(self, name: str | None) -> None:
        """Step 2: Prompt for and validate project name."""
        if name is None:
            while True:
                name = Prompt.ask(
                    "Project name (alphanumeric, hyphen, underscore, dot; no spaces)",
                    default="my-project",
                )
                if self.validate_project_name(name):
                    self.name = name
                    break
                else:
                    self.console.print(
                        "[red]Invalid project name. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.[/red]"
                    )
        else:
            if not self.validate_project_name(name):
                self.console.print(
                    f"[red]Error: Invalid project name '{name}'. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.[/red]"
                )
                raise typer.Exit(code=1)
            self.name = name

    def prompt_organization(self, organization: str | None) -> None:
        """Step 3: Prompt for organization name (optional but recommended)."""
        if organization is None:
            while True:
                organization = Prompt.ask(
                    "Organization name [dim](optional but recommended; alphanumeric, hyphen, underscore, dot)[/dim]",
                    default="",
                )
                if self.validate_organization_name(organization):
                    self.organization = organization if organization else None
                    if not organization:
                        self.console.print(
                            "[yellow]Note: It's recommended to set an organization name for better package management.[/yellow]"
                        )
                    break
                else:
                    self.console.print(
                        "[red]Invalid organization name. Please use only alphanumeric characters, hyphens, underscores, or dots. Leave empty to skip.[/red]"
                    )
        else:
            if not self.validate_organization_name(organization):
                self.console.print(
                    f"[red]Error: Invalid organization name '{organization}'. Please use only alphanumeric characters, hyphens, underscores, or dots.[/red]"
                )
                raise typer.Exit(code=1)
            self.organization = organization if organization else None

    def prompt_version(self, version: str | None) -> None:
        """Step 4: Prompt for project version."""
        if version is None:
            version = Prompt.ask("Project version (SemVer)", default="1.0.0")
        self.version = version

    def prompt_description(self, description: str | None) -> None:
        """Step 5: Prompt for project description."""
        if description is None:
            default_description = f"{self.project_type.value} for MetaTrader"
            description = Prompt.ask("Project description", default=default_description)
        self.description = description

    def prompt_author(self, author: str | None) -> None:
        """Step 6: Prompt for author name."""
        if author is None:
            author = Prompt.ask("Author's name", default="No name")
        self.author = author

    def prompt_license(self, license: str | None) -> None:
        """Step 7: Prompt for license identifier."""
        if license is None:
            license = Prompt.ask("License identifier", default="Undefined")
        self.license = license

    def select_target(self, target: Target | None) -> None:
        """Step 8: Select MetaTrader platform target."""
        if target is None:
            target_input = Prompt.ask(
                "MetaTrader platform target",
                choices=[t.value for t in Target],
                default=Target.MQL5.value,
            )
            self.target = Target(target_input)
        else:
            try:
                self.target = Target(target)
            except ValueError:
                self.console.print(
                    f"[red]Error: Invalid target '{target}'. Choose from {', '.join([t.value for t in Target])}.[/red]"
                )
                raise typer.Exit(code=1)

    def select_include_mode_and_entrypoints(
        self,
        include_mode: IncludeMode | None,
        entrypoints_str: str | None,
    ) -> None:
        """Step 9: Select include mode and entrypoints (conditional for non-package projects)."""
        if self.project_type != MQLProjectType.PACKAGE:
            if include_mode is None:
                include_mode_input = Prompt.ask(
                    "Include resolution mode",
                    choices=[im.value for im in IncludeMode],
                    default=IncludeMode.INCLUDE.value,
                )
                self.include_mode = IncludeMode(include_mode_input)
            else:
                try:
                    self.include_mode = IncludeMode(include_mode)
                except ValueError:
                    self.console.print(
                        f"[red]Error: Invalid include mode '{include_mode}'. Choose from {', '.join([im.value for im in IncludeMode])}.[/red]"
                    )
                    raise typer.Exit(code=1)

            if self.include_mode == IncludeMode.FLAT:
                if entrypoints_str is None:
                    while not self.entrypoints:
                        ep_input = Prompt.ask(
                            "Entrypoint files (comma-separated, e.g., MyHeader.mqh, Another.mqh)",
                            default=f"{self.name}.mqh",
                        )
                        self.entrypoints = [ep.strip() for ep in ep_input.split(",") if ep.strip()]
                        if not self.entrypoints:
                            self.console.print(
                                "[red]Entrypoints cannot be empty when include_mode is 'flat'. Please provide at least one.[/red]"
                            )
                else:
                    self.entrypoints = [ep.strip() for ep in entrypoints_str.split(",") if ep.strip()]
                    if not self.entrypoints:
                        self.console.print(
                            "[red]Error: Entrypoints cannot be empty when include_mode is 'flat'.[/red]"
                        )
                        raise typer.Exit(code=1)

    def determine_project_location(self, location: Path | None) -> None:
        """Step 10: Determine project location."""
        if location is None:
            location_str = Prompt.ask(
                "Directory where the project will be created", default="."
            )
            if location_str == ".":
                self.project_root = Path.cwd() / self.name
            else:
                self.project_root = Path(location_str).resolve() / self.name
        else:
            self.project_root = location.resolve() / self.name

    def handle_existing_directory(self) -> None:
        """Step 11: Check if target directory exists and handle warnings."""
        if self.project_root.exists():
            self.console.print(
                f"[yellow]Warning: Directory '{self.project_root}' already exists.[/yellow]"
            )
            existing_files = list(self.project_root.iterdir())
            if existing_files:
                self.console.print(
                    f"[yellow]It contains {len(existing_files)} files/directories. Listing up to 5:[/yellow]"
                )
                for item in existing_files[:5]:
                    self.console.print(f"  - {item.name}")

                mqproj_files = list(self.project_root.glob("*.mqproj"))
                if mqproj_files:
                    self.console.print(
                        "[yellow]Found existing .mqproj files. It's recommended to remove them for Helix projects.[/yellow]"
                    )
                    if Confirm.ask("Do you want to remove existing .mqproj files?", default=True):
                        for mqproj in mqproj_files:
                            if not self.dry_run:
                                mqproj.unlink()
                            msg = (
                                f"  [green]Removed '{mqproj.name}'.[/green]"
                                if not self.dry_run
                                else f"  [yellow]Would remove '{mqproj.name}'.[/yellow]"
                            )
                            self.console.print(msg)
        else:
            self.console.print(f"[blue]Directory '{self.project_root}' will be created.[/blue]")

    def prompt_git_init(self, git_init: bool) -> None:
        """Step 12: Prompt for Git initialization."""
        if not git_init:
            self.git_init = Confirm.ask("Do you want to initialize a Git repository?", default=True)
        else:
            self.git_init = git_init

    def display_summary_and_confirm(self) -> bool:
        """Step 13: Display summary and confirm project creation."""
        self.console.print(Text("\n--- Project Summary ---", style="bold magenta"))
        self.console.print(f"  Type: [cyan]{self.project_type.value}[/cyan]")
        self.console.print(f"  Name: [cyan]{self.name}[/cyan]")
        if self.organization:
            self.console.print(f"  Organization: [cyan]{self.organization}[/cyan]")
        self.console.print(f"  Version: [cyan]{self.version}[/cyan]")
        self.console.print(f"  Description: [cyan]{self.description}[/cyan]")
        self.console.print(f"  Author: [cyan]{self.author}[/cyan]")
        self.console.print(f"  License: [cyan]{self.license}[/cyan]")
        self.console.print(f"  Target: [cyan]{self.target.value}[/cyan]")
        if self.include_mode:
            self.console.print(f"  Include Mode: [cyan]{self.include_mode.value}[/cyan]")
        if self.entrypoints:
            self.console.print(f"  Entrypoints: [cyan]{', '.join(self.entrypoints)}[/cyan]")
        self.console.print(f"  Location: [cyan]{self.project_root}[/cyan]")
        self.console.print(f"  Initialize Git: [cyan]{'Yes' if self.git_init else 'No'}[/cyan]")
        self.console.print(Text("-----------------------", style="bold magenta"))

        return Confirm.ask("Proceed with project creation?", default=True)

    def create_artifacts(self) -> None:
        """Create all project artifacts (directories, files, git repo)."""
        try:
            self.project_root.mkdir(parents=True, exist_ok=True)
            self.console.print(f"[green]Created project directory: {self.project_root}[/green]")

            # Create helix.yaml
            manifest_data = {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "author": self.author,
                "license": self.license,
                "target": self.target.value,
                "type": self.project_type.value,
            }
            if self.organization:
                manifest_data["organization"] = self.organization
            if self.include_mode:
                manifest_data["include_mode"] = self.include_mode.value
            if self.entrypoints:
                manifest_data["entrypoints"] = self.entrypoints

            if self.project_type in [
                MQLProjectType.EXPERT,
                MQLProjectType.INDICATOR,
                MQLProjectType.LIBRARY,
                MQLProjectType.SERVICE,
            ]:
                manifest_data["compile"] = [f"{self.name}.mq5"]
            else:
                manifest_data["compile"] = []

            manifest_data["dependencies"] = {}

            with open(self.project_root / "helix.yaml", "w") as f:
                yaml.dump(manifest_data, f, sort_keys=False)
            self.console.print(f"[green]Created {self.project_root / 'helix.yaml'}[/green]")

            # Create .gitignore
            gitignore_content = self.get_gitignore_content()
            with open(self.project_root / ".gitignore", "w") as f:
                f.write(gitignore_content)
            self.console.print(f"[green]Created {self.project_root / '.gitignore'}[/green]")

            # Create helix/ directories
            helix_dir = self.project_root / "helix"
            helix_dir.mkdir(exist_ok=True)
            (helix_dir / "flat").mkdir(exist_ok=True)
            (helix_dir / "autocomplete").mkdir(exist_ok=True)
            if self.project_type != MQLProjectType.PACKAGE:
                (helix_dir / "include").mkdir(exist_ok=True)
            self.console.print(f"[green]Created Helix internal directories under {helix_dir}[/green]")

            # Create example file(s)
            self.create_example_file()
            self.console.print(
                f"[green]Created initial example file(s) for {self.project_type.value} project.[/green]"
            )

            # Initialize Git repository using GitPython
            if self.git_init:
                try:
                    Repo.init(self.project_root)
                    self.console.print(
                        f"[green]Initialized Git repository in {self.project_root}[/green]"
                    )
                except Exception as e:
                    self.console.print(f"[red]Error initializing Git: {e}[/red]")

            self.console.print(
                Text(
                    f"\n🎉 Project '{self.name}' created successfully in {self.project_root}",
                    style="bold green",
                )
            )
            self.console.print(Text("Next steps:", style="bold blue"))
            self.console.print(f"  cd {self.project_root.name}")
            self.console.print(f"  Start coding your {self.project_type.value}!")

        except Exception as e:
            self.console.print(
                f"[red]An error occurred during project creation: {e}[/red]"
            )
            raise typer.Exit(code=1)

    def run(
        self,
        dry_run: bool,
        project_type: MQLProjectType | None,
        name: str | None,
        organization: str | None,
        version: str | None,
        description: str | None,
        author: str | None,
        license: str | None,
        target: Target | None,
        include_mode: IncludeMode | None,
        entrypoints_str: str | None,
        location: Path | None,
        git_init: bool,
    ) -> None:
        """Execute the project initialization workflow."""
        self.dry_run = dry_run
        self.console.print(Text("\n🚀 Initializing a new Helix project...", style="bold blue"))

        # Execute steps
        self.select_project_type(project_type)
        self.prompt_project_name(name)
        self.prompt_organization(organization)
        self.prompt_version(version)
        self.prompt_description(description)
        self.prompt_author(author)
        self.prompt_license(license)
        self.select_target(target)
        self.select_include_mode_and_entrypoints(include_mode, entrypoints_str)
        self.determine_project_location(location)
        self.handle_existing_directory()
        self.prompt_git_init(git_init)

        # Confirmation
        if not self.display_summary_and_confirm():
            self.console.print("[red]Project creation cancelled.[/red]")
            raise typer.Exit()

        if self.dry_run:
            self.console.print(
                Text("\n[yellow]Dry run complete. No changes were made.[/yellow]", style="bold")
            )
            raise typer.Exit()

        # Create artifacts
        self.create_artifacts()


def register(app):
    """Register the init command with the Typer app."""

    @app.command(name="init", help="Initializes a new Helix project.")
    def init_project(
        dry_run: bool = typer.Option(
            False, "--dry-run", "-d", help="Show what would be done without making actual changes."
        ),
        project_type: MQLProjectType = typer.Option(
            None, "--type", "-t", help="Project type (package, expert, indicator, library, service)."
        ),
        name: str = typer.Option(
            None,
            "--name",
            "-n",
            help="Project name (alphanumeric, hyphen, underscore, dot; no spaces).",
        ),
        organization: str = typer.Option(
            None,
            "--organization",
            "-o",
            help="Organization name (optional; alphanumeric, hyphen, underscore, dot).",
        ),
        version: str = typer.Option(
            None, "--version", "-v", help="Project version (SemVer, e.g., 1.0.0)."
        ),
        description: str = typer.Option(None, "--description", help="Short project description."),
        author: str = typer.Option(None, "--author", help="Author's name."),
        license: str = typer.Option(None, "--license", help="License identifier (e.g., MIT)."),
        target: Target = typer.Option(None, "--target", help="MetaTrader platform target (MQL4 or MQL5)."),
        include_mode: IncludeMode = typer.Option(
            None, "--include-mode", help="Include resolution mode (include or flat)."
        ),
        entrypoints_str: str = typer.Option(
            None,
            "--entrypoints",
            help="Comma-separated list of entrypoint files (required if include_mode=flat and type!=package).",
        ),
        location: Path = typer.Option(
            None, "--location", "-l", help="Directory where the project will be created."
        ),
        git_init: bool = typer.Option(False, "--git-init", help="Initialize a Git repository."),
    ):
        """Initializes a new Helix project interactively."""
        console = Console()
        initializer = ProjectInitializer(console)
        initializer.run(
            dry_run=dry_run,
            project_type=project_type,
            name=name,
            organization=organization,
            version=version,
            description=description,
            author=author,
            license=license,
            target=target,
            include_mode=include_mode,
            entrypoints_str=entrypoints_str,
            location=location,
            git_init=git_init,
        )
