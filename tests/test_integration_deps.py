# No seu test_integration_deps.py
from helix.commands.install import HelixInstaller
from helix.commands.autocomplete import AutocompleteGenerator
from pathlib import Path
import pytest

# --- MockConsole para capturar a saída ---
class MockConsole:
    """
    A mock console that captures all output for testing purposes.
    Simulates the rich.Console interface.
    """
    def __init__(self):
        self.logs = []
        self.prints = []
        self.warnings = []
        self.errors = []
        self.status_messages = []
        self.last_status_message = None
        self.is_quiet = False # Adicionado para simular o comportamento de quiet mode

    def log(self, *objects, **kwargs):
        self.logs.append(" ".join(map(str, objects)))

    def print(self, *objects, **kwargs):
        self.prints.append(" ".join(map(str, objects)))

    def warn(self, message):
        self.warnings.append(message)

    def error(self, message):
        self.errors.append(message)

    def rule(self, title=None, **kwargs):
        self.logs.append(f"--- RULE: {title} ---")

    def status(self, status_text):
        # Simulate status context manager
        class MockStatus:
            def __enter__(s_self):
                self.status_messages.append(f"START STATUS: {status_text}")
                self.last_status_message = status_text
                return s_self
            def __exit__(s_self, exc_type, exc_val, exc_tb):
                self.status_messages.append(f"END STATUS: {status_text}")
                self.last_status_message = None
        return MockStatus()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    # Métodos adicionais que podem ser chamados pela rich.Console
    @property
    def width(self):
        return 80 # Retorna uma largura padrão para evitar erros de layout

    @property
    def is_terminal(self):
        return True # Simula que está rodando em um terminal

    def record_traceback(self, *args, **kwargs):
        self.errors.append("TRACEBACK RECORDED (mocked)")

    def get_console_width(self):
        return self.width

    def get_console_height(self):
        return 25 # Altura padrão

    def get_encoding(self):
        return 'utf-8' # Encoding padrão para o mock

    def get_buffer(self):
        return [] # Retorna um buffer vazio para simular a rich.Console

    def set_quiet(self, quiet: bool):
        self.is_quiet = quiet

# --- Conteúdo dos arquivos MQL5 para cada projeto ---

# Level 4 (Leaf)
DEP_E_MQH_CONTENT = """
//+------------------------------------------------------------------+
//|                                                           DepE.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency E: Leaf package.                                     |
//|                                                                  |
//+------------------------------------------------------------------+
string GetDepEValue() { return "DepE_Value"; }
"""

DEP_E_YAML_CONTENT = """
name: DepE
version: 1.0.0
type: package
target: MQL5
description: Dependency E package
"""

# Level 3
DEP_D_MQH_CONTENT = """

//+------------------------------------------------------------------+
//|                                                           DepD.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency D: Depends on DepA and DepB.                         |
//|                                                                  |
//+------------------------------------------------------------------+
#include "../autocomplete/autocomplete.mqh" /* @helix:replace-with "helix/include/DepA.mqh" */

/* @helix:include "helix/include/DepB/DepB.mqh" */

string GetDepDValue() { return "DepD_Value(" + GetDepAValue() + "," + GetDepBValue() + ")"; }
"""

DEP_D_INCLUDE_MODE_RESOLVED_CONTENT = """

//+------------------------------------------------------------------+
//|                                                           DepD.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency D: Depends on DepA and DepB.                         |
//|                                                                  |
//+------------------------------------------------------------------+
#include "DepA.mqh" /*** ← dependence resolved by Helix. Original include: "../autocomplete/autocomplete.mqh" ***/

#include "DepB/DepB.mqh" /*** ← dependence added by Helix ***/

string GetDepDValue() { return "DepD_Value(" + GetDepAValue() + "," + GetDepBValue() + ")"; }
"""

DEP_D_MQ5_CONTENT = """
//+------------------------------------------------------------------+
//|                                                    UnitTests.mq5 |
//|                                                   Douglas Rechia |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Douglas Rechia"
#property link      "https://www.mql5.com"
#property version   "1.00"

#include "helix/include/DepD.mqh"
//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
   Print(GetDepDValue());
  }
//+------------------------------------------------------------------+
"""

DEP_D_YAML_CONTENT = """

name: DepD
version: 1.0.0
type: package
target: MQL5
description: Dependency D package
dependencies:
  DepA: ../DepA
  DepB: ../DepB

compile:
  - DepD.mq5
"""

