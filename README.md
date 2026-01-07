# KnitPkg — The Modern Dependency Manager for MQL5

**Free • Open-source • MIT Licensed • Built for 2026**


### Why KnitPkg Exists

For over 20 years, MQL5 developers have suffered from the same painful workflow:

- Manual `#include` chaos across dozens of files  
- Copy-pasting headers between projects (and praying nothing breaks)  
- Impossible to implement truly reusable, component-based architecture  
- Extremely hard to maintain clean architectural organization in large projects with multiple developers  
- No reproducible builds — "works on my machine" syndrome  
- No version pinning — silent breaking changes from updated libraries  

**KnitPkg was born to end this suffering — once and for all.**

It brings the modern development practices that Node.js, Rust, Go, and Python developers take for granted — but built from the ground up for the reality of algorithmic trading and the MetaTrader ecosystem.

With KnitPkg, you finally get:

- Clean, modular, maintainable codebases  
- Real component reusability across projects  
- Team-friendly architecture that scales  
- **Reproducible builds** — identical results on every machine  
- **True Semantic Versioning** — `^1.2.0`, `~2.3.4`, `>=1.0.0 <2.0.0`, pre-releases, build metadata — all fully supported  
- Full confidence in every deployment  
- Professional-grade tooling — **100% free**

**KnitPkg doesn’t just solve dependency management.**  
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
git clone https://github.com/knitpkg-dev/knitpkg-mt.git
cd knitpkg-mt

# Install with Poetry (creates isolated environment)
poetry install

# Enter the virtual environment
poetry shell

# You're ready!
kp-mt --version
```

### Free Edition — Already More Powerful Than Anything Else Available

| Feature                         | Status | Description                                                    |
|---------------------------------|--------|----------------------------------------------------------------|
| Dependency resolution           | Done   | Local and remote (Git) dependencies with full SemVer support   |
| `kp-mt install` / `build`  | Done   | Reproducible, lockfile-based installs                          |
| `kp-mt autocomplete`       | Done   | Full IntelliSense during development                           |
| **KnitPkg Build Directives**      | Done   | Revolutionary development-time includes                        |
| Flat and Include modes          | Done   | One-click clean builds                                         |


### The Crown Jewel: **KnitPkg Build Directives**

The most loved feature in the KnitPkg ecosystem — and for good reason.

**KnitPkg Build Directives** are designed exclusively for **include-type projects** — the true reusable components of the MQL5 world.

These libraries (examples: `knitpkg-bar`, `knitpkg-calc`, `knitpkg-logger`) are meant to be shared across dozens of EAs, indicators, and scripts. And that’s exactly where traditional `#include` workflows collapse: **broken builds, endless path hell.**

KnitPkg fixes this forever — with pure elegance.

#### While developing an include library (e.g. `Calc.mqh` in `knitpkg-calc`, which depends on `Bar.mqh` in `knitpkg-bar`):

```mql5
#include "../../autocomplete/autocomplete.mqh"   

/* @knitpkg:include "knitpkg/include/Bar/Bar.mqh" */
/* @knitpkg:include "knitpkg/include/Math/Utils.mqh" */
```

You get:

- **Perfect IntelliSense** — every class, method, and constant appears instantly  
- **Zero friction** — code as if all dependencies were already included  
- Full control with `@knitpkg:include` for extra headers when needed


**After `knitpkg install` - in the final EA/indicator:**

```mql5
// ──────────────────────────────────────────────────────────────────
// Dependency includes — resolved and optimized by KnitPkg
// ──────────────────────────────────────────────────────────────────
#include "knitpkg/include/Calc/Calc.mqh"      // Provides SMA, ATR, etc. → automatically pulls Bar via dependency chain
#include "knitpkg/include/Math/Utils.mqh"     // Reusable math utilities — shared across multiple projects

// Clean • Correct • Fast • No traces of autocomplete
```

The placeholder and directives vanish.

Only pure, professional, production-ready code remains.

**No other tool in the MQL5 ecosystem even attempts this.**

KnitPkg doesn’t just make it possible — it makes it beautiful.

**This is how reusable components should feel in 2026.**

It’s not magic.
It’s **engineering elegance**.


### Pro & Enterprise — The Future (2026)
| Feature | Edition | Description |
|---------|---------|-------------|
| Private Git repositories | Pro | GitHub, GitLab, Bitbucket, Azure DevOps |
| SSO / OAuth login | Pro | No more personal access tokens |
| knitpkg package | Pro | Create distributable .zip packages (recursively) |
| knitpkg deploy | Pro | One-click deployment to MT5 terminals |
| KnitPkg Proxy & Audit Trail | Enterprise | Full visibility: who downloaded what, when |
| Compliance & Policy Engine | Enterprise | Block unapproved packages, enforce 2FA |
| On-premise / air-gapped | Enterprise | For banks and high-security environments |


### Join the Revolution
KnitPkg is not just a tool.

It’s the foundation of the next generation of professional MQL5 development.

Whether you're a solo trader building your edge, a prop firm managing 50+ developers,
or a bank running thousands of strategies —  

**KnitPkg scales with you.**

**Free today. Powerful forever.**

```bash
kp-mt init include      # start your first library
kp-mt autocomplete      # code with joy
```

**In your EA/indicator:**

```bash
kp-mt install             # all dependencies solved
```

### KnitPkg Manifest Specification
Interactive documentation: [knitpkg-manifest.html](docs/knitpkg-manifest.html)

**KnitPkg — Because you deserve modern tools.**

**KnitPkg — The dependency manager MQL5 always needed.**

Made with passion

MIT Licensed — Forever free for the community

GitHub: https://github.com/knitpkg-dev/knitpkg-mt.git

Documentation: https://knitpkg.dev

Discord: https://discord.gg/knitpkgWelcome to the future.

**KnitPkg – The future of MQL5 development**
