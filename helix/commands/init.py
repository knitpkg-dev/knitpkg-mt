import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text
from pathlib import Path
import re
import yaml
from enum import Enum
from jinja2 import Template

from git import Repo

from helix.mql.models import MQLProjectType, Target, IncludeMode


# .gitignore content templates
GITIGNORE_PACKAGE = """
.helix/
helix/autocomplete/
helix/flat/

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
""".strip()

GITIGNORE_DEFAULT = """
.helix/
helix/autocomplete/
helix/flat/
helix/include

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
""".strip()

# MQL5/MQL4 source code templates
TEMPLATE_INCLUDE = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+

//--------------------------------------------------------------------
// For packages with dependencies, use the following Helix features:
//
// 1. Autocomplete support for MetaEditor IntelliSense.
// Run `helix autocomplete` to generate this file and uncomment the
// include below:
//
// #include "{{autocomplete_path_prefix}}/autocomplete/autocomplete.mqh"
//
//
// 2. Include directives. For headers with external dependencies, specify
// the file path relative to helix/include and uncomment the Helix directive
// below. Helix automatically resolves dependencies based on these directives.
// See documentation for details.
//
// /* @helix:include "Path/To/Dependency/Header.mqh" */
//--------------------------------------------------------------------

// Add your package code here and rename the file as needed.
"""

TEMPLATE_UNITTESTS = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: Unit tests for package {{name}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// Include the headers under test
//#include "helix/include/{{organization}}/MyHeaderHere.mqh"

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool TestName()
  {
   // Add your test code here. Rename this function to a descriptive name.
   // Create more test functions like this as needed.
   return false;
  }
//+------------------------------------------------------------------+
//| DoTests                                                          |
//+------------------------------------------------------------------+
void DoTests(int &testsPerformed,int &testsPassed)
  {
   string testName="";

   //--- TestName
   testsPerformed++;
   testName="TestName";
   if(TestName())
     {
      testsPassed++;
      PrintFormat("%s pass",testName);
     }
   else
      PrintFormat("%s failed",testName);

   //---
   // Add more tests here as needed
  }
//+------------------------------------------------------------------+
//| UnitTests()                                                      |
//+------------------------------------------------------------------+
void UnitTests(const string packageName)
  {
   PrintFormat("Unit tests for Package %s\\n",packageName);
   //--- initial values
   int testsPerformed=0;
   int testsPassed=0;
   //--- test distributions
   DoTests(testsPerformed,testsPassed);
   //--- print statistics
   PrintFormat("\\n%d of %d passed",testsPassed,testsPerformed);
  }
//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
   UnitTests("{{name}}");
  }
//+------------------------------------------------------------------+
"""

TEMPLATE_EXPERT = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   //---

   //---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   //---

  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   //---

  }
//+------------------------------------------------------------------+
"""

TEMPLATE_BARS = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   //--- indicator buffers mapping

   //---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int32_t rates_total,
                const int32_t prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int32_t &spread[])
  {
   //---

   //--- return value of prev_calculated for next call
   return(rates_total);
  }
//+------------------------------------------------------------------+
"""

TEMPLATE_SERIES = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
   //--- indicator buffers mapping

   //---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int32_t rates_total,
                const int32_t prev_calculated,
                const int32_t begin,
                const double &price[])
  {
   //---

   //--- return value of prev_calculated for next call
   return(rates_total);
  }
//+------------------------------------------------------------------+
"""

TEMPLATE_LIBRARY = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property library
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| My function                                                      |
//+------------------------------------------------------------------+
// int MyCalculator(int value,int value2) export
//   {
//    return(value+value2);
//   }
//+------------------------------------------------------------------+
"""

TEMPLATE_SERVICE = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property service
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by Helix for MetaTrader"
#property description "http://helix.dev"

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| Service program start function                                   |
//+------------------------------------------------------------------+
void OnStart()
  {
   //---

  }