DEP_C_MQH_CONTENT = """
//+------------------------------------------------------------------+
//|                                                           DepC.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency C: Depends on DepA.                                  |
//|                                                                  |
//+------------------------------------------------------------------+
#include "../autocomplete/autocomplete.mqh" 
 
/* @helix:include "helix/include/DepA.mqh" */

string GetDepCValue() { return "DepC_Value(" + GetDepAValue() + ")"; }
"""

DEP_C_INCLUDE_MODE_RESOLVED_CONTENT = """
//+------------------------------------------------------------------+
//|                                                           DepC.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency C: Depends on DepA.                                  |
//|                                                                  |
//+------------------------------------------------------------------+
// #include "../autocomplete/autocomplete.mqh"  /*** ← disabled by Helix install (dev helper) ***/
 
#include "DepA.mqh" /*** ← dependence added by Helix ***/

string GetDepCValue() { return "DepC_Value(" + GetDepAValue() + ")"; }
"""

DEP_C_YAML_CONTENT = """
name: DepC
version: 1.0.0
type: package
target: MQL5
description: Dependency C package
dependencies:
  DepA: ../DepA
"""

# Level 2
DEP_B_MQH_CONTENT = """
//+------------------------------------------------------------------+
//|                                                           DepB.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency B: Simple package.                                   |
//|                                                                  |
//+------------------------------------------------------------------+
string GetDepBValue() { return "DepB_Value"; }
"""

DEP_B_YAML_CONTENT = """
name: DepB
version: 1.0.0
type: package
target: MQL5
description: Dependency B package
"""

DEP_A_MQH_CONTENT = """
//+------------------------------------------------------------------+
//|                                                           DepA.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Dependency A: Simple package.                                   |
//|                                                                  |
//+------------------------------------------------------------------+
string GetDepAValue() { return "DepA_Value"; }
"""

DEP_A_YAML_CONTENT = """
name: DepA
version: 1.0.0
type: package
target: MQL5
description: Dependency A package
"""

# Level 1 (Expert)
EXPERT_TEST_MQH_CONTENT = """
//+------------------------------------------------------------------+
//|                                                  ExpertTest.mqh |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  ExpertTest: Main Expert Advisor header.                         |
//|                                                                  |
//+------------------------------------------------------------------+
#include "helix/include/DepC.mqh"
#include "helix/include/DepD.mqh"
#include "helix/include/DepE.mqh"

string GetExpertTestValue() {
    return "ExpertTest started! " + GetDepCValue() + " " + GetDepDValue() + " " + GetDepEValue();
}
"""

EXPERT_TEST_MQ5_CONTENT_FLAT_MODE = """
//+------------------------------------------------------------------+
//|                                                  ExpertTest.mq5 |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  ExpertTest: Main Expert Advisor file.                           |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Douglas Rechia"
#property link      "https://www.helix-mt.com"
#property version   "1.00"
#property description "Integration Test Expert"

#include "helix/flat/ExpertTest_flat.mqh" // This will be replaced by the flat include

int OnInit()
{
    Print(GetExpertTestValue());
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("ExpertTest deinitialized.");
}

void OnTick()
{
    // Simple tick logic
}
"""

EXPERT_TEST_MQ5_CONTENT_INCLUDE_MODE = """
//+------------------------------------------------------------------+
//|                                                  ExpertTest.mq5 |
//|                                                                  |
//|                    Helix for MetaTrader                          |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  ExpertTest: Main Expert Advisor file.                           |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Douglas Rechia"
#property link      "https://www.helix-mt.com"
#property version   "1.00"
#property description "Integration Test Expert"

#include "ExpertTest.mqh" 

int OnInit()
{
    Print(GetExpertTestValue());
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    Print("ExpertTest deinitialized.");
}

void OnTick()
{
    // Simple tick logic
}
"""

EXPERT_TEST_YAML_CONTENT_1 = """
name: ExpertTest
version: 1.0.0
type: expert
target: MQL5
description: Expert Advisor Test Project
include_mode: flat
entrypoints:
  - ExpertTest.mqh
dependencies:
  DepA: ../DepA # Local dependency
  DepB: ../DepB # Local dependency
  DepC: ../DepC # Local dependency
  DepD: ../DepD # Local dependency
  DepE: ../DepE # Local dependency
"""

