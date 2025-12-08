# Helix — The Modern Dependency Manager for MQL5

**Free • Open-source • MIT Licensed • Built for 2025**


### Why Helix Exists

For over 20 years, MQL5 developers have suffered from the same painful workflow:

- Manual `#include` chaos across dozens of files  
- Copy-pasting headers between projects (and praying nothing breaks)  
- Impossible to implement truly reusable, component-based architecture  
- Extremely hard to maintain clean architectural organization in large projects with multiple developers  
- No reproducible builds — "works on my machine" syndrome  
- No version pinning — silent breaking changes from updated libraries  
- No security, compliance, or audit trail in corporate environments  

**Helix was born to end this suffering — once and for all.

It brings the modern development practices that Node.js, Rust, Go, and Python developers take for granted — but built from the ground up for the reality of algorithmic trading and the MetaTrader ecosystem.

With Helix, you finally get:

- Clean, modular, maintainable codebases  
- Real component reusability across projects  
- Team-friendly architecture that scales  
- Full confidence in every build  
- Professional-grade tooling — even in the Free version  

**Helix doesn’t just solve dependency management.**  
**It enables professional MQL5 development at scale.**


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

**Helix Build Directives** are designed exclusively for **include-type projects** — the true reusable components of the MQL5 world.

These libraries (your `helix-bar`, `helix-calc`, `helix-logger`, etc.) are meant to be shared across dozens of EAs, indicators, and scripts. And that’s exactly where traditional `#include` workflows collapse: **zero autocomplete, broken builds, endless path hell.**

Helix fixes this forever — with pure elegance.

#### While developing an include library (e.g. `Calc.mqh`):

```mql5
#include "../../autocomplete/autocomplete.mqh" /* @helix:replace-with "helix/include/Bar/Bar.mqh" */
/* @helix:include      "helix/include/Math/Utils.mqh" */
```

You get:

- **Perfect IntelliSense** — every class, method, and constant appears instantly  
- **Zero friction** — code as if all dependencies were already included  
- Full control with `@helix:include` for extra headers when needed

**After `helix mkinc` - in the final EA/indicator: **

```mql5
#include "helix/include/Bar/Bar.mqh"
#include "helix/include/Math/Utils.mqh"

// Clean • Correct • Fast • No traces of autocomplete
```

The placeholder and directives vanish.

Only pure, professional, production-ready code remains.

**No other tool in the MQL5 ecosystem even attempts this.**

Helix doesn’t just make it possible — it makes it beautiful.

**This is how reusable components should feel in 2026.**

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
