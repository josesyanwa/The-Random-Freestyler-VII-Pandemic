//+------------------------------------------------------------------+
//|                                           LastTradeEA.mq5        |
//|                        Copyright 2025, Your Name or Company Name |
//|                                             https://www.example.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Your Name or Company Name"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict

// Define the file path within MQL5\Files
string filePath = "last_trade.json"; // Saved in MQL5\Files folder

struct OpenTradeInfo
{
   string symbol;
   string trade_type;
   double open_price;
   datetime open_time;
   ulong ticket;
   long duration;
};

void SortOpenTradesDescending(int &indices[], OpenTradeInfo &trades[])
{
   int n = ArraySize(indices);
   for(int i = 0; i < n; i++)
   {
      for(int j = i + 1; j < n; j++)
      {
         if(trades[indices[i]].open_time < trades[indices[j]].open_time)
         {
            int temp = indices[i];
            indices[i] = indices[j];
            indices[j] = temp;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(10); // Set timer to run every 10 seconds
   Print("EA initialized and starting periodic updates every 10 seconds.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer(); // Stop the timer
   Print("EA deinitialized.");
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Initialize history for the last 24 hours
   datetime fromTime = TimeCurrent() - 86400; // 24 hours in seconds
   datetime toTime = TimeCurrent();
   
   if (!HistorySelect(fromTime, toTime))
   {
      Print("Failed to select history, error code: ", GetLastError());
      return;
   }

   // Find the latest closed trade
   int totalDeals = HistoryDealsTotal();
   ulong latestClosedTicket = 0;
   datetime latestClosedTime = 0;
   if (totalDeals > 0)
   {
      for (int i = totalDeals - 1; i >= 0; i--)
      {
         ulong ticket = HistoryDealGetTicket(i);
         datetime dealTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
         ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);
         if (entry == DEAL_ENTRY_OUT)
         {
            latestClosedTime = dealTime;
            latestClosedTicket = ticket;
            break;
         }
      }
   }

   string closedSymbol = "";
   double closePrice = 0;
   double closedProfit = 0;
   datetime closeTime = 0;
   double closedOpenPrice = 0;
   datetime closedOpenTime = 0;
   string closedTradeType = "";
   long closedDuration = 0;

   bool hasClosed = false;
   if (latestClosedTicket != 0)
   {
      hasClosed = true;
      closedSymbol = HistoryDealGetString(latestClosedTicket, DEAL_SYMBOL);
      closePrice = HistoryDealGetDouble(latestClosedTicket, DEAL_PRICE);
      closedProfit = HistoryDealGetDouble(latestClosedTicket, DEAL_PROFIT);
      closeTime = (datetime)HistoryDealGetInteger(latestClosedTicket, DEAL_TIME);

      // Find the corresponding open deal
      ulong positionId = HistoryDealGetInteger(latestClosedTicket, DEAL_POSITION_ID);
      for (int i = 0; i < totalDeals; i++)
      {
         ulong ticket = HistoryDealGetTicket(i);
         if (HistoryDealGetInteger(ticket, DEAL_POSITION_ID) == positionId &&
             HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN)
         {
            closedOpenTime = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
            closedOpenPrice = HistoryDealGetDouble(ticket, DEAL_PRICE);
            ENUM_DEAL_TYPE inType = (ENUM_DEAL_TYPE)HistoryDealGetInteger(ticket, DEAL_TYPE);
            closedTradeType = (inType == DEAL_TYPE_BUY) ? "Buy" : "Sell";
            break;
         }
      }

      closedDuration = closeTime - closedOpenTime;
   }

   // Collect all open positions and find the latest one
   OpenTradeInfo latestOpen;
   latestOpen.open_time = 0;
   bool hasOpen = false;
   const long TWENTY_MINUTES = 20 * 60; // 1200 seconds
   for (int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if (PositionSelectByTicket(ticket))
      {
         datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
         if (openTime > latestOpen.open_time)
         {
            latestOpen.symbol = PositionGetString(POSITION_SYMBOL);
            latestOpen.open_price = PositionGetDouble(POSITION_PRICE_OPEN);
            ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            latestOpen.trade_type = (ptype == POSITION_TYPE_BUY) ? "Buy" : "Sell";
            latestOpen.open_time = openTime;
            latestOpen.ticket = ticket;
            latestOpen.duration = TimeCurrent() - openTime;
            hasOpen = true;
         }
      }
   }

   // Decide which trade to use
   string jsonData = "";
   string tradeStatus = "";
   if (hasOpen && latestOpen.duration > TWENTY_MINUTES && (!hasClosed || latestOpen.open_time > latestClosedTime))
   {
      // Use the latest open trade if it qualifies and is more recent than closed
      tradeStatus = "Open trade";
      jsonData = "{";
      jsonData += "\"status\": \"Open\",";
      jsonData += "\"symbol\": \"" + latestOpen.symbol + "\",";
      jsonData += "\"trade_type\": \"" + latestOpen.trade_type + "\",";
      jsonData += "\"open_price\": " + DoubleToString(latestOpen.open_price, 5) + ",";
      jsonData += "\"open_time\": \"" + TimeToString(latestOpen.open_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",";
      jsonData += "\"current_time\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",";
      jsonData += "\"trade_duration_seconds\": " + IntegerToString(latestOpen.duration);
      jsonData += "}";
   }
   else if (hasClosed)
   {
      // Use the latest closed trade otherwise
      tradeStatus = "Closed trade";
      string profitLoss = (closedProfit > 0) ? "Profit" : (closedProfit < 0) ? "Loss" : "Break Even";
      jsonData = "{";
      jsonData += "\"status\": \"Closed\",";
      jsonData += "\"symbol\": \"" + closedSymbol + "\",";
      jsonData += "\"trade_type\": \"" + closedTradeType + "\",";
      jsonData += "\"profit_loss\": \"" + profitLoss + "\",";
      jsonData += "\"open_price\": " + DoubleToString(closedOpenPrice, 5) + ",";
      jsonData += "\"close_price\": " + DoubleToString(closePrice, 5) + ",";
      jsonData += "\"open_time\": \"" + TimeToString(closedOpenTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",";
      jsonData += "\"close_time\": \"" + TimeToString(closeTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS) + "\",";
      jsonData += "\"trade_duration_seconds\": " + IntegerToString(closedDuration);
      jsonData += "}";
   }
   else
   {
      // No trades found
      tradeStatus = "No trades";
      jsonData = "{}";
   }

   // Write to JSON file
   int fileHandle = FileOpen(filePath, FILE_WRITE | FILE_TXT);
   if (fileHandle != INVALID_HANDLE)
   {
      FileWriteString(fileHandle, jsonData);
      FileClose(fileHandle);
      Print("JSON data successfully written to MQL5\\Files\\", filePath, " (Using: ", tradeStatus, ")");
   }
   else
   {
      Print("Failed to open file ", filePath, " error code: ", GetLastError());
      return;
   }
}
//+------------------------------------------------------------------+