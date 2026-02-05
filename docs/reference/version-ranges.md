# Version Ranges Reference

KnitPkg uses **Semantic Versioning (SemVer)** to manage dependency versions. A *version range* (also called a *specifier*) tells KnitPkg which versions are acceptable when resolving dependencies.

This page documents the version range formats supported by KnitPkg and the resolution rules used to pick the final version.

---

## Supported formats

### Exact version

Pin to one specific version.

- Examples: `1.2.3`, `=1.2.3`
- Behavior:
    - Resolves **only** to `1.2.3`.
    - If that exact version is **yanked**, it can still be selected because it’s an explicit pin.

---

### Caret ranges (`^`)

Allow updates that do not change the left-most non-zero component (npm-style caret semantics).

- `^1.2.3` means: `>=1.2.3 <2.0.0`
- `^0.1.2` means: `>=0.1.2 <0.2.0`
- `^0.0.1` means: only `0.0.1`

Notes:

- In `0.x.y`, breaking changes are assumed to happen at the **minor** level.
- In `0.0.x`, breaking changes are assumed to happen at the **patch** level.

---

### Tilde ranges (`~`)

Allow patch-level updates when a minor is specified; allow minor-level updates when only a major is specified.

- `~1.2.3` means: `>=1.2.3 <1.3.0`
- `~1.2` means: `>=1.2.0 <1.3.0`
- `~1` means: `>=1.0.0 <2.0.0`

---

### Wildcards (`*`, `x`, `X`)

Use `*`, `x`, or `X` to allow variation in one or more components.

- `*` or `x` resolves to the **latest stable** version available.
- `1.x` means: `>=1.0.0 <2.0.0`
- `1.2.x` means: `>=1.2.0 <1.3.0`

---

### Comparison operators

You can build custom ranges using comparison operators:

- Operators: `>`, `>=`, `<`, `<=`, `=`, `!=`
- Examples:
    - `>=1.0.0 <2.0.0` (any `1.x.x`)
    - `>=1.2.0 <=1.5.0` (closed range)
    - `>1.0.0 !=1.2.1` (anything greater than `1.0.0` except `1.2.1`)

Combined ranges are written as space-separated comparisons.

---

## Resolution rules

When multiple versions match a range, KnitPkg selects the final version using the rules below.

### Highest matching version wins

KnitPkg resolves to the **highest available version** that satisfies the range, preferring versions that are not yanked and (by default) not pre-release.

---

### Stable vs pre-release versions

- **Ranges do not include pre-releases by default.**
  - Example: `^1.2.0` will **not** resolve to `1.3.0-beta.1`.
- **Pre-releases are only considered when the specifier explicitly contains a pre-release identifier.**
  - Example: `^1.3.0-beta` indicates you are opting into pre-release resolution.

Pre-release matching behavior:

- A range like `>=2.1.1-alpha.1` may accept:
  - `2.1.1-alpha.2`
  - `2.1.1-beta`
- But it will **not** accept `2.1.2-alpha.1` (a pre-release of a higher stable version)
  unless the stable `2.1.2` has already been released.

(In practice: pre-releases are scoped to the corresponding base version line unless that base version exists as a stable release.)

---

### Yanked versions

Versions marked as **yanked** are ignored for range-based resolution:

- caret (`^`)
- tilde (`~`)
- wildcards (`x`, `*`)
- comparison ranges (`>=`, `<`, etc.)

Exception / safety fallback:

- If a comparison range has an **exact boundary** that matches a yanked version (for example a lower bound like `>=1.0.0`),
  and that yanked version is the only candidate that can satisfy the constraint,
  KnitPkg may return it as a **last resort** to avoid breaking builds that rely on that fixed boundary.

Exact pins remain explicit:

- If you request `=1.2.3` (or `1.2.3`), and `1.2.3` is yanked, KnitPkg can still resolve it because you asked for that exact version.

---

## Validation rules (common gotchas)

These examples reflect what KnitPkg considers valid/invalid in a manifest dependency version range.

| Specifier | Valid? | Notes |
| :--- | :---: | :--- |
| `1.2.3` | Yes | Exact version. |
| `=1.2.3` | Yes | Exact version (explicit). |
| `^1.2.0` | Yes | Caret range. |
| `1.x` | Yes | Wildcard range. |
| `>=1.0.0 <2.0.0` | Yes | Composite comparison range. |
| `v1.2.3` | No | `v` prefix is not allowed (use numbers only). |
| `1.0` | No | Incomplete SemVer (use `1.0.0` or `1.0.x`). |
| `latest` | No | Text tags are not supported; use `*` instead. |

---

## Practical examples

**Pin exactly (maximum reproducibility):**

```yaml
dependencies:
  calc: "1.0.0"
```

**Allow compatible updates (caret):**

```yaml
dependencies:
  calc: "^1.0.0"
```

**Stay within a minor line (tilde):**

```yaml
dependencies:
  calc: "~1.2.0"
```

**Use latest stable (wildcard):**

```yaml
dependencies:
  calc: "*"
```

**Exclude a problematic release (not-equal operator):**

```yaml
dependencies:
  calc: ">=1.0.0 !=1.2.1"
```