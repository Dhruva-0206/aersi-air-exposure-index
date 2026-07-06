"""
Step 4 — Compute AERSI station scores

Formula:
    AERSI = PL_robust^0.50 × EPF_adj^0.25 × VSF_robust^0.25

    PL_robust  = Σ w_p_adj × (C_p / L_p)^0.6
                 C_p = mean concentration across the rolling window.
                 WHO-normalized, soft-saturated, weight-renormalized
                 over only the pollutants actually present.

    EPF_adj    = 1 + (D_exceed / D_obs) × (D_obs/30)^0.5
                 Persistence of AQI > 100 over observed days,
                 dampened by sqrt of data coverage.

    VSF_robust = 1 + tanh(S / 45)
                 S = median |AQI_t - AQI_{t-1}| over consecutive
                 calendar days only. Robust to sensor spikes.

    CF_data and confidence label are computed and stored separately
    but do NOT affect the AERSI score — they are metadata only.

Score bands:
    < 0.6      Very Low
    0.6–1.0    Low
    1.0–1.5    Moderate
    1.5–2.0    High
    > 2.0      Extreme

Confidence labels (from CF_data, metadata only):
    >= 0.85    High
    >= 0.65    Medium
    >= 0.40    Low
    <  0.40    Provisional
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
    "PM2.5": 0.40,   # GBD 2019 India: ambient PM2.5 = 31.1M DALYs (dominant share)
    "PM10":  0.20,   # Coarse PM respiratory morbidity literature
    "NO2":   0.15,   # Global IER comparative risk — unchanged
    "OZONE": 0.15,   # GBD 2019 India: ambient ozone = 3.06M DALYs — unchanged
    "SO2":   0.10,   # Global comparative risk — unchanged
}

CORE_POLLUTANTS = set(WEIGHTS.keys())

BANDS = [
    ("Very Low",  0,    0.6),
    ("Low",       0.6,  1.0),
    ("Moderate",  1.0,  1.5),
    ("High",      1.5,  2.0),
    ("Extreme",   2.0,  9999),
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def compute_pl_robust(mean_conc: pd.Series) -> tuple:
    """PL from per-pollutant MEAN concentrations across the rolling window.

    mean_conc: Series indexed by pollutant_id, values = 30-day mean µg/m³.
    Weight renormalization runs over whichever core pollutants are present
    anywhere in the window.
    """
    present = {p: c for p, c in mean_conc.items()
               if p in CORE_POLLUTANTS and not pd.isna(c) and c >= 0}
    if not present:
        return np.nan, 0
    weight_sum = sum(WEIGHTS[p] for p in present)
    pl = sum((WEIGHTS[p] / weight_sum) * ((c / WHO_LIMITS[p]) ** 0.6)
             for p, c in present.items())
    return pl, len(present)


def compute_epf_adj(aqi_series: pd.Series, d_obs: int) -> float:
    if d_obs == 0 or len(aqi_series) == 0:
        return 1.0
    d_exceed    = (aqi_series > AQI_THRESHOLD).sum()
    data_weight = (min(d_obs, TARGET_WINDOW) / TARGET_WINDOW) ** 0.5
    # Persistence fraction uses actual observed days, not the 30-day target:
    # dividing by 30 when only e.g. 15 days exist understates persistence and
    # double-penalizes sparse stations (data_weight already handles sparsity).
    return float(1.0 + (d_exceed / max(d_obs, 1)) * data_weight)


def compute_vsf_robust(aqi_series: pd.Series) -> float:
    """S = median |AQI_t - AQI_{t-1}| over CONSECUTIVE calendar days only.

    aqi_series is indexed by ISO date strings. Observation pairs more than
    one day apart (window gaps, outages) are excluded — a diff spanning a
    week is not a day-to-day change and would inflate volatility.
    """
    if len(aqi_series) < 2:
        return 1.0
    dates   = pd.to_datetime(pd.Index(aqi_series.index), format="%Y-%m-%d", errors="coerce")
    day_gap = pd.Series(dates).diff().dt.days
    diffs   = aqi_series.reset_index(drop=True).diff().abs()
    consecutive = diffs[day_gap == 1].dropna()
    if len(consecutive) == 0:
        return 1.0
    return 1.0 + float(np.tanh(consecutive.median() / 45.0))


def compute_cf(n_pollutants: int, d_obs: int) -> tuple:
    """CF is metadata only — does not affect AERSI score."""
    cf_pollutant = min(n_pollutants / 5, 1.0)
    cf_day       = min(d_obs / TARGET_WINDOW, 1.0)
    cf_data      = 0.5 * cf_pollutant + 0.3 * cf_day + 0.2 * 1.0
    return cf_data


def confidence_label(cf_data: float) -> str:
    if cf_data >= 0.85: return "High"
    elif cf_data >= 0.65: return "Medium"
    elif cf_data >= 0.40: return "Low"
    else: return "Provisional"


# ── Load ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT_FILE)

required = {"station", "date", "pollutant_id", "avg_value",
            "AQI", "latitude", "longitude", "city", "state"}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}")

df["pollutant_id"] = df["pollutant_id"].str.upper().str.strip()
df["avg_value"]    = pd.to_numeric(df["avg_value"], errors="coerce")
df["AQI"]          = pd.to_numeric(df["AQI"], errors="coerce")

print(f"Loaded {len(df)} rows across {df['station'].nunique()} stations")

# ── Step 1: 30-day mean concentration per station-pollutant ─────────────────
# PL is computed from the MEAN concentration of each pollutant across all
# available days in the rolling window, so AERSI is a true 30-day composite
# (previously PL used only the single most recent day). Readings are averaged
# within each date first, so duplicate rows from repeated snapshots do not
# double-count a day.

print("Computing 30-day mean concentrations per station")

core_rows = df[
    df["pollutant_id"].isin(CORE_POLLUTANTS)
    & df["avg_value"].notna()
    & (df["avg_value"] >= 0)
]
daily_means  = core_rows.groupby(["station", "pollutant_id", "date"])["avg_value"].mean()
window_means = daily_means.groupby(["station", "pollutant_id"]).mean()
conc_by_station = {st: s.droplevel(0) for st, s in window_means.groupby(level=0)}

# One AQI value per station-day, indexed by date (chronological ISO strings)
aqi_by_day     = df.groupby(["station", "date"])["AQI"].first()
aqi_by_station = {st: s.droplevel(0) for st, s in aqi_by_day.groupby(level=0)}

station_meta = (
    df.sort_values("date")
    .groupby("station")
    .tail(1)
    .set_index("station")[["city", "state", "latitude", "longitude"]]
)
last_date = df.groupby("station")["date"].max()

# ── Step 2: PL, EPF, VSF, CF, AERSI per station ──────────────────────────────

print("Computing PL, EPF, VSF, CF per station")
results = []

for station in sorted(df["station"].unique()):
    conc       = conc_by_station.get(station, pd.Series(dtype=float))
    pl, n_poll = compute_pl_robust(conc)

    aqi_series = aqi_by_station.get(station, pd.Series(dtype=float)).dropna()
    d_obs      = len(aqi_series)

    epf     = compute_epf_adj(aqi_series, d_obs)
    vsf     = compute_vsf_robust(aqi_series)
    cf_data = compute_cf(n_poll, d_obs)

    if not pd.isna(pl) and pl > 0:
        # CF does NOT multiply — confidence is metadata only
        aersi = (pl ** 0.50) * (epf ** 0.25) * (vsf ** 0.25)
    else:
        aersi = np.nan

    m = station_meta.loc[station]
    results.append({
        "station":    station,
        "date":       last_date[station],
        "PL":         round(pl,      4) if not pd.isna(pl)    else np.nan,
        "EPF":        round(epf,     4),
        "VSF":        round(vsf,     4),
        "CF_data":    round(cf_data, 4),
        "AERSI":      round(aersi,   4) if not pd.isna(aersi) else np.nan,
        "confidence": confidence_label(cf_data),
        "city":       m["city"],
        "state":      m["state"],
        "latitude":   m["latitude"],
        "longitude":  m["longitude"],
    })

final_df = pd.DataFrame(results)

# ── Save ─────────────────────────────────────────────────────────────────────

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
final_df.to_csv(OUTPUT_FILE, index=False)

# ── Summary ───────────────────────────────────────────────────────────────────

valid = final_df.dropna(subset=["AERSI"])
print(f"\nAERSI computation complete")
print(f"Stations scored: {len(valid)} / {len(final_df)}")
print(f"Window days:     {df['date'].nunique()} / {TARGET_WINDOW}")
print()
print("Score distribution:")
for label, lo, hi in BANDS:
    count = ((valid["AERSI"] >= lo) & (valid["AERSI"] < hi)).sum()
    pct   = 100 * count / len(valid) if len(valid) else 0
    upper = str(hi) if hi < 9999 else "inf"
    print(f"  {label:10s} ({lo}–{upper:>5}) : {count:4d} ({pct:.1f}%)")

print()
print("Confidence (metadata):")
for label in ["High", "Medium", "Low", "Provisional"]:
    print(f"  {label:12s}: {(final_df['confidence'] == label).sum()}")
