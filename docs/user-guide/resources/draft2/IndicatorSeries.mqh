//+------------------------------------------------------------------+
//|                                              IndicatorSeries.mqh |
//|                                                Package barhelper |
//|                                      Organization: douglasrechia |
//+------------------------------------------------------------------+

#include "../../../autocomplete/autocomplete.mqh"

/* @knitpkg:include "douglasrechia/bar/TimeSeriesArray.mqh" */

namespace douglasrechia
{

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
TimeSeriesArray<double>* NewTimeSeriesFromIndicator(int indicatorHandler, int indicatorBufferNum, int startPos, int count)
  {
   double array[];
   ArraySetAsSeries(array, true);
   if(CopyBuffer(indicatorHandler, indicatorBufferNum, startPos, count, array) == -1)
      return NULL;

   return new TimeSeriesArray<double>(array);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
TimeSeriesArray<double>* NewTimeSeriesFromIndicator(int indicatorHandler, int indicatorBufferNum, datetime startTime, int count)
  {
   double array[];
   ArraySetAsSeries(array, true);
   if(CopyBuffer(indicatorHandler, indicatorBufferNum, startTime, count, array) == -1)
      return NULL;

   return new TimeSeriesArray<double>(array);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
TimeSeriesArray<double>* NewTimeSeriesFromIndicator(int indicatorHandler, int indicatorBufferNum, datetime startTime, datetime stopTime)
  {
   double array[];
   ArraySetAsSeries(array, true);
   if(CopyBuffer(indicatorHandler, indicatorBufferNum, startTime, stopTime, array) == -1)
      return NULL;

   return new TimeSeriesArray<double>(array);
  }

}
//+------------------------------------------------------------------+
