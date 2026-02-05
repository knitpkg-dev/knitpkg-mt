# Concepts Overview

Let’s use a real-world repository to introduce KnitPkg’s core ideas: the [**SMA project**](https://forge.mql5.io/DouglasRechia/sma/src/commit/d50674497d1664b21acb0caf056c6e2f8d7be413). You're encouraged to browse and explore SMA repo (even if *another* SMA implementation doesn't seem
to be interesting to you ;-) ).

!!! note
    This entire documentation set is based on **SMA version 1.0.0**. For that reason, every reference link to the SMA source code points to the **exact commit** for that version. This keeps the docs consistent even as the repository changes over time.

    The SMA project is hosted on MQL5Forge, and you can view the exact code snapshot used by this documentation in the above link (the commit hash is the “anchor” that guarantees consistency). The latest revision is [here](https://forge.mql5.io/DouglasRechia/sma.git).

At first glance it looks like a normal indicator repository. But when you inspect the main `.mq5` file [`src/KnitPkgSMA.mq5`](https://forge.mql5.io/DouglasRechia/sma/src/commit/d50674497d1664b21acb0caf056c6e2f8d7be413/src/KnitPkgSMA.mq5), you’ll notice an `#include` that points to a file that **is not present** in the repo:

```mql5 title="KnitPkgSMA.mq5" linenums="1" hl_lines="19"
//+------------------------------------------------------------------+
//|                                                   KnitPkgSMA.mq5 |
//|                                                   Douglas Rechia |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright   "Douglas Rechia"
#property link        "https://knitpkg.dev"
#property description ""
#property description "Version: 1.0.0"
#property description ""
#property description "Description: KnitPkg for Metatrader - SMA Indicator Demo"
#property description "Organization: douglasrechia"
#property description "Author: Douglas Rechia"
#property description "License: MIT"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

#include "../knitpkg/flat/KnitPkgSMA_flat.mqh"
//---
#property indicator_chart_window
//--- The rest of the code continues below; this is just an excerpt.
```


That is not a mistake. It’s the core idea:

- The repository contains *your* project code and a manifest (`knitpkg.yaml`) that describes what it depends on.
- The missing headers are produced and/or downloaded during **installation**.
- After running KnitPkg, the project becomes compile-ready because dependencies are resolved and files are placed where the compiler expects them.

In other words, some KnitPkg projects are intentionally **not buildable by “git clone + compile”**. They are buildable by **“install + compile”**.

## What you’ll learn in this section

By the end of the Concepts section you will understand:

- The difference between **packages** (reusable code) and **projects** (EAs, indicators, scripts, libraries, services).
- How the **registry** fits in (metadata, versions, discovery) without hosting your code.
- How versioning works (SemVer, ranges, yanks) and why reproducible installs matter.
- How KnitPkg assembles a local workspace (including generated/flattened headers) so MetaTrader tooling can compile reliably.

## Next: the manifest (`knitpkg.yaml`)

The next page dives into the most important file in a KnitPkg repository: **`knitpkg.yaml`**.

It’s the link between the code you see in the repo and the dependencies KnitPkg installs to make the project compile and run.