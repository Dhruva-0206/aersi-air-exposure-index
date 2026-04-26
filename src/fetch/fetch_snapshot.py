"""
Step 1 — Fetch daily CPCB snapshot
Pulls all station data from data.gov.in and saves as a dated CSV.
Skips gracefully if today's snapshot already exists.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ── Config ───────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("DATA_GOV_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "DATA_GOV_API_KEY not found.\n"
        "  Local: add it to your .env file\n"
        "  GitHub Actions: add it in repo Settings → Secrets → Actions"
    )

RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
BASE_URL     = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
PAGE_SIZE    = 1000

SNAPSHOT_DIR = Path("data/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

TODAY       = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUTPUT_FILE = SNAPSHOT_DIR / f"cpcb_snapshot_{TODAY}.csv"

# ── Skip if already fetched today ────────────────────────────────────────────

if OUTPUT_FILE.exists():
    print(f"Snapshot already exists for {TODAY}, skipping fetch.")
    raise SystemExit(0)

# ── Paginated fetch ──────────────────────────────────────────────────────────

print(f"Fetching CPCB snapshot for {TODAY}")

all_records = []
offset = 0
page   = 1

while True:
    for attempt in range(3):
        try:
            response = requests.get(
                BASE_URL,
                params={
                    "api-key": API_KEY,
                    "format":  "json",
                    "limit":   PAGE_SIZE,
                    "offset":  offset,
                },
                timeout=90,
            )
            if response.status_code in (502, 503, 504):
                print(f"  HTTP {response.status_code} on page {page}, attempt {attempt + 1}/3 — retrying...")
                if attempt == 2:
                    raise RuntimeError(f"API returned {response.status_code} three times on page {page}.")
                continue
            break
        except requests.exceptions.ReadTimeout:
            print(f"  Timeout on page {page}, attempt {attempt + 1}/3 — retrying...")
            if attempt == 2:
                raise RuntimeError("API timed out 3 times in a row. Try again later.")

    if response.status_code != 200:
        raise RuntimeError(
            f"API request failed (HTTP {response.status_code}): {response.text[:300]}"
        )

    payload = response.json()
    records = payload.get("records", [])

    if not records:
        break

    all_records.extend(records)
    print(f"  Page {page}: {len(records)} records")
    offset += PAGE_SIZE
    page   += 1

print(f"Total records fetched: {len(all_records)}")

if not all_records:
    raise RuntimeError("API returned zero records — aborting.")

# ── Save ─────────────────────────────────────────────────────────────────────

df = pd.DataFrame(all_records)
df.to_csv(OUTPUT_FILE, index=False)

print(f"Snapshot saved: {OUTPUT_FILE}")
print(f"Columns: {list(df.columns)}")