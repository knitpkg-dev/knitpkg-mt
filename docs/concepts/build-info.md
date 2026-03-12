# Build Info

When you run `kp compile` (or `kp build`) and your manifest includes a `defines`
section, KnitPkg automatically generates a compile-time header at
`knitpkg/build/BuildInfo.mqh` **before** invoking the MetaEditor compiler.

This header exports project metadata and user-defined constants as MQL
preprocessor `#define` directives, making them available at compile time —
no runtime parsing, no string manipulation.

!!! note
    `BuildInfo.mqh` is auto-generated. Do not edit it manually; your changes
    will be overwritten on the next `kp compile` or `kp build`.

## Defining constants

Constants are declared in the `defines` section of `knitpkg.yaml`. There are
two subsections, and they can be used independently or together: `from_manifest` 
and `extra`.

```yaml title="'defines' in manifest"
defines:
  from_manifest:
    MANIFEST_VERSION:     version       # value of version      → #define MANIFEST_VERSION "2.0.1"
    MANIFEST_ORG:         organization  # value of organization → #define MANIFEST_ORG "douglasrechia"
    MANIFEST_AUTHOR:      author        # value of author       → #define MANIFEST_AUTHOR "Douglas Rechia"
    MANIFEST_DESCRIPTION: description   # value of description  → #define MANIFEST_DESCRIPTION "KnitPkg for Metatrader - Expert Demo"
  extra:
    MQL_STORE_VERSION:    '2.1'         # string value          → #define MQL_STORE_VERSION "2.1"
    MAX_BARS:             500           # numeric value         → #define MAX_BARS 500
    FEATURE_X_ENABLED:    true          # true                  → #define FEATURE_X_ENABLED true
    FEATURE_Y_ENABLED:    null          # null                  → #define FEATURE_Y_ENABLED 
```

In the `from_manifest` section, the generated constant value is always the value of the field
as it appears in `knitpkg.yaml`. In the `extra`, a flat key/value map for constants that do not come from the 
manifest are defined.

## Adding constants at compile time

You can inject constants directly from the command line using `--define` or
`-D`. This is useful for CI pipelines, release channels, and feature flags
that should not be stored in the manifest:

```bash
kp compile -D NIGHTLY
kp compile -D BUILD_TYPE=release
kp compile -D FEATURE_X_ENABLED -D MAX_BARS=500
```

## Why this matters

The `BuildInfo.mqh` feature is about **controlling your Expert/Indicator at
compile time**, instead of scattering hardcoded values and `#define`s across
your codebase.

Some typical use cases:

- **Correct version and metadata in the EA properties**  
  Instead of duplicating version and description strings in multiple places,
  you define them once in the manifest and expose them via `BuildInfo.mqh`,
  then wire them directly into the EA "Common" tab using `#property`:

    ```mql5
    #include "../knitpkg/build/BuildInfo.mqh"

    #property copyright   "Copyright © 2026 " + MANIFEST_AUTHOR + ". All rights reserved."
    #property link        "https://knitpkg.dev"
    #property version     (string)MQL_STORE_VERSION

    #property description ""
    #property description "Version: " + MANIFEST_VERSION
    #property description ""
    #property description "Description: " + MANIFEST_DESCRIPTION
    #property description "Organization: " + MANIFEST_ORG
    #property description "Author: " + MANIFEST_AUTHOR
    #property description ""
    #property description "Powered by KnitPkg for MetaTrader"
    #property description "https://knitpkg.dev"
    ```

- **Feature flags**  
Enable or disable blocks of code without touching source files:

    ```bash
    kp compile -D FEATURE_RISK_MODEL_V2
    ```

    ```mql5
    #include "../knitpkg/build/BuildInfo.mqh"

    double CalculateRisk() 
      { 
        #ifdef FEATURE_RISK_MODEL_V2 
            return NewRiskModel(); 
        #else 
            return LegacyRiskModel(); 
        #endif 
      }
    ```

- **Environment-specific builds**  
  Generate binaries for different brokers, environments or channels from the
  same source tree:

    ```bash
    kp compile -D BUILD_CHANNEL=beta 
    kp compile -D BUILD_CHANNEL=production
    ```

    ```mql5
    #include "../knitpkg/build/BuildInfo.mqh"

    /// .....

    #ifdef BUILD_CHANNEL 
        Print("Build channel: ", BUILD_CHANNEL); 
    #endif
    ```

This way:

- The **manifest** is the single source of truth for your project metadata.
- `BuildInfo.mqh` turns that metadata (plus any `-D` flags) into **compile-time
  constants**.
- Your MQL code **stays clean and declarative**, focusing on logic instead of
  plumbing values around.

Together with `kp compile --define / -D`, this gives you a light but powerful
build system for MQL: from a single codebase, you can produce multiple variants
(debug, store, internal, nightly, broker-specific, etc.) just by changing
compile-time constants — no branching, no manual edits.