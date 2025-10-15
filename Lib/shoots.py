import MetaTrader5 as mt5
import pickle
import time
import math
import os
from dotenv import load_dotenv
import schedule
import datetime


# Load environment variables
load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

PICKLE_FILE = "../lib/assets/shoot_values.pkl"

def initialize_mt5():
    # Connect to the first MT5 instance
    # # path = "C:\\Program Files\\MT5_Instance1\\terminal64.exe"
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        mt5.shutdown()
        return False
    return True
    

def add_symbol_to_market_watch(symbol):
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to add {symbol} to Market Watch. It may be unavailable.")
        return False
    return True

def get_current_market_price(symbol):
    if not initialize_mt5():
        return None
    if not add_symbol_to_market_watch(symbol):
        return None
    tick = mt5.symbol_info_tick(symbol)
    mt5.shutdown()
    if not tick:
        print(f"Failed to get tick data for symbol {symbol}. Ensure it is enabled in MT5.")
        return None
    return tick.bid

def get_market_points(symbol, increment_value):
    current_price = get_current_market_price(symbol)
    if current_price is None:
        return None
    if 'XAU' in symbol:
        MP1 = round(current_price / 100) * 100
    elif 'JPY' in symbol:
        MP1 = math.floor(current_price / 10) * 10
    else:
        MP1 = round(current_price, 1)
    MP2 = round(MP1 + increment_value, 1)
    MP3 = round(MP1 - increment_value, 1)
    return current_price, MP1, MP2, MP3

def calculate_half_points(MP1, MP2, MP3):
    return (MP1 + MP3) / 2, (MP1 + MP2) / 2

def calculate_quarter_points(MP1, HP1, MP2, HP2, MP3):
    return (MP3 + HP1) / 2, (HP1 + MP1) / 2, (MP1 + HP2) / 2, (HP2 + MP2) / 2

def calculate_quarter_half_points(QP1, MP3, HP1, QP2, MP1, HP2, QP3, QP4, is_jpy=False, is_xau=False):
    offset = 12.5 if is_xau else 1.25 if is_jpy else 0.0125
    return (
        round(MP3 + offset, 4), round(QP1 + offset, 4), round(HP1 + offset, 4), round(QP2 + offset, 4),
        round(QP3 - offset, 4), round(QP3 + offset, 4), round(HP2 + offset, 4), round(QP4 + offset, 4)
    )

def calculate_overshoot(symbol, values, is_jpy=False, is_xau=False):
    offset = 2.5 if is_xau else 0.25 if is_jpy else 0.0025
    return {f'Overshoot_{symbol}': [round(value + offset, 4) for value in values]}

def calculate_undershoot(symbol, values, is_jpy=False, is_xau=False):
    offset = 2.5 if is_xau else 0.25 if is_jpy else 0.0025
    return {f'Undershoot_{symbol}': [round(value - offset, 4) for value in values]}

def calculate_upper_lower_limits(overshoot, undershoot, point_value):
    # Calculate upper and lower limits based on overshoot and undershoot with a dynamic point size
    upper_limit = overshoot + 60 * point_value  # Add 60 points to overshoot
    lower_limit = undershoot - 60 * point_value  # Subtract 60 points from undershoot
    return upper_limit, lower_limit

def save_to_pickle(data, filename=PICKLE_FILE):
    # Delete the pickle file if it exists
    if os.path.exists(filename):
        os.remove(filename)
    
    # Write new data to the pickle file
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

def load_from_pickle(filename=PICKLE_FILE):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return {}

