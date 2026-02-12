from rich.console import Console
from rich.prompt import Prompt, Confirm
from pathlib import Path
import re
import yaml
from enum import Enum
from jinja2 import Template
from typing import Optional

from git import Repo

from knitpkg.mql.models import MQLProjectType, Target, IncludeMode
from knitpkg.mql.mql_paths import find_mql_paths
from knitpkg.mql import project_init_templates as templates
from knitpkg.core.console import Console, ConsoleAware
from knitpkg.core.exceptions import InvalidUsageError

from knitpkg.core.models import PROJECT_NAME_RE, ORGANIZATION_RE
from knitpkg.core.version_handling import validate_version
from knitpkg.core.settings import Settings

class IndicatorInputType(str, Enum):
    """Indicator data input type."""
    OHLC = "OHLC"
    SERIES = "Series"

class ProjectInitializer(ConsoleAware):
    """Encapsulates the logic for initializing a new KnitPkg project."""

    def __init__(self, console: Console):
        """Initialize the ProjectInitializer with a Rich console instance."""
        super().__init__(console, False)

        self.project_root: Optional[Path] = None

        # Project attributes
        self.project_type: Optional[MQLProjectType] = None
        self.indicator_input_type: Optional[IndicatorInputType] = None
        self.name: Optional[str] = None
        self.organization: Optional[str] = None
        self.version: Optional[str] = None
        self.description: Optional[str] = None
        self.keywords: Optional[list[str]] = None
        self.author: Optional[str] = None
        self.license: Optional[str] = None
        self.target: Optional[Target] = None
        self.include_mode: Optional[IncludeMode] = None
        self.entrypoints: list[str] = []
        self.compile: list[str] = []

        # Init options
        self.git_init: bool = False
        self.dry_run: bool = False
        self.enable_telemetry: bool = False

    def validate_project_name(self, name: str) -> bool:
        """Validates if the project name is suitable for a directory name."""
        return PROJECT_NAME_RE.fullmatch(name) is not None

    def validate_organization_name(self, name: str) -> bool:
        """Validates organization name. Accepts empty or alphanumeric pattern."""
        return ORGANIZATION_RE.fullmatch(name) is not None
    
    def get_gitignore_content(self) -> str:
        """Returns the appropriate .gitignore content based on project type."""
        if self.project_type == MQLProjectType.PACKAGE:
            return templates.GITIGNORE_PACKAGE
        else:
            return templates.GITIGNORE_DEFAULT

    def render_template(self, template_str: str, context: dict = {}) -> str:
        """Render a Jinja2 template with project context."""
        return Template(template_str).render(**context)

    @staticmethod
    def format_mql_header(txt: str) -> str:
        header_dashes_len = len("//+------------------------------------------------------------------+")
        return f"{' '*(header_dashes_len-len(txt)-6)}{txt} |"

    def create_package_files(self) -> None:
        """Create files for package project type."""
        org_dir = self.organization if self.organization else "."
        name: str = self.name # type: ignore
        project_root: Path = self.project_root # type: ignore

        # Create Header.mqh
        header_dir = project_root / "knitpkg" / "include" / org_dir / name
        header_dir.mkdir(parents=True, exist_ok=True)
        header_path = header_dir / "Header.mqh"

        header_content = self.render_template(templates.TEMPLATE_PACKAGE_INCLUDE, {
            "header_file_name": ProjectInitializer.format_mql_header("Header.mqh"),
            "header_name": ProjectInitializer.format_mql_header(f"Package {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "autocomplete_path_prefix": "../../..",
        })
        header_path.write_text(header_content.strip() + "\n", encoding="utf-8")
        self.print(f"[green]Created {header_path.relative_to(project_root)}[/green]")

        # Create UnitTests
        tests_dir = project_root / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        unit_file_name = "UnitTests.mq5" if self.target == Target.mql5 else "UnitTests.mq4"
        unit_path = tests_dir / unit_file_name
        self.compile.append("tests/UnitTests.mq5")

        unit_content = self.render_template(templates.TEMPLATE_PACKAGE_UNITTESTS, {
            "header_file_name": ProjectInitializer.format_mql_header(unit_file_name),
            "header_name": ProjectInitializer.format_mql_header(f"Unit Tests for Package {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "name": self.name,
            "organization": self.organization if self.organization else "No organization",
            "version": self.version,
            "author": self.author,
            "license": self.license,
            "header_path": f"../{header_path.relative_to(project_root).as_posix()}",
        })
        unit_path.write_text(unit_content.strip() + "\n", encoding="utf-8")
        self.print(f"[green]Created {unit_path.relative_to(project_root)}[/green]")

        # Create GETTING_STARTED
        getting_started_content = self.render_template(templates.TEMPLATE_PACKAGE_GETTING_STARTED, {
            "header_path": header_path.relative_to(project_root).as_posix(),
            "unit_test_path": "tests/UnitTests.mq5"
        })
        getting_started_path = project_root / "GETTING_STARTED"
        getting_started_path.write_text(getting_started_content.strip() + "\n", encoding="utf-8")
        self.print(f"[green]Created {getting_started_path.relative_to(project_root)}[/green]")

    def create_expert_files(self) -> None:
        self.create_project_files('Expert Advisor', templates.TEMPLATE_EXPERT, templates.TEMPLATE_EXPERT_GETTING_STARTED)

    def create_indicator_files(self) -> None:
        if self.target == Target.mql4:
            template = templates.TEMPLATE_INDICATOR_BARS_MQL4
        else:
            template = templates.TEMPLATE_INDICATOR_BARS_MQL5 \
                if self.indicator_input_type == IndicatorInputType.OHLC else templates.TEMPLATE_INDICATOR_SERIES
        self.create_project_files('Indicator', template, templates.TEMPLATE_INDICATOR_GETTING_STARTED)

    def create_script_files(self) -> None:
        self.create_project_files('Script', templates.TEMPLATE_SCRIPT, templates.TEMPLATE_SCRIPT_GETTING_STARTED)

    def create_library_files(self) -> None:
        self.create_project_files('Library', templates.TEMPLATE_LIBRARY, templates.TEMPLATE_LIBRARY_GETTING_STARTED)

    def create_service_files(self) -> None:
        self.create_project_files('Service', templates.TEMPLATE_SERVICE, templates.TEMPLATE_SERVICE_GETTING_STARTED)

    def create_project_files(self, header_name_preffix: str, template_project_content: str, template_get_started: str) -> None:
        """Create files for expert, indicator, script, ... project types."""
        project_root: Path = self.project_root # type: ignore
        org: str = self.organization # type: ignore
        src_dir = project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        if self.include_mode == IncludeMode.FLAT:
            project_includes = []
            for entrypoint_path in self.entrypoints:
                entrypoint_file_name = Path(entrypoint_path).name
                entrypoint_flattened_name = entrypoint_file_name[:len(entrypoint_file_name)-4] + "_flat" + entrypoint_file_name[len(entrypoint_file_name)-4:]
                    
                entrypoint_content = self.render_template(
                    templates.TEMPLATE_ENTRYPOINT_MQH if entrypoint_file_name.lower().endswith(".mqh") else templates.TEMPLATE_ENTRYPOINT_MQL, {
                    "header_file_name": ProjectInitializer.format_mql_header(entrypoint_file_name),
                    "header_name": ProjectInitializer.format_mql_header(f"Flattened file: {entrypoint_flattened_name}"),
                    "header_organization": ProjectInitializer.format_mql_header(org),
                })

                (project_root / entrypoint_path).write_text(entrypoint_content.strip() + "\n", encoding="utf-8")

                if entrypoint_file_name.lower().endswith(".mqh"):
                    project_includes.append(f'#include "../knitpkg/flat/{entrypoint_flattened_name}"')
        else:
            project_includes = ['// Add here your includes to the resolved dependencies, something like:',
                                '// #include "../knitpkg/include/Path/to/header.mqh"']

        file_ext = ".mq5" if self.target == Target.mql5 else ".mq4"
        file_name = f"{self.name}{file_ext}"
        expert_path = src_dir / file_name

        expert_content = self.render_template(template_project_content, {
            "header_file_name": ProjectInitializer.format_mql_header(file_name),
            "header_name": ProjectInitializer.format_mql_header(f"{header_name_preffix} {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "version": self.version,
            "description": self.description,
            "organization": self.organization if self.organization else "No organization",
            "author": self.author,
            "license": self.license,
            "project_includes": "\n".join(project_includes) if project_includes else '',
        })

        expert_path.write_text(expert_content.strip() + "\n", encoding="utf-8")

        self.compile.append(f"src/{file_name}")

        self.print(f"[green]Created {expert_path.relative_to(project_root)}[/green]")

        # Create GETTING_STARTED
        getting_started_content = self.render_template(template_get_started)
        getting_started_path = project_root / "GETTING_STARTED"
        getting_started_path.write_text(getting_started_content.strip() + "\n", encoding="utf-8")
        self.print(f"[green]Created {getting_started_path.relative_to(project_root)}[/green]")


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
                raise InvalidUsageError(f"Invalid project type '{project_type}'. Choose from {', '.join([pt.value for pt in MQLProjectType])}.")

    def select_indicator_input_type(self, indicator_input_type: IndicatorInputType | None) -> None:
        """Select indicator input type (only for indicator projects)."""
        if self.project_type != MQLProjectType.INDICATOR:
            return
        
        if self.target == Target.mql4:
            self.indicator_input_type = IndicatorInputType.OHLC
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
                raise InvalidUsageError(f"Invalid indicator input type '{indicator_input_type}'. Choose from {', '.join([it.value for it in IndicatorInputType])}.")

    def prompt_project_name(self, name: Optional[str]) -> None:
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
                self.print(
                    "[red]Invalid project name. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.[/red]"
                )
        else:
            if not self.validate_project_name(name):
                raise InvalidUsageError(f"Invalid project name '{name}'. Please use only alphanumeric characters, hyphens, underscores, or dots. No spaces.")
            self.name = name

    def prompt_organization(self, organization: Optional[str]) -> None:
        """Prompt for organization name (optional but recommended)."""
        if organization is None:
            while True:
                organization = Prompt.ask(
                    "Organization name [dim](alphanumeric, hyphen, underscore, dot)[/dim]",
                    default="",
                )
                if self.validate_organization_name(organization):
                    self.organization = organization if organization else None
                    break
                self.print(
                    "[yellow bold]⚠️  Warning:[/] Invalid organization name. Please use only alphanumeric characters, hyphens, underscores, or dots. Leave empty to skip."
                )
        else:
            if not self.validate_organization_name(organization):
                raise InvalidUsageError(f"Invalid organization name '{organization}'. Please use only alphanumeric characters, hyphens, underscores, or dots.")
            self.organization = organization if organization else None

        
    def prompt_version(self, version: Optional[str]) -> None:
        """Prompt for project version."""
        if version is None:
            while True:
                version = Prompt.ask("Project version (SemVer)", default="1.0.0")
                if validate_version(version):
                    self.version = version
                    break
                self.print(
                    f"[red]Invalid version: `{version}`. Only SemVer or ranges are accepted.[/]"
                )
        else:
            if not validate_version(version):
                raise InvalidUsageError(f"Invalid version: `{version}`. Only SemVer or ranges are accepted.")
        self.version = version

    def prompt_description(self, description: Optional[str]) -> None:
        """Prompt for project description."""
        if description is None:
            default_description = f"{self.project_type.value} for MetaTrader" # type: ignore
            description = Prompt.ask("Project description", default=default_description)
        self.description = description

    def prompt_keywords(self, keywords: Optional[str]) -> None:
        """Prompt for project keywords (up to 10)."""
        if keywords is None:
            while True:
                keywords_input = Prompt.ask(
                    "Project keywords (comma-separated, up to 10)",
                    default=""
                )
                if not keywords_input.strip():
                    self.keywords = None
                    break
                
                keywords_list = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
                if len(keywords_list) > 10:
                    self.print("[red]Maximum 10 keywords allowed. Please try again.[/red]")
                    continue
                self.keywords = keywords_list
                break
        else:
            keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            if len(keywords_list) > 10:
                raise InvalidUsageError("Maximum 10 keywords allowed.")
            self.keywords = keywords_list if keywords_list else None

    def prompt_author(self, author: Optional[str]) -> None:
        """Prompt for author name."""
        if author is None:
            author = Prompt.ask("Author's name", default="No name")
        self.author = author

    def prompt_license(self, license: Optional[str]) -> None:
        """Prompt for license identifier."""
        if license is None:
            license = Prompt.ask("License identifier", default="MIT")
        self.license = license

    def select_target(self, target: Optional[Target]) -> None:
        """Select MetaTrader platform target."""
        if target is None:
            target_input = Prompt.ask(
                "MetaTrader platform target",
                choices=[t.value for t in Target],
                default=Target.mql5.value,
            )
            self.target = Target(target_input)
        else:
            try:
                self.target = Target(target)
            except ValueError:
                raise InvalidUsageError(f"Invalid target '{target}'. Choose from {', '.join([t.value for t in Target])}.")

    def select_include_mode_and_entrypoints(
        self,
        include_mode: IncludeMode | None,
        entrypoints_str: Optional[str],
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
                    raise InvalidUsageError(f"Invalid include mode '{include_mode}'. Choose from {', '.join([im.value for im in IncludeMode])}.")

            if self.include_mode == IncludeMode.FLAT:
                mql_ext = '.mq5' if self.target == Target.mql5 else '.mq4'

                entrypoints_raw = []
                if entrypoints_str is None:
                    while True:
                        ep_input = Prompt.ask(
                            "Entrypoint files (comma-separated, e.g., MyHeader.mqh, Another.mqh)",
                            default=f"{self.name}.mqh",
                        )
                        entrypoints_raw = [ep.strip() for ep in ep_input.split(",") if ep.strip()]
                        if not entrypoints_raw:
                            self.print(
                                "[red]Entrypoints cannot be empty when include_mode is 'flat'. Please provide at least one.[/red]"
                            )
                            continue
                        if not all(ep.lower().endswith(".mqh") or ep.lower().endswith(mql_ext) for ep in entrypoints_raw):
                            self.print(
                                f"[red]All entrypoints must end with '.mqh' or {mql_ext}.[/red]"
                            )
                            continue
                        break
                else:
                    entrypoints_raw = [ep.strip() for ep in entrypoints_str.split(",") if ep.strip()]
                    if not entrypoints_raw:
                        raise InvalidUsageError("Entrypoints cannot be empty when include_mode is 'flat'.")
                    if not all(ep.lower().endswith(".mqh") or ep.lower().endswith(f'.{mql_ext}') for ep in entrypoints_raw):
                        raise InvalidUsageError(f"All entrypoints must end with '.mqh' or {mql_ext}.")
                
                self.entrypoints = []
                for ep in entrypoints_raw:
                    ep_path = Path(ep)
                    if ep_path.root != 'src':
                        self.entrypoints.append(f'src/{ep}')
                    else:
                        self.entrypoints.append(ep)
                

    def determine_project_location(self, location: Path | None) -> None:
        """Determine project location."""
        name: str = self.name  # type: ignore
        if location is None:
            mql_paths = find_mql_paths(self.target) # type: ignore
            if mql_paths and len(mql_paths) == 1:
                mql_path = mql_paths[0]
                if self.project_type == MQLProjectType.PACKAGE:
                    location_str = mql_path / "Scripts"
                elif self.project_type == MQLProjectType.EXPERT:
                    location_str = mql_path / "Experts"
                elif self.project_type == MQLProjectType.INDICATOR:
                    location_str = mql_path / "Indicators"
                elif self.project_type == MQLProjectType.LIBRARY:
                    location_str = mql_path / "Libraries"
                elif self.project_type == MQLProjectType.SCRIPT:
                    location_str = mql_path / "Scripts"
                elif self.project_type == MQLProjectType.SERVICE:
                    location_str = mql_path / "Services"
                else:
                    location_str = "."
            else:
                location_str = Prompt.ask(
                    "Directory where the project will be created", default='.'
                )
            if location_str == ".":
                self.project_root = Path.cwd() / name
            else:
                self.project_root = Path(location_str).resolve() / name
        else:
            self.project_root = location.resolve() / name

    def handle_existing_directory(self) -> None:
        """Check if target directory exists and handle warnings."""
        project_root: Path = self.project_root  # type: ignore
        if project_root.exists():
            self.print(
                f"[yellow]⚠️  Warning[/yellow]: Directory '{project_root}' already exists."
            )
            existing_files = list(project_root.iterdir())
            if existing_files:
                self.print(
                    f"It contains {len(existing_files)} files/directories. Listing up to 5:"
                )
                count = 0
                for item in existing_files:
                    if item.name == ".git":
                        continue
                    self.print(f"  - {item.name}{'/' if item.is_dir() else ''}")
                    count += 1
                    if count >= 5:
                        break

                if not Confirm.ask("[yellow]Project files will be overwritten.[/] Continue?", default=False):
                    raise KeyboardInterrupt()

                mqproj_files = list(project_root.glob("*.mqproj"))
                if mqproj_files:
                    self.print(
                        "[yellow]Found existing .mqproj files. It's recommended to remove them for KnitPkg projects.[/yellow]"
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
                            self.print(msg)
        else:
            self.print(f"[blue]Directory '{project_root}' will be created.[/blue]")

    def prompt_git_init(self, git_init: Optional[bool]) -> None:
        """Prompt for Git initialization."""
        project_root: Path = self.project_root  # type: ignore
        if (project_root / ".git").is_dir():
            self.git_init = False
            return

        if git_init is None:
            self.git_init = Confirm.ask("Do you want to initialize a Git repository?", default=True)
        else:
            self.git_init = git_init

    def prompt_enable_telemetry(self, enable_telemetry: Optional[bool]) -> None:
        """Prompt for telemetry enablement."""
        if enable_telemetry is None:
            enable_telemetry = Confirm.ask("Do you want to enable telemetry for this project?", default=True)

        if not enable_telemetry:
            self.print(
                "\n[yellow bold]⚠️  Telemetry will be disabled for this project.[/] "
                "Are you sure? The KnitPkg ecosystem's vitality depends on community participation. "
                "Without telemetry data, we cannot effectively improve and maintain this critical infrastructure."
            )
            enable_telemetry = Confirm.ask("Enable telemetry for this project? ( please say 'yes' :-D )", default=False)

        self.enable_telemetry = enable_telemetry

    def display_summary_and_confirm(self) -> bool:
        if self.organization:
            self.print(f"  Organization: [cyan]{self.organization}[/cyan]")
        self.print(f"  Version: [cyan]{self.version}[/cyan]")
        self.print(f"  Description: [cyan]{self.description}[/cyan]")
        self.print(f"  Author: [cyan]{self.author}[/cyan]")
        self.print(f"  License: [cyan]{self.license}[/cyan]")
        self.print(f"  Target: [cyan]{self.target.value}[/cyan]") # type: ignore
        if self.include_mode:
            self.print(f"  Include Mode: [cyan]{self.include_mode.value}[/cyan]")
        if self.entrypoints:
            self.print(f"  Entrypoints: [cyan]{', '.join(self.entrypoints)}[/cyan]")
        self.print(f"  Location: [cyan]{self.project_root}[/cyan]")
        self.print(f"  Initialize Git: [cyan]{'Yes' if self.git_init else 'No'}[/cyan]")
        self.print("[bold magenta]-----------------------------[/bold magenta]")

        return Confirm.ask("Proceed with project creation?", default=True)

    def create_artifacts(self) -> None:
        """Create all project artifacts (directories, files, git repo)."""
        project_root: Path = self.project_root  # type: ignore

        project_root.mkdir(parents=True, exist_ok=True)
        self.print(f"[green]Created project directory: {project_root}[/green]")

        # Create .gitignore
        gitignore_content = self.get_gitignore_content()
        with open(project_root / ".gitignore", "w") as f:
            f.write(gitignore_content)
        self.print(f"[green]Created {project_root / '.gitignore'}[/green]")

        # Create knitpkg/ directories
        knitpkg_dir = project_root / "knitpkg"
        knitpkg_dir.mkdir(exist_ok=True)


        if self.project_type == MQLProjectType.PACKAGE:
            (knitpkg_dir / "autocomplete").mkdir(exist_ok=True)
            (knitpkg_dir / "include" / self.organization).mkdir(exist_ok=True, parents=True) # type: ignore
        else:
            if self.include_mode == IncludeMode.FLAT:
                (knitpkg_dir / "flat").mkdir(exist_ok=True)
            else:
                (knitpkg_dir / "include").mkdir(exist_ok=True)


        self.print(f"[green]Created KnitPkg internal directories under {knitpkg_dir}[/green]")

        # Create project-specific files based on type
        if self.project_type == MQLProjectType.PACKAGE:
            self.create_package_files()
        elif self.project_type == MQLProjectType.EXPERT:
            self.create_expert_files()
        elif self.project_type == MQLProjectType.INDICATOR:
            self.create_indicator_files()
        elif self.project_type == MQLProjectType.SCRIPT:
            self.create_script_files()
        elif self.project_type == MQLProjectType.LIBRARY:
            self.create_library_files()
        elif self.project_type == MQLProjectType.SERVICE:
            self.create_service_files()

        # Create knitpkg.yaml
        manifest_data = {
            "target": self.target.value, # type: ignore
            "type": self.project_type.value, # type: ignore
            "organization": self.organization,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
        }
        if self.keywords:
            manifest_data["keywords"] = self.keywords
        if self.include_mode:
            manifest_data["include_mode"] = self.include_mode.value
        if self.entrypoints:
            manifest_data["entrypoints"] = self.entrypoints

        manifest_data["compile"] = self.compile

        manifest_data["dependencies"] = {}

        with open(project_root / "knitpkg.yaml", "w") as f:
            yaml.dump(manifest_data, f, sort_keys=False)
        self.print(f"[green]Created {project_root / 'knitpkg.yaml'}[/green]")

        # Initialize Git repository using GitPython
        if self.git_init:
            try:
                Repo.init(project_root)
                self.print(
                    f"[green]Initialized Git repository in {project_root}[/green]"
                )
            except Exception as e:
                self.print(f"[red]✗ Error initializing Git[/red]: {e}")

        if self.enable_telemetry:
            settings = Settings(project_root)
            settings.save_if_changed("telemetry", True)

        self.print(f"\n🎉[bold green] Project '{self.name}' created successfully in {project_root}[/bold green]")
        self.print("[bold blue]Next steps:[/bold blue]")
        self.print(f"  cd {project_root}")
        self.print(f"  Read GETTING_STARTED")
        self.print(f"  Start coding your {self.project_type.value}!") # type: ignore

    def run(
        self,
        dry_run: bool,
        project_type: Optional[MQLProjectType],
        name: Optional[str],
        organization: Optional[str],
        version: Optional[str],
        description: Optional[str],
        keywords: Optional[str],
        author: Optional[str],
        license: Optional[str],
        target: Optional[Target],
        include_mode: Optional[IncludeMode],
        entrypoints_str: Optional[str],
        location: Optional[Path],
        git_init: Optional[bool],
        enable_telemetry: Optional[bool],
        indicator_input_type: Optional[IndicatorInputType] = None,
    ) -> None:
        """Execute the project initialization workflow."""
        self.dry_run = dry_run
        self.print("\n[bold blue]🚀 Initializing a new KnitPkg project...[/bold blue]")

        # Execute steps
        self.select_target(target)
        self.select_project_type(project_type)
        self.prompt_project_name(name)
        self.determine_project_location(location)
        self.handle_existing_directory()
        self.prompt_organization(organization)
        self.prompt_version(version)
        self.prompt_description(description)
        self.prompt_keywords(keywords)
        self.prompt_author(author)
        self.prompt_license(license)
        self.select_indicator_input_type(indicator_input_type)
        self.select_include_mode_and_entrypoints(include_mode, entrypoints_str)
        self.prompt_git_init(git_init)
        self.prompt_enable_telemetry(enable_telemetry)
        
        # Confirmation
        if not self.display_summary_and_confirm():
            raise KeyboardInterrupt()

        if self.dry_run:
            self.print("\n[bold yellow]Dry run complete. No changes were made.[/bold yellow]")
            return

        # Create artifacts
        self.create_artifacts()
