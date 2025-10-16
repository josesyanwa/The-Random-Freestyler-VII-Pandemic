import MetaTrader5 as mt5
import json
from pathlib import Path
import os
from dotenv import load_dotenv
import time
import logging

# Configure logging
log_dir = "../../Lib/logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, "trailing_stop.log"),
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
file_path = Path(os.getenv('FILE_PATH'))  # Path to ATR_Data.json
original_atr_file = "..\\..\\json\\original_atr.json"  # File to store original ATR per ticket

# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        logging.error("MT5 initialization failed")
        return False
    print("Connected to MT5 Account:", mt5.account_info().name)
    logging.info("MT5 connected")
    return True

# Load ATR from JSON (current ATR, but not used for original)
def load_atr():
    try:
        json_text = file_path.read_text(encoding='utf-16')
        atr_data = json.loads(json_text)
        atr_value = atr_data.get('atr_value', 0.0)
        logging.info(f"Loaded current ATR value: {atr_value}")
        return atr_value
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logging.error(f"Error loading ATR from JSON: {e}")
        print(f"Error loading ATR from JSON: {e}, skipping adjustments")
        return 0.0

# Load original ATRs from JSON
def load_original_atrs():
    try:
        with open(original_atr_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save original ATRs to JSON
def save_original_atrs(original_atrs):
    with open(original_atr_file, 'w') as f:
        json.dump(original_atrs, f)

# Main trailing stop logic
def adjust_trailing_stops():
    current_atr = load_atr()
    if current_atr == 0.0:
        print("Current ATR value is 0.0, skipping adjustments.")
        logging.warning("Current ATR value is 0.0, skipping adjustments")
        return

    # Load stored original ATRs
    original_atrs = load_original_atrs()

    # Get open positions
    positions = mt5.positions_get()
    if positions is None:
        print("Failed to get positions:", mt5.last_error())
        logging.error("Failed to get positions")
        return

    for position in positions:
        symbol = position.symbol
        pos_type = position.type  # 0: BUY, 1: SELL
        entry = position.price_open
        current_sl = position.sl
        ticket = str(position.ticket)  # Use str for JSON key

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logging.warning(f"Symbol info not found for {symbol}")
            continue

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.warning(f"Tick info not found for {symbol}")
            continue

        # Calculate current profit
        if pos_type == mt5.POSITION_TYPE_BUY:
            current_price = tick.bid
            profit = current_price - entry
        elif pos_type == mt5.POSITION_TYPE_SELL:
            current_price = tick.ask
            profit = entry - current_price
        else:
            continue  # Unknown type

        if profit <= 0:
            continue  # No adjustment if not in profit

        # Get or calculate original ATR
        if ticket not in original_atrs:
            # Assume current SL is initial, calculate original ATR
            original_atr = abs(entry - current_sl) / 2.0
            if original_atr == 0.0:
                logging.warning(f"Calculated original ATR is 0.0 for ticket {ticket}, skipping")
                continue
            original_atrs[ticket] = original_atr
            save_original_atrs(original_atrs)
            logging.info(f"Calculated and saved original ATR {original_atr} for ticket {ticket}")

        original_atr = original_atrs[ticket]

        profit_atr = profit / original_atr

        # Determine trailing multiplier and adjustment
        if profit_atr >= 4:
            # Trail at 1 ATR, adjust every 2 ATR profit beyond 4 ATR
            trail_mult = 1.0
            # Calculate the number of 2 ATR increments beyond 4 ATR
            additional_steps = max(0, int((profit_atr - 4) / 2))
            if pos_type == mt5.POSITION_TYPE_BUY:
                new_sl = current_price - (trail_mult * original_atr)  # 1 ATR below current price
                # Adjust based on highest profit level achieved
                new_sl = max(current_sl, new_sl - (additional_steps * original_atr))  # Move 1 ATR per 2 ATR profit
            else:  # SELL
                new_sl = current_price + (trail_mult * original_atr)  # 1 ATR above current price
                new_sl = min(current_sl, new_sl + (additional_steps * original_atr))  # Move 1 ATR per 2 ATR profit
        elif profit_atr >= 2:
            trail_mult = 1.5
            if pos_type == mt5.POSITION_TYPE_BUY:
                new_sl = current_price - (trail_mult * original_atr)
            else:  # SELL
                new_sl = current_price + (trail_mult * original_atr)
        else:
            trail_mult = 2.0
            if pos_type == mt5.POSITION_TYPE_BUY:
                new_sl = current_price - (trail_mult * original_atr)
            else:  # SELL
                new_sl = current_price + (trail_mult * original_atr)

        # Apply adjustment only if new SL is more favorable
        if pos_type == mt5.POSITION_TYPE_BUY and new_sl > current_sl:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "sl": new_sl,
                "tp": 0.0  # No TP
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"Adjusted SL for BUY position {position.ticket} to {new_sl}")
                logging.info(f"Adjusted SL for BUY position {position.ticket} to {new_sl}")
            else:
                print(f"Failed to adjust SL for {position.ticket}: {result.retcode}")
                logging.error(f"Failed to adjust SL for {position.ticket}: {result.retcode}")
        elif pos_type == mt5.POSITION_TYPE_SELL and new_sl < current_sl:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "sl": new_sl,
                "tp": 0.0  # No TP
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"Adjusted SL for SELL position {position.ticket} to {new_sl}")
                logging.info(f"Adjusted SL for SELL position {position.ticket} to {new_sl}")
            else:
                print(f"Failed to adjust SL for {position.ticket}: {result.retcode}")
                logging.error(f"Failed to adjust SL for {position.ticket}: {result.retcode}")

# Main loop
if __name__ == "__main__":
    if not initialize_mt5():
        print("Exiting due to initialization failure.")
        exit()

    try:
        while True:
            adjust_trailing_stops()
            time.sleep(9)  # Run every 7 seconds to match ATR update interval
    except KeyboardInterrupt:
        print("Script interrupted by user.")
        logging.info("Script interrupted by user")
    finally:
        mt5.shutdown()
        print("MT5 connection closed.")
        logging.info("MT5 connection closed")