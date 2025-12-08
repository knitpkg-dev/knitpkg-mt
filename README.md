# Helix — The Modern Dependency Manager for MQL5

**Free • Open-source • MIT Licensed • Built for 2025**


### Why Helix Exists

For over 20 years, MQL5 developers have suffered from the same painful workflow:

- Manual `#include` chaos across dozens of files  
- Copy-pasting headers between projects  
- Broken autocomplete when using external libraries  
- No reproducible builds  
- No version pinning  
- No security or audit trail in corporate environments  

**Helix ends this forever.**

Helix brings modern software engineering practices to the MetaTrader ecosystem — 
the same tools that Node.js, Rust, Go, and Python developers take for granted — 
but built from the ground up for algorithmic trading.

### Installation

**Tip**: _We strongly recommend Poetry — it guarantees the exact same environment across 
all machines_.

#### Prerequisites
- Python 3.13+
- [Poetry](https://python-poetry.org/docs/#installation)

#### Install with Poetry

```bash
# Clone the repository
git clone https://github.com/helix-project/helix.git
cd helix

# Install with Poetry (creates isolated environment)
poetry install

# Enter the virtual environment
poetry shell

# You're ready!
helix --version
```

### Free Edition — Already More Powerful Than Anything Else Available

| Feature                         | Status | Description                                                    |
|---------------------------------|--------|----------------------------------------------------------------|
| Dependency resolution           | Done   | Local and remote (Git) dependencies with full SemVer support   |
| `helix install` / `build`       | Done   | Reproducible, lockfile-based installs                          |
| `helix autocomplete`            | Done   | Full IntelliSense during development                           |
| **Helix Build Directives**      | Done   | Revolutionary development-time includes                        |
| Flat and Include modes          | Done   | One-click clean builds                                         |


### The Crown Jewel: **Helix Build Directives**

The most loved feature in the Helix ecosystem — and for good reason.

```mql5
#include "../../autocomplete/autocomplete.mqh" /* @helix:replace-with "helix/include/Bar/Bar.mqh" */
```

This single line gives you:
- Perfect autocomplete while writing code  
- Zero placeholder files in final builds  
- Clean, correct, and fast-compiling output  
- Optional extra includes via /* @helix:include "path/to/Extra.mqh" */

**No other tool in the MQL5 world comes close.**
It’s not magic.
It’s **engineering elegance**.


### Pro & Enterprise — The Future (2026)
| Feature | Edition | Description |
|---------|---------|-------------|
| Private Git repositories | Pro | GitHub, GitLab, Bitbucket, Azure DevOps |
| SSO / OAuth login | Pro | No more personal access tokens |
| helix package | Pro | Create distributable .zip packages |
| helix deploy | Pro | One-click deployment to MT5 terminals |
| Helix Proxy & Audit Trail | Enterprise | Full visibility: who downloaded what, when |
| Compliance & Policy Engine | Enterprise | Block unapproved packages, enforce 2FA |
| On-premise / air-gapped | Enterprise | For banks and high-security environments |


### Join the Revolution
Helix is not just a tool.
It’s the foundation of the next generation of professional MQL5 development.
Whether you're a solo trader building your edge,
a prop firm managing 50+ developers,
or a bank running thousands of strategies —  
**Helix scales with you.**
**Free today. Powerful forever.**

```bash
helix init include      # start your first library
helix autocomplete      # code with joy
helix mkinc             # ship with confidence
```

### Helix Manifest Specification
Interactive documentation: [helix-manifest.html](docs/helix-manifest.html)

**Helix 2025 — Because you deserve modern tools.**
**Helix 2025 — The dependency manager MQL5 always needed.**

Made with passion
MIT Licensed — Forever free for the community

GitHub: https://github.com/helix-project
Documentation: https://helix.dev
Discord: https://discord.gg/helixWelcome to the future.

**Welcome to the future**
