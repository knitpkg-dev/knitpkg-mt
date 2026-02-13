//+------------------------------------------------------------------+
//|                                                          atr.mq5 |
//|                                                    Indicator atr |
//|                                      Organization: douglasrechia |
//+------------------------------------------------------------------+
#property copyright   "Douglas Rechia"
#property link        "https://knitpkg.dev"
#property version     "1.00"
#property description ""
#property description "Version: 1.0.0"
#property description ""
#property description "Description: ATR showdemo for MetaTrader5"
#property description "Organization: douglasrechia"
#property description "Author: Douglas Rechia"
#property description "License: MIT"
#property description ""
#property description "Powered by KnitPkg for MetaTrader"
#property description "https://knitpkg.dev"

#include "../knitpkg/include/douglasrechia/bar/BarArray.mqh"
#include "../knitpkg/include/douglasrechia/calc/Calc.mqh"

//--- indicator settings
#property indicator_separate_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrDodgerBlue

//--- input parameters
input int InpATRPeriod=14; // ATR period

//--- indicator buffer
double ATRBuffer[];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
  {
//--- indicator buffers mapping
   SetIndexBuffer(0, ATRBuffer, INDICATOR_DATA);
//--- set index labels
   PlotIndexSetString(0,PLOT_LABEL,"KnitPkg ATR("+string(InpATRPeriod)+")");
//--- indicator name
   IndicatorSetString(INDICATOR_SHORTNAME,"KnitPkg ATR");
//--- indexes draw begin settings
   PlotIndexSetInteger(0,PLOT_DRAW_BEGIN,InpATRPeriod);
//--- number of digits of indicator value
   IndicatorSetInteger(INDICATOR_DIGITS,_Digits);
//---
   ArraySetAsSeries(ATRBuffer, true);
//---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int32_t rates_total,
                const int32_t prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int32_t &spread[])
  {
//---
   if(rates_total < InpATRPeriod+1)
      return(0);
   if(prev_calculated >= rates_total)
      return rates_total;

   douglasrechia::BarArray bars(time, open, high, low, close, volume, tick_volume,
                                prev_calculated - InpATRPeriod - 2, rates_total-1, true);

   // The following loop recalculates the ATR for the most recent bars.
   // This is necessary because the current bar's data can change with each tick
   // until its formation is complete. The `shiftStart` variable determines
   // the initial index for recalculation, ensuring that the ATR is accurately
   // updated for the latest bar and any preceding bars affected by recent data changes.
   int shiftStart = rates_total-prev_calculated;
   if(shiftStart >= rates_total)
      shiftStart--;

   for(int shift=shiftStart; shift>=0 && !IsStopped(); shift--)
     {
      ATRBuffer[shift] = douglasrechia::ATR(bars, InpATRPeriod, shift);
     }

//--- return value of prev_calculated for next call
   return(rates_total);
  }
//+------------------------------------------------------------------+
