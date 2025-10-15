import MetaTrader5 as mt5
import pandas as pd
import pytz
import json
import os
from datetime import datetime, timedelta
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

# Initialize MT5 connection with retry
def initialize_mt5():
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        mt5.shutdown()
        return False
    print("Connected to FTMO Account:", mt5.account_info().name)
    return True

# Ranging market detection
def is_ranging_market(df):
    df['Midpoint'] = ((df['high'] + df['low']) / 2).round(5)  # Round to 5 decimal places

def calculate_range(df, symbol):
    symbol_df = df[df['symbol'] == symbol]
    if len(symbol_df) < 5:  # Need at least 5 candles (4 previous + 1 current)
        return None
    current_midpoint = symbol_df['Midpoint'].iloc[-1]  # Current candle's midpoint
    previous_candles = symbol_df.iloc[-5:-1]  # Previous 4 candles
    previous_highs = previous_candles['high'].values
    previous_lows = previous_candles['low'].values
    count = 0
    for i in range(len(previous_candles)):  # Should be 4 candles
        if previous_lows[i] <= current_midpoint <= previous_highs[i]:
            count += 1
    return 1 if count >= 2 else 0  # 1 for ranging, 0 for trending

# Load existing JSON data
def load_existing_json(json_path="..\\..\\json\\ranging_market.json"):
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"timestamp": "", "symbols": []}

# Save data to JSON if changed
def save_to_json(data, json_path="..\\..\\json\\ranging_market.json"):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)  # Ensure json directory exists
    existing_data = load_existing_json(json_path)
    
    # Compare new data with existing to check for changes
    new_symbols = {s["pair"]: s for s in data["symbols"]}
    existing_symbols = {s["pair"]: s for s in existing_data.get("symbols", [])}
    has_changes = False
    for pair, new_symbol_data in new_symbols.items():
        existing_symbol_data = existing_symbols.get(pair, {})
        if (existing_symbol_data.get("market_status") != new_symbol_data["market_status"] or
            existing_symbol_data.get("midpoint") != new_symbol_data["midpoint"] or
            existing_symbol_data.get("candle_time") != new_symbol_data["candle_time"]):
            has_changes = True
            break
    
    if not has_changes and existing_data.get("timestamp") == data.get("timestamp"):
        return  # No changes, skip saving
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Updated {json_path}")

# Main function
def main():
    # Initialize MT5
    if not initialize_mt5():
        return

    try:
        # Define timezone and symbols
        timezone = pytz.timezone("Africa/Nairobi")
        symbols = ["XAUUSD", "XAUEUR"]
        timeframe = mt5.TIMEFRAME_H4
        num_candles = 5  # Only need 5 candles (4 previous + 1 current)

        # Ensure symbols are selected in Market Watch
        for symbol in symbols:
            if not mt5.symbol_select(symbol, True):
                print(f"Failed to select {symbol} in Market Watch")
                continue

        # Get historical price data (most recent candles)
        df_list = []
        for symbol in symbols:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
            if rates is None or len(rates) == 0:
                print(f"No data retrieved for {symbol}")
                continue
            rates_frame = pd.DataFrame(rates)
            rates_frame['symbol'] = symbol
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
            df_list.append(rates_frame)

        df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

        if df.empty:
            print("No data available for any symbols")
            return

        df = df[df['symbol'].isin(symbols)]
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.sort_index(inplace=True)

        # Apply ranging market detection
        is_ranging_market(df)
        df['range'] = df.apply(lambda row: calculate_range(df, row['symbol']), axis=1)

        # Prepare JSON data
        json_data = {
            "timestamp": datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S"),
            "symbols": []
        }
        for symbol in symbols:
            symbol_df = df[df['symbol'] == symbol]
            if not symbol_df.empty:
                latest_row = symbol_df.iloc[-1]
                range_status = "Ranging" if latest_row['range'] == 1 else "Trending"
                symbol_data = {
                    "pair": symbol,
                    "market_status": range_status,
                    "midpoint": float(latest_row['Midpoint']),  # Convert to float for JSON
                    "is_trending": range_status == "Trending",
                    "candle_time": str(latest_row.name)  # Timestamp of the latest candle
                }
                json_data["symbols"].append(symbol_data)
                print(f"{symbol} on H4: {range_status} (Midpoint: {latest_row['Midpoint']:.5f})")

        # Save to JSON if data has changed
        save_to_json(json_data)

    finally:
        mt5.shutdown()
        print("MT5 connection closed.")

if __name__ == "__main__":
    # Schedule to run every minute
    print("H4 Ranging Market Detection Script Started")
    schedule.every(1).hours.do(main)
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Sleep for 60 seconds to reduce CPU usage
    except KeyboardInterrupt:
        print("Script stopped by user.")
    finally:
        mt5.shutdown()
        print("Final MT5 connection closed.")
