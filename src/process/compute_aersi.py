"""
Step 4 — Compute AERSI station scores

Formula:
    AERSI = PL × EPF × VSF

    PL  = Σ weight_p × (concentration_p / WHO_limit_p)
              — WHO-normalized pollution load, today's reading

    EPF = 1 + (D_exceed / W) × confidence
              — how often AQI > 100, shrunk toward 1.0 when data is sparse
              — confidence = min(W / 30, 1.0)

    VSF = 1 + tanh(σ / 100)
              — bounded volatility penalty, always between 1.0 and 2.0
              — σ = std dev of daily AQI across the rolling window

Reference baseline:
    AERSI = 1.0  →  station at exactly WHO thresholds,
                     no exceedances, zero volatility.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

INPUT_FILE  = Path("data/rolling/last_30_days_with_aqi.csv")
OUTPUT_FILE = Path("data/processed/aersi_station_scores.csv")

TARGET_WINDOW = 30   # full EPF confidence at this many days
AQI_THRESHOLD = 100  # CPCB exceedance threshold for EPF

WHO_LIMITS = {
    "PM2.5": 15,
    "PM10":  45,
    "NO2":   25,
    "SO2":   40,
    "OZONE": 100,
}

WEIGHTS = {
    "PM2.5": 0.35,
    "PM10":  0.25,
    "NO2":   0.15,
    "OZONE": 0.15,
    "SO2":   0.10,
}

CORE_POLLUTANTS = set(WEIGHTS.keys())

# ── Helpers ──────────────────────────────────────────────────────────────────

def compute_pl(group: pd.DataFrame) -> float:
    """
    Pollution Load for a single station-day.
    Weighted sum of WHO-normalized pollutant concentrations.
    Returns NaN if no core pollutant data is available.
    """
    terms = []
    for _, row in group.iterrows():
        p = row["pollutant_id"]
        c = row["avg_value"]
        if p in CORE_POLLUTANTS and not pd.isna(c):
            terms.append(WEIGHTS[p] * (c / WHO_LIMITS[p]))

    return sum(terms) if terms else np.nan


def compute_epf(aqi_series: pd.Series, target_window: int) -> float:
    """
    Exposure Persistence Factor.
    EPF = 1 + (D_exceed / W) × confidence
    confidence = min(W / target_window, 1.0)

    Shrinks toward 1.0 when data is sparse, reaches full
    strength at target_window days.
    """
    w          = len(aqi_series)
    d_exceed   = (aqi_series > AQI_THRESHOLD).sum()
    confidence = min(w / target_window, 1.0)
    return 1.0 + (d_exceed / w) * confidence


def compute_vsf(aqi_series: pd.Series) -> float:
    """
    Variability Severity Factor.
    VSF = 1 + tanh(σ / 100)

    Always in [1.0, 2.0]. Mean-independent — captures absolute
    swing regardless of how high the baseline pollution is.
    Requires at least 2 data points; returns 1.0 otherwise.
    """
    if len(aqi_series) < 2:
        return 1.0
    sigma = aqi_series.std(ddof=0)
    return 1.0 + np.tanh(sigma / 100.0)

# ── Load ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_FILE)

required = {
    "station", "date", "pollutant_id", "avg_value",
    "AQI", "latitude", "longitude", "city", "state"
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()
df["avg_value"]    = pd.to_numeric(df["avg_value"], errors="coerce")
df["AQI"]          = pd.to_numeric(df["AQI"], errors="coerce")

print(f"Loaded {len(df)} rows across {df['station'].nunique()} stations")

# ── Step 1: Compute PL per station-day ──────────────────────────────────────

print("Computing PL per station-day")

pl_rows = []

for (station, date), group in df.groupby(["station", "date"]):
    meta = group.iloc[0]
    pl_rows.append({
        "station":   station,
        "date":      date,
        "PL":        compute_pl(group),
        "AQI":       meta["AQI"],
        "city":      meta["city"],
        "state":     meta["state"],
        "latitude":  meta["latitude"],
        "longitude": meta["longitude"],
    })

pl_df = pd.DataFrame(pl_rows)

# ── Step 2: Compute EPF and VSF per station (across the full window) ─────────

print("Computing EPF and VSF per station")

results = []

for station, group in pl_df.groupby("station"):
    group      = group.sort_values("date")
    aqi_series = group["AQI"].dropna()

    # Need at least one valid AQI reading
    if len(aqi_series) == 0:
        epf = 1.0
        vsf = 1.0
    else:
        epf = compute_epf(aqi_series, TARGET_WINDOW)
        vsf = compute_vsf(aqi_series)

    for _, row in group.iterrows():
        pl    = row["PL"]
        aersi = pl * epf * vsf if not pd.isna(pl) else np.nan

        results.append({
            "station":   station,
            "date":      row["date"],
            "PL":        round(pl,    4) if not pd.isna(pl)    else np.nan,
            "EPF":       round(epf,   4),
            "VSF":       round(vsf,   4),
            "AERSI":     round(aersi, 4) if not pd.isna(aersi) else np.nan,
            "city":      row["city"],
            "state":     row["state"],
            "latitude":  row["latitude"],
            "longitude": row["longitude"],
        })

final_df = pd.DataFrame(results)

# ── Step 3: Keep only the most recent row per station ────────────────────────

final_df = (
    final_df
    .sort_values("date")
    .groupby("station", as_index=False)
    .tail(1)
    .reset_index(drop=True)
)

# ── Save ─────────────────────────────────────────────────────────────────────

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
final_df.to_csv(OUTPUT_FILE, index=False)

# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\nAERSI computation complete")
print(f"Output:           {OUTPUT_FILE}")
print(f"Stations scored:  {len(final_df)}")
print(f"Window days used: {pl_df['date'].nunique()} / {TARGET_WINDOW}")
print(f"Confidence level: {min(pl_df['date'].nunique() / TARGET_WINDOW, 1.0):.0%}")
print()
print("Score distribution:")
for label, lo, hi in [
    ("Very Low  (< 0.8)",    0,    0.8),
    ("Low       (0.8–1.2)",  0.8,  1.2),
    ("Moderate  (1.2–2.0)",  1.2,  2.0),
    ("High      (2.0–3.0)",  2.0,  3.0),
    ("Extreme   (> 3.0)",    3.0,  9999),
]:
    count = ((final_df["AERSI"] >= lo) & (final_df["AERSI"] < hi)).sum()
    print(f"  {label} :  {count} stations")
