import os
import pandas as pd
from datetime import datetime

# setup of directory
SNAPSHOT_DIR = "data/snapshots"
OUTPUT_DIR = "data/rolling"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "last_30_days.csv")
WINDOW_DAYS = 30

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Scanning snapshot directory")

# Collect all CPCB snapshots
files = [
    f for f in os.listdir(SNAPSHOT_DIR)
    if f.startswith("cpcb_snapshot_") and f.endswith(".csv")
]

if not files:
    raise RuntimeError("No snapshot files found in data/snapshots")

# Parse dates 
snapshot_info = []

for fname in files:
    try:
        date_str = fname.replace("cpcb_snapshot_", "").replace(".csv", "")
        snap_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        snapshot_info.append((snap_date, fname))
    except ValueError:
        print(f"Skipping file with unexpected name: {fname}")

# Sort newest 
snapshot_info.sort(reverse=True)

# Select up to the most recent = 30 days
selected = snapshot_info[:WINDOW_DAYS]

print(f"Using {len(selected)} snapshot(s):")
for snap_date, fname in selected:
    print(f"  {snap_date} -> {fname}")

# Load and merge snapshots files
dfs = []

for snap_date, fname in selected:
    path = os.path.join(SNAPSHOT_DIR, fname)
    df = pd.read_csv(path)

    # Attach snapshot date for downstream processing
    df["snapshot_date"] = snap_date
    dfs.append(df)

rolling_df = pd.concat(dfs, ignore_index=True)

# Normalize column names for consistency
rolling_df.columns = (
    rolling_df.columns
    .str.strip()
    .str.lower()
)

# Save rolling dataset
rolling_df.to_csv(OUTPUT_FILE, index=False)

print("Rolling dataset created")
print(f"Output file: {OUTPUT_FILE}")
print(f"Total rows: {len(rolling_df)}")
print(f"Unique snapshot days: {rolling_df['snapshot_date'].nunique()}")
print(f"Pollutants present: {sorted(rolling_df['pollutant_id'].unique())}")