EXPERT_TEST_YAML_CONTENT_2 = """
name: ExpertTest
version: 1.0.0
type: expert
target: MQL5
description: Expert Advisor Test Project
include_mode: flat
entrypoints:
  - ExpertTest.mqh
dependencies:
  DepC: ../DepC # Local dependency
  DepD: ../DepD # Local dependency
  DepE: ../DepE # Local dependency
"""

EXPERT_TEST_YAML_CONTENT_3 = """
name: ExpertTest
version: 1.0.0
type: expert
target: MQL5
description: Expert Advisor Test Project
include_mode: include
compile:
  - ExpertTest.mq5
dependencies:
  DepC: ../DepC # Local dependency
  DepD: ../DepD # Local dependency
  DepE: ../DepE # Local dependency
"""

# --- Helper function to create project files ---
def create_project_files(root_dir: Path, project_name: str, mqh_path: str, mqh_content: str, yaml_content: str, mq5_path: str = None, mq5_content: str = None):
    project_path = root_dir / project_name
    project_path.mkdir(parents=True, exist_ok=True)

    # Create helix.yaml
    with open(project_path / "helix.yaml", "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # Create .mqh file
    mqh_file_path = project_path / mqh_path / f"{project_name}.mqh"
    mqh_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mqh_file_path, "w", encoding="utf-8") as f:
        f.write(mqh_content)

    # Create .mq5 file if provided (only for ExpertTest)
    if mq5_path and mq5_content:
        mq5_file_path = project_path / mq5_path / f"{project_name}.mq5"
        mq5_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mq5_file_path, "w", encoding="utf-8") as f:
            f.write(mq5_content)

def create_test_dir_with_all_projects(tmp_path: Path, expert_test_yaml_content: str, expert_test_mq5_content: str) -> str:
    """
    Tests the resolution of a complex dependency tree (4 levels with merge)
    and the correct generation of the flat include file by instantiating HelixInstaller directly.
    """
    root_dir = tmp_path / "helix_test_root"
    print('='*50)
    print(f"===========complex_dependency_tree_and_flat_include root dir: {root_dir}")
    print('='*50)
    root_dir.mkdir()

    # Create dependency projects (Level 4)
    create_project_files(root_dir, "DepE", "helix/include", DEP_E_MQH_CONTENT, DEP_E_YAML_CONTENT)
    # Create dependency projects (Level 3)
    create_project_files(root_dir, "DepC", "helix/include", DEP_C_MQH_CONTENT, DEP_C_YAML_CONTENT)
    create_project_files(root_dir, "DepD", "helix/include", DEP_D_MQH_CONTENT, DEP_D_YAML_CONTENT, ".", DEP_D_MQ5_CONTENT)
    # Create dependency projects (Level 2)
    create_project_files(root_dir, "DepA", "helix/include", DEP_A_MQH_CONTENT, DEP_A_YAML_CONTENT)
    create_project_files(root_dir, "DepB", "helix/include/DepB", DEP_B_MQH_CONTENT, DEP_B_YAML_CONTENT)
    # Create Expert project (Level 1)
    create_project_files(root_dir, "ExpertTest", ".", EXPERT_TEST_MQH_CONTENT, expert_test_yaml_content, ".", expert_test_mq5_content)

    expert_test_path = root_dir / "ExpertTest"

    # Instantiate MockConsole
    mock_console = MockConsole()

    # Instantiate InstallCommand and call install directly
    # The InstallCommand expects a Console instance
    installer = HelixInstaller(console=mock_console, project_dir=expert_test_path)

    print(f"\nRunning HelixInstaller.install for {expert_test_path}")
    try:
        # The install method expects the path to the project root
        installer.install(locked_mode=False, show_tree=True)

        # Print captured output for debugging if needed
        print("\n--- Captured Console Logs ---")
        for log in mock_console.logs:
            print(log)
        if mock_console.warnings:
            print("\n--- Captured Console Warnings ---")
            for warn in mock_console.warnings:
                print(warn)
        if mock_console.errors:
            print("\n--- Captured Console Errors ---")
            for error in mock_console.errors:
                print(error)

    except Exception as e:
        # If an exception occurs within HelixInstaller, print captured output
        print(f"\n--- HelixInstaller FAILED with an exception: {e} ---")
        print("\n--- Captured Console Logs (before exception) ---")
        for log in mock_console.logs:
            print(log)
        if mock_console.warnings:
            print("\n--- Captured Console Warnings (before exception) ---")
            for warn in mock_console.warnings:
                print(warn)
        if mock_console.errors:
            print("\n--- Captured Console Errors (before exception) ---")
            for error in mock_console.errors:
                print(error)
        pytest.fail(f"HelixInstaller.install failed: {e}")

    return root_dir


