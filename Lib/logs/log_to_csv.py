
import pandas as pd
import re
import numpy as np
import os

# Initialize list to store parsed log entries
log_data = []

# Regular expression to match trading data lines
# Matches: timestamp, symbol, high, low, spread, open, close, tick_volume, TradeSignal, trade-zone, range, EMA_crossover
data_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\w+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\S+)\s+([a-z-]+)\s+(\d+)\s+(\S+)"

# Output directory and file
output_dir = r"C:\Users\User\Desktop\projects\FreeStyler-VI-Pandemic\Lib\logs\lib"
output_file = os.path.join(output_dir, "mt5_Pandemic_MAIN_clean.csv")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Read the log file
try:
    with open("mt5_Pandemic_MAIN.log", "r") as file:
        for line in file:
            # Strip whitespace and skip empty lines
            line = line.strip()
            if not line:
                continue
                
            # Skip metadata lines (e.g., containing "DataFrame Tail" or column headers)
            if "DataFrame Tail" in line or "symbol" in line:
                continue
                
            # Check if the line matches the data pattern
            match = re.match(data_pattern, line)
            if match:
                # Extract fields
                timestamp, symbol, high, low, spread, open_price, close, tick_volume, trade_signal, trade_zone, range_val, ema_crossover = match.groups()
                
                # Convert fields to appropriate types, preserving NaN
                log_data.append({
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "high": float(high),
                    "low": float(low),
                    "spread": int(spread),
                    "open": float(open_price),
                    "close": float(close),
                    "tick_volume": int(tick_volume),
                    "TradeSignal": np.nan if trade_signal == "NaN" else trade_signal,
                    "trade-zone": trade_zone,
                    "range": int(range_val),
                    "EMA_crossover": np.nan if ema_crossover == "NaN" else ema_crossover
                })
            else:
                print(f"Skipped line: {line}")

    # Create DataFrame
    df = pd.DataFrame(log_data)
    
    # Remove duplicates based on timestamp, keeping the last entry
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    
    # Define column order
    columns = ["timestamp", "symbol", "high", "low", "spread", "open", "close", 
               "tick_volume", "TradeSignal", "trade-zone", "range", "EMA_crossover"]
    df = df[columns]
    
    # Sort by timestamp for consistency
    df = df.sort_values(by="timestamp")
    
    # Save to CSV, ensuring NaN is printed as "NaN"
    df.to_csv(output_file, index=False, na_rep="NaN")
    print(f"Successfully converted mt5_Pandemic_MAIN.log to {output_file}")
    
except FileNotFoundError:
    print("Error: mt5_Pandemic_MAIN.log not found")
except Exception as e:
    print(f"Error: {str(e)}")
