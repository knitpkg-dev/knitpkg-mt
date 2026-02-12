//+------------------------------------------------------------------+
//|                                            KnitPkgExpertDemo.mq5 |
//|                                                                  |
//|                    KnitPkg for MetaTrader — Demo                 |
//|                                                                  |
//|                          MIT License                             |
//|                    Copyright (c) 2025 Douglas Rechia             |
//|                                                                  |
//|  Expert Advisor demonstrating package reuse with KnitPkg.        |
//|  Uses @douglasrechia/calc and @douglasrechia/bar to implement    |
//|  a simple trading logic based on bar changes and SMA calculation.|
//|                                                                  |
//|  DISCLAIMER:                                                     |
//|  This code is provided AS-IS for educational purposes only.      |
//|  No warranty is given. The author assumes no liability for any   |
//|  damages or legal consequences arising from its use.             |
//|                                                                  |
//+------------------------------------------------------------------+

#property copyright "Douglas Rechia"
#property link      "https://www.mql5.com"
#property version   "2.00"

//------------------------------------------------------------------
// Flat mode include — resolves dependencies and enables
// MetaEditor IntelliSense. Run `kp install` to generate.
//------------------------------------------------------------------
#include "../knitpkg/flat/KnitPkgExpertDemo_flat.mqh"

// Standard Library includes. No conflict with KnitPkg at all.
#include <Trade/PositionInfo.mqh>
#include <Trade/Trade.mqh>

input int sma1period = 10;          // Short term SMA period
input int sma2period = 25;          // Mid term SMA period
input int sma3period = 200;         // Short term SMA period
input bool filterEnabled = false;   // Entry filter on/off

// Global variables
douglasrechia::BarWatcher *barWatcher;
douglasrechia::BarMqlRates *myBar;
//---
int sma1handle = INVALID_HANDLE;
int sma2handle = INVALID_HANDLE;
int sma3handle = INVALID_HANDLE;
//---
CPositionInfo positionInfo;
CTrade trade;
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
//---
   barWatcher = new douglasrechia::BarWatcher();
   myBar = new douglasrechia::BarMqlRates();
//--- Validate that sma1.period < sma2.period < sma3.period
   if(!(sma1period < sma2period && sma2period < sma3period))
     {
      Print("Invalid moving average periods");
      return(INIT_FAILED);
     }
//--- Handlers for SMA indicators calculated at three different periods
   sma1handle = iCustom(_Symbol, _Period, "sma/bin/KnitPkgSMA", sma1period);
   sma2handle = iCustom(_Symbol, _Period, "sma/bin/KnitPkgSMA", sma2period);
   sma3handle = iCustom(_Symbol, _Period, "sma/bin/KnitPkgSMA", sma3period);
   if(sma1handle == INVALID_HANDLE || sma2handle == INVALID_HANDLE || sma3handle == INVALID_HANDLE)
     {
      Print("Could not initialize KnitPkgSMA indicator");
      return(INIT_FAILED);
     }
//---
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//--- Releasing indicator resources
   if(sma1handle != INVALID_HANDLE)
      IndicatorRelease(sma1handle);
   if(sma2handle != INVALID_HANDLE)
      IndicatorRelease(sma2handle);
   if(sma3handle != INVALID_HANDLE)
      IndicatorRelease(sma3handle);
//---
   delete barWatcher;
   delete myBar;
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
//---
   barWatcher.Update();
   if(barWatcher.IsFirstTick())
     {
      Print("Hello world! This is KnitPkg's debut EA. I'm mostly here for show, but hey, looking good is half the battle! ;-)");
     }
   else
      if(barWatcher.IsNewBar())
        {
         OnNewBar();
        }
  }

//+------------------------------------------------------------------+
//| OnNewBar — called when a new bar is formed                       |
//+------------------------------------------------------------------+
void OnNewBar()
  {
//--- Get latest 5 bars data
   myBar.Refresh(5);

//--- Get the 5 most recent values of SMA into the TimeSeries.
//--- Do it for the three SMAs.
   double sma1array[];
   ArraySetAsSeries(sma1array, true);
   CopyBuffer(sma1handle, 0, 0, 5, sma1array);
   douglasrechia::TimeSeriesArray<double> sma1(sma1array);

   double sma2array[];
   ArraySetAsSeries(sma2array, true);
   CopyBuffer(sma2handle, 0, 0, 5, sma2array);
   douglasrechia::TimeSeriesArray<double> sma2(sma2array);

   double sma3array[];
   ArraySetAsSeries(sma3array, true);
   CopyBuffer(sma3handle, 0, 0, 5, sma3array);
   douglasrechia::TimeSeriesArray<double> sma3(sma3array);

   if(!positionInfo.Select(_Symbol))
     {
      //--- No position. Check filter conditions.
      if(!filterEnabled || (myBar.Close(1) > sma1.ValueAtShift(1) &&
                            sma1.ValueAtShift(1) > sma2.ValueAtShift(1) &&
                            sma2.ValueAtShift(1) > sma3.ValueAtShift(1)))
        {
         //--- Open position if Short term sma1 crosses up Mid term sma2
         if(douglasrechia::CrossUp(sma1, sma2, 1))
           {
            Print(StringFormat("[%s] Let's do it", TimeToString(myBar.Time(0))));
            trade.Buy(1);
           }
        }
     }
   else
     {
      //--- Position is found. Close it if Short term sma1 crosses down Mid term sma2.
      if(douglasrechia::CrossUp(sma2, sma1, 1))
        {
         Print(StringFormat("[%s] Time to go", TimeToString(myBar.Time(0))));
         trade.PositionClose(_Symbol);
        }
     }

  }

//+------------------------------------------------------------------+