def check_flat_content(root_dir: Path):
    
    expert_test_path = root_dir / "ExpertTest"

    # Verify if the flat include file was created
    flat_include_path = expert_test_path / "helix" / "flat" / "ExpertTest_flat.mqh"
    assert flat_include_path.exists(), f"Flat include file not found: {flat_include_path}"

    # Verify the content of the flat include file
    with open(flat_include_path, "r", encoding="utf-8") as f:
        flat_content = f.read()

    print(f"\nContent of {flat_include_path}:\n{flat_content}")

    # Assertions to check if dependencies were included and in correct order (or at least present)
    # The exact order might vary depending on Helix implementation, but all must be present.
    assert "//+------------------------------------------------------------------+\n//|                                                           DepE.mqh |" in flat_content
    assert "//+------------------------------------------------------------------+\n//|                                                           DepC.mqh |" in flat_content
    assert "//+------------------------------------------------------------------+\n//|                                                           DepD.mqh |" in flat_content
    assert "//+------------------------------------------------------------------+\n//|                                                           DepA.mqh |" in flat_content
    assert "//+------------------------------------------------------------------+\n//|                                                           DepB.mqh |" in flat_content
    assert "//+------------------------------------------------------------------+\n//|                                                  ExpertTest.mqh |" in flat_content

    # Verify if dependency functions are present (indicating content concatenation)
    assert "string GetDepEValue()" in flat_content
    assert "string GetDepDValue()" in flat_content
    assert "string GetDepCValue()" in flat_content
    assert "string GetDepAValue()" in flat_content
    assert "string GetDepBValue()" in flat_content

    # Verify inclusion order to ensure dependencies are resolved before their dependents
    # This is crucial for MQL5 compilation.
    assert flat_content.find("GetDepAValue()") < flat_content.find("GetDepCValue()")
    assert flat_content.find("GetDepAValue()") < flat_content.find("GetDepDValue()")
    assert flat_content.find("GetDepBValue()") < flat_content.find("GetDepDValue()")
    assert flat_content.find("GetDepCValue()") < flat_content.find("GetExpertTestValue()")
    assert flat_content.find("GetDepDValue()") < flat_content.find("GetExpertTestValue()")
    assert flat_content.find("GetDepEValue()") < flat_content.find("GetExpertTestValue()")

    print("\nFlat include file created and verified successfully using MockConsole!")

# --- Pytest Integration Test ---
def test_complex_dependency_tree_and_flat_include_expert_yaml1(tmp_path: Path):
    check_flat_content(create_test_dir_with_all_projects(tmp_path, EXPERT_TEST_YAML_CONTENT_1, EXPERT_TEST_MQ5_CONTENT_FLAT_MODE))

def test_complex_dependency_tree_and_flat_include_expert_yaml2(tmp_path: Path):
    check_flat_content(create_test_dir_with_all_projects(tmp_path, EXPERT_TEST_YAML_CONTENT_2, EXPERT_TEST_MQ5_CONTENT_FLAT_MODE))

