import pandas as pd
import numpy as np
from pathlib import Path

# I/O paths
INPUT_FILE = Path("data/rolling/last_30_days.csv")
OUTPUT_FILE = Path("data/rolling/last_30_days_with_aqi.csv")

# CPCB AQI breakpoints 
AQI_BREAKPOINTS = {
    "PM2.5": [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 10000, 401, 500),
    ],
    "PM10": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 10000, 401, 500),
    ],
    "NO2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 180, 101, 200),
        (181, 280, 201, 300),
        (281, 400, 301, 400),
        (401, 10000, 401, 500),
    ],
    "SO2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 380, 101, 200),
        (381, 800, 201, 300),
        (801, 1600, 301, 400),
        (1601, 10000, 401, 500),
    ],
    "OZONE": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 168, 101, 200),
        (169, 208, 201, 300),
        (209, 748, 301, 400),
        (749, 10000, 401, 500),
    ],
}

def compute_sub_index(pollutant, concentration):
    if pollutant not in AQI_BREAKPOINTS or pd.isna(concentration):
        return np.nan

    for blo, bhi, ilo, ihi in AQI_BREAKPOINTS[pollutant]:
        if blo <= concentration <= bhi:
            return ((ihi - ilo) / (bhi - blo)) * (concentration - blo) + ilo

    return np.nan

# Load rolling dataset
df = pd.read_csv(INPUT_FILE)

required_cols = {"station", "pollutant_id", "avg_value", "last_update"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Prepare datetime
df["last_update"] = pd.to_datetime(df["last_update"], errors="coerce")
df["date"] = df["last_update"].dt.date.astype(str)

# Normalize pollutants
df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()

# Compute daily AQI 
aqi_rows = []

for (station, date), group in df.groupby(["station", "date"]):
    sub_indices = []

    for _, row in group.iterrows():
        si = compute_sub_index(row["pollutant_id"], row["avg_value"])
        if not pd.isna(si):
            sub_indices.append(si)

    aqi = max(sub_indices) if sub_indices else np.nan
    aqi_rows.append({
        "station": station,
        "date": date,
        "AQI": aqi
    })

aqi_df = pd.DataFrame(aqi_rows)

# Merge AQI into rolling dataset
df = df.merge(aqi_df, on=["station", "date"], how="left")

# Save output
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print("Daily AQI computed using CPCB methodology")
print(f"Output file: {OUTPUT_FILE}")
print(f"Total rows: {len(df)}")
print(f"Station-days with AQI: {df['AQI'].notna().sum()}")
