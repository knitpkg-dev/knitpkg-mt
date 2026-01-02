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
from helix.mql.mql_paths import find_mql_paths


# .gitignore content templates
GITIGNORE_PACKAGE = """
.helix/
helix/autocomplete/
helix/flat/

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
GETTING_STARTED
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
GETTING_STARTED
""".strip()

# MQL5/MQL4 source code templates
TEMPLATE_PACKAGE_INCLUDE = """//+------------------------------------------------------------------+
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
// 2. Include directives. For headers with external dependencies, 
// specify the file path relative to helix/include directory, see an 
// example below (inactive due to the double slashes at the begin of
// the line). When this project is installed as a dependency in another
// project, Helix automatically resolves the includes based on these 
// directives. See documentation for details.
//
// /* @helix:include "Path/To/Dependency/Header.mqh" */
//--------------------------------------------------------------------

// Add your package code here and rename the file as needed.
"""

TEMPLATE_PACKAGE_UNITTESTS = """//+------------------------------------------------------------------+
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
#include "{{header_path}}"

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

TEMPLATE_PACKAGE_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH HELIX PACKAGE DEVELOPMENT
================================================================================

This file should be deleted after reading. It is excluded from version control
and serves only as a quick reference during initial setup.

================================================================================
                              PACKAGE STRUCTURE
================================================================================

Export headers exclusively in the helix/include directory. Headers located in
other paths will be ignored during package resolution and compilation.

A sample header file has been created at:

  {{header_path}}

Use it as a foundation for developing your own headers. Additional headers can
be created in the same directory or in subdirectories within this location.

================================================================================
                            UNIT TESTING GUIDELINES
================================================================================

Place unit tests in the tests directory. A basic unit test skeleton has been
created to help you begin development at {{unit_test_path}}

Refer to the test file for examples on how to structure and execute tests for
your package components.

================================================================================
                              NEXT STEPS
================================================================================

1. If your package has dependencies on other packages:
   - Add them to the dependencies section in helix.yaml
   - Run 'helix autocomplete' to resolve dependencies and IntelliSense support

2. Review the sample header in {{header_path}}

3. Develop your package headers following the same structure

4. Add unit tests in the tests directory

5. Delete this file when setup is complete

For detailed documentation, visit: https://helix.dev/docs

================================================================================
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

{{expert_include}}

/***** Add your code and rename the file as needed. *****/

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
TEMPLATE_EXPERT_ENTRYPOINT_INCLUDE = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+

//------------------------------------------------------------------
// Add here your includes from the resolved dependencies. 
//------------------------------------------------------------------

/* @helix:include "Path/To/Resolved/Header.mqh" */
"""

TEMPLATE_EXPERT_ENTRYPOINT_MQL = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+

//------------------------------------------------------------------
// Add here your includes from the resolved dependencies. 
//------------------------------------------------------------------

/* @helix:include "Path/To/Resolved/Header.mqh" */

// ***** Add your code here. *****
"""

TEMPLATE_EXPERT_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH HELIX EXPERT ADVISOR DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

An Expert Advisor project has the following structure (generated by
`helix-mt init --type expert`):

  helix/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <ProjectName>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  helix.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), Helix will generate a 
`<ProjectName>_flat.mqh` file in `helix/flat/` that contains all resolved 
dependencies - this file is the one that should be included in your Expert. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `helix/include/` (mirroring the 
package layout) once you run `helix-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `helix/include/` directory, it is automatically generated by Helix.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit helix.yaml manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    '@helix.dev/helix-mt-bar': https://forge.mql5.io/DouglasRechia/helix-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<ProjectName>.mqh` at this point and add the headers you'll 
  be using in your EA by means of Helix directives. Skip this step otherwise.

  Run the following Helix command:

      helix-mt install

  The command reads all the dependencies from `helix.yaml`, downloads the 
  required packages and resolves all `@helix:include` directives. After the 
  first install you will see either `helix/flat/` directory containing the 
  flattened headers or `helix/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `helix.yaml`.

* Update a dependency

  helix-mt install   # re-runs the resolver and updates `helix/flat` or `helix/include`

* Remove a dependency

  Delete the entry from the `dependencies` map in `helix.yaml` and run
  `helix-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if your're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the external headers Helix
   just installed in `helix/include` by means of standard MQL #include directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal `#include`
   directives.

================================================================================
                         COMPILING YOUR EXPERT
================================================================================

1. Run the compiler:

   helix-mt compile

   The compiler will compile the generated flat file
   helix/flat/<ProjectName>_flat.mq5 (if applicable) and then the
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file in the MetaTrader `Experts` folder. Attach it to a chart and
   start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Version control** - commit the `src/` directory and `helix.yaml`. Delete
   the `GETTING_STARTED` (once you delete it, remove it from the `.gitignore`
   entry if you want). The `helix/flat` and `helix/include` directories are 
   ignored by default.

2. **Documentation** - update the `description` field in `helix.yaml` and
   consider adding a `README.md` with usage instructions for your EA.

4. **Publish** - when you are ready, push the repository to a Git host.

For the full Helix documentation visit: https://helix.dev/docs

================================================================================
"""

