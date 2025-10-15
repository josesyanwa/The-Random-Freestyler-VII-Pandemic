import MetaTrader5 as mt5
import schedule
import time
import os
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN3'))
server = os.getenv('MT5_SERVER3')
password = os.getenv('MT5_PASSWORD3')
path = os.getenv('MT5_PATH3')

print(f"Initiate random trade placementS...")

# Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize(path=path, login=login, server=server, password=password):
        print("Initialization failed:", mt5.last_error())
        mt5.shutdown()
        return False
    print("Connected to FTMO Account:", mt5.account_info().name)
    return True

def place_trade():
    # Initialize MT5 connection
    if not initialize_mt5():
        return

    # Define symbol (assuming EURUSD; change as needed)
    symbol = "XAUUSD"

    # Check if symbol exists
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, "not found, cannot call order_check()")
        mt5.shutdown()
        return

    # If the symbol is unavailable in MarketWatch, add it
    if not symbol_info.visible:
        print(symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print("symbol_select({}) failed, exit", symbol)
            mt5.shutdown()
            return

    # Get the point size for the symbol
    point = symbol_info.point

    # Get current ask and bid prices
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("Failed to get tick data")
        mt5.shutdown()
        return

    ask = tick.ask
    bid = tick.bid

    # Randomly choose buy or sell
    trade_type = random.choice([mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL])
    trade_type_str = "Buy" if trade_type == mt5.ORDER_TYPE_BUY else "Sell"

    # Set price, SL, and TP based on trade type
    price = ask if trade_type == mt5.ORDER_TYPE_BUY else bid
    sl = price - 500 * point if trade_type == mt5.ORDER_TYPE_BUY else price + 500 * point
    tp = price + 500 * point if trade_type == mt5.ORDER_TYPE_BUY else price - 500 * point

    # Prepare the trade request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,  # Lot size; adjust as needed
        "type": trade_type,
        "price": price,
        "sl": sl,  # SL 500 points away
        "tp": tp,  # TP 500 points away
        "deviation": 20,  # Deviation in points
        "magic": 234000,  # Magic number
        "comment": f"Python {trade_type_str} trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send the trading request
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"{trade_type_str} order_send failed, retcode =", result.retcode)
    else:
        print(f"{trade_type_str} order_send done, ", result)

    # Shutdown connection
    mt5.shutdown()

# Schedule the trade to run every hour at :30
schedule.every().hour.at(":30").do(place_trade)
schedule.every().hour.at(":00").do(place_trade)
# Run the scheduler in a loop
while True:
    schedule.run_pending()
    time.sleep(1)


# 172357
# sE!r2z57x6
# FusionMarkets-Demo