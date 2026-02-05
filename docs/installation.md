# Installation

This guide explains how to install the **KnitPkg CLI for MetaTrader** (`kp`) and configure your machine for MQL4/MQL5 development.

> KnitPkg is currently **Windows-first**, because MetaTrader and MetaEditor are typically used on Windows.

---

## Prerequisites

Before installing `kp`, make sure you have:

1. **(Updated) Windows Terminal**  
   Windows 11 already includes it. On older Windows versions, you may need the newer terminal to correctly render the CLI’s UTF-8 symbols and formatting. Available in Microsoft Store: [https://aka.ms/terminal](https://aka.ms/terminal). For other installation methods see [https://github.com/microsoft/terminal](https://github.com/microsoft/terminal).

2. **Git client**  
   KnitPkg *leverages Git* for MetaTrader package & project management, so a Git client is essential. Available at: [https://git-scm.com/](https://git-scm.com/).

3. **MetaTrader 4 and/or MetaTrader 5**
    Available at: [https://www.mql5.com/](https://www.mql5.com/).

---

## Install the CLI (`kp`)

### Option A (recommended): download the prebuilt executable

1. Download the latest `kp.exe` from the project’s [**GitHub Releases**](https://github.com/knitpkg-dev/knitpkg-mt/releases).
2. Put `kp.exe` in a folder you control (example: `C:\tools\knitpkg\`).
3. Add that folder to your **PATH** so `kp` can be called from any terminal.

### Verify the installation

Open a new terminal and run:

```bash
kp --version
```

If the command is not found, PATH is not set correctly (or the terminal session needs to be restarted).

### Option B: PyPI (coming soon)
  Distribution via `pip` is in progress. This section will be expanded once the package is published and stabilized.

---

## Essential workflow commands

Once `kp` is installed, these are the commands you’ll use most often.

```bash
# Create a new project (wizard-style)
kp init

# Add a dependency to your project
kp add @organization/package-name

# Install dependencies
kp install

# Compile MQL sources
kp compile

# One-shot: install + compile
kp build
```

## Beta note

KnitPkg is currently in **Beta**. Expect occasional breaking changes and keep an eye on release notes when updating.