# .gitignore content templates
GITIGNORE_PACKAGE = """
.knitpkg/
knitpkg/autocomplete/
knitpkg/flat/
bin/
target/

*.mqproj

**/*.ex5
**/*.ex4
**/*.log
GETTING_STARTED
""".strip()

GITIGNORE_DEFAULT = """
.knitpkg/
knitpkg/autocomplete/
knitpkg/flat/
knitpkg/include
bin/
target/

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
// For packages with dependencies, use the following KnitPkg features:
//
// 1. Autocomplete support for the Unit tests. Run `kp-mt autocomplete` 
// to generate this file and uncomment the include below:
//
// #include "{{autocomplete_path_prefix}}/autocomplete/autocomplete.mqh"
//
//
// 2. Include directives. For headers with external dependencies, 
// specify the file path relative to knitpkg/include directory, see an 
// example below (inactive due to the double slashes at the begin of
// the line, delimiters /* and */ are required). 
//
// /* @knitpkg:include "Path/To/Dependency/Header.mqh" */
//
// When this project is installed as a dependency in another
// project, KnitPkg automatically neutralizes the autocomplete include
// and resolves the others based on these directives. See 
// documentation for details.
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
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

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
                GETTING STARTED WITH KNITPKG PACKAGE DEVELOPMENT
================================================================================

This file should be deleted after reading. It is excluded from version control
and serves only as a quick reference during initial setup.

================================================================================
                              PACKAGE STRUCTURE
================================================================================

Export headers exclusively in the knitpkg/include directory. Headers located in
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
   - Add them to the dependencies section in knitpkg.yaml
   - Run 'kp-mt autocomplete' to resolve dependencies for the Unit tests and 
     IntelliSense support

2. Review the sample header in {{header_path}}

3. Develop your package headers following the same structure

4. Add unit tests in the tests directory

5. Delete this file when setup is complete

For detailed documentation, visit: https://knitpkg.dev/docs

================================================================================
"""

TEMPLATE_EXPERT = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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
TEMPLATE_ENTRYPOINT_MQH = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+

//--------------------------------------------------------------------
// In order to generate the flattened headers with KnitPkg, specify 
// the content of this file as a list of @knitpkg:include directives. 
// Each @knitpkg:include refers to an external header file path relative 
// to knitpkg/include directory, see an example below (inactive due to 
// the double slashes at the begin of the line). 
//
// /* @knitpkg:include "Path/To/Dependency/Header.mqh" */
//
// Run `kp-mt install` after you add your headers.
//--------------------------------------------------------------------

"""

TEMPLATE_ENTRYPOINT_MQL = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+

//--------------------------------------------------------------------
// In order to generate the flattened headers with KnitPkg, specify 
// the content of this file as a list of @knitpkg:include directives. 
// Each @knitpkg:include refers to an external header file path relative 
// to knitpkg/include directory, see an example below (inactive due to 
// the double slashes at the begin of the line). 
//
// /* @knitpkg:include "Path/To/Dependency/Header.mqh" */
//
// Run `kp-mt install` after you add your headers.
//--------------------------------------------------------------------

// ***** Add your code here. *****
"""

TEMPLATE_EXPERT_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH KNITPKG EXPERT ADVISOR DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

An Expert Advisor project has the following structure (generated by
`kp-mt init --type expert`):

  <ProjectName>/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <EntryPointN>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  knitpkg.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), `kp-mt install` will generate a 
flattened header named `<EntryPointN>_flat.mqh` in `knitpkg/flat/` for each 
entry point declared in `knitpkg.yaml`. Those are the files that should be 
included in your Expert. The flattened headers will contain all resolved 
dependencies based upon `@knitpkg:include` directives declared in
`src/<EntryPointN>.mqh`. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `knitpkg/include/` (mirroring the 
package layout) after you run `kp-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `knitpkg/include/` or `knitpkg/flat/` as they are generated automatically by 
KnitPkg.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit `knitpkg.yaml` manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    # others dependencies...
    '@knitpkg.dev/knitpkg-mt-bar': https://forge.mql5.io/DouglasRechia/knitpkg-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<EntryPointN>.mqh` at this point and add the headers you'll 
  be using in your EA by means of KnitPkg directives. Skip this step otherwise.

