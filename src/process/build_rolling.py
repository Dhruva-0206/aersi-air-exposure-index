"""
Step 2 — Build rolling 30-day dataset
Merges the most recent 30 daily snapshots.
Detects and reports any missing days in the window.
"""

import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

SNAPSHOT_DIR  = Path("data/snapshots")
OUTPUT_DIR    = Path("data/rolling")
OUTPUT_FILE   = OUTPUT_DIR / "last_30_days.csv"
WINDOW_DAYS   = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Discover snapshots ───────────────────────────────────────────────────────

print("Scanning snapshot directory")

files = sorted(SNAPSHOT_DIR.glob("cpcb_snapshot_*.csv"), reverse=True)

if not files:
    raise RuntimeError(f"No snapshots found in {SNAPSHOT_DIR}")

snapshot_map = {}
for f in files:
    try:
        date_str  = f.stem.replace("cpcb_snapshot_", "")
        snap_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        snapshot_map[snap_date] = f
    except ValueError:
        print(f"  Skipping unexpected filename: {f.name}")

# ── Gap detection ────────────────────────────────────────────────────────────

today     = datetime.now(timezone.utc).date()
all_dates = [today - timedelta(days=i) for i in range(WINDOW_DAYS)]
missing   = [d for d in all_dates if d not in snapshot_map]

if missing:
    print(f"WARNING: {len(missing)} day(s) missing from the rolling window:")
    for d in sorted(missing):
        print(f"  - {d}")
    print("EPF and VSF will be computed on available data only.")
else:
    print(f"All {WINDOW_DAYS} days present -- full window available.")

# ── Select up to 30 most recent snapshots ────────────────────────────────────

selected = sorted(snapshot_map.items(), reverse=True)[:WINDOW_DAYS]

print(f"\nUsing {len(selected)} snapshot(s):")
for snap_date, fname in selected:
    print(f"  {snap_date} -> {fname.name}")

# ── Load and merge ───────────────────────────────────────────────────────────

dfs = []
for snap_date, fpath in selected:
    df = pd.read_csv(fpath)
    df["snapshot_date"] = str(snap_date)
    dfs.append(df)

rolling_df = pd.concat(dfs, ignore_index=True)

# Normalize column names
rolling_df.columns = rolling_df.columns.str.strip().str.lower()

# ── Save ─────────────────────────────────────────────────────────────────────

rolling_df.to_csv(OUTPUT_FILE, index=False)

print(f"\nRolling dataset saved: {OUTPUT_FILE}")
print(f"Total rows:            {len(rolling_df)}")
print(f"Snapshot days present: {rolling_df['snapshot_date'].nunique()} / {WINDOW_DAYS}")
print(f"Pollutants found:      {sorted(rolling_df['pollutant_id'].str.upper().unique())}")