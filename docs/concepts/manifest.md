```yaml
target: mql5
type: indicator

organization: douglasrechia
name: sma
version: 1.0.0
version_description: Initial version

# Registry search fields
description: KnitPkg for Metatrader - SMA Indicator Demo
keywords: [ "indicator", "sma", "showcase" ]
author: Douglas Rechia
license: MIT

# Include mode resolution
include_mode: flat

# File to be flattened with all the dependencies for this project
entrypoints:
  - src/KnitPkgSMA.mqh

compile:
  - src/KnitPkgSMA.mq5

# Dependencies of the project
dependencies:
    '@douglasrechia/calc': ^1.0.0
```