* Download and resolve dependencies: run the following KnitPkg command:

      kp-mt install

  The command reads all the dependencies from `knitpkg.yaml`, downloads the 
  required packages and resolves all `@knitpkg:include` directives. After the 
  first install you will see either `knitpkg/flat/` directory containing the 
  flattened headers or `knitpkg/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `knitpkg.yaml`.

* Update a dependency: in the case you need to update a dependency, just
  update the version in `knitpkg.yaml` and run `kp-mt install` again to
  re-run the resolver and update `knitpkg/flat` or `knitpkg/include`.

      kp-mt install 

* Remove a dependency

  Delete the entry from the `dependencies` map in `knitpkg.yaml` and run
  `kp-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if you're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the required external headers 
   KnitPkg just installed in `knitpkg/include`. Use the standard MQL #include 
   directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **(Optional) Add MQL Standard library includes**

   If you want to use MQL Standard library headers, add them with the
   regular MQL #include and angle brackets, for example:

       #include <Trade/SymbolInfo.mqh>

   NOTE: all the KnitPkg includes, no matter if it is a regular MQL `#include` or 
   `@knitpkg:include`, must use double quotes as the delimiter to the header
   path. Angle brackets are used with the MQL Standard library only.
   
4. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal MQL #include
   directives.

================================================================================
                         COMPILING YOUR EXPERT
================================================================================

1. Run the compiler:

   kp-mt compile

   The compiler will compile, if applicable, all the generated flat files
   knitpkg/flat/<EntryPointN>_flat.mq5 just for syntax check, and then the 
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file along with your src/<ProjectName>.mq5 (or `.mq4`) in the MetaTrader 
   `Experts` folder. Attach it to a chart and start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Documentation** - update the `version` and `description` fields in 
   `knitpkg.yaml` and consider adding a `README.md` with usage instructions 
   for your EA.

2. **Version control** - commit all the files respecting the default 
   `.gitignore` (automatically generated by `kp-mt init`). If you prefer, 
   delete the `GETTING_STARTED`. The `knitpkg/flat` and `knitpkg/include` 
   directories are ignored from version control by default, because 
   `kp-mt install` will add the resolved dependencies into one of 
   those directories.

4. **Register** - when you are ready, push the repository to a Git host.

For the full KnitPkg documentation visit: https://knitpkg.dev/docs

