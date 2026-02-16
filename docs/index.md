# KnitPkg for MetaTrader

**KnitPkg** is a modern **package and project manager for MQL5/MQL4**, bringing an *npm-like* dependency workflow to real-world MetaTrader development.

MetaTrader projects often evolve through manual copy/paste, ad-hoc folder sharing, and “it works on my machine” dependency drift. KnitPkg exists to fix that by making code reuse and collaboration **predictable, reproducible, and automated**—without changing how MQL developers already publish code (Git repos).

## What KnitPkg is

KnitPkg is built around a **Git-first** model:

- Your code lives in **Git repositories** (Mql5Forge, GitHub, GitLab, Bitbucket).
- KnitPkg acts as a **metadata registry** that indexes projects via their manifests (it does **not** host your source or binaries).
- A **CLI tool** installs dependencies, resolves versions (SemVer + ranges), generates reproducible installs via a lock file, and can automate compilation.

The public registry API is available and currently operational.

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
- **Getting started**: a quick introduction to your first steps using KnitPkg
- **Core Concepts**: packages vs projects, the registry, and the Git-first workflow
- **User Guide**: day-to-day workflows (init, add, install, get, publish, search)
- **Reference**: exact specs (manifest format, directives, SemVer rules, layouts, CLI)
- **Contributing**: how to participate in the CLI and ecosystem

---

**KnitPkg — The dependency manager MQL5 always needed.**

Made with passion

MIT Licensed — Forever free for the community

GitHub: [https://github.com/knitpkg-dev/knitpkg-mt.git](https://github.com/knitpkg-dev/knitpkg-mt.git)

Discord: [https://discord.gg/hCbmYtkn](https://discord.gg/hCbmYtkn) to the future.

Contact: [contact@knitpkg.dev](mailto:contact@knitpkg.dev)

**KnitPkg – The future of MQL5 development**

---
