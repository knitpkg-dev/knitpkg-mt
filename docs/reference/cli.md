# CLI Reference

This page documents all available commands in the `kp` CLI (KnitPkg Command Line Interface), grouped by category.

To see a quick overview of all commands, run:

```bash
kp --help
```

All commands support the global option:

| Flag       | Description         |
|------------|---------------------|
| `--verbose` | Show detailed output |

---

## Core Workflow Commands

### `kp init`

Initializes a new KnitPkg project interactively or via flags.

**Usage:**
```bash
kp init [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--dry-run`, `-d` | Show what would be done without making changes | `False` |
| `--type` | Project type (`package`, `expert`, `indicator`, `library`, `service`) | Prompt |
| `--target`, `-t` | MetaTrader platform (`mql4` or `mql5`) | Prompt |
| `--name`, `-n` | Project name (alphanumeric, hyphen, underscore, dot) | Prompt |
| `--organization`, `-o` | Organization name | Prompt |
| `--version`, `-v` | Initial version (SemVer) | Prompt |
| `--description` | Short description | Prompt |
| `--author` | Author name | Prompt |
| `--license` | License identifier (e.g., MIT) | Prompt |
| `--include-mode` | `include` or `flat` | Prompt |
| `--entrypoints` | Comma-separated list of entrypoints (required for flat mode) | Prompt |
| `--location`, `-l` | Output directory | Prompt |
| `--git-init` | Initialize Git repository | Prompt |
| `--enable-telemetry` / `--disable-telemetry` | Enable or disable telemetry | Prompt |

**Example:**
```bash
kp init --type indicator --target mql5 --name MyRSI --organization acme --version 1.0.0
```

---

### `kp add`

Adds a dependency to the current project.

**Usage:**
```bash
kp add <project_name> [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verspec`, `-v` | Version specifier | `*` |
| `--project-dir`, `-d` | Project directory | `.` |

**Example:**
```bash
kp add @acme/math -v ~1.2.0
```

---

### `kp install`

Resolves and installs all dependencies.

**Usage:**
```bash
kp install [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |
| `--locked` | Enforce lockfile consistency | `False` |
| `--no-tree` | Skip dependency tree display | `False` |

**Example:**
```bash
kp install --locked
```

---

### `kp compile`

Compiles MQL source files.

**Usage:**
```bash
kp compile [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |
| `--in-place` | Keep binaries in place | `False` |
| `--entrypoints-only` | Compile only entrypoints | `False` |
| `--compile-only` | Compile only compile list | `False` |

**Example:**
```bash
kp compile
```

---

### `kp build`

Builds the project. For packages, runs `checkinstall` and `compile` in sequence. For others, runs `install` and then `compile`.

**Usage:**
```bash
kp build [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |
| `--locked` | Enforce lockfile consistency | `True` |
| `--no-tree` | Skip dependency tree display | `False` |
| `--in-place` | Keep binaries in place | `False` |
| `--entrypoints-only` | Compile only entrypoints | `False` |
| `--compile-only` | Compile only compile list | `False` |

**Example:**
```bash
kp build
```

---

## Package Development Commands

### `kp autocomplete`

Generates `autocomplete.mqh` for MetaEditor IntelliSense.

**Usage:**
```bash
kp autocomplete [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |

**Example:**
```bash
kp autocomplete
```

---

### `kp checkinstall`

Validates all directives and headers.

**Usage:**
```bash
kp checkinstall [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--skip-autocomplete` | Skip autocomplete generation | `False` |
| `--project-dir`, `-d` | Project directory | `.` |

**Example:**
```bash
kp checkinstall --skip-autocomplete
```

---

## Registry Commands

### `kp search`

Searches the KnitPkg registry.

**Usage:**
```bash
kp search <target> [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--query`, `-q` | Search term | `None` |
| `--organization`, `-o` | Filter by organization | `None` |
| `--type`, `-t` | Filter by project type | `None` |
| `--author`, `-a` | Filter by author | `None` |
| `--license`, `-l` | Filter by license | `None` |
| `--sort-by`, `-S` | Sort field | `published_at` |
| `--sort-order`, `-O` | `asc` or `desc` | `desc` |
| `--page`, `-p` | Page number | `1` |
| `--page-size`, `-s` | Results per page | `20` |

**Example:**
```bash
kp search mql5 --query rsi --organization douglasrechia
```

---

### `kp info`

Displays metadata for a specific project.

**Usage:**
```bash
kp info <target> <specifier> [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Show detailed output | `False` |

**Example:**
```bash
kp info mql5 @douglasrechia/bar
```

---

### `kp get`

Downloads and installs a project directly into MetaTrader.

**Usage:**
```bash
kp get <target> <proj_specifier> [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verspec`, `-v` | Version specifier | `*` |
| `--mql-data-folder`, `-m` | Path to MQL data folder | Auto-detect |

**Example:**
```bash
kp get mql5 @douglasrechia/sma ^1.0.0 --mql-data-folder ~/AppData/Roaming/MetaQuotes/Terminal/ABC123/MQL5
```

---

### `kp register`

Publishes the current project to the registry.

**Usage:**
```bash
kp register [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |

**Example:**
```bash
kp register
```

---

### `kp yank`

Yanks a specific version from the registry.

**Usage:**
```bash
kp yank <target> <specifier> <version> [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Show detailed output | `False` |

**Example:**
```bash
kp yank mql5 @acme/math 1.2.3
```

---

### `kp status`

Shows registry and authentication status along with supported Git providers.

**Usage:**
```bash
kp status [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Show detailed output | `False` |

---

### `kp login`

Authenticates with the registry via OAuth. Run `kp status` to see the list of available providers.

**Usage:**
```bash
kp login [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--provider` | OAuth provider (e.g., github). | Required |
| `--verbose` | Show detailed output | `False` |

---

### `kp logout`

Logs out from the registry.

**Usage:**
```bash
kp logout [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Show detailed output | `False` |

---

### `kp whoami`

Displays the currently authenticated user.

**Usage:**
```bash
kp whoami [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--verbose` | Show detailed output | `False` |

---

## Configuration Commands

### `kp config`

Sets project-specific configuration.

**Usage:**
```bash
kp config [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--project-dir`, `-d` | Project directory | `.` |
| `--mql5-compiler-path` | Path to MetaEditor64.exe | `None` |
| `--mql4-compiler-path` | Path to MetaEditor.exe | `None` |
| `--mql5-data-folder-path` | MQL5 data folder path | `None` |
| `--mql4-data-folder-path` | MQL4 data folder path | `None` |
| `--list`, `-l` | List current config | `False` |

---

### `kp globalconfig`

Sets global CLI settings.

**Usage:**
```bash
kp globalconfig [options]
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--set-registry` | Set default registry URL | `None` |
| `--list`, `-l` | Show current global config | `False` |

---

### `kp telemetry`

Enables or disables telemetry.

**Usage:**
```bash
kp telemetry <state> [options]
```

**Arguments:**

| Name | Description |
|------|-------------|
| `state` | `on` or `off` |

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--global` / `--local` | Scope of telemetry setting | `global` |
| `--project-dir`, `-d` | Project directory | `.` |

**Example:**
```bash
kp telemetry on
```

!!! note
    Telemetry is opt-in and collects anonymized usage data to improve KnitPkg. See [Telemetry Policy](../terms-of-service/telemetry.md).