import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load the variables (env)
load_dotenv()
API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    raise RuntimeError("DATA_GOV_API_KEY not found in .env file")

# API configuration of the cpcb
RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

LIMIT = 1000  # API size limit of page
FORMAT = "json"

# Use UTC date , keep filenames consistent
TODAY = datetime.utcnow().strftime("%Y-%m-%d")
OUTPUT_DIR = "data/snapshots"
OUTPUT_FILE = f"{OUTPUT_DIR}/cpcb_snapshot_{TODAY}.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Fetching CPCB daily AQI snapshot")
print(f"Snapshot date: {TODAY}")

all_records = []
offset = 0
page = 1

# Fetch data (pagination
while True:
    params = {
        "api-key": API_KEY,
        "format": FORMAT,
        "limit": LIMIT,
        "offset": offset
    }

    response = requests.get(BASE_URL, params=params, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"API request failed ({response.status_code}): {response.text}"
        )

    payload = response.json()
    records = payload.get("records", [])

    if not records:
        break

    all_records.extend(records)
    print(f"Page {page}: {len(records)} records")

    offset += LIMIT
    page += 1

print(f"\nTotal records fetched: {len(all_records)}")

if not all_records:
    raise RuntimeError("No data received from CPCB API")

# Save raw snapshot 
df = pd.DataFrame(all_records)
df.to_csv(OUTPUT_FILE, index=False)

print("Daily snapshot saved")
print(f"File: {OUTPUT_FILE}")
print(f"Columns: {list(df.columns)}")
