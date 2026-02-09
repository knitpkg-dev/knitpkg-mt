# Telemetry

KnitPkg telemetry exists to collect package usage information: which packages get installed, which versions are adopted, and which dependencies are most common.

This data helps improve the KnitPkg ecosystem by guiding product decisions with real-world usage signals, rather than guesswork.

---

## What telemetry is used for

Telemetry helps the KnitPkg CLI and the registry understand:

- which packages are most installed
- which versions are most adopted
- which dependency graphs are most common

These insights help the KnitPkg team:

- prioritize improvements that matter most to users
- identify potential compatibility issues earlier
- optimize system performance and user experience

Telemetry is also a building block for future ecosystem features, such as a Health score that helps developers choose reliable organizations/projects to depend on (based on objective signals such as adoption and stability patterns).

---

## Privacy and consent

KnitPkg telemetry is designed with two non-negotiable principles:

1. No personal user information is collected.
2. Nothing is sent without user authorization.

Any telemetry data sent to the registry is sent only after the user explicitly authorizes it.

This follows the general best practice for telemetry systems: collect only what you need to improve the product, and avoid sensitive/user-identifying data. See the [KnitPkg CLI Telemetry Policy](../terms-of-service/telemetry.md).

---

## Scope: per project or global

Telemetry can be enabled in two ways:

- Per project: enable telemetry for a single project repository.
- Globally: enable telemetry for all projects on the machine.

This lets you adopt telemetry gradually and keep full control over where it applies.

## How to enable telemetry

Telemetry authorization and configuration are managed through the CLI.

See the [CLI reference](../reference/cli.md) for the exact commands and configuration options.