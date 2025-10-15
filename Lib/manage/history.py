from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
import os
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Retrieve login credentials for MT5
login = int(os.getenv('MT5_LOGIN'))
server = os.getenv('MT5_SERVER')
password = os.getenv('MT5_PASSWORD')
path = os.getenv('MT5_PATH')

# Set pandas display options
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1500)

# MetaTrader5 package info
print("MetaTrader5 package author: ", mt5.__author__)
print("MetaTrader5 package version: ", mt5.__version__)
print()

# Connect to MetaTrader 5
if not mt5.initialize(path=path, login=login, server=server, password=password):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# Time range
from_date = datetime(2025, 7, 26)
to_date = datetime.now()
from_timestamp = int(from_date.timestamp())
to_timestamp = int(to_date.timestamp())

# Get history
history_deals = mt5.history_deals_get(from_timestamp, to_timestamp)

if history_deals is None:
    print(f"No history deals retrieved, error code={mt5.last_error()}")
    quit()

elif len(history_deals) > 0:
    print(f"history_deals_get({from_date}, {to_date}) = {len(history_deals)} deals")

    trade_data = []

    # Bot mapping
    bot_map = {
        0.03: "FreeStyler",
        0.02: "FreeStyler",
        0.01: "FreeStyler",
        0.1: "Gladiator",
        0.05: "Gladiator",
        0.025: "Gladiator",
        1.5: "Wire",
        0.75: "Wire",
        0.37: "Wire",
        0.38: "Wire",
    }

    # Define trade ranges for symbols with tags
    trade_ranges = {
        'XAUUSD': [
            (3203.1, 3206.25, "B"),
            (3206.25, 3209.4, "T"),
            (3215.6, 3218.75, "B"),
            (3218.75, 3221.9, "T"),
            (3228.1, 3231.25, "B"),
            (3231.25, 3234.4, "T"),
            (3240.6, 3243.75, "B"),
            (3243.75, 3246.9, "T"),
            (3253.1, 3256.25, "B"),
            (3256.25, 3259.4, "T"),
            (3265.6, 3268.75, "B"),
            (3268.75, 3271.9, "T"),
            (3278.1, 3281.25, "B"),
            (3281.25, 3284.4, "T"),
            (3290.6, 3293.75, "B"),
            (3293.75, 3296.9, "T"),
            (3303.1, 3306.25, "B"),
            (3306.25, 3309.4, "T"),
            (3315.6, 3318.75, "B"),
            (3318.75, 3321.9, "T"),
            (3328.1, 3331.25, "B"),
            (3331.25, 3334.4, "T"),
            (3340.6, 3343.75, "B"),
            (3343.75, 3346.9, "T"),
            (3353.1, 3356.25, "B"),
            (3356.25, 3359.4, "T"),
            (3365.6, 3368.75, "B"),
            (3368.75, 3371.9, "T"),
            (3378.1, 3381.25, "B"),
            (3381.25, 3384.4, "T"),
            (3390.6, 3393.75, "B"),
            (3393.75, 3396.9, "T"),
        ],
    }

    # Function to determine trade range based on entry price and symbol
    def get_trade_range(symbol, entry_price):
        ranges = trade_ranges.get(symbol, [])
        for lower, upper, tag in ranges:
            if lower <= entry_price < upper:
                return f"{tag} {lower}-{upper}"
        return "Outside Defined Ranges"

    # Function to determine duration range
    def get_duration_range(duration_minutes):
        if duration_minutes < 0:
            return "Negative Duration"
        lower = int(duration_minutes // 5) * 5
        upper = lower + 5
        return f"{lower}-{upper} min"

    # Group deals by position_id to pair open and close times
    position_trades = {}
    timezone = pytz.timezone("Africa/Nairobi")
    for deal in history_deals:
        position_id = deal.position_id
        # Convert UTC timestamp to Nairobi time, subtract 3 hours, and format as string
        utc_time = datetime.fromtimestamp(deal.time, tz=pytz.UTC)
        nairobi_time = utc_time.astimezone(timezone)
        adjusted_time = nairobi_time - timedelta(hours=3)
        deal_time = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')
        deal_day = adjusted_time.strftime('%A')
        # Calculate trade time interval (2-hour intervals)
        hour = adjusted_time.hour
        interval_start = hour - (hour % 2)
        interval_end = interval_start + 2
        trade_interval = f"{interval_start:02d}-{interval_end:02d}"
        print(f"Debug: Position ID {position_id}, UTC Time: {utc_time}, Initial Nairobi Time: {nairobi_time.strftime('%Y-%m-%d %H:%M:%S')}, Adjusted Nairobi Time: {deal_time}, Trade Time Interval: {trade_interval}, Day: {deal_day}")
        if position_id not in position_trades:
            position_trades[position_id] = {
                'order_id': deal.order,
                'symbol': deal.symbol,
                'lot_size': round(deal.volume, 5),
                'open_time': None,
                'close_time': None,
                'profit': 0.0,
                'trade_time_interval': None,
                'deal_day': None,
                'trade_type': None,
                'entry_price': None
            }
        if deal.entry == mt5.DEAL_ENTRY_IN:
            position_trades[position_id]['open_time'] = deal_time
            position_trades[position_id]['trade_time_interval'] = trade_interval
            position_trades[position_id]['deal_day'] = deal_day
            position_trades[position_id]['trade_type'] = 'Buy' if deal.type == mt5.DEAL_TYPE_BUY else 'Sell'
            position_trades[position_id]['entry_price'] = deal.price
        elif deal.entry == mt5.DEAL_ENTRY_OUT:
            position_trades[position_id]['close_time'] = deal_time
            position_trades[position_id]['profit'] = deal.profit

    # Build trade data for completed trades
    for position_id, trade in position_trades.items():
        if trade['open_time'] and trade['close_time']:  # Only include completed trades
            bot_name = bot_map.get(trade['lot_size'], "Unknown")
            trade_range = get_trade_range(trade['symbol'], trade['entry_price'])
            outcome = "Profit" if trade['profit'] > 0 else "Loss" if trade['profit'] < 0 else "Break Even"
            # Calculate trade duration in minutes
            open_time = datetime.strptime(trade['open_time'], '%Y-%m-%d %H:%M:%S')
            close_time = datetime.strptime(trade['close_time'], '%Y-%m-%d %H:%M:%S')
            duration_minutes = (close_time - open_time).total_seconds() / 60.0
            duration_range = get_duration_range(duration_minutes)
            trade_data.append([
                trade['order_id'],
                trade['open_time'],
                trade['close_time'],
                trade['symbol'],
                trade['lot_size'],
                trade['profit'],
                bot_name,
                trade['trade_time_interval'],
                trade['deal_day'],
                trade['trade_type'],
                trade['entry_price'],
                trade_range,
                outcome,
                duration_minutes,
                duration_range
            ])

    # Modified: Added "Trade Duration (min)" and "Duration Range" columns to DataFrame
    df = pd.DataFrame(trade_data, columns=["Trade ID", "Open Time", "Close Time", "Symbol", "Lot", "Profit", "Bot Name", "Trade Time Interval", "Day", "Trade Type", "Entry Price", "Trade Range", "Outcome", "Trade Duration (min)", "Duration Range"])
    df.insert(0, 'Row', '')  # Insert an empty 'Row' column initially

    # Save path
    lib_dir = "../manage/Excel"
    if not os.path.exists(lib_dir):
        os.makedirs(lib_dir)

    current_date = datetime.now().strftime('%Y-%m-%d')
    excel_file_path = os.path.join(lib_dir, f"trade_history_{current_date}.xlsx")

    if os.path.exists(excel_file_path):
        os.remove(excel_file_path)

    # Write Excel with formatting and dynamic subtotal
    with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Format Time columns as text (since they are strings)
        text_format = workbook.add_format({'num_format': '@'})
        worksheet.set_column('C:D', 20, text_format)  # Open Time and Close Time
        worksheet.set_column('I:I', 12, text_format)  # Trade Time Interval
        worksheet.set_column('J:J', 12, text_format)  # Day column
        worksheet.set_column('K:K', 12, text_format)  # Trade Type column
        worksheet.set_column('M:M', 15, text_format)  # Trade Range column
        worksheet.set_column('N:N', 12, text_format)  # Outcome column
        worksheet.set_column('P:P', 15, text_format)  # Duration Range column
        worksheet.set_column('A:A', 10)  # Row
        worksheet.set_column('B:B', 15)  # Trade ID
        worksheet.set_column('E:K', 12)  # Adjusted range (Symbol, Lot, Profit, Bot Name, Trade Time Interval, Day, Trade Type)
        worksheet.set_column('L:L', 12)  # Entry Price column
        worksheet.set_column('O:O', 15)  # Trade Duration (min) column

        # Add filter
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

        # Add dynamic row numbering for visible rows
        for row in range(2, len(df) + 2):  # Start from row 2 (data starts after header)
            worksheet.write_formula(
                f'A{row}',
                f'=IF(SUBTOTAL(3,B{row}),AGGREGATE(3,5,$B$2:$B{row}),"")'
            )

        # Add subtotal formula under Profit column (column G)
        profit_column_letter = 'G'
        start_row = 2  # Excel is 1-indexed and row 1 is header
        end_row = len(df) + 1
        total_row = end_row + 1

        # Write label and formula
        worksheet.write(f'F{total_row}', "Filtered Total Profit")
        worksheet.write_formula(f'{profit_column_letter}{total_row}', f'=SUBTOTAL(9,{profit_column_letter}{start_row}:{profit_column_letter}{end_row})')

    print(f"Excel saved with dynamic filtered totals at {excel_file_path}")

# Shutdown MT5
mt5.shutdown()