def process_currency_pair(symbol, increment_value, all_values):
    is_jpy = 'JPY' in symbol
    is_xau = 'XAU' in symbol
    market_points = get_market_points(symbol, increment_value)
    if not market_points:
        return None
    current_price, MP1, MP2, MP3 = market_points
    HP1, HP2 = calculate_half_points(MP1, MP2, MP3)
    QP1, QP2, QP3, QP4 = calculate_quarter_points(MP1, HP1, MP2, HP2, MP3)
    QHP_values = calculate_quarter_half_points(QP1, MP3, HP1, QP2, MP1, HP2, QP3, QP4, is_jpy, is_xau)

    # Calculate the shoot values (Overshoot and Undershoot)
    shoot_values = [MP3, QHP_values[0], QP1, QHP_values[1], HP1, QHP_values[2], QP2, QHP_values[3], MP1, QHP_values[4], QP3, QHP_values[5], HP2, QHP_values[6], QP4, QHP_values[7], MP2]
    overshoot = calculate_overshoot(symbol, shoot_values, is_jpy, is_xau)
    undershoot = calculate_undershoot(symbol, shoot_values, is_jpy, is_xau)

    # Define labels for each level
    level_labels = [
        "zone1", "zone2", "zone3", "zone4", "zone5", "zone6", "zone7", "zone8", "zone9", "zone10", "zone11", "zone12", "zone13", "zone14", "zone15", "zone16", "zone17"
    ]

    # Extract overshoot and undershoot values
    overshoot_values = overshoot[f'Overshoot_{symbol}']
    undershoot_values = undershoot[f'Undershoot_{symbol}']

    if not mt5.initialize():  # Initialize MT5 once, not inside the loop
          print("initialize() failed, error code =", mt5.last_error())
          quit()

    # Get the point value dynamically for the symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "not found, can not call order_check()")
        return None

    if not symbol_info.visible:
        print(symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print("symbol_select({}) failed, exit".format(symbol))
            return None

    point_value = symbol_info.point  # Get the point size

    # Calculate upper and lower limits dynamically
    upper_limits = []
    lower_limits = []
    for os_val, us_val in zip(overshoot_values, undershoot_values):
        upper_limit, lower_limit = calculate_upper_lower_limits(os_val, us_val, point_value)
        upper_limits.append(upper_limit)
        lower_limits.append(lower_limit)

    # Save the overshoot and undershoot data to the all_values dictionary
    all_values[symbol] = {}
    for idx, label in enumerate(level_labels):
        all_values[symbol][label] = {
            "Overshoot": overshoot_values[idx],
            "Undershoot": undershoot_values[idx],
            "Upper Limit": upper_limits[idx],
            "Lower Limit": lower_limits[idx]
        }

    # Print the output for verification
    print(f"\n--- Data for {symbol} ---")
    for label in level_labels:
        print(f"{label}:")
        print(f"  Overshoot: {all_values[symbol][label]['Overshoot']}")
        print(f"  Undershoot: {all_values[symbol][label]['Undershoot']}")
        print(f"  Upper Limit: {all_values[symbol][label]['Upper Limit']}")
        print(f"  Lower Limit: {all_values[symbol][label]['Lower Limit']}")


def job():
    # Define a list of symbols
    symbol_list = ["XAUUSD", "XAUAUD", "XAUEUR"]


    # Define the increment value mapping for each symbol
    symbol_increment_map = {
        symbol: (100 if 'XAU' in symbol else 10 if 'JPY' in symbol else 0.1) for symbol in symbol_list
    }

    # Initialize an empty dictionary to store all values
    all_values = {}

    # Iterate through the symbol list and process each one using the corresponding increment value
    for symbol in symbol_list:
        increment_value = symbol_increment_map[symbol]
        process_currency_pair(symbol, increment_value, all_values)

    # Save all the accumulated data to the pickle file after processing all symbols
    save_to_pickle(all_values)

    now = datetime.datetime.now()
    next_run = min([job.next_run for job in schedule.jobs if job.next_run > now], default="N/A")
    print(f"✅ Updated values at {now.strftime('%Y-%m-%d %H:%M:%S')} | Next update scheduled for {next_run}")

# Schedule the job three times a day
schedule.every().day.at("00:01").do(job)
schedule.every().day.at("08:01").do(job)
schedule.every().day.at("16:01").do(job)

print(f"✅ Script is active and waiting for the first scheduled run at {schedule.next_run().strftime('%Y-%m-%d %H:%M:%S')}")
# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(60)
