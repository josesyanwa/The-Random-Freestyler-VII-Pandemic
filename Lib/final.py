from datetime import datetime, timedelta, time as dtime
import MetaTrader5 as mt5
import pandas_ta as ta
import pytz
import pickle
import pandas as pd
import time
import numpy as np
import re
import ta
import schedule
import os
import json
from dotenv import load_dotenv
import logging
from pathlib import Path
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.trading_ranges import TRADING_RANGES  

# Ensure log directory exists
log_dir = "../Lib/logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=os.path.join(log_dir, "mt5_Pandemic_MAIN.log"),
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# Load environment variables
load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

print(f"🏊‍♂️  Pandemic Main initiated 🦠🦠🦠...")

# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        mt5.shutdown()
        return False
    print("Connected to FTMO Account:", mt5.account_info().name)
    return True

# Function to calculate daily P/L
def calculate_daily_pl(timezone):
    today = datetime.now(timezone).date()
    start_of_day = datetime.combine(today, dtime(0, 0), tzinfo=timezone)
    end_of_day = datetime.combine(today, dtime(23, 59, 59), tzinfo=timezone)
    
    # Convert to UTC for MT5
    utc_start = start_of_day.astimezone(pytz.utc)
    utc_end = end_of_day.astimezone(pytz.utc)
    
    # Get closed trades from history
    history = mt5.history_deals_get(utc_start, utc_end)
    if history is None or len(history) == 0:
        return 0.0  # No trades today
    
    total_pl = 0.0
    for deal in history:
        if deal.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
            total_pl += deal.profit  # Sum profit/loss for each deal
    
    return total_pl