TEMPLATE_INDICATOR_BARS = """//+------------------------------------------------------------------+
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

TEMPLATE_INDICATOR_SERIES = """//+------------------------------------------------------------------+
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

    def format_mql_header(txt: str) -> str:
        header_dashes_len = len("//+------------------------------------------------------------------+")
        return f"{' '*(header_dashes_len-len(txt)-6)}{txt} |"

    def create_package_files(self) -> None:
        """Create files for package project type."""
        org_dir = self.organization if self.organization else "."

        # Create Header.mqh
        header_dir = self.project_root / "helix" / "include" / org_dir / self.name
        header_dir.mkdir(parents=True, exist_ok=True)
        header_path = header_dir / "Header.mqh"

        header_content = self.render_template(TEMPLATE_PACKAGE_INCLUDE, {
            "header_file_name": ProjectInitializer.format_mql_header("Header.mqh"),
            "header_name": ProjectInitializer.format_mql_header(f"Package {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "autocomplete_path_prefix": "../../..",
        })
        header_path.write_text(header_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {header_path.relative_to(self.project_root)}[/green]")

        # Create UnitTests
        tests_dir = self.project_root / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        unit_file_name = "UnitTests.mq5" if self.target == Target.MQL5 else "UnitTests.mq4"
        unit_path = tests_dir / unit_file_name
        self.compile.append("tests/UnitTests.mq5")

        unit_content = self.render_template(TEMPLATE_PACKAGE_UNITTESTS, {
            "header_file_name": ProjectInitializer.format_mql_header(unit_file_name),
            "header_name": ProjectInitializer.format_mql_header(f"Unit Tests for Package {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "name": self.name,
            "organization": self.organization if self.organization else "No organization",
            "version": self.version,
            "author": self.author,
            "license": self.license,
            "header_path": f"../{header_path.relative_to(self.project_root).as_posix()}",
        })
        unit_path.write_text(unit_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {unit_path.relative_to(self.project_root)}[/green]")

        # Create GETTING_STARTED
        getting_started_content = self.render_template(TEMPLATE_PACKAGE_GETTING_STARTED, {
            "header_path": header_path.relative_to(self.project_root).as_posix(),
            "unit_test_path": "tests/UnitTests.mq5"
        })
        getting_started_path = self.project_root / "GETTING_STARTED"
        getting_started_path.write_text(getting_started_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {getting_started_path.relative_to(self.project_root)}[/green]")

    def create_expert_files(self) -> None:
        """Create files for expert project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        expert_include = []
        if self.include_mode == IncludeMode.FLAT:
            for entrypoint_path in self.entrypoints:
                entrypoint_file_name = Path(entrypoint_path).name
                entrypoint_flattened_name = entrypoint_file_name[:len(entrypoint_file_name)-4] + "_flat" + entrypoint_file_name[len(entrypoint_file_name)-4:]
                    
                entrypoint_content = self.render_template(
                    TEMPLATE_EXPERT_ENTRYPOINT_INCLUDE if entrypoint_file_name.lower().endswith(".mqh") else TEMPLATE_EXPERT_ENTRYPOINT_MQL, {
                    "header_file_name": ProjectInitializer.format_mql_header(entrypoint_file_name),
                    "header_name": ProjectInitializer.format_mql_header(f"Flattened file: {entrypoint_flattened_name}"),
                    "header_organization": ProjectInitializer.format_mql_header(self.organization),
                })

                (self.project_root / entrypoint_path).write_text(entrypoint_content.strip() + "\n", encoding="utf-8")

                if entrypoint_file_name.lower().endswith(".mqh"):
                    expert_include.append(f'#include "../helix/flat/{entrypoint_flattened_name}"')

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        file_name = f"{self.name}{file_ext}"
        expert_path = src_dir / file_name

        expert_content = self.render_template(TEMPLATE_EXPERT, {
            "header_file_name": ProjectInitializer.format_mql_header(file_name),
            "header_name": ProjectInitializer.format_mql_header(f"Expert Advisor {self.name}"),
            "header_organization": ProjectInitializer.format_mql_header(f"Organization: {self.organization}" if self.organization else "No organization"),
            "version": self.version,
            "description": self.description,
            "organization": self.organization if self.organization else "No organization",
            "author": self.author,
            "license": self.license,
            "expert_include": "\n".join(expert_include) if expert_include else '',
        })

        expert_path.write_text(expert_content.strip() + "\n", encoding="utf-8")

        self.compile.append(f"src/{file_name}")

        self.console.print(f"[green]Created {expert_path.relative_to(self.project_root)}[/green]")

        # Create GETTING_STARTED
        getting_started_content = self.render_template(TEMPLATE_EXPERT_GETTING_STARTED)
        getting_started_path = self.project_root / "GETTING_STARTED"
        getting_started_path.write_text(getting_started_content.strip() + "\n", encoding="utf-8")
        self.console.print(f"[green]Created {getting_started_path.relative_to(self.project_root)}[/green]")


    def create_indicator_files(self) -> None:
        """Create files for indicator project type."""
        src_dir = self.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        file_ext = ".mq5" if self.target == Target.MQL5 else ".mq4"
        indicator_path = src_dir / f"{self.name}{file_ext}"

        template = TEMPLATE_INDICATOR_BARS if self.indicator_input_type == IndicatorInputType.OHLC else TEMPLATE_INDICATOR_SERIES
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
            license = Prompt.ask("License identifier", default="MIT")
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
                mql_ext = '.mq5' if self.target == Target.MQL5 else '.mq4'

                entrypoints_raw = []
                if entrypoints_str is None:
                    while True:
                        ep_input = Prompt.ask(
                            "Entrypoint files (comma-separated, e.g., MyHeader.mqh, Another.mqh)",
                            default=f"{self.name}.mqh",
                        )
                        entrypoints_raw = [ep.strip() for ep in ep_input.split(",") if ep.strip()]
                        if not entrypoints_raw:
                            self.console.print(
                                "[red]Entrypoints cannot be empty when include_mode is 'flat'. Please provide at least one.[/red]"
                            )
                            continue
                        if not all(ep.lower().endswith(".mqh") or ep.lower().endswith(mql_ext) for ep in entrypoints_raw):
                            self.console.print(
                                f"[red]All entrypoints must end with '.mqh' or {mql_ext}.[/red]"
                            )
                            continue
                        break
                else:
                    entrypoints_raw = [ep.strip() for ep in entrypoints_str.split(",") if ep.strip()]
                    if not entrypoints_raw:
                        self.console.print(
                            "[red]Error: Entrypoints cannot be empty when include_mode is 'flat'.[/red]"
                        )
                        raise typer.Exit(code=1)
                    if not all(ep.lower().endswith(".mqh") or ep.lower().endswith(f'.{mql_ext}') for ep in entrypoints_raw):
                        self.console.print(
                            f"[red]All entrypoints must end with '.mqh' or {mql_ext}.[/red]"
                        )
                        raise typer.Exit(code=1)
                
                self.entrypoints = []
                for ep in entrypoints_raw:
                    ep_path = Path(ep)
                    if ep_path.root != 'src':
                        self.entrypoints.append(f'src/{ep}')
                    else:
                        self.entrypoints.append(ep)
                

    def determine_project_location(self, location: Path | None) -> None:
        """Determine project location."""
        if location is None:
            mql_paths = find_mql_paths(self.target)
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
                count = 0
                for item in existing_files:
                    if item.name == ".git":
                        continue
                    self.console.print(f"  - {item.name}{'/' if item.is_dir() else ''}")
                    count += 1
                    if count >= 5:
                        break

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
        if (self.project_root / ".git").is_dir():
            self.git_init = False
            return
        
        if git_init is None:
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

            # Create .gitignore
            gitignore_content = self.get_gitignore_content()
            with open(self.project_root / ".gitignore", "w") as f:
                f.write(gitignore_content)
            self.console.print(f"[green]Created {self.project_root / '.gitignore'}[/green]")

            # Create helix/ directories
            helix_dir = self.project_root / "helix"
            helix_dir.mkdir(exist_ok=True)


            if self.project_type == MQLProjectType.PACKAGE:
                (helix_dir / "autocomplete").mkdir(exist_ok=True)
                (helix_dir / "include" / self.organization).mkdir(exist_ok=True, parents=True)
            else:
                if self.include_mode == IncludeMode.FLAT:
                    (helix_dir / "flat").mkdir(exist_ok=True)
                else:
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
            self.console.print(f"  Read GETTING_STARTED")
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
        git_init: bool | None,
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
        git_init: bool = typer.Option(None, "--git-init", help="Initialize a Git repository."),
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
