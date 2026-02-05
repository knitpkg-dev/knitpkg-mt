# Manifest (`knitpkg.yaml`)

As we saw in the previous section, the main file `src/KnitPkgSMA.mq5` tries to include a file that does **not** exist in the Git repository. To understand where that file comes from, we need to look at the project [manifest](https://forge.mql5.io/DouglasRechia/sma/src/commit/d50674497d1664b21acb0caf056c6e2f8d7be413/knitpkg.yaml):

```yaml title="knitpkg.yaml excerpt" linenums="1" hl_lines="16 19-20 26-27"
target: mql5
type: indicator

organization: douglasrechia
name: sma
version: 1.0.0
version_description: Initial version

# Registry search fields
description: KnitPkg for Metatrader - SMA Indicator Demo
keywords: [ "indicator", "sma", "showcase" ]
author: Douglas Rechia
license: MIT

# Include mode resolution
include_mode: flat

# File to be flattened with all the dependencies for this project
entrypoints:
  - src/KnitPkgSMA.mqh

compile:
  - src/KnitPkgSMA.mq5

# Dependencies of the project
dependencies:
    '@douglasrechia/calc': ^1.0.0
```

## Key manifest points

The manifest is the “brain” of a KnitPkg repository: it tells KnitPkg **what this repository is**, **how to build it**, and **which dependencies it needs**.

Pay special attention to the highlighted parts:

- **`entrypoints`**: declares `src/KnitPkgSMA.mqh` as the entrypoint for dependency resolution. With `include_mode: flat`, KnitPkg will use this file as the root to generate the flattened header needed for compilation.
- **`dependencies`**: declares that this project depends on the package `@douglasrechia/calc`. KnitPkg will use this information to resolve the dependency version and fetch the required code.

In other words: the manifest explains *why* the repository is missing some includes—because they are produced during installation.

For the complete manifest field reference, see the [Manifest reference page](../reference/manifest.md)

--- 

Now it's time to have KnitPkgSMA working!

