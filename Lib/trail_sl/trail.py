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

print("Connected to FTMO Account:", mt5.account_info().name)

# Function to convert points to price format using symbol's point value
def convert_to_points(symbol, value_in_points):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None or symbol_info.point is None:
        print(f"⚠️ Warning: Failed to retrieve point value for {symbol}.")
        return None
    return value_in_points * symbol_info.point  # Convert points to price format

# Function to get previous two M2 candles' data
def get_previous_m5_candles(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, 2)  # Get previous 2 M2 candles
    if rates is None or len(rates) < 2:
        print(f"⚠️ Warning: Failed to retrieve M2 candle data for {symbol}.")
        return None
    return rates  # Return array with previous candle (index 1) and candle before it (index 0)

# Function to trail SL based on previous M2 candle with conditions
def trail_sl(position):
    symbol = position.symbol
    default_sl_points = convert_to_points(symbol, 100)  # Default 100 points
    if default_sl_points is None:
        print(f"❌ Failed to trail SL for {symbol}: Unable to convert default SL points.")
        return None

    # Get position data
    order_type = position.type
    price_open = position.price_open
    price_current = position.price_current
    sl = position.sl
    tp = position.tp  # Get the take profit value

    # Get previous two M2 candles' data
    candles = get_previous_m5_candles(symbol)
    if candles is None:
        print(f"❌ Failed to trail SL for {symbol}: No candle data.")
        return None

    prev_candle = candles[1]  # Previous M2 candle
    prev_prev_candle = candles[0]  # Candle before previous M2 candle

    # Check if trade is in profit
    in_profit = (order_type == 0 and price_current > price_open) or (order_type == 1 and price_current < price_open)

    # Check candle position relative to entry price
    candle_above_entry = order_type == 0 and prev_candle['low'] > price_open and prev_candle['high'] > price_open
    candle_below_entry = order_type == 1 and prev_candle['high'] < price_open and prev_candle['low'] < price_open

    # Check close price trend
    close_trend = (order_type == 0 and prev_candle['close'] > prev_prev_candle['close']) or \
                  (order_type == 1 and prev_candle['close'] < prev_prev_candle['close'])

    # Proceed only if all conditions are met
    if in_profit and (candle_above_entry or candle_below_entry) and close_trend:
        # Calculate new SL based on previous M2 candle
        offset = convert_to_points(symbol, 20)  # 20 points offset
        if offset is None:
            print(f"❌ Failed to trail SL for {symbol}: Unable to convert offset points.")
            return None

        if order_type == 0:  # Buy order
            new_sl = prev_candle['low'] - offset  # 20 points below previous M2 low
        elif order_type == 1:  # Sell order
            new_sl = prev_candle['high'] + offset  # 20 points above previous M2 high
        else:
            print(f"⚠️ Warning: Unknown order type {order_type} for {symbol}.")
            return None

        # Use default SL if no SL is set
        if sl == 0.0:
            new_sl = price_open - default_sl_points if order_type == 0 else price_open + default_sl_points

        # Only update SL if it's different from the current SL
        if sl != new_sl:
            request = {
                'action': mt5.TRADE_ACTION_SLTP,
                'position': position.ticket,
                'sl': new_sl,
                'tp': tp  # Keep TP unchanged
            }

            result = mt5.order_send(request)
            print(result)
            return result

    return None

# Main execution loop
if __name__ == '__main__':
    print('Trailing Stoploss - ALL Symbols...')

    while True:
        positions = mt5.positions_get()
        if positions:
            for position in positions:
                position_id = position.ticket
                result = trail_sl(position)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Position {position_id} ({position.symbol}) SL updated")

        # Wait 60 seconds before checking again
        time.sleep(33)