================================================================================
"""

TEMPLATE_INDICATOR_BARS_MQL5 = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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

TEMPLATE_INDICATOR_BARS_MQL4 = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long& tick_volume[],
                const long& volume[],
                const int& spread[])
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
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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

TEMPLATE_INDICATOR_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH KNITPKG INDICATOR DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

An Indicator project has the following structure (generated by
`kp-mt init --type indicator`):

  <ProjectName>/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <EntryPointN>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  knitpkg.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), `kp-mt install` will generate a 
flattened header named `<EntryPointN>_flat.mqh` in `knitpkg/flat/` for each 
entry point declared in `knitpkg.yaml`. Those are the files that should be 
included in your Indicator. The flattened headers will contain all resolved 
dependencies based upon `@knitpkg:include` directives declared in
`src/<EntryPointN>.mqh`. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `knitpkg/include/` (mirroring the 
package layout) after you run `kp-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `knitpkg/include/` or `knitpkg/flat/` as they are generated automatically by 
KnitPkg.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit `knitpkg.yaml` manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    # others dependencies...
    '@knitpkg.dev/knitpkg-mt-bar': https://forge.mql5.io/DouglasRechia/knitpkg-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<EntryPointN>.mqh` at this point and add the headers you'll 
  be using in your EA by means of KnitPkg directives. Skip this step otherwise.

* Download and resolve dependencies: run the following KnitPkg command:

      kp-mt install

  The command reads all the dependencies from `knitpkg.yaml`, downloads the 
  required packages and resolves all `@knitpkg:include` directives. After the 
  first install you will see either `knitpkg/flat/` directory containing the 
  flattened headers or `knitpkg/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `knitpkg.yaml`.

* Update a dependency: in the case you need to update a dependency, just
  update the version in `knitpkg.yaml` and run `kp-mt install` again to
  re-run the resolver and update `knitpkg/flat` or `knitpkg/include`.

      kp-mt install 

* Remove a dependency

  Delete the entry from the `dependencies` map in `knitpkg.yaml` and run
  `kp-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if you're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the required external headers 
   KnitPkg just installed in `knitpkg/include`. Use the standard MQL #include 
   directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **(Optional) Add MQL Standard library includes**

   If you want to use MQL Standard library headers, add them with the
   regular MQL #include and angle brackets, for example:

       #include <Trade/SymbolInfo.mqh>

   NOTE: all the KnitPkg includes, no matter if it is a regular MQL `#include` or 
   `@knitpkg:include`, must use double quotes as the delimiter to the header
   path. Angle brackets are used with the MQL Standard library only.
   
4. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal MQL #include
   directives.

================================================================================
                         COMPILING YOUR INDICATOR
================================================================================

1. Run the compiler:

   kp-mt compile

   The compiler will compile, if applicable, all the generated flat files
   knitpkg/flat/<EntryPointN>_flat.mq5 just for syntax check, and then the 
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file along with your src/<ProjectName>.mq5 (or `.mq4`) in the MetaTrader 
   `Experts` folder. Attach it to a chart and start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Documentation** - update the `version` and `description` fields in 
   `knitpkg.yaml` and consider adding a `README.md` with usage instructions 
   for your EA.

2. **Version control** - commit all the files respecting the default 
   `.gitignore` (automatically generated by `kp-mt init`). If you prefer, 
   delete the `GETTING_STARTED`. The `knitpkg/flat` and `knitpkg/include` 
   directories are ignored from version control by default, because 
   `kp-mt install` will add the resolved dependencies into one of 
   those directories.

4. **Register** - when you are ready, push the repository to a Git host.

For the full KnitPkg documentation visit: https://knitpkg.dev/docs

================================================================================
"""

TEMPLATE_SCRIPT = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

// ***** Add your code and rename the file as needed. *****

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
//---
   
  }
