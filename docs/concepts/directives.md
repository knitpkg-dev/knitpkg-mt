## The entrypoint and the @knitpkg:include directives

As we saw in the [previous section](manifest.md), the entrypoint file is [src/KnitPkgSMA.mqh](https://forge.mql5.io/DouglasRechia/sma/src/commit/d50674497d1664b21acb0caf056c6e2f8d7be413/src/KnitPkgSMA.mqh). Inside it, you can see special KnitPkg directives:

```mql5 linenums="24" title="src/KnitPkgSMA.mqh excerpt"
/* @knitpkg:include "douglasrechia/calc/Calc.mqh" */
/* @knitpkg:include "douglasrechia/bar/TimeSeriesArray.mqh" */
```

Those `@knitpkg:include` directives are the missing link: they point to headers that live **outside** the current repo, inside dependencies.

!!! note "About KnitPkg directives (`@knitpkg:*`)"
    KnitPkg directives are written inside `/* ... */` comment blocks on purpose. They are **not part of standard MQL**, so they must remain valid MQL source code. During `kp install`, KnitPkg scans these comment annotations and uses them to resolve and materialize external headers from your dependencies.
