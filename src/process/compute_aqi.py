"""
Step 3 — Compute daily AQI per station
Uses official CPCB sub-index breakpoints.
AQI = max of all valid pollutant sub-indices for that station-day.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

INPUT_FILE  = Path("data/rolling/last_30_days.csv")
OUTPUT_FILE = Path("data/rolling/last_30_days_with_aqi.csv")

# CPCB AQI breakpoints: (conc_lo, conc_hi, aqi_lo, aqi_hi)
AQI_BREAKPOINTS = {
    "PM2.5": [
        (0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
        (91, 120, 201, 300), (121, 250, 301, 400), (251, 10000, 401, 500),
    ],
    "PM10": [
        (0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200),
        (251, 350, 201, 300), (351, 430, 301, 400), (431, 10000, 401, 500),
    ],
    "NO2": [
        (0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200),
        (181, 280, 201, 300), (281, 400, 301, 400), (401, 10000, 401, 500),
    ],
    "SO2": [
        (0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200),
        (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 10000, 401, 500),
    ],
    "OZONE": [
        (0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200),
        (169, 208, 201, 300), (209, 748, 301, 400), (749, 10000, 401, 500),
    ],
}

AQI_THRESHOLD = 100  # CPCB: above this = unhealthy

# ── Helpers ──────────────────────────────────────────────────────────────────

def sub_index(pollutant: str, concentration: float) -> float:
    """Compute CPCB AQI sub-index for one pollutant reading."""
    if pollutant not in AQI_BREAKPOINTS or pd.isna(concentration):
        return np.nan

    for blo, bhi, ilo, ihi in AQI_BREAKPOINTS[pollutant]:
        if blo <= concentration <= bhi:
            return ((ihi - ilo) / (bhi - blo)) * (concentration - blo) + ilo

    return np.nan

# ── Load ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_FILE)

required = {"station", "pollutant_id", "avg_value", "last_update"}
missing  = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns in rolling dataset: {missing}")

df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")
df["date"]        = df["last_update"].dt.date.astype(str)
df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()

# ── Compute daily AQI per station ────────────────────────────────────────────

print("Computing daily AQI per station")

aqi_rows = []

for (station, date), group in df.groupby(["station", "date"]):
    sub_indices = [
        sub_index(row["pollutant_id"], row["avg_value"])
        for _, row in group.iterrows()
    ]
    valid = [s for s in sub_indices if not np.isnan(s)]
    aqi   = max(valid) if valid else np.nan

    aqi_rows.append({"station": station, "date": date, "AQI": aqi})

aqi_df = pd.DataFrame(aqi_rows)

# ── Merge back and save ──────────────────────────────────────────────────────

df = df.merge(aqi_df, on=["station", "date"], how="left")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print(f"Output saved:             {OUTPUT_FILE}")
print(f"Total rows:               {len(df)}")
print(f"Station-days with AQI:    {df['AQI'].notna().sum()}")
print(f"Station-days above {AQI_THRESHOLD}:   {(df['AQI'] > AQI_THRESHOLD).sum()}")