//+------------------------------------------------------------------+
"""

class IndicatorInputType(str, Enum):
    """Indicator data input type."""
    OHLC = "OHLC"
    SERIES = "Series"

class ProjectInitializer:
    """Encapsulates the logic for initializing a new Helix project."""

    def __init__(self, console: Console):
        """Initialize the ProjectInitializer with a Rich console instance."""
        self.console = console

        # Project attributes
        self.project_type: MQLProjectType | None = None
        self.indicator_input_type: IndicatorInputType | None = None
        self.name: str | None = None
        self.organization: str | None = None
        self.version: str | None = None
        self.description: str | None = None
        self.author: str | None = None
        self.license: str | None = None
        self.target: Target | None = None
        self.include_mode: IncludeMode | None = None
        self.entrypoints: list[str] = []
        self.compile: list[str] = []
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
        if self.project_type == MQLProjectType.PACKAGE:
            return GITIGNORE_PACKAGE
        else:
            return GITIGNORE_DEFAULT

    def render_template(self, template_str: str, context: dict = {}) -> str:
        """Render a Jinja2 template with project context."""
        return Template(template_str).render(**context)

    def create_package_files(self) -> None:
        """Create files for package project type."""
        org_dir = self.organization if self.organization else "."

        # Create Header.mqh
        header_dir = self.project_root / "helix" / "include" / org_dir / self.name
        header_dir.mkdir(parents=True, exist_ok=True)
        header_path = header_dir / "Header.mqh"

        header_content = self.render_template(TEMPLATE_INCLUDE)
        header_path.write_text(header_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {header_path.relative_to(self.project_root)}[/green]")

        # Create UnitTests
        tests_dir = self.project_root / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        unit_file_name = "UnitTests.mq5" if self.target == Target.MQL5 else "UnitTests.mq4"
        unit_path = tests_dir / unit_file_name
        self.compile.append(f"tests/UnitTests.mq5")

        unit_content = self.render_template(TEMPLATE_UNITTESTS)
        unit_path.write_text(unit_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {unit_path.relative_to(self.project_root)}[/green]")

    def create_expert_files(self) -> None:
        """Create files for expert project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        expert_path = src_dir / f"{self.name}{file_ext}"

        expert_content = self.render_template(TEMPLATE_EXPERT)
        expert_path.write_text(expert_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {expert_path.relative_to(self.project_root)}[/green]")

    def create_indicator_files(self) -> None:
        """Create files for indicator project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        indicator_path = src_dir / f"{self.name}{file_ext}"

        template = TEMPLATE_BARS if self.indicator_input_type == IndicatorInputType.OHLC else TEMPLATE_SERIES
        indicator_content = self.render_template(template)
        indicator_path.write_text(indicator_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {indicator_path.relative_to(self.project_root)}[/green]")

    def create_library_files(self) -> None:
        """Create files for library project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        library_path = src_dir / f"{self.name}{file_ext}"

        library_content = self.render_template(TEMPLATE_LIBRARY)
        library_path.write_text(library_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {library_path.relative_to(self.project_root)}[/green]")

    def create_service_files(self) -> None:
        """Create files for service project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        service_path = src_dir / f"{self.name}{file_ext}"

        service_content = self.render_template(TEMPLATE_SERVICE)
        service_path.write_text(service_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {service_path.relative_to(self.project_root)}[/green]")

    def select_project_type(self, project_type: MQLProjectType | None) -> None:
        """Select project type."""
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

    def select_indicator_input_type(self, indicator_input_type: IndicatorInputType | None) -> None:
        """Select indicator input type (only for indicator projects)."""
        if self.project_type != MQLProjectType.INDICATOR:
            return

        if indicator_input_type is None:
            input_type_input = Prompt.ask(
                "Indicator data input type",
                choices=[it.value for it in IndicatorInputType],
                default=IndicatorInputType.SERIES.value,
            )
            self.indicator_input_type = IndicatorInputType(input_type_input)
        else:
            try:
                self.indicator_input_type = IndicatorInputType(indicator_input_type)
            except ValueError:
                self.console.print(
                    f"[red]Error: Invalid indicator input type '{indicator_input_type}'. Choose from {', '.join([it.value for it in IndicatorInputType])}.[/red]"
                )
                raise typer.Exit(code=1)

    def prompt_project_name(self, name: str | None) -> None:
        """Prompt for and validate project name."""
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
        """Prompt for organization name (optional but recommended)."""
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
        """Prompt for project version."""
        if version is None:
            version = Prompt.ask("Project version (SemVer)", default="1.0.0")
        self.version = version

    def prompt_description(self, description: str | None) -> None:
        """Prompt for project description."""
        if description is None:
            default_description = f"{self.project_type.value} for MetaTrader"
            description = Prompt.ask("Project description", default=default_description)
        self.description = description

    def prompt_author(self, author: str | None) -> None:
        """Prompt for author name."""
        if author is None:
            author = Prompt.ask("Author's name", default="No name")
        self.author = author

    def prompt_license(self, license: str | None) -> None:
        """Prompt for license identifier."""
        if license is None:
            license = Prompt.ask("License identifier", default="Undefined")
        self.license = license

    def select_target(self, target: Target | None) -> None:
        """Select MetaTrader platform target."""
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
        """Select include mode and entrypoints (conditional for non-package projects)."""
        if self.project_type != MQLProjectType.PACKAGE:
            if include_mode is None:
                include_mode_input = Prompt.ask(
                    "Include resolution mode",
                    choices=[im.value for im in IncludeMode],
                    default=IncludeMode.FLAT.value,
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
        """Determine project location."""
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
        """Check if target directory exists and handle warnings."""
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
        """Prompt for Git initialization."""
        if not git_init:
            self.git_init = Confirm.ask("Do you want to initialize a Git repository?", default=True)
        else:
            self.git_init = git_init

    def display_summary_and_confirm(self) -> bool:
        """Display summary and confirm project creation."""
        self.console.print(Text("\n--- Project Summary ---", style="bold magenta"))
        self.console.print(f"  Type: [cyan]{self.project_type.value}[/cyan]")
        if self.project_type == MQLProjectType.INDICATOR:
            self.console.print(f"  Indicator Input Type: [cyan]{self.indicator_input_type.value}[/cyan]")
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

            manifest_data["compile"] = self.compile

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

            # Create project-specific files based on type
            if self.project_type == MQLProjectType.PACKAGE:
                self.create_package_files()
            elif self.project_type == MQLProjectType.EXPERT:
                self.create_expert_files()
            elif self.project_type == MQLProjectType.INDICATOR:
                self.create_indicator_files()
            elif self.project_type == MQLProjectType.LIBRARY:
                self.create_library_files()
            elif self.project_type == MQLProjectType.SERVICE:
                self.create_service_files()

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
        indicator_input_type: IndicatorInputType | None = None,
    ) -> None:
        """Execute the project initialization workflow."""
        self.dry_run = dry_run
        self.console.print(Text("\n🚀 Initializing a new Helix project...", style="bold blue"))

        # Execute steps
        self.select_project_type(project_type)
        self.select_indicator_input_type(indicator_input_type)
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



class IndicatorInputType(str, Enum):
    """Indicator data input type."""
    OHLC = "OHLC"
    SERIES = "Series"


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
