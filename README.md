# KnitPkg for MetaTrader (`kp`)

**A modern package & project manager for MQL5/MQL4 — built for real-world MetaTrader development.**

**KnitPkg** is a modern **package and project manager for MQL5/MQL4**, bringing an *npm-like* dependency workflow to real-world MetaTrader development.

MetaTrader projects often evolve through manual copy/paste, ad-hoc folder sharing, and “it works on my machine” dependency drift. KnitPkg exists to fix that by making code reuse and collaboration **predictable, reproducible, and automated**—without changing how MQL developers already publish code (Git repos).

- Home page: [knitpkg.dev](https://knitpkg.dev)  
- Documentation: [docs.knitpkg.dev](https://docs.knitpkg.dev)
- Registry: [registry.knitpkg.dev](https://registry.knitpkg.dev)

---

## What KnitPkg is

KnitPkg is built around a **Git-first** model:

- Your code lives in **Git repositories** (Mql5Forge, GitHub, GitLab, Bitbucket).
- KnitPkg acts as a **metadata registry** that indexes projects via their manifests (it does **not** host your source or binaries).
- A **CLI tool** installs dependencies, resolves versions (SemVer + ranges), generates reproducible installs via a lock file, and can automate compilation.

The public registry API is available and currently operational.

## Why developers use KnitPkg

KnitPkg focuses on the pain points that show up fast in MQL development:

- **Versioned dependencies** (SemVer + ranges like `^`, `~`, `<`, `>`, `*`, `!=`)
- **Reproducible builds** with a lock file
- **Composed packages** (dependency trees), including helpers like autocomplete and `@knitpkg:include`
- **Safe ecosystem maintenance** with *yanked* versions (removed from range resolution without breaking history)
- **Git-host login via OAuth** for publishing (no extra KnitPkg account); public installs need no auth

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

3. **MetaTrader 4 and/or MetaTrader 5**
   Available at: [https://www.mql5.com/](https://www.mql5.com/).

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

See [Getting started](https://docs.knitpkg.dev/getting-started/) for a quick introduction and first steps using KnitPkg.


---

## Support the Project

KnitPkg aims to strengthen the MQL ecosystem with better tooling. You can help keep the CLI and the **public registry** running by:

- Giving the repo a **GitHub star**
- Donating via **GitHub Sponsors / Donations** (not yet available)

---

**KnitPkg — The dependency manager MQL always needed**

[Home page](https://knitpkg.dev/) - [Browse Registry](https://registry.knitpkg.dev/)

[GitHub](https://github.com/knitpkg-dev/knitpkg-mt.git) - [Join Discord](https://discord.gg/bWvWpjw5m4) - [contact@knitpkg.dev](mailto:contact@knitpkg.dev)

MIT Licensed — Forever free for the community

**KnitPkg – The future of MQL5 development.**

---

## Beta Disclaimer (No Warranty / No Liability)

The current version of **KnitPkg** is a **beta release**.

**DISCLAIMER:**  
THE SOFTWARE IS PROVIDED **"AS IS"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