def test_autocomplete(tmp_path: Path):
    root_dir = tmp_path / "helix_test_root"
    print('='*50)
    print(f"===========test_autocomplete root dir: {root_dir}")
    print('='*50)
    root_dir.mkdir()

    create_project_files(root_dir, "DepD", "helix/include", DEP_D_MQH_CONTENT, DEP_D_YAML_CONTENT, ".", DEP_D_MQ5_CONTENT)
    create_project_files(root_dir, "DepA", "helix/include", DEP_A_MQH_CONTENT, DEP_A_YAML_CONTENT)
    create_project_files(root_dir, "DepB", "helix/include", DEP_B_MQH_CONTENT, DEP_B_YAML_CONTENT)

    depd_test_path = root_dir / "DepD"

    # Instantiate MockConsole
    mock_console = MockConsole()

    # Instantiate AutocompleteGenerator and call generate directly
    # The AutocompleteGenerator expects a Console instance
    generator = AutocompleteGenerator(mock_console, depd_test_path)

    print(f"\nRunning AutocompleteGenerator.generate for {depd_test_path}")
    try:
        # Generates helix/autocomplete/autocomplete.mqh
        generator.generate()

        # Print captured output for debugging if needed
        print("\n--- Captured Console Logs ---")
        for log in mock_console.logs:
            print(log)
        if mock_console.warnings:
            print("\n--- Captured Console Warnings ---")
            for warn in mock_console.warnings:
                print(warn)
        if mock_console.errors:
            print("\n--- Captured Console Errors ---")
            for error in mock_console.errors:
                print(error)

    except Exception as e:
        # If an exception occurs within HelixInstaller, print captured output
        print(f"\n--- AutocompleteGenerator FAILED with an exception: {e} ---")
        print("\n--- Captured Console Logs (before exception) ---")
        for log in mock_console.logs:
            print(log)
        if mock_console.warnings:
            print("\n--- Captured Console Warnings (before exception) ---")
            for warn in mock_console.warnings:
                print(warn)
        if mock_console.errors:
            print("\n--- Captured Console Errors (before exception) ---")
            for error in mock_console.errors:
                print(error)
        pytest.fail(f"AutocompleteGenerator.install failed: {e}")

    # Verify if autocomplete.mqh include file was created
    autocomplete_path = depd_test_path / "helix" / "autocomplete" / "autocomplete.mqh"
    assert autocomplete_path.exists(), f"autocomplete.mqh file not found: {autocomplete_path}"

    # Verify the content of the autocomplete include file
    with open(autocomplete_path, "r", encoding="utf-8") as f:
        autocomplete_content = f.read()

    print(f"\nContent of {autocomplete_path}:\n{autocomplete_content}")

    # Assertions to check if DepA.mqh and DepB.mqh are included
    assert "//+------------------------------------------------------------------+\n//|                                          autocomplete.mqh        |" in autocomplete_content
    
    assert '#include "../../../DepA/helix/include/DepA.mqh"' in autocomplete_content
    assert '#include "../../../DepB/helix/include/DepB.mqh"' in autocomplete_content

    print("\nAutocomplete include file created and verified successfully using MockConsole!")

def check_include_mode(root_dir: Path):
    
    expert_test_path = root_dir / "ExpertTest"
    expert_test_includes_path = expert_test_path / "helix" / "include"

    # Verify if DepA.mqh include file was created with expected content
    depa_path = expert_test_includes_path / "DepA.mqh"
    assert depa_path.exists(), f"DepA.mqh include file not found: {depa_path}"

    with open(depa_path, "r", encoding="utf-8") as f:
        depa_content = f.read()

    assert depa_content == DEP_A_MQH_CONTENT

    # Verify if DepB.mqh include file was created with expected content
    depb_path = expert_test_includes_path / "DepB" / "DepB.mqh"
    assert depb_path.exists(), f"DepB.mqh include file not found: {depb_path}"

    with open(depb_path, "r", encoding="utf-8") as f:
        depb_content = f.read()

    assert depb_content == DEP_B_MQH_CONTENT

    # Verify if DepC.mqh include file was created with expected content
    depc_path = expert_test_includes_path / "DepC.mqh"
    assert depc_path.exists(), f"DepC.mqh include file not found: {depc_path}"

    with open(depc_path, "r", encoding="utf-8") as f:
        depc_content = f.read()

    assert depc_content == DEP_C_INCLUDE_MODE_RESOLVED_CONTENT

    # Verify if DepD.mqh include file was created with expected content
    depd_path = expert_test_includes_path / "DepD.mqh"
    assert depd_path.exists(), f"DepD.mqh include file not found: {depd_path}"

    with open(depd_path, "r", encoding="utf-8") as f:
        depd_content = f.read()

    assert depd_content == DEP_D_INCLUDE_MODE_RESOLVED_CONTENT

    # Verify if DepE.mqh include file was created with expected content
    depe_path = expert_test_includes_path / "DepE.mqh"
    assert depe_path.exists(), f"DepE.mqh include file not found: {depe_path}"

    with open(depe_path, "r", encoding="utf-8") as f:
        depe_content = f.read()

    assert depe_content == DEP_E_MQH_CONTENT

def test_helix_directives_and_include_mode(tmp_path: Path):
    check_include_mode(create_test_dir_with_all_projects(tmp_path, EXPERT_TEST_YAML_CONTENT_3, EXPERT_TEST_MQ5_CONTENT_INCLUDE_MODE))
