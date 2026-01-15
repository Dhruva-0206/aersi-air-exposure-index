import pandas as pd
import numpy as np
from pathlib import Path

# I/O paths
INPUT_FILE = Path("data/rolling/last_30_days_with_aqi.csv")
OUTPUT_FILE = Path("data/processed/aersi_station_scores.csv")

# WHO limits 
WHO_LIMITS = {
    "PM2.5": 15,
    "PM10": 45,
    "NO2": 25,
    "SO2": 40,
    "OZONE": 100
}

# Relative weights (sum = 1)
WEIGHTS = {
    "PM2.5": 0.35,
    "PM10": 0.25,
    "NO2": 0.15,
    "OZONE": 0.15,
    "SO2": 0.10
}

CORE_POLLUTANTS = set(WEIGHTS.keys())

# Load rolling dataset with AQI
df = pd.read_csv(INPUT_FILE)

required_cols = {
    "station", "date", "pollutant_id", "avg_value",
    "AQI", "latitude", "longitude", "city", "state"
}

missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Normalize pollutants
df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()

# Compute PL
pl_rows = []

for (station, date), group in df.groupby(["station", "date"]):
    terms = []

    for _, row in group.iterrows():
        pollutant = row["pollutant_id"]
        concentration = row["avg_value"]

        if pollutant in CORE_POLLUTANTS and not pd.isna(concentration):
            terms.append(
                WEIGHTS[pollutant] * (concentration / WHO_LIMITS[pollutant])
            )

    pl = sum(terms) if terms else np.nan
    meta = group.iloc[0]

    pl_rows.append({
        "station": station,
        "date": date,
        "PL": pl,
        "AQI": meta["AQI"],
        "city": meta["city"],
        "state": meta["state"],
        "latitude": meta["latitude"],
        "longitude": meta["longitude"]
    })

pl_df = pd.DataFrame(pl_rows)

# Compute EPF VSF 
results = []

for station, group in pl_df.groupby("station"):
    group = group.sort_values("date")
    window_size = len(group)

    aqi_series = group["AQI"]

    if window_size >= 2:
        days_exceed = (aqi_series > 100).sum()
        epf = 1 + (days_exceed / window_size)

        mean_aqi = aqi_series.mean()
        std_aqi = aqi_series.std(ddof=0)

        vsf = 1 + (std_aqi / mean_aqi) if mean_aqi > 0 else 1.0
    else:
        epf = 1.0
        vsf = 1.0

    for _, row in group.iterrows():
        pl = row["PL"]

        aersi = (
            pl * epf * vsf
            if not pd.isna(pl)
            else np.nan
        )

        results.append({
            "station": station,
            "date": row["date"],
            "PL": pl,
            "EPF": epf,
            "VSF": vsf,
            "AERSI": aersi,
            "city": row["city"],
            "state": row["state"],
            "latitude": row["latitude"],
            "longitude": row["longitude"]
        })

final_df = pd.DataFrame(results)

# Keep the most recent day per station
final_df = (
    final_df.sort_values("date")
    .groupby("station", as_index=False)
    .tail(1)
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
final_df.to_csv(OUTPUT_FILE, index=False)

print("AERSI computation completed")
print(f"Output file: {OUTPUT_FILE}")
print(f"Stations scored: {len(final_df)}")
print("PL is WHO-normalized; EPF and VSF are AQI-based")