//+------------------------------------------------------------------+
"""

TEMPLATE_SCRIPT_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH KNITPKG SCRIPT DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

An Script project has the following structure (generated by
`kp-mt init --type script`):

  <ProjectName>/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <EntryPointN>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  knitpkg.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), `kp-mt install` will generate a 
flattened header named `<EntryPointN>_flat.mqh` in `knitpkg/flat/` for each 
entry point declared in `knitpkg.yaml`. Those are the files that should be 
included in your Script. The flattened headers will contain all resolved 
dependencies based upon `@knitpkg:include` directives declared in
`src/<EntryPointN>.mqh`. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `knitpkg/include/` (mirroring the 
package layout) after you run `kp-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `knitpkg/include/` or `knitpkg/flat/` as they are generated automatically by 
KnitPkg.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit `knitpkg.yaml` manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    # others dependencies...
    '@knitpkg.dev/knitpkg-mt-bar': https://forge.mql5.io/DouglasRechia/knitpkg-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<EntryPointN>.mqh` at this point and add the headers you'll 
  be using in your EA by means of KnitPkg directives. Skip this step otherwise.

* Download and resolve dependencies: run the following KnitPkg command:

      kp-mt install

  The command reads all the dependencies from `knitpkg.yaml`, downloads the 
  required packages and resolves all `@knitpkg:include` directives. After the 
  first install you will see either `knitpkg/flat/` directory containing the 
  flattened headers or `knitpkg/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `knitpkg.yaml`.

* Update a dependency: in the case you need to update a dependency, just
  update the version in `knitpkg.yaml` and run `kp-mt install` again to
  re-run the resolver and update `knitpkg/flat` or `knitpkg/include`.

      kp-mt install 

* Remove a dependency

  Delete the entry from the `dependencies` map in `knitpkg.yaml` and run
  `kp-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if you're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the required external headers 
   KnitPkg just installed in `knitpkg/include`. Use the standard MQL #include 
   directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **(Optional) Add MQL Standard library includes**

   If you want to use MQL Standard library headers, add them with the
   regular MQL #include and angle brackets, for example:

       #include <Trade/SymbolInfo.mqh>

   NOTE: all the KnitPkg includes, no matter if it is a regular MQL `#include` or 
   `@knitpkg:include`, must use double quotes as the delimiter to the header
   path. Angle brackets are used with the MQL Standard library only.
   
4. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal MQL #include
   directives.

================================================================================
                         COMPILING YOUR SCRIPT
================================================================================

1. Run the compiler:

   kp-mt compile

   The compiler will compile, if applicable, all the generated flat files
   knitpkg/flat/<EntryPointN>_flat.mq5 just for syntax check, and then the 
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file along with your src/<ProjectName>.mq5 (or `.mq4`) in the MetaTrader 
   `Experts` folder. Attach it to a chart and start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Documentation** - update the `version` and `description` fields in 
   `knitpkg.yaml` and consider adding a `README.md` with usage instructions 
   for your EA.

2. **Version control** - commit all the files respecting the default 
   `.gitignore` (automatically generated by `kp-mt init`). If you prefer, 
   delete the `GETTING_STARTED`. The `knitpkg/flat` and `knitpkg/include` 
   directories are ignored from version control by default, because 
   `kp-mt install` will add the resolved dependencies into one of 
   those directories.

4. **Register** - when you are ready, push the repository to a Git host.

For the full KnitPkg documentation visit: https://knitpkg.dev/docs

================================================================================
"""

TEMPLATE_LIBRARY = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property library
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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

TEMPLATE_LIBRARY_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH KNITPKG LIBRARY DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

A Library project has the following structure (generated by
`kp-mt init --type library`):

  <ProjectName>/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <EntryPointN>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  knitpkg.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), `kp-mt install` will generate a 
flattened header named `<EntryPointN>_flat.mqh` in `knitpkg/flat/` for each 
entry point declared in `knitpkg.yaml`. Those are the files that should be 
included in your Library. The flattened headers will contain all resolved 
dependencies based upon `@knitpkg:include` directives declared in
`src/<EntryPointN>.mqh`. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `knitpkg/include/` (mirroring the 
package layout) after you run `kp-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `knitpkg/include/` or `knitpkg/flat/` as they are generated automatically by 
KnitPkg.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit `knitpkg.yaml` manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    # others dependencies...
    '@knitpkg.dev/knitpkg-mt-bar': https://forge.mql5.io/DouglasRechia/knitpkg-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<EntryPointN>.mqh` at this point and add the headers you'll 
  be using in your EA by means of KnitPkg directives. Skip this step otherwise.

* Download and resolve dependencies: run the following KnitPkg command:

      kp-mt install

  The command reads all the dependencies from `knitpkg.yaml`, downloads the 
  required packages and resolves all `@knitpkg:include` directives. After the 
  first install you will see either `knitpkg/flat/` directory containing the 
  flattened headers or `knitpkg/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `knitpkg.yaml`.

* Update a dependency: in the case you need to update a dependency, just
  update the version in `knitpkg.yaml` and run `kp-mt install` again to
  re-run the resolver and update `knitpkg/flat` or `knitpkg/include`.

      kp-mt install 

* Remove a dependency

  Delete the entry from the `dependencies` map in `knitpkg.yaml` and run
  `kp-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if you're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the required external headers 
   KnitPkg just installed in `knitpkg/include`. Use the standard MQL #include 
   directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **(Optional) Add MQL Standard library includes**

   If you want to use MQL Standard library headers, add them with the
   regular MQL #include and angle brackets, for example:

       #include <Trade/SymbolInfo.mqh>

   NOTE: all the KnitPkg includes, no matter if it is a regular MQL `#include` or 
   `@knitpkg:include`, must use double quotes as the delimiter to the header
   path. Angle brackets are used with the MQL Standard library only.
   
4. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal MQL #include
   directives.

================================================================================
                         COMPILING YOUR LIBRARY
================================================================================

1. Run the compiler:

   kp-mt compile

   The compiler will compile, if applicable, all the generated flat files
   knitpkg/flat/<EntryPointN>_flat.mq5 just for syntax check, and then the 
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file along with your src/<ProjectName>.mq5 (or `.mq4`) in the MetaTrader 
   `Experts` folder. Attach it to a chart and start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Documentation** - update the `version` and `description` fields in 
   `knitpkg.yaml` and consider adding a `README.md` with usage instructions 
   for your EA.

2. **Version control** - commit all the files respecting the default 
   `.gitignore` (automatically generated by `kp-mt init`). If you prefer, 
   delete the `GETTING_STARTED`. The `knitpkg/flat` and `knitpkg/include` 
   directories are ignored from version control by default, because 
   `kp-mt install` will add the resolved dependencies into one of 
   those directories.

4. **Register** - when you are ready, push the repository to a Git host.

For the full KnitPkg documentation visit: https://knitpkg.dev/docs

================================================================================
"""


TEMPLATE_SERVICE = """//+------------------------------------------------------------------+
//| {{header_file_name}}
//| {{header_name}}
//| {{header_organization}}
//+------------------------------------------------------------------+
#property service
#property copyright   "<Add copyright here>"
#property link        "<Add link here>"
#property version     "" // If needed for MQL5 Market, add version number formatted as "X.Y"
#property description ""
#property description "Version: {{version}}"
#property description ""
#property description "Description: {{description}}"
#property description "Organization: {{organization}}"
#property description "Author: {{author}}"
#property description "License: {{license}}"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

{{project_includes}}

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

