## The entrypoint source file and the @knitpkg:include directives

As we saw in the [previous section](manifest.md), the entrypoint source file is [src/KnitPkgSMA.mqh](https://forge.mql5.io/DouglasRechia/sma/src/commit/d50674497d1664b21acb0caf056c6e2f8d7be413/src/KnitPkgSMA.mqh). Inside it, you can see special KnitPkg directives:

```mql5 linenums="24" title="src/KnitPkgSMA.mqh"
/* @knitpkg:include "douglasrechia/calc/Calc.mqh" */
/* @knitpkg:include "douglasrechia/bar/TimeSeriesArray.mqh" */
```

Those `@knitpkg:include` directives are the missing link: they point to headers that live **outside** the current repo, inside dependencies.

!!! note "About KnitPkg directives (`@knitpkg:*`)"
    KnitPkg directives are written inside `/* ... */` comment blocks on purpose. They are **not part of standard MQL**, so the source file must remain valid MQL. During `kp install`, KnitPkg scans these comment annotations and uses them to resolve and materialize external headers from your dependencies.

    Important: KnitPkg only recognizes a directive when it is **the only thing on the line**. If there is **anything** before the opening `/*` or **anything** after the closing `*/`, KnitPkg will **not** recognize that directive.

