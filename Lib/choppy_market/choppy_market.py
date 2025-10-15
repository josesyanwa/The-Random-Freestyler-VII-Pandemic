from dotenv import load_dotenv
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import schedule
import time
import os
from datetime import datetime

# Load environment variables
load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        mt5.shutdown()
        return False
    print("Connected to FTMO Account:", mt5.account_info().name)
    return True

def is_choppy_market(df, point, window=10, atr_threshold=200, doji_threshold=3, range_threshold=500, doji_body_points=50):
    """
    Detects if XAUUSD M5 market is choppy using <=10 candles, with values in points.
    
    Parameters:
    - df: DataFrame with 'open', 'high', 'low', 'close' in USD (e.g., 3500.00)
    - point: Point value from mt5.symbol_info(symbol).point (e.g., 0.01 for XAUUSD)
    - window: Number of candles to analyze (default 10, i.e., 50 minutes on M5)
    - atr_threshold: Max ATR in points (default 200 points = 20 pips). Lower for stricter chop detection (e.g., 150).
    - doji_threshold: Min number of doji candles (default 3). Increase for stricter (e.g., 4) or lower for looser (e.g., 2).
    - range_threshold: Max price range in points (default 500 points = 50 pips). Lower for stricter (e.g., 400).
    - doji_body_points: Max body size for a doji in points (default 40 points = 3 pips). Lower for stricter (e.g., 20).
    
    Returns:
    - dict: Contains results including 'is_choppy', 'market_condition', and metrics
    """
    if len(df) < window:
        print(f"Error: Only {len(df)} candles available, need {window}")
        return {
            "timestamp": datetime.now().isoformat(),
            "is_choppy": False,
            "market_condition": "Insufficient Data",
            "avg_atr_points": 0.0,
            "num_dojis": 0,
            "price_range_points": 0.0,
            "thresholds": {
                "atr": atr_threshold,
                "dojis": doji_threshold,
                "range": range_threshold,
                "doji_body": doji_body_points
            }
        }
    
    recent = df.tail(window).copy()
    
    # Calculate price differences
    recent['body_price'] = abs(recent['close'] - recent['open'])
    recent['prev_close'] = recent['close'].shift(1)
    recent['tr_price'] = np.maximum(
        recent['high'] - recent['low'],
        np.maximum(
            abs(recent['high'] - recent['prev_close']),
            abs(recent['low'] - recent['prev_close'])
        )
    )
    
    # Convert to points
    recent['body_points'] = recent['body_price'] / point
    recent['tr_points'] = recent['tr_price'] / point
    recent['candle_range_points'] = (recent['high'] - recent['low']) / point
    
    # ATR (simple average over window, i.e., 10 candles for XAUUSD M5)
    # To change ATR period, modify the window here (e.g., recent['tr_points'].tail(5).mean() for 5-candle ATR)
    avg_atr_points = recent['tr_points'].mean()
    
    # Identify dojis (body < doji_body_points), ensure Python bool
    recent['is_doji'] = recent['body_points'] < doji_body_points
    recent['is_doji'] = recent['is_doji'].astype(bool)  # Fix NumPy bool_ issue
    num_dojis = int(recent['is_doji'].sum())
    
    # Overall price range in points
    max_high = recent['high'].max()
    min_low = recent['low'].min()
    price_range_points = (max_high - min_low) / point
    
    # Choppy conditions: all must be True
    # 1. Low volatility: ATR < atr_threshold (e.g., 200 points)
    # 2. Enough dojis: num_dojis >= doji_threshold (e.g., 3)
    # 3. Tight range: price_range_points < range_threshold (e.g., 500 points)
    is_low_vol = avg_atr_points < atr_threshold
    is_many_dojis = num_dojis >= doji_threshold
    is_tight_range = price_range_points < range_threshold
    
    choppy = is_low_vol and is_many_dojis and is_tight_range
    market_condition = "Choppy" if choppy else "Trending/Volatile"
    
    # Prepare results dict
    results = {
        "timestamp": datetime.now().isoformat(),
        "is_choppy": bool(choppy),  # Ensure Python bool
        "market_condition": market_condition,
        "avg_atr_points": round(float(avg_atr_points), 2),  # Ensure float
        "num_dojis": int(num_dojis),  # Ensure int
        "price_range_points": round(float(price_range_points), 2),  # Ensure float
        "thresholds": {
            "atr": int(atr_threshold),
            "dojis": int(doji_threshold),
            "range": int(range_threshold),
            "doji_body": int(doji_body_points)
        }
    }
    
    # Print diagnostics
    print(f"[{results['timestamp']}] Average ATR: {results['avg_atr_points']} points")
    print(f"Number of Dojis (body < {doji_body_points} points): {results['num_dojis']}")
    print(f"Price Range: {results['price_range_points']} points")
    print(f"Market Condition: {results['market_condition']}")
    
    return results

def save_to_json(results, json_path):
    """Save results to JSON file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Updated JSON at {json_path}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

def job(symbol, timeframe, json_path, point):
    """Job function to run detection and update JSON."""
    # Fetch last 10 M5 candles
    num_bars = 10
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    
    if rates is None or len(rates) == 0:
        print("Failed to fetch rates")
        results = {
            "timestamp": datetime.now().isoformat(),
            "is_choppy": False,
            "market_condition": "Data Fetch Error",
            "avg_atr_points": 0.0,
            "num_dojis": 0,
            "price_range_points": 0.0,
            "thresholds": {
                "atr": 200,
                "dojis": 3,
                "range": 500,
                "doji_body": 50
            }
        }
        save_to_json(results, json_path)
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df[['time', 'open', 'high', 'low', 'close']]
    
    print(f"[{datetime.now().isoformat()}] Fetched {len(df)} M5 candles for {symbol}")
    
    # Detect and save
    results = is_choppy_market(df, point)
    save_to_json(results, json_path)
    
    if results['is_choppy']:
        print("🚨 Choppy market detected! Avoid scalping.")
    else:
        print("📈 Market may be trending or volatile. Check for scalp opportunities.")

if __name__ == "__main__":
    # Initialize MT5 connection
    if not initialize_mt5():
        quit()
    
    # Symbol and timeframe
    symbol = "XAUUSD"
    timeframe = mt5.TIMEFRAME_M5
    
    # Ensure XAUUSD is selected
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select {symbol}")
        mt5.shutdown()
        quit()
    
    # Get point value
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Failed to get info for {symbol}")
        mt5.shutdown()
        quit()
    point = symbol_info.point  # e.g., 0.01 for XAUUSD
    print(f"Point value for {symbol}: {point}")
    
    # JSON path
    json_path = r'..\..\json\choppy_market_detection.json'
    
    # Schedule job every hour at minutes divisible by 5
    schedule.every().hour.at("04:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("09:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("14:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("19:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("24:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("29:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("34:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("39:54").do(job, symbol, timeframe, json_path, point)  #35:35
    schedule.every().hour.at("44:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("49:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("54:54").do(job, symbol, timeframe, json_path, point)
    schedule.every().hour.at("59:54").do(job, symbol, timeframe, json_path, point)


    
    # Run initial job
    job(symbol, timeframe, json_path, point)
    
    # Run scheduler loop
    print("Scheduler started. Running every hour at minutes 05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Scheduler stopped.")
    finally:
        mt5.shutdown()