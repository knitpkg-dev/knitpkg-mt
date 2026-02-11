# Local Dependencies

In this section, we will demonstrate how to use **local dependencies** during development. We’ll enhance the [`expertdemo`](https://forge.mql5.io/DouglasRechia/expertdemo/src/commit/fa5ea913177f0b01a66306c2be36743d6bc9f163) project with a simple SMA-based trading strategy using the `CrossUp` function from the new `barhelper` package — even before `barhelper` is published to the registry.

---

## Why Use Local Dependencies?

Even if you write thorough unit tests (and we know you always do), you might still want to test your package in a real project before publishing it. In other cases, you may want to integrate a package into a consumer project while still developing it. KnitPkg supports this common workflow through **local dependencies**.

---

## Adding a Local Dependency

To add a local dependency, you must manually edit the `knitpkg.yaml` manifest and provide the path to the local package directory. There are two supported formats:

- **Relative path** (must start with `./` or `../` and use `/` as separator)
- **File URI** (must start with `file://`, supports both `/` and `\` separators, and can be absolute or relative)

Here’s how to add `barhelper` as a local dependency to [`expertdemo`](https://forge.mql5.io/DouglasRechia/expertdemo/src/commit/fa5ea913177f0b01a66306c2be36743d6bc9f163), using a relative path:

```yaml linenums="26" hl_lines="3"
dependencies:
    '@douglasrechia/barhelper': ../../Scripts/barhelper
```

## Should transitive dependencies be declared?

We see that `barhelper` depends on `bar`, so `bar` will be available to `expertdemo` as a transitive dependency. But should we declare `bar` explicitly in the manifest?

Let’s consider:

- `barhelper` exposes a function whose signature uses `ITimeSeries`, a type declared in `bar`. This is a dependency in the **API**, not just the implementation.
- If `barhelper` used `bar` only internally (i.e., no symbols from `bar` exposed in its API), then `expertdemo` wouldn’t need to depend on `bar`.
- However, `expertdemo` also uses `bar` directly — for example, `BarWatcher` and `BarMqlRates`.

From this, we conclude that a transitive dependency should be declared explicitly if:

- The direct dependency’s API uses symbols from the transitive dependency
- The consumer project uses symbols from the transitive dependency directly

So yes, `expertdemo` should add `bar` explicitly. Let’s do that:

```bash
kp add @douglasrechia/bar
```

Now the dependencies section looks like this:

```yaml
dependencies:
  '@douglasrechia/bar': ^1.0.0
  '@douglasrechia/barhelper': ../../Scripts/barhelper
```

---

## Updating the Entrypoint

The `expertdemo` project uses [Flat mode](https://forge.mql5.io/DouglasRechia/expertdemo/src/commit/fa5ea913177f0b01a66306c2be36743d6bc9f163/knitpkg.yaml), and its entrypoint is [`KnitPkgExpertDemo.mqh`](https://forge.mql5.io/DouglasRechia/expertdemo/src/commit/fa5ea913177f0b01a66306c2be36743d6bc9f163/src/KnitPkgExpertDemo.mqh).

We need to:

- Add `Cross.mqh` to include `Cross` and `CrossUp`
- Remove `Calc.mqh` (no longer needed)
- Add `TimeSeriesArray.mqh` to construct the input series

Here’s the updated include section:

```mql5 linenums="28"
/* @knitpkg:include "douglasrechia/bar/BarWatcher.mqh" */
/* @knitpkg:include "douglasrechia/bar/BarMqlRates.mqh" */
/* @knitpkg:include "douglasrechia/bar/TimeSeriesArray.mqh" */
/* @knitpkg:include "douglasrechia/barhelper/Cross.mqh" */
```

---

## Installing Dependencies

Now run:

```bash
kp install
```

You should see output like this:

![alt text](images/vscode-install-local-dependency.png)

Notice that `@douglasrechia/barhelper` appears in the dependency tree. This means the flat file now includes `Cross` and `CrossUp`.

Let’s verify in MetaEditor:

![alt text](images/metaeditor-expertdemo-crossup.png)

The IntelliSense confirms that `CrossUp` is available via the generated flat file `knitpkg/flat/KnitPkgExpertDemo_flat.mqh`.

---

## Updating `expertdemo`

To avoid making this guide too long, we’ve provided the updated source files here:

- [KnitPkgExpertDemo.mq5](resources/KnitPkgExpertDemo.mq5)
- [KnitPkgExpertDemo.mqh](resources/KnitPkgExpertDemo.mqh)

Now `expertdemo` is a fully functional Expert Advisor. Below is the equity curve for EURUSD H4 from 2025-01-01 to 2025-12-31 using default parameters:

![alt text](images/expertdemo-equity.png)

---

Congratulations! You’ve successfully used a local dependency to integrate and test a package before publishing it. This is a powerful workflow for iterative development and real-world validation.