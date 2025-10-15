#property copyright "Your Name"
#property link      "https://www.example.com"
#property version   "1.00"
#property strict

// Input parameters
input int ATRPeriod = 14; // ATR Period
input int UpdateInterval = 7; // Update interval in seconds

// Global variables
datetime lastUpdateTime = 0;
double lastATR = 0.0;

//+------------------------------------------------------------------
//| Expert initialization function                                     |
//+------------------------------------------------------------------
int OnInit()
{
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------
void OnDeinit(const int reason)
{
   // Cleanup if needed
}

//+------------------------------------------------------------------
//| Expert tick function                                               |
//+------------------------------------------------------------------
void OnTick()
{
   // Check if 7 seconds have passed since last update
   if (TimeCurrent() - lastUpdateTime >= UpdateInterval)
   {
      // Create ATR handle
      int atrHandle = iATR(_Symbol, PERIOD_M5, ATRPeriod);
      if (atrHandle == INVALID_HANDLE)
      {
         Print("Failed to create ATR handle, error: ", GetLastError());
         return;
      }
      
      // Buffer to store ATR values
      double atrBuffer[];
      ArraySetAsSeries(atrBuffer, true);
      
      // Copy the latest ATR value
      if (CopyBuffer(atrHandle, 0, 0, 1, atrBuffer) <= 0)
      {
         Print("Failed to copy ATR buffer, error: ", GetLastError());
         IndicatorRelease(atrHandle);
         return;
      }
      
      // Update lastATR with the latest value
      lastATR = atrBuffer[0];
      IndicatorRelease(atrHandle);
      
      // Update JSON file
      UpdateJSONFile();
      
      // Update last update time
      lastUpdateTime = TimeCurrent();
   }
}

//+------------------------------------------------------------------
//| Update JSON file function                                          |
//+------------------------------------------------------------------
void UpdateJSONFile()
{
   // Open file in the MQL5/Files folder
   string fileName = "ATR_Data.json";
   int fileHandle = FileOpen(fileName, FILE_WRITE | FILE_TXT);
   if (fileHandle == INVALID_HANDLE)
   {
      Print("Failed to open file, error: ", GetLastError());
      return;
   }
   
   // Prepare JSON content
   string jsonContent = StringFormat(
      "{\"symbol\":\"%s\",\"timeframe\":\"M5\",\"atr_period\":%d,\"atr_value\":%.5f,\"timestamp\":\"%s\"}",
      _Symbol, ATRPeriod, lastATR, TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS)
   );
   
   // Write to file (overwrite existing content)
   if (FileWriteString(fileHandle, jsonContent, StringLen(jsonContent)) < 0)
   {
      Print("Failed to write to file, error: ", GetLastError());
   }
   else
   {
      Print("ATR updated in JSON: ", jsonContent);
   }
   
   // Close file
   FileClose(fileHandle);
}