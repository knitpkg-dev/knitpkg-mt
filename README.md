# KnitPkg for MetaTrader (`kp`)

**A modern package & project manager for MQL5/MQL4 — built for real-world MetaTrader development.**

KnitPkg brings **npm-like dependency workflows** to MetaTrader while staying true to how MQL projects are actually built and shared: **Git repositories + reproducible installs + automation**.

- Main page: [knitpkg.dev](https://knitpkg.dev)  
- Documentation: [docs.knitpkg.dev](https://docs.knitpkg.dev)
- Registry: [registry.knitpkg.dev](https://registry.knitpkg.dev)

---

## Why KnitPkg

### Ship faster with reproducible builds
- **SemVer + ranges (npm-style)**: `^ ~ < > * !=` with **pre-releases** support.
- **Lockfile for reproducibility**: get the *same* dependency graph across machines and time.
- **Yank support**: yanked versions stop being resolved by ranges (without breaking existing builds).

### Dependencies that feel effortless
- **One-command install**: resolve the full dependency tree and download everything ready-to-use.
- **Composable packages**: build packages that reuse other packages (clean dependency trees).
- **Dependency overrides**: take full control by overriding indirect dependency versions (like npm `overrides`).
- **Local path dependencies**: develop packages locally before publishing them.

### Built for MQL ergonomics (not generic C/C++)
- **Standardized MQL project structure** (`src/`, `bin/`, manifest, etc).
- **Automatic compilation** from the CLI.
- **Autocomplete helpers** for MetaEditor to make composed packages pleasant to work with.
- **`@knitpkg:include` directive**: include headers from other packages and have them resolved at install time.

### Public registry (metadata-first)
- KnitPkg uses a public registry to store **project metadata from manifests** (not source code or binaries).
- Supports projects hosted on **Mql5Forge, GitHub, GitLab, and Bitbucket**.
- Installing **public** projects doesn’t require authentication.

---

## Quick Start

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

## (Some) Supported Commands

- `kp init` — initialize a new KnitPkg project (wizard)
- `kp add` — add a dependency to the current project
- `kp install` — resolve and download dependencies
- `kp compile` — compile MQL source files via CLI
- `kp build` — install + compile in one step
- `kp search` — search the KnitPkg public registry
- `kp info` — show details about a registry project
- `kp get` — query the registry for the project metadata, download and build it directly to your MetaTrader instalation
- `kp login` / `kp logout` — manage registry authentication (needed for publishing; not required for installing public projects)
- `kp register` - register a new project or a version of an existing project to the registry (requires registry authentication)

(run `kp --help` for the complete commands list)

---

## Suggested Project Structure (typical)

While KnitPkg supports both MQL5 and MQL4 projects, it encourages a consistent layout:

- `src/` — MQL sources for Expert advisors, indicators, etc
- `bin/` — compiled artifacts
- `knitpkg/` — installed dependency headers made available to your project
- `knitpkg.yaml` — project metadata + dependencies

(See the docs for the authoritative structure and examples.)

---
## Installation

### Prerequisites

1. **(Updated) Windows Terminal**  
   Windows 11 already includes it. On older Windows versions, you may need the newer terminal to correctly render the CLI’s UTF-8 symbols and formatting.  
   - Microsoft Store: [https://aka.ms/terminal](https://aka.ms/terminal)  
   - Other install methods: [https://github.com/microsoft/terminal](https://github.com/microsoft/terminal)

2. **Git client**  
   KnitPkg *leverages Git* for MetaTrader package & project management, so a Git client is essential.  
   - Download: [https://git-scm.com/](https://git-scm.com/)

### Install `kp`

- **GitHub Releases (Windows)**  
  Download `kp.exe` from the repository [Releases](https://github.com/knitpkg-dev/knitpkg-mt/releases) and add it to your `PATH`.

- **PyPI (coming soon)**  
  Distribution via `pip` is in progress. This section will be expanded once the package is published and stabilized.

---

## Explore Seed Projects (Examples by the Author)

If you want real-world examples of how KnitPkg projects and reusable packages can be structured, you can explore the author’s public “seed” projects in the registry.

**MQL5 seeds:**

```bash
kp search mql5 -o douglasrechia
```

**MQL4 seeds:**

```bash
kp search mql5 -o douglasrechia
```

From the results, you can inspect details with `kp info`, or fetch and compile a project locally with `kp get`.


---

## Support the Project

KnitPkg aims to strengthen the MQL ecosystem with better tooling. You can help keep the CLI and the **public registry** running by:

- Giving the repo a **GitHub star**
- Donating via **GitHub Sponsors / Donations**

---

**KnitPkg — The dependency manager MQL5 always needed.**

Made with passion

MIT Licensed — Forever free for the community

GitHub: https://github.com/knitpkg-dev/knitpkg-mt.git

Documentation: https://docs.knitpkg.dev

Discord: (link here when channel is available) to the future.

**KnitPkg – The future of MQL5 development**

---

## Beta Disclaimer (No Warranty / No Liability)

The current version of **KnitPkg** is a **beta release**.

**DISCLAIMER:**  
THE SOFTWARE IS PROVIDED **"AS IS"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

