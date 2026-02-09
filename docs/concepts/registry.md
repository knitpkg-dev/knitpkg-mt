# Registry

KnitPkg is split into two parts:

- **The CLI**: the tool you run locally and interact with directly (kp ...).
- **The registry**: a web service that stores metadata extracted from project manifests and serves that metadata to the CLI.

The registry exists so the CLI can reliably discover projects and resolve dependencies, while source code continues to live in Git repositories.

---

## What the registry is

The registry stores **manifest metadata** for KnitPkg-managed projects (such as target, project type, organization, name, published versions, and repository information).

It is a web service used by the KnitPkg CLI to:

- search and query public projects,
- resolve dependency version ranges into a concrete version, and
- locate the exact source revision (commit) corresponding to that resolved version.

---

## What the registry is NOT

The registry:

- does not store MQL source code,
- does not distribute source code, and
- does not distribute binaries.

Instead, it tells the CLI where the code is (repo URL) and which exact revision to fetch (commit hash).  

## Why the CLI needs the registry during kp install

When you run kp install, the CLI needs an exact answer for every dependency:

- If a dependency is declared with a version range (specifier), the CLI asks the registry for the latest version that satisfies that range.
- In practice, the registry resolves the specifier and returns the Git commit hash that represents that exact version.  
- Then the CLI downloads that exact commit and installs the dependency locally.

This is the key contract:

- The registry resolves ranges → exact versions → exact commits.
- The CLI fetches the code from Git and performs the install (include tree / flat file generation, directive resolution, etc.).

---

### Example: resolving a dependency specifier

For the curious, you can call the registry [resolve endpoint](https://api.registry.knitpkg.dev/v1/project/mql5/douglasrechia/bar/^1.0.0/resolve) directly (for example, from a browser or API tool like Postman) to see how specifiers are resolved.

Resolving @douglasrechia/bar with the specifier ^1.0.0 returns a response like:

```json 
{
    "project_id": 2,
    "repo_url": "https://forge.mql5.io/DouglasRechia/bar.git",
    "commit_hash": "1b865e19fcfbbb907a6aa3f95a9ff4812181bcc8",
    "provider": "mql5forge",
    "resolved_version": "1.0.0",
    "resolved_version_id": 2,
    "specifier": "^1.0.0",
    "target": "mql5",
    "type": "package",
    "organization": "douglasrechia",
    "name": "bar",
    "source_type": "git",
    "yanked": false,
    "is_public": true
}
```

The important detail is that the registry does not return code. It returns metadata (including repo_url and commit_hash) so the CLI can fetch the correct revision.

## Version immutability and yanking

In the registry, a published version is immutable. Once a version is published, it will:

- always resolve to the same commit_hash, and
- never be deleted.

This is a guarantee provided by the registry.

As a contingency measure, a project owner may mark a version as yanked. Yanked versions are not removed, but are treated as withdrawn to discourage new usage while preserving stability for existing builds. This should not break the ecosystem thanks to the [version ranges](reference/version-ranges.md) system, which enables dependency resolution to move away from yanked releases without forcing a hard break.

## Using the registry from the CLI

Typically you interact with the registry through KnitPkg commands:

- `kp status` — Show registry status and configuration information
- `kp search` — Search public projects
- `kp info` — Show detailed information about a project
- `kp get` — Download and automatically build a project with a single command
- `kp login` / `kp logout` — Authenticate to register/manage projects
- `kp whoami` — Show information about the currently authenticated user
- `kp register` — Register a project in the registry
- `kp yank` — Yank a package version from the registry

## Registry and reproducible builds
By default, `kp install` uses the registry to resolve each dependency range to the latest compatible release. 

For reproducible builds, KnitPkg can install using locked versions (for example with `kp install --locked`), ensuring the same dependency versions are used even if newer ones are published later. This workflow is referenced in package documentation as well.  

## Future plans
A simple web UI for browsing and searching projects in the registry is planned to be released soon.
