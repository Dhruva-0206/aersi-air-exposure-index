"""
Step 4 — Compute AERSI v3 station scores

Formula:
    AERSI_v3 = PL_robust^0.45 × EPF_adj^0.25 × VSF_robust^0.20 × CF_impact

    PL_robust   = Σ w_p_adj × (C_p / L_p)^0.6
    EPF_adj     = 1 + (D_exceed / W) × (D_obs/30)^0.5
    VSF_robust  = 1 + tanh(S / 45)  where S = median |AQI_t - AQI_{t-1}|
    CF_impact   = 0.7 + 0.3 × CF_data

Score bands (recalibrated for geometric mean structure):
    < 0.6      Very Low
    0.6–1.0    Low
    1.0–1.5    Moderate
    1.5–2.2    High
    > 2.2      Extreme

Confidence labels (from CF_data):
    ≥ 0.85     High Confidence
    ≥ 0.65     Medium Confidence
    ≥ 0.40     Low Confidence
    < 0.40     Provisional
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

INPUT_FILE  = Path("data/rolling/last_30_days_with_aqi.csv")
OUTPUT_FILE = Path("data/processed/aersi_station_scores.csv")

TARGET_WINDOW = 30
AQI_THRESHOLD = 100

WHO_LIMITS = {
    "PM2.5": 15,
    "PM10":  45,
    "NO2":   25,
    "SO2":   40,
    "OZONE": 60,
}

WEIGHTS = {
    "PM2.5": 0.35,
    "PM10":  0.25,
    "NO2":   0.15,
    "OZONE": 0.15,
    "SO2":   0.10,
}

CORE_POLLUTANTS = set(WEIGHTS.keys())

# ── Score bands ───────────────────────────────────────────────────────────────

BANDS = [
    ("Very Low",  0,    0.6),
    ("Low",       0.6,  1.0),
    ("Moderate",  1.0,  1.5),
    ("High",      1.5,  2.2),
    ("Extreme",   2.2,  9999),
]

def aersi_category(v):
    for label, lo, hi in BANDS:
        if lo <= v < hi:
            return label
    return "Extreme"

# ── Helpers ──────────────────────────────────────────────────────────────────

def compute_pl_robust(group: pd.DataFrame) -> tuple:
    present = {}
    for _, row in group.iterrows():
        p = row["pollutant_id"]
        c = row["avg_value"]
        if p in CORE_POLLUTANTS and not pd.isna(c) and c >= 0:
            present[p] = c

    if not present:
        return np.nan, 0

    weight_sum = sum(WEIGHTS[p] for p in present)
    pl = 0.0
    for p, c in present.items():
        w_adj = WEIGHTS[p] / weight_sum
        n_p   = c / WHO_LIMITS[p]
        pl   += w_adj * (n_p ** 0.6)

    return pl, len(present)


def compute_epf_adj(aqi_series: pd.Series, d_obs: int) -> float:
    if d_obs == 0 or len(aqi_series) == 0:
        return 1.0
    d_exceed    = (aqi_series > AQI_THRESHOLD).sum()
    data_weight = (min(d_obs, TARGET_WINDOW) / TARGET_WINDOW) ** 0.5
    return float(1.0 + (d_exceed / TARGET_WINDOW) * data_weight)


def compute_vsf_robust(aqi_series: pd.Series) -> float:
    if len(aqi_series) < 2:
        return 1.0
    s = aqi_series.diff().dropna().abs().median()
    return 1.0 + float(np.tanh(s / 45.0))


def compute_cf(n_pollutants: int, d_obs: int, window: int = TARGET_WINDOW) -> tuple:
    cf_pollutant = min(n_pollutants / 5, 1.0)
    cf_day       = min(d_obs / window, 1.0)
    cf_quality   = 1.0
    cf_data      = 0.5 * cf_pollutant + 0.3 * cf_day + 0.2 * cf_quality
    cf_impact    = 0.7 + 0.3 * cf_data
    return cf_data, cf_impact


def confidence_label(cf_data: float) -> str:
    if cf_data >= 0.85: return "High"
    elif cf_data >= 0.65: return "Medium"
    elif cf_data >= 0.40: return "Low"
    else: return "Provisional"


# ── Load ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_FILE)

required = {"station", "date", "pollutant_id", "avg_value", "AQI", "latitude", "longitude", "city", "state"}
missing  = required - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()
df["avg_value"]    = pd.to_numeric(df["avg_value"], errors="coerce")
df["AQI"]          = pd.to_numeric(df["AQI"], errors="coerce")

print(f"Loaded {len(df)} rows across {df['station'].nunique()} stations")

# ── Step 1: PL per station-day ───────────────────────────────────────────────

print("Computing PL_robust per station-day")

pl_rows = []
for (station, date), group in df.groupby(["station", "date"]):
    meta = group.iloc[0]
    pl, n_poll = compute_pl_robust(group)
    pl_rows.append({
        "station": station, "date": date,
        "PL": pl, "n_pollutants": n_poll,
        "AQI": meta["AQI"], "city": meta["city"], "state": meta["state"],
        "latitude": meta["latitude"], "longitude": meta["longitude"],
    })

pl_df = pd.DataFrame(pl_rows)

# ── Step 2: EPF, VSF, CF per station ─────────────────────────────────────────

print("Computing EPF_adj, VSF_robust, CF per station")

results = []

for station, group in pl_df.groupby("station"):
    group      = group.sort_values("date")
    aqi_series = group["AQI"].dropna()
    d_obs      = len(aqi_series)
    n_poll_avg = int(group["n_pollutants"].median()) if len(group) > 0 else 0

    epf = compute_epf_adj(aqi_series, d_obs)
    vsf = compute_vsf_robust(aqi_series)
    cf_data, cf_impact = compute_cf(n_poll_avg, d_obs)

    for _, row in group.iterrows():
        pl  = row["PL"]
        if not pd.isna(pl) and pl > 0:
            aersi = (pl ** 0.45) * (epf ** 0.25) * (vsf ** 0.20) * cf_impact
        else:
            aersi = np.nan

        results.append({
            "station":    station,
            "date":       row["date"],
            "PL":         round(pl,        4) if not pd.isna(pl)    else np.nan,
            "EPF":        round(epf,       4),
            "VSF":        round(vsf,       4),
            "CF_data":    round(cf_data,   4),
            "CF_impact":  round(cf_impact, 4),
            "AERSI":      round(aersi,     4) if not pd.isna(aersi) else np.nan,
            "confidence": confidence_label(cf_data),
            "city":       row["city"],
            "state":      row["state"],
            "latitude":   row["latitude"],
            "longitude":  row["longitude"],
        })

final_df = pd.DataFrame(results)

# ── Step 3: Most recent row per station ──────────────────────────────────────

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

# ── Summary ───────────────────────────────────────────────────────────────────

valid = final_df.dropna(subset=["AERSI"])

print(f"\nAERSI v3 computation complete")
print(f"Output:          {OUTPUT_FILE}")
print(f"Stations scored: {len(valid)} / {len(final_df)}")
print(f"Window days:     {pl_df['date'].nunique()} / {TARGET_WINDOW}")
print()
print("Score distribution:")
for label, lo, hi in BANDS:
    count = ((valid["AERSI"] >= lo) & (valid["AERSI"] < hi)).sum()
    pct   = 100 * count / len(valid) if len(valid) else 0
    print(f"  {label:10s} ({lo}–{hi if hi < 9999 else '∞':>5}) : {count:4d} stations ({pct:.1f}%)")

print()
print("Confidence distribution:")
for label in ["High", "Medium", "Low", "Provisional"]:
    count = (final_df["confidence"] == label).sum()
    print(f"  {label:12s}: {count} stations")
