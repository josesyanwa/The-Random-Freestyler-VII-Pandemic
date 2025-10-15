import json
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the file path from the environment variable
file_path = Path(os.getenv('FILE_PATH'))

try:
    json_text = file_path.read_text(encoding='utf-16')  # Read as UTF-16 encoded text
    data = json.loads(json_text)
    print("JSON data read from MT5 file:")
    print(json.dumps(data, indent=4))
except FileNotFoundError:
    print("File not found:", file_path)
except json.JSONDecodeError as e:
    print("Error decoding JSON:", e)
except Exception as e:
    print("An error occurred:", e)


# FILE_PATH=C:/Users/User/AppData/Roaming/MetaQuotes/Terminal/4FBA2952F23B1029F2DE78CC8BF367AD/MQL5/Files/last_trade.json
