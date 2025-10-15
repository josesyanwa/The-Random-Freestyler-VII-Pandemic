import MetaTrader5 as mt5
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

if not mt5.initialize( path=path, login=login, server=server, password=password):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

print(mt5.terminal_info())
# print(mt5.version())
print("Connected to FTMO Account:", mt5.account_info().name)

# Track the phase of each position
position_phases = {}

# Function to convert points dynamically for each symbol
def convert_to_points(symbol, value_in_points):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"⚠️ Warning: Failed to retrieve point value for {symbol}. Using default value.")
        return value_in_points * 0.0001  # Default for Forex pairs

    return value_in_points * symbol_info.point  # Convert points to price format

# Function to trail SL dynamically
def trail_sl(position, phase):
    symbol = position.symbol  # Now works on any symbol

    config = PHASES[phase]
    max_dist_sl = convert_to_points(symbol, config["MAX_DIST_SL"])
    trail_amount = convert_to_points(symbol, config["TRAIL_AMOUNT"])
    default_sl = convert_to_points(symbol, config.get("DEFAULT_SL", 100))  # Default 100 points

    # Get position data
    order_type = position.type
    price_current = position.price_current
    price_open = position.price_open
    sl = position.sl
    tp = position.tp  # Get the take profit value

    dist_from_sl = abs(price_current - sl)

    if dist_from_sl >= max_dist_sl:
        # Calculate new SL
        if sl != 0.0:
            if order_type == 0:  # Buy order
                new_sl = sl + trail_amount
            elif order_type == 1:  # Sell order
                new_sl = sl - trail_amount
        else:
            new_sl = price_open - default_sl if order_type == 0 else price_open + default_sl

        new_tp = tp  # Keep TP unchanged

        request = {
            'action': mt5.TRADE_ACTION_SLTP,
            'position': position.ticket,
            'sl': new_sl,
            'tp': new_tp
        }

        result = mt5.order_send(request)
        print(result)
        return result

    return None

# Configurations for each phase (Values now represent points)
PHASES = [
    {"MAX_DIST_SL": 140, "TRAIL_AMOUNT": 105, "DEFAULT_SL": 100},  # 0
    {"MAX_DIST_SL": 50, "TRAIL_AMOUNT": 20},                    # 1
    {"MAX_DIST_SL": 40, "TRAIL_AMOUNT": 20},                    # 2
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 3
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 4
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 5
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 6
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 7
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 8
    {"MAX_DIST_SL": 40, "TRAIL_AMOUNT": 20},                    # 9
    {"MAX_DIST_SL": 40, "TRAIL_AMOUNT": 10},                    # 10
    {"MAX_DIST_SL": 40, "TRAIL_AMOUNT": 20},                    # 11
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 12
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 13
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                    # 14
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                     # 15
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                 #  # 16
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                     # 17   
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                  # 18                 
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                   # 19
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                   # 20
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10},                  # 21
    {"MAX_DIST_SL": 30, "TRAIL_AMOUNT": 10}                   # 22
]

# Main execution loop
if __name__ == '__main__':
    print('Trailing Stoploss - ALL Symbols...')

    while True:
        positions = mt5.positions_get()
        if positions:
            for position in positions:
                position_id = position.ticket

                if position_id not in position_phases:
                    position_phases[position_id] = -1  # No phase initially

                current_phase = position_phases[position_id]
                if current_phase == -1:
                    next_phase = 0
                else:
                    next_phase = current_phase + 1

                if next_phase < len(PHASES):
                    max_dist_sl = convert_to_points(position.symbol, PHASES[next_phase]["MAX_DIST_SL"])
                    price_current = position.price_current
                    sl = position.sl

                    dist_from_sl = abs(price_current - sl)

                    if dist_from_sl >= max_dist_sl or sl == 0.0:
                        result = trail_sl(position, next_phase)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            position_phases[position_id] = next_phase
                            print(f"✅ Position {position_id} ({position.symbol}) moved to phase {next_phase}")
                        else:
                            print(f"❌ Failed to trail SL for position {position_id} ({position.symbol}) in phase {next_phase}")

        # Wait 10 seconds before checking again
        time.sleep(5)
