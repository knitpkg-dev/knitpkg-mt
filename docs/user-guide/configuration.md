# Configuration

KnitPkg requires a few configuration settings to function properly. These settings define how the CLI interacts with your MetaTrader environment, the registry, and telemetry services.

---

## What Needs to Be Configured

The following items must be configured:

- **MQL Compiler Path** — Path to the MetaEditor executable (`.exe`)
- **MQL Data Folder** — Path to the MetaTrader Data Folder, required for project installation and compilation (must include the MQL Standard Library)
- **Telemetry** — Whether to allow telemetry data to be sent to the KnitPkg Registry
- **Registry** — The base URL of the KnitPkg Registry

---

## Where Configuration Is Stored

KnitPkg reads configuration from three sources, in order of priority:

1. **Environment variables**
2. **Project-specific YAML config**: `<project_dir>/.knitpkg/config.yaml`
3. **Global YAML config**: `<User Home>/.knitpkg/config.yaml`

---

## Configuration Precedence

The following precedence rules apply for each setting:

| Setting                | Priority 1 (Highest)         | Priority 2                  | Priority 3 (Lowest)         |
|------------------------|------------------------------|-----------------------------|-----------------------------|
| MQL5 Compiler Path     | `MQL5_COMPILER_PATH`         | Project config YAML         | Global config YAML          |
| MQL5 Data Folder       | `MQL5_DATA_FOLDER_PATH`      | Project config YAML         | Global config YAML          |
| MQL4 Compiler Path     | `MQL4_COMPILER_PATH`         | Project config YAML         | Global config YAML          |
| MQL4 Data Folder       | `MQL4_DATA_FOLDER_PATH`      | Project config YAML         | Global config YAML          |
| Telemetry              | —                            | Project config YAML         | Global config YAML          |
| Registry               | `KNITPKG_REGISTRY`           | —                           | Global config YAML          |

If a value is not found in any of the above, KnitPkg falls back to the default values.

---

## Default Values

- **MQL5 Compiler Path**:  
  `C:\Program Files\MetaTrader 5\MetaEditor64.exe`

- **MQL4 Compiler Path**:  
  `C:\Program Files (x86)\MetaTrader 4\metaeditor.exe`

- **MQL5/MQL4 Data Folder**:  
  If not explicitly configured or if the path is invalid, KnitPkg will attempt to auto-detect a valid MetaTrader installation in the following locations:

    - `%USERPROFILE%\AppData\Roaming\MetaQuotes\Terminal`
    - `C:\Program Files\MetaTrader 5\Terminal` (for MQL5)
    - `C:\Program Files (x86)\MetaTrader 4\Terminal` (for MQL4)

- **Registry**:  
  `https://api.registry.knitpkg.dev`

---

## How to Configure

Use the following CLI commands to configure KnitPkg:

### Project-Specific Configuration

Use [`kp config`](../reference/cli.md/#kp-config) to configure settings for the current project:

```bash
kp config --mql5-data-folder-path C:\Users\dougl\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075
```

### Global Configuration

Use [`kp globalconfig`](../reference/cli.md/#kp-globalconfig) to configure settings globally:

```bash
kp globalconfig --mql5-data-folder-path C:\Users\dougl\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075
```

Set the MQL4 compiler path globally:

```bash
kp globalconfig --mql4-compiler-path "C:\Program Files (x86)\MetaTrader - Acme\metaeditor.exe"
```

Enable telemetry globally:

```bash
kp telemetry on
```

---

## Summary

KnitPkg offers flexible configuration through environment variables, project-level settings, and global defaults. This layered approach ensures that you can fine-tune your development environment while maintaining consistent behavior across projects