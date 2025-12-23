# Helix — The Modern Dependency Manager for MQL5

**Free • Open-source • MIT Licensed • Built for 2026**


### Why Helix Exists

For over 20 years, MQL5 developers have suffered from the same painful workflow:

- Manual `#include` chaos across dozens of files  
- Copy-pasting headers between projects (and praying nothing breaks)  
- Impossible to implement truly reusable, component-based architecture  
- Extremely hard to maintain clean architectural organization in large projects with multiple developers  
- No reproducible builds — "works on my machine" syndrome  
- No version pinning — silent breaking changes from updated libraries  

**Helix was born to end this suffering — once and for all.**

It brings the modern development practices that Node.js, Rust, Go, and Python developers take for granted — but built from the ground up for the reality of algorithmic trading and the MetaTrader ecosystem.

With Helix, you finally get:

- Clean, modular, maintainable codebases  
- Real component reusability across projects  
- Team-friendly architecture that scales  
- **Reproducible builds** — identical results on every machine  
- **True Semantic Versioning** — `^1.2.0`, `~2.3.4`, `>=1.0.0 <2.0.0`, pre-releases, build metadata — all fully supported  
- Full confidence in every deployment  
- Professional-grade tooling — **100% free**

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

These libraries (examples: `helix-bar`, `helix-calc`, `helix-logger`) are meant to be shared across dozens of EAs, indicators, and scripts. And that’s exactly where traditional `#include` workflows collapse: **broken builds, endless path hell.**

Helix fixes this forever — with pure elegance.

#### While developing an include library (e.g. `Calc.mqh` in `helix-calc`, which depends on `Bar.mqh` in `helix-bar`):

```mql5
#include "../../autocomplete/autocomplete.mqh"   

/* @helix:include "helix/include/Bar/Bar.mqh" */
/* @helix:include "helix/include/Math/Utils.mqh" */
```

You get:

- **Perfect IntelliSense** — every class, method, and constant appears instantly  
- **Zero friction** — code as if all dependencies were already included  
- Full control with `@helix:include` for extra headers when needed


**After `helix install` - in the final EA/indicator:**

```mql5
// ──────────────────────────────────────────────────────────────────
// Dependency includes — resolved and optimized by Helix
// ──────────────────────────────────────────────────────────────────
#include "helix/include/Calc/Calc.mqh"      // Provides SMA, ATR, etc. → automatically pulls Bar via dependency chain
#include "helix/include/Math/Utils.mqh"     // Reusable math utilities — shared across multiple projects

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
| helix package | Pro | Create distributable .zip packages (recursively) |
| helix deploy | Pro | One-click deployment to MT5 terminals |
| Helix Proxy & Audit Trail | Enterprise | Full visibility: who downloaded what, when |
| Compliance & Policy Engine | Enterprise | Block unapproved packages, enforce 2FA |
| On-premise / air-gapped | Enterprise | For banks and high-security environments |


### Join the Revolution
Helix is not just a tool.

It’s the foundation of the next generation of professional MQL5 development.

Whether you're a solo trader building your edge, a prop firm managing 50+ developers,
or a bank running thousands of strategies —  

**Helix scales with you.**

**Free today. Powerful forever.**

```bash
helix init include      # start your first library
helix autocomplete      # code with joy
```

**In your EA/indicator:**

```bash
helix install             # all dependencies solved
```

### Helix Manifest Specification
Interactive documentation: [helix-manifest.html](docs/helix-manifest.html)

**Helix — Because you deserve modern tools.**

**Helix — The dependency manager MQL5 always needed.**

Made with passion

MIT Licensed — Forever free for the community

GitHub: https://github.com/helix-project

Documentation: https://helix.dev

Discord: https://discord.gg/helixWelcome to the future.

**Helix – The future of MQL5 development**
