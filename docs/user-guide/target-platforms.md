# Target Platforms

KnitPkg supports both `mql5` and `mql4` as target platforms. While all the examples in this user guide were built using **MQL5**, the same principles apply seamlessly to **MQL4**.

---

## Specifying the Target Platform

To indicate the target platform for your project or package, use the `target` field in the `knitpkg.yaml` manifest. For example, a project targeting MQL4 would declare:

```yaml
target: mql4
```

As an example, you can explore existing MQL4 projects by the author using the following command:

```bash
kp search mql4 -o douglasrechia
```

One such example is the [`sma`](https://forge.mql5.io/DouglasRechia/mql4-sma) project for MQL4. Its [manifest](https://forge.mql5.io/DouglasRechia/mql4-sma/src/branch/main/knitpkg.yaml) includes:

```yaml
target: mql4
```

---

## Differences Between MQL5 and MQL4

Although KnitPkg usage is nearly identical across both platforms, there are two important differences to be aware of:

### 1. No Namespace Support in MQL4

MQL4 does not support `namespace`, which means that packages written for MQL4 cannot encapsulate their symbols. This can lead to **symbol conflicts** when multiple packages define classes or functions with the same name.

This is rare when using packages from the same organization, but more likely when combining packages from different organizations.

#### Mitigation Strategy

If a symbol conflict occurs, you can encapsulate one of the conflicting packages into a **MQL4 Library**. This wraps the package into a compiled binary, effectively isolating its symbols and preventing name collisions.

### 2. Platform-Specific Compilation

Ensure that your code and dependencies are compatible with the declared `target`. For example, packages using MQL5-specific features (like `namespace` or `OnChartEvent`) will not compile under MQL4.

---

## Summary

| Feature                     | MQL5           | MQL4           |
|-----------------------------|----------------|----------------|
| `namespace` support         | ✅ Yes        | ❌ No          |
| `target` in manifest        | `mql5`         | `mql4`         |
| Compilation behavior        | MQL5 compiler  | MQL4 compiler  |
| Symbol conflict mitigation  | Not needed     | Use libraries  |

---

## Final Notes

Other than the two differences mentioned above, all other KnitPkg workflows — including `kp init`, `kp add`, `kp install`, `kp compile`, and `kp register` — work exactly the same for both MQL5 and MQL4.

This ensures a consistent developer experience across platforms, while still respecting the technical constraints of each.