TEMPLATE_SERVICE_GETTING_STARTED = """================================================================================
                GETTING STARTED WITH KNITPKG SERVICE DEVELOPMENT
================================================================================

This file is only a quick-start guide.  Delete it after you have read it - it
is ignored by version control.

================================================================================
                              PROJECT LAYOUT
================================================================================

A Service project has the following structure (generated by
`kp-mt init --type service`):

  <ProjectName>/
    flat/                # Generated flat files (only when include_mode = flat)
    include/             # Used only when include_mode = include
  src/
    <ProjectName>.mq5    # Main EA source file (or .mq4 for MQL4)
    <EntryPointN>.mqh    # Dependencies entrypoint (only when include_mode = flat)
  knitpkg.yaml             # Project manifest
  .gitignore             # Git ignore
  GETTING_STARTED        # This file

When **flat** mode is used (recommended), `kp-mt install` will generate a 
flattened header named `<EntryPointN>_flat.mqh` in `knitpkg/flat/` for each 
entry point declared in `knitpkg.yaml`. Those are the files that should be 
included in your Service. The flattened headers will contain all resolved 
dependencies based upon `@knitpkg:include` directives declared in
`src/<EntryPointN>.mqh`. 

If you chose **include** mode, any headers that you want to include from 
dependencies will be placed automatically under `knitpkg/include/` (mirroring the 
package layout) after you run `kp-mt install`. 

IMPORTANT: All source code of your EA lives under `src/`. Do not change anything 
in `knitpkg/include/` or `knitpkg/flat/` as they are generated automatically by 
KnitPkg.

================================================================================
                         DEPENDENCY MANAGEMENT
================================================================================

* Add a dependency: edit `knitpkg.yaml` manifest file and add any package you want
under the `dependencies` section. For example:

  dependencies:
    # others dependencies...
    '@knitpkg.dev/knitpkg-mt-bar': https://forge.mql5.io/DouglasRechia/knitpkg-mt-bar.git#^4.0.0

  
  FLAT MODE: if your're using include_mode = flat, edit your dependencies 
  entrypoint `src/<EntryPointN>.mqh` at this point and add the headers you'll 
  be using in your EA by means of KnitPkg directives. Skip this step otherwise.

* Download and resolve dependencies: run the following KnitPkg command:

      kp-mt install

  The command reads all the dependencies from `knitpkg.yaml`, downloads the 
  required packages and resolves all `@knitpkg:include` directives. After the 
  first install you will see either `knitpkg/flat/` directory containing the 
  flattened headers or `knitpkg/include` directory containing the resolved 
  headers, depending on your choice as configured by include_mode entry in 
  `knitpkg.yaml`.

* Update a dependency: in the case you need to update a dependency, just
  update the version in `knitpkg.yaml` and run `kp-mt install` again to
  re-run the resolver and update `knitpkg/flat` or `knitpkg/include`.

      kp-mt install 

* Remove a dependency

  Delete the entry from the `dependencies` map in `knitpkg.yaml` and run
  `kp-mt install` again.

================================================================================
                         QUICK START - CREATE YOUR EA
================================================================================

1. **Open the generated source file**

   The file `src/<ProjectName>.mq5` (or `.mq4`) already contains a minimal
   skeleton. Replace the placeholders (`<...>`) with your project information.

2. **Add dependency includes**  

   INCLUDE MODE: if you're using include_mode = include, edit your EA
   `src/<ProjectName>.mq5` at this point and add the required external headers 
   KnitPkg just installed in `knitpkg/include`. Use the standard MQL #include 
   directive.

   FLAT MODE: if your're using include_mode = flat, you don't have to do anything
   here. The flattened headers will be automatically included in your EA.

3. **(Optional) Add MQL Standard library includes**

   If you want to use MQL Standard library headers, add them with the
   regular MQL #include and angle brackets, for example:

       #include <Trade/SymbolInfo.mqh>

   NOTE: all the KnitPkg includes, no matter if it is a regular MQL `#include` or 
   `@knitpkg:include`, must use double quotes as the delimiter to the header
   path. Angle brackets are used with the MQL Standard library only.
   
4. **Write your trading logic**  

   Implement the usual EA callbacks (`OnInit`, `OnDeinit`, `OnTick`,
   `OnTimer`, etc.) inside the skeleton.  You can also create additional
   helper headers in `src/` and include them with normal MQL #include
   directives.

================================================================================
                         COMPILING YOUR SERVICE
================================================================================

1. Run the compiler:

   kp-mt compile

   The compiler will compile, if applicable, all the generated flat files
   knitpkg/flat/<EntryPointN>_flat.mq5 just for syntax check, and then the 
   `compile` entries as defined in the manifest.

2. Run the EA

   After a successful compilation you will have an `.ex5` (or `.ex4`)
   file along with your src/<ProjectName>.mq5 (or `.mq4`) in the MetaTrader 
   `Experts` folder. Attach it to a chart and start testing.

================================================================================
                              NEXT STEPS
================================================================================

1. **Documentation** - update the `version` and `description` fields in 
   `knitpkg.yaml` and consider adding a `README.md` with usage instructions 
   for your EA.

2. **Version control** - commit all the files respecting the default 
   `.gitignore` (automatically generated by `kp-mt init`). If you prefer, 
   delete the `GETTING_STARTED`. The `knitpkg/flat` and `knitpkg/include` 
   directories are ignored from version control by default, because 
   `kp-mt install` will add the resolved dependencies into one of 
   those directories.

4. **Register** - when you are ready, push the repository to a Git host.

For the full KnitPkg documentation visit: https://knitpkg.dev/docs

================================================================================
"""