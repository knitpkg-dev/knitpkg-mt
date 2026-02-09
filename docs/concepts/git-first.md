# Git-first

Most mainstream package managers (like npm, pip, maven, etc.) are built around a central service that hosts and distributes source archives and/or binaries.

KnitPkg takes a different approach: it is Git-first.

Being Git-first means:

- KnitPkg does not store and does not distribute source code or binaries.
- The KnitPkg ecosystem relies on the Git repositories where projects actually live.
- The KnitPkg registry stores and serves metadata (so the CLI can resolve versions), but the CLI fetches code directly from Git.

This design choice has real tradeoffs—good and bad.

## Advantages of Git-first

### Decentralization

Code and binaries remain fully under the control of developers and organizations, without requiring a centralized code-hosting service owned by the package manager.

This reduces “single point of control” concerns and keeps ownership where it belongs: with the project maintainers.

### Transparency

Users can inspect the full project history: commits, branches, tags, pull requests / merge requests. That visibility promotes review culture and collaboration, and makes it easier to understand how a dependency evolves over time.

### Flexibility

Developers can host projects on the Git platform that fits their workflow (for example, different Git providers), without being locked into a single “blessed” hosting service.

## The main caveat of Git-first: External dependency risk
Depending on projects maintained by other developers and organizations introduces risk. If a dependency maintainer:

- publishes a broken version,
- changes a repository from public to private, or
- removes the repository,

then any projects depending on it may break.

In a Git-first ecosystem, availability and stability are strongly tied to the stability of upstream repositories.

---

## Contingency: mitigating dependency risks

Git-first does not mean “trust everyone blindly”. KnitPkg encourages practical habits that reduce ecosystem risk.

### Choose dependencies carefully

Prefer dependencies from developers/organizations with a strong track record and good maintenance reputation.

### Health score (planned)

To help identify reliable projects, KnitPkg plans to introduce a Health score that may take into account signals such as:

- project history and maintenance consistency
- number of broken releases
- number of yanked versions
- telemetry signals
- community feedback

This is intended to guide selection, not to replace engineering judgment.

### Practices that keep projects healthy

KnitPkg encourages simple, high-impact practices that contribute to a high Health score:

- Never change the visibility of a public project.
- Never change the Git URL of a project.
- Never remove a Git repository that has been registered in the registry.
- Never **delete, rename, move, or repoint** any `knitpkg-registry/*` tags. They are required to preserve the registry's immutability guarantees.
- Version correctly using SemVer and maintain a robust testing process, so published package APIs remain stable and consumers aren’t surprised by breaking changes.

## Community goal

KnitPkg aims to foster a strong, engaged community that produces reliable, high-quality packages—reducing code duplication and maximizing productivity.

Git-first makes the ecosystem more decentralized and transparent, but it also asks maintainers and consumers to act responsibly. When everyone plays their part, the ecosystem becomes both powerful and resilient.