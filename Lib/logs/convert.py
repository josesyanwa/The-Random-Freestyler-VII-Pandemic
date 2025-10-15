import re
import pandas as pd

# Initialize list to store parsed log entries
log_data = []

# Regular expression to match common log format: "2023-10-01 10:00:00 LEVEL Message"
log_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+) (.*)"

# Read the log file
try:
    with open("mt5_Pandemic_XE.log", "r") as file:
        for line in file:
            # Strip whitespace and skip empty lines
            line = line.strip()
            if not line:
                continue
                
            # Try to match the log pattern
            match = re.match(log_pattern, line)
            if match:
                timestamp, level, message = match.groups()
                log_data.append({
                    "timestamp": timestamp,
                    "level": level,
                    "message": message
                })
            else:
                # If line doesn't match, log it as unparsed
                log_data.append({
                    "timestamp": None,
                    "level": None,
                    "message": line
                })

    # Convert to DataFrame
    df = pd.DataFrame(log_data)
    
    # Save to CSV
    df.to_csv("mt5_Pandemic_XE.csv", index=False)
    print("Successfully converted mt5_Pandemic_MAIN.log to mt5_Pandemic_MAIN.csv")
    
except FileNotFoundError:
    print("Error: mt5_Pandemic_MAIN.log not found")
except Exception as e:
    print(f"Error: {str(e)}")