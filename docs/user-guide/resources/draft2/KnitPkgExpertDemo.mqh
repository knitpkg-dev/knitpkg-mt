//+------------------------------------------------------------------+
//|                                            KnitPkgExpertDemo.mqh |
//|                                                                  |
//|                    KnitPkg for MetaTrader — Demo                 |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Entry point header for the KnitPkgExpertDemo Expert Advisor.    |
//|  Resolves and includes all dependencies from @douglasrechia/calc |
//|  and @douglasrechia/bar for use in the EA.                       |
//|                                                                  |
//|  DISCLAIMER:                                                     |
//|  This code is provided AS-IS for educational purposes only.      |
//|  No warranty is given. The author assumes no liability for any   |
//|  damages or legal consequences arising from its use.             |
//|                                                                  |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

//------------------------------------------------------------------
// Add here your includes from the resolved dependencies
//------------------------------------------------------------------

/* @knitpkg:include "douglasrechia/bar/BarWatcher.mqh" */
/* @knitpkg:include "douglasrechia/bar/BarMqlRates.mqh" */
/* @knitpkg:include "douglasrechia/bar/TimeSeriesArray.mqh" */
/* @knitpkg:include "douglasrechia/barhelper/Cross.mqh" */
/* @knitpkg:include "douglasrechia/barhelper/IndicatorSeries.mqh" */