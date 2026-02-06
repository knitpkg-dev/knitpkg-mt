# Manifest Reference (`knitpkg.yaml`)

This page documents the fields accepted by KnitPkg in the project manifest file: `knitpkg.yaml`.

!!! note "Manifest file names"
    The most common manifest file name is `knitpkg.yaml`, but `knitpkg.yml` is also accepted.

    JSON is supported as well. In that case, the manifest must be named `knitpkg.json`.

!!! note
    The manifest is intentionally forward-compatible. Unknown fields are allowed, so the format can evolve over time (and you can keep custom metadata in your manifest).

---

## Example (`knitpkg.yaml`)

```yaml
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

## Top-level fields (core)

### `target` (required)

- **Type:** string (enum)
- **Allowed values:** `mql4`, `mql5`
- **Meaning:** Selects the MetaTrader language/toolchain target for the repository.

---

### `organization` (required)

- **Type:** string
- **Meaning:** The organization/namespace that owns the project (typically matches the Git host organization/user).
- **Constraints (human-readable):**
    - Must follow a strict naming format (letters/digits plus safe separators; no spaces).
    - Maximum length: 100 characters.
- **Why it matters:** The organization is part of the project identity and is used to avoid naming collisions across different owners.

---

### `name` (required)

- **Type:** string
- **Meaning:** The project/package name inside the organization.
- **Constraints (human-readable):**
    - Must not be empty.
    - Maximum length: 50 characters.
    - Must follow a strict naming format (letters/digits plus safe separators; no spaces).
- **Registry generic search:** This field is indexed by the registry’s generic search.

---

### `description` (required)

- **Type:** string
- **Meaning:** Short, human-readable summary of the project.
- **Constraints (human-readable):**
    - Must be at least 10 characters long.
    - Must be at most 500 characters long.
    - Must be concise: up to 50 words.
- **Registry generic search:** This field is indexed by the registry’s generic search.

---

### `version` (required)

- **Type:** string (SemVer)
- **Meaning:** The project version following Semantic Versioning.
- **Notes:** Pre-releases (e.g. `1.0.0-beta.1`) are supported as long as the version is valid SemVer.

---

### `version_description` (optional)

- **Type:** string
- **Meaning:** A short note describing what changed in this version (changelog-style).

---

### `type` (required)

- **Type:** string (enum)
- **Allowed values:** `package`, `expert`, `indicator`, `script`, `library`, `service`
- **Meaning:** Declares what kind of repository this is:
    - `package` for reusable code
    - the other values for runnable MetaTrader artifacts (EAs, indicators, scripts, etc.)

---

### `keywords` (optional)

- **Type:** list of strings
- **Meaning:** Search keywords/tags to help users discover the project.
- **Constraints (human-readable):**
    - Up to 10 words total.
- **Registry generic search:** This field is indexed by the registry’s generic search.

---

### `author` (optional)

- **Type:** string
- **Meaning:** Author name (free-form).

---

### `license` (optional)

- **Type:** string
- **Meaning:** License identifier (free-form).

---

### `compile` (optional)

- **Type:** list of strings (paths)
- **Meaning:** Source files KnitPkg should compile (e.g. `.mq4` / `.mq5`) when running compilation-related commands.
- **Typical usage:** Put your EA/Indicator “entry” `.mq5`/`.mq4` files here (not `.mqh` headers).

---

## Dependencies

### `dependencies` (optional)

- **Type:** map/dictionary of `dependency -> version_range` or `dependency -> local_path`
- **Meaning:** Declares the direct dependencies required by this project.

    **Dependency key format**

    - If the dependency is in the **same organization** declared by this manifest (`organization`), you can omit the organization prefix:

        ```yaml
        organization: douglasrechia
        dependencies:
            calc: ^1.0.0
        ```

    - If the dependency belongs to a **different organization**, prefix it with `@organization/`:

        ```yaml
        dependencies:
            '@douglasrechia/calc': ^1.0.0
            '@acme/utils': ~2.1.0
        ```

    **Version range format**

    - Values are SemVer ranges (npm-style operators such as `^`, `~`, `<`, `>`, `*`, `!=`, etc.), as supported by KnitPkg. See: [Version ranges](version-ranges.md).

    **Local path**

    - Local paths are accepted in the place of the version range. In this case, KnitPkg resolves to a local project
        instead of fetching from the registry. This is useful for development and testing. Once the dependency
        is published to the registry, replace the local path with the correct version specifier.

        ```yaml
        dependencies:
            '@acme/utils': ../acme_utils
        ```

---

### `overrides` (optional)

- **Type:** map/dictionary of `dependency -> exactVersion`
- **Meaning:** Forces specific versions for dependencies (including transitive ones), similar to npm `overrides`.
- **Important:** Only **exact versions** are accepted here (no ranges). This is meant for “pin this dependency to exactly X.Y.Z”.

    Example:

    ```yaml
    overrides:
        '@someorg/somedep': "2.3.4"
    ```

---

## MQL-specific fields

These fields apply to MQL4/MQL5 repositories.

### `include_mode` (required)

- **Type:** string (enum)
- **Meaning:** Controls how KnitPkg makes dependency headers available to your project after installation.

Common modes:

- **`include`**: dependencies are made available as individual headers under a KnitPkg-managed include directory.
- **`flat`**: KnitPkg generates a flattened header (a single self-contained `.mqh`) per entrypoint under a KnitPkg-managed `flat/` directory.

---

### `entrypoints` (optional, but required for `include_mode: flat`)

- **Type:** list of strings (paths)
- **Meaning:** Header files that act as “roots” for the flattening process.
- **Typical usage:** Your project’s main `.mqh` that includes (directly or indirectly) all required package headers.

Example:

```yaml
include_mode: flat
entrypoints:
  - src/KnitPkgSMA.mqh
```

---

## Summary: required fields

In practice, a valid manifest must include at least:

- `target`
- `organization`
- `name`
- `description`
- `version`
- `type`

And for MQL projects:

- `include_mode`
- `entrypoints` (when using `include_mode: flat`)