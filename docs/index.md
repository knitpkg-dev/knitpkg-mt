# KnitPkg for MetaTrader

**KnitPkg** is a modern **package and project manager for MQL5/MQL4**, bringing an *npm-like* dependency workflow to real-world MetaTrader development.

MetaTrader projects often evolve through manual copy/paste, ad-hoc folder sharing, and “it works on my machine” dependency drift. KnitPkg exists to fix that by making code reuse and collaboration **predictable, reproducible, and automated**—without changing how MQL developers already publish code (Git repos).

## What KnitPkg is

KnitPkg is built around a **Git-first** model:

- Your code lives in **Git repositories** (Mql5Forge, GitHub, GitLab, Bitbucket).
- KnitPkg acts as a **metadata registry** that indexes projects via their manifests (it does **not** host your source or binaries).
- A **CLI tool** installs dependencies, resolves versions (SemVer + ranges), generates reproducible installs via a lock file, and can automate compilation.

The public registry API is available and currently operational. <sources>[1]</sources>

## Packages vs Projects

KnitPkg manages two kinds of repositories:

- **Packages**: reusable MQL source code meant to be imported by other projects.
- **Projects**: runnable MetaTrader artifacts such as **Expert Advisors**, **Indicators**, **Libraries**, **Services**, or **Scripts**.

Both are installed from their original Git sources, but they serve different goals: packages maximize reuse; projects ship final trading artifacts.

## Why developers use KnitPkg

KnitPkg focuses on the pain points that show up fast in MQL development:

- **Versioned dependencies** (SemVer + ranges like `^`, `~`, `<`, `>`, `*`, `!=`)
- **Reproducible builds** with a lock file
- **Composed packages** (dependency trees), including helpers like autocomplete and `@knitpkg:include`
- **Safe ecosystem maintenance** with *yanked* versions (removed from range resolution without breaking history)
- **Git-host login via OAuth** for publishing (no extra KnitPkg account); public installs need no auth

## How this documentation is organized

This site is structured to take you from “first install” to “deep reference”:

- **Overview**: what KnitPkg is and the core idea behind it
- **Installation**: getting the CLI working on your machine
- **Core Concepts**: packages vs projects, the registry, and the Git-first workflow
- **User Guide**: day-to-day workflows (init, add, install, get, publish, search)
- **Reference**: exact specs (manifest format, directives, SemVer rules, layouts, CLI)
- **Troubleshooting & FAQ**: common pitfalls and how to fix them
- **Contributing**: how to participate in the CLI and ecosystem

---

Now that you understand what KnitPkg is and why it exists, you’re ready for the next step: **installing the KnitPkg CLI**.