# Function to save drawdown state to JSON
def save_drawdown_state(max_pl, date, filename="../json/drawdown_state.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump({'max_daily_pl': max_pl, 'last_date': date.strftime('%Y-%m-%d')}, f)

# Function to load drawdown state from JSON
def load_drawdown_state(filename="../json/drawdown_state.json"):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return {
                'max_daily_pl': data.get('max_daily_pl', 0.0),
                'last_date': datetime.strptime(data.get('last_date', '1970-01-01'), '%Y-%m-%d').date()
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {'max_daily_pl': 0.0, 'last_date': None}

# Function to check daily drawdown limit
def check_daily_drawdown(timezone, drawdown_limit):
    current_pl = calculate_daily_pl(timezone)
    
    # Load or initialize drawdown state
    state = load_drawdown_state()
    max_daily_pl = state['max_daily_pl']
    last_date = state['last_date']
    
    # Initialize or update max_daily_pl for the day
    today = datetime.now(timezone).date()
    if last_date != today:
        max_daily_pl = current_pl
    else:
        max_daily_pl = max(max_daily_pl, current_pl)
    
    # Save updated state only if changed
    if max_daily_pl != state['max_daily_pl'] or last_date != today:
        save_drawdown_state(max_daily_pl, today)
    
    # Check if current P/L has dropped by drawdown_limit from max_daily_pl
    if current_pl <= max_daily_pl + drawdown_limit and max_daily_pl > 0:
        message = f"🚫 DAILY DRAWDOWN HIT: P/L dropped from ${max_daily_pl:.2f} to ${current_pl:.2f}. Trading paused for today."
        print(message)
        logging.info(message)
        return False
    return True

# Function to reset drawdown at midnight
def reset_drawdown_at_midnight():
    timezone = pytz.timezone("Africa/Nairobi")
    today = datetime.now(timezone).date()
    save_drawdown_state(0.0, today)
    print(f"Reset drawdown to 0.0 at midnight {today}")

# Modified: Function to check if today is a weekday
def is_weekday(timezone):
    today = datetime.now(timezone).weekday()
    return today < 5  # Monday=0, Tuesday=1, ..., Friday=4

# Modified: Function to get trading time ranges for the current day
def get_day_trading_ranges(day_name):
    return TRADING_RANGES.get(day_name, [])

# Modified: Updated function to check if current time is within allowed time ranges
def is_within_time_ranges(timezone):
    now = datetime.now(timezone)
    day_name = now.strftime('%A')
    
    # Check if today is a weekday
    if not is_weekday(timezone):
        return False, f"🚫 NOT A WEEKDAY: No trading on {day_name}."
    
    # Get trading time ranges for the current day
    trading_time_ranges = get_day_trading_ranges(day_name)
    if not trading_time_ranges:
        return False, f"🚫 NO TRADING RANGES DEFINED for {day_name}."
    
    current_time = now.time()
    for start_time, end_time in trading_time_ranges:
        if start_time <= current_time <= end_time:
            return True, f"✅ TRADING ALLOWED: {day_name} {current_time.strftime('%H:%M:%S')} within {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
    return False, f"🚫 NOT TRADING TIME: {day_name} {current_time.strftime('%H:%M:%S')} outside defined ranges."

# New: Function to check if today is a trading day based on trading_schedule.json
def check_trading_day(timezone, json_path="../json/trading_schedule.json"):
    today = datetime.now(timezone).date().strftime('%Y-%m-%d')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Validate JSON structure and date range
        if 'schedule' not in data or 'start_date' not in data or 'end_date' not in data:
            print(f"Error: Invalid JSON format in {json_path}. Pausing trading.")
            return False, "Invalid JSON"
        
        schedule = data['schedule']
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if today < start_date.strftime('%Y-%m-%d') or today > end_date.strftime('%Y-%m-%d'):
            print(f"Error: Today ({today}) is outside JSON date range ({start_date} to {end_date}). Pausing trading.")
            return False, "Outside date range"
        
        if today not in schedule:
            print(f"Error: Today ({today}) not found in schedule. Pausing trading.")
            return False, "Date not found"
        
        status = schedule[today]
        if status == "Trading Day":
            return True, f"✅ Today ({today}) is a Trading Day. Trading allowed."
        else:
            return False, f"🚫 Today is {status}, no trading."
    
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: Could not load {json_path} ({str(e)}). Pausing trading.")
        return False, "JSON load error"

# Function to load choppy market data from JSON
def load_choppy_market_data(json_path="../json/choppy_market_detection.json"):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            return data.get("market_condition", "Choppy")  # Default to Choppy if key missing
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Could not load {json_path}, assuming choppy market for safety.")
        return "Choppy"

# Run trading logic
def run_trading_script():
    # Define timezone
    timezone = pytz.timezone("Africa/Nairobi")
    current_time = datetime.now(timezone).strftime("%H:%M:%S")
    daily_loss_limit = float(os.getenv('DAILY_LOSS_LIMIT_2', '-20.0'))
    drawdown_limit = float(os.getenv('DAILY_DRAWDOWN_LIMIT_2', '-11.0'))

    # New: Check if today is a trading day
    is_trading_day, message = check_trading_day(timezone)
    if not is_trading_day:
        print(message)
        logging.info(message)
        return  # Skip trading logic

    # Modified: Check if current time is within allowed trading ranges
    is_allowed, message = is_within_time_ranges(timezone)
    if not is_allowed:
        print(message)
        logging.info(message)
        return  # Skip trading logic but allow scheduler to continue

    # Check daily loss limit
    daily_pl = calculate_daily_pl(timezone)
    if daily_pl <= daily_loss_limit:
        message = f"🚫 DAILY LOSS LIMIT HIT: ${-daily_pl:.2f} exceeds ${-daily_loss_limit:.2f}. Trading paused for today."
        print(message)
        logging.info(message)
        return  # Skip trading logic

    # Check daily drawdown limit
    if not check_daily_drawdown(timezone, drawdown_limit):
        return  # Skip trading logic

    # Check market condition from choppy_market_detection.json
    market_condition = load_choppy_market_data()
    if market_condition == "Choppy":
        message = "Update: Market choppy, no trades placed."
        print(message)
        logging.info(message)
        return  # Skip trading logic if market is choppy

    # Log current P/L status
    message = f"Daily P/L: ${daily_pl:.2f}"
    print(message)
    logging.info(message)

    # Proceed with trading logic
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1500)

    print("MetaTrader5 package author: ", mt5.__author__)
    print("MetaTrader5 package version: ", mt5.__version__)

    # Get symbols
    symbols = mt5.symbols_get()
    desired_symbols = ["XAUUSD"]

    count = 0
    for s in symbols:
        if s.name in desired_symbols:
            count += 1
            if count == len(desired_symbols):
                break

    timeframe = getattr(mt5, os.getenv('TIMEFRAME_2', 'TIMEFRAME_M2'))
    num_candles = int(os.getenv('NUM_CANDLES', '50'))

    # Get historical price data
    now = datetime.now(timezone)
    start_time = now - timedelta(days=4)
    utc_start_time = start_time.astimezone(pytz.utc)

    # Convert the data to a pandas DataFrame
    df_list = []
    for symbol in desired_symbols:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        rates_frame = pd.DataFrame(rates)
        rates_frame['symbol'] = symbol
        rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
        df_list.append(rates_frame)
    
    df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

    df = df[df['symbol'].isin(desired_symbols)]
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)

    # Calculate EMAs
    intraday_prices_dict = {}
    for symbol in desired_symbols:
        intraday_prices_dict[symbol] = df[df['symbol'] == symbol]['close']

    ema_dict = {}
    for symbol, prices in intraday_prices_dict.items():
        ema_2_min = prices.ewm(span=2, adjust=False).mean()
        ema_10_min = prices.ewm(span=10, adjust=False).mean()
        ema_dict[symbol] = {'ema_2_min': ema_2_min, 'ema_10_min': ema_10_min}

    # Load shoot values
    def load_from_pickle(filename='../Lib/assets/shoot_values.pkl'):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                return pickle.load(f)
        return {}

    shoot_values = load_from_pickle('../Lib/assets/shoot_values.pkl')
    if shoot_values:
        print("Successfully loaded the shoot values.")
    else:
        print("No data found or unable to load the pickle file.")

    # Check tradable zone
    def check_tradable_zone(symbol, current_price, shoot_values, df):
        if symbol in shoot_values:
            symbol_zones = shoot_values[symbol]
            for zone, values in symbol_zones.items():
                upper_limit = values['Upper Limit']
                lower_limit = values['Lower Limit']
                if lower_limit <= current_price <= upper_limit:
                    df.loc[df['symbol'] == symbol, 'trade-zone'] = 'not tradable'
                    print(f"Symbol {symbol}: Current price {current_price} is in the untradable zone.")
                    break
            else:
                print(f"Symbol {symbol}: Current price {current_price} is tradable.")
                df.loc[df['symbol'] == symbol, 'trade-zone'] = 'tradable'
        else:
            print(f"No data found for symbol {symbol}.")
        return df

    def update_trade_zone(df, shoot_values):
        for symbol in df['symbol'].unique():
            current_price = df[df['symbol'] == symbol]['close'].iloc[-1]
            df = check_tradable_zone(symbol, current_price, shoot_values, df)
        return df

    df = update_trade_zone(df, shoot_values)

    # EMA crossover entry strategy
    def calculate_ema_crossover(df, ema_dict):
        df['EMA_crossover'] = np.nan
        df['EMA_crossover'] = df['EMA_crossover'].astype('object')
        for symbol in df['symbol'].unique():
            df.loc[df['symbol'] == symbol, 'bullish'] = np.where(
                ema_dict[symbol]['ema_2_min'] > ema_dict[symbol]['ema_10_min'], 1.0, 0.0
            )
            df.loc[df['symbol'] == symbol, 'crossover'] = df[df['symbol'] == symbol]['bullish'].diff()
            bullish_crossover = (df['symbol'] == symbol) & (df['crossover'] == 1)
            bearish_crossover = (df['symbol'] == symbol) & (df['crossover'] == -1)
            df.loc[bullish_crossover, 'EMA_crossover'] = 'bullish'
            df.loc[bearish_crossover, 'EMA_crossover'] = 'bearish'
        return df

    df = calculate_ema_crossover(df, ema_dict)

    # Ranging market detection
    def is_ranging_market(df):
        df['Midpoint'] = (df['high'] + df['low']) / 2

    is_ranging_market(df)

    def calculate_range(df, symbol):
        symbol_df = df[df['symbol'] == symbol]
        if not symbol_df.empty:
            current_midpoint = symbol_df['Midpoint'].iloc[-1]
        else:
            return None
        previous_candles = symbol_df.iloc[-9:-1]
        previous_highs = previous_candles['high'].values
        previous_lows = previous_candles['low'].values
        count = 0
        for i in range(6):
            if previous_lows[i] <= current_midpoint <= previous_highs[i]:
                count += 1
        if count >= 4:
            return 1
        else:
            return 0

    df['range'] = df.apply(lambda row: calculate_range(df, row['symbol']), axis=1)

    # Trade signals
    df['TradeSignal'] = np.nan
    df['TradeSignal'] = df['TradeSignal'].astype('object')
    df.loc[(df['trade-zone'] == 'tradable') & (df['range'] == 0) & (df['EMA_crossover'] == 'bullish'), 'TradeSignal'] = 'Buy'
    df.loc[(df['trade-zone'] == 'tradable') & (df['range'] == 0) & (df['EMA_crossover'] == 'bearish'), 'TradeSignal'] = 'Sell'

    # Log and print DataFrame
    logging.info(df[df['TradeSignal'].isin(['Buy', 'Sell'])].to_string())
    print(df[['symbol', 'high', 'low', 'spread', 'open', 'close', 'tick_volume', 'TradeSignal', 'trade-zone', 'range', 'EMA_crossover']].tail())

    # Trade execution
    current_time = df.index[-1]
    past_df = df[df.index < current_time]
    current_df = df[df.index >= current_time]

    # Load ranging market data from JSON
    def load_ranging_market_data(json_path="../json/ranging_market_fusion_acc.json"):
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Could not load {json_path}, assuming ranging market for safety.")
            return {"symbols": [{"pair": s, "market_status": "Ranging", "is_marabozu": False, "candle_type": "Neutral"} for s in desired_symbols]}

    ranging_data = load_ranging_market_data()

    # Load ATR from JSON
    try:
        json_text = Path(os.getenv('FILE_PATH')).read_text(encoding='utf-16')
        atr_data = json.loads(json_text)
        atr_value = atr_data.get('atr_value', 0.0)  # Default to 0.0 if not found
        print(f"Loaded ATR value: {atr_value}")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error loading ATR from JSON: {e}, using default ATR of 0.0")
        atr_value = 0.0

    # Skip trading if ATR is not available (0.0)
    if atr_value == 0.0:
        print("ATR value is 0.0, skipping all trades due to missing ATR data.")
        return
    
    for index, row in current_df.iterrows():
        symbol = row['symbol']
        trade_signal = row['TradeSignal']

        if pd.isna(trade_signal):
            print(f"No trade for {symbol}")
            continue
    
        # Modified: Check additional conditions from JSON (is_marabozu and candle_type alignment)
        market_status = next((s["market_status"] for s in ranging_data["symbols"] if s["pair"] == symbol), "Ranging")
        is_marabozu = next((s["is_marabozu"] for s in ranging_data["symbols"] if s["pair"] == symbol), False)
        candle_type = next((s["candle_type"] for s in ranging_data["symbols"] if s["pair"] == symbol), "Neutral")
        
        # Check if market is trending and is_marabozu is True
        if market_status != "Trending" or not is_marabozu:
            print(f"Skipping trade for {symbol}: Market status is {market_status} or not a Marabozu candle (is_marabozu: {is_marabozu}).")
            continue

        # Check if trade signal matches candle type
        if (trade_signal == "Sell" and candle_type != "Bearish") or (trade_signal == "Buy" and candle_type != "Bullish"):
            print(f"Skipping trade for {symbol}: Trade signal {trade_signal} does not match candle type {candle_type}.")
            continue

        if trade_signal == 'Sell':
            print(f"Sell {symbol}")
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(symbol, "not found, can not call order_check()")
                continue
            if not symbol_info.visible:
                print(symbol, "is not visible, trying to switch on")
                if not mt5.symbol_select(symbol, True):
                    print("symbol_select({}) failed, exit".format(symbol))
                continue

            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).bid
            sl = price + (2 * atr_value)  # Stop-loss at 2 ATR above entry price

            deviation = 20
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 0.04,  # Constant lot size
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl,
                "deviation": deviation,
                "magic": 234000,
                "comment": "python script open",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print("order_send failed, retcode={}".format(result.retcode))
                result_dict = result._asdict()
                for field in result_dict.keys():
                    print("   {}={}".format(field, result_dict[field]))
                    if field == "request":
                        traderequest_dict = result_dict[field]._asdict()
                        for tradereq_filed in traderequest_dict:
                            print("       traderequest: {}={}".format(tradereq_filed, traderequest_dict[tradereq_filed]))
                continue
            print("order_send done, ", result)
            print("   opened position with POSITION_TICKET={}".format(result.order))

        elif trade_signal == 'Buy':
            print(f"Buy {symbol}")
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(symbol, "not found, can not call order_check()")
                continue
            if not symbol_info.visible:
                print(symbol, "is not visible, trying to switch on")
                if not mt5.symbol_select(symbol, True):
                    print("symbol_select({}) failed, exit".format(symbol))
                continue

            point = mt5.symbol_info(symbol).point
            price = mt5.symbol_info_tick(symbol).ask
            sl = price - (2 * atr_value)  # Stop-loss at 2 ATR below entry price

            deviation = 20
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 0.04,  # Constant lot size
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "sl": sl,
                "deviation": deviation,
                "magic": 234000,
                "comment": "python script open",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print("order_send failed, retcode={}".format(result.retcode))
                result_dict = result._asdict()
                for field in result_dict.keys():
                    print("   {}={}".format(field, result_dict[field]))
                    if field == "request":
                        traderequest_dict = result_dict[field]._asdict()
                        for tradereq_filed in traderequest_dict:
                            print("       traderequest: {}={}".format(tradereq_filed, traderequest_dict[tradereq_filed]))
                continue
            print("order_send done, ", result)
            print("   opened position with POSITION_TICKET={}".format(result.order))

    print(f"🏊‍♂️ Pandemic Main🦠🦠🦠🦠🦠...")

# Main script
if __name__ == "__main__":
    # Initialize MT5 connection
    if not initialize_mt5():
        print("Exiting due to initialization failure.")
        exit()

    # Schedule the script to run
    schedule.every().day.at("00:00").do(reset_drawdown_at_midnight)
    
    schedule.every().hour.at("04:56").do(run_trading_script)
    schedule.every().hour.at("09:56").do(run_trading_script)
    schedule.every().hour.at("14:56").do(run_trading_script)
    schedule.every().hour.at("19:56").do(run_trading_script)
    schedule.every().hour.at("24:56").do(run_trading_script)
    schedule.every().hour.at("29:56").do(run_trading_script)
    schedule.every().hour.at("34:56").do(run_trading_script)
    schedule.every().hour.at("39:56").do(run_trading_script)  #35:35
    schedule.every().hour.at("44:56").do(run_trading_script)
    schedule.every().hour.at("49:56").do(run_trading_script)
    schedule.every().hour.at("54:56").do(run_trading_script)
    schedule.every().hour.at("59:56").do(run_trading_script)


    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    finally:
        # Ensure MT5 connection is closed on script exit
        mt5.shutdown()
        print("MT5 connection closed.")