"""
AERSI Sensitivity Analysis
===========================
Tests robustness of:
  1. Saturation exponent (alpha): 0.4, 0.5, 0.6, 0.7, 0.8
  2. EPF threshold variants: AQI>100, PM2.5>35, PM2.5>15

Output: Spearman rank correlations vs baseline (alpha=0.6, AQI>100)
Used as a methods table in the research paper.

Run from the project root:
    python src/analysis/sensitivity_analysis.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import spearmanr

# ── Config ────────────────────────────────────────────────────────────────────

ROLLING_FILE = Path("data/rolling/last_30_days_with_aqi.csv")
SCORES_FILE  = Path("data/processed/aersi_station_scores.csv")

WHO_LIMITS = {
    "PM2.5": 15,
    "PM10":  45,
    "NO2":   25,
    "SO2":   40,
    "OZONE": 60,
}

WEIGHTS = {
    "PM2.5": 0.40,
    "PM10":  0.20,
    "NO2":   0.15,
    "OZONE": 0.15,
    "SO2":   0.10,
}

CORE_POLLUTANTS = set(WEIGHTS.keys())
TARGET_WINDOW   = 30
BASELINE_ALPHA  = 0.6
BASELINE_THRESH = 100   # AQI > 100

# ── Load data ─────────────────────────────────────────────────────────────────

print("Loading data...")
rolling = pd.read_csv(ROLLING_FILE)
scores  = pd.read_csv(SCORES_FILE)

rolling["pollutant_id"] = rolling["pollutant_id"].str.upper().str.strip()
rolling["avg_value"]    = pd.to_numeric(rolling["avg_value"], errors="coerce")
rolling["AQI"]          = pd.to_numeric(rolling["AQI"],       errors="coerce")

stations = scores["station"].unique()
print(f"Stations: {len(stations)}  |  Rolling rows: {len(rolling)}")

# ── Helper: compute PL for one station-day with given alpha ───────────────────

def compute_pl(group: pd.DataFrame, alpha: float) -> float:
    present = {}
    for _, row in group.iterrows():
        p = row["pollutant_id"]
        c = row["avg_value"]
        if p in CORE_POLLUTANTS and pd.notna(c) and c >= 0:
            present[p] = c
    if not present:
        return np.nan
    w_sum = sum(WEIGHTS[p] for p in present)
    pl = sum(
        (WEIGHTS[p] / w_sum) * ((c / WHO_LIMITS[p]) ** alpha)
        for p, c in present.items()
    )
    return pl


# ── Helper: compute EPF for one station with given AQI threshold ──────────────

def compute_epf(aqi_series: pd.Series, d_obs: int, threshold: float) -> float:
    if d_obs == 0 or len(aqi_series) == 0:
        return 1.0
    d_exceed    = (aqi_series > threshold).sum()
    data_weight = (min(d_obs, TARGET_WINDOW) / TARGET_WINDOW) ** 0.5
    return float(1.0 + (d_exceed / TARGET_WINDOW) * data_weight)


# ── Helper: compute VSF (unchanged across sensitivity tests) ──────────────────

def compute_vsf(aqi_series: pd.Series) -> float:
    if len(aqi_series) < 2:
        return 1.0
    s = aqi_series.diff().dropna().abs().median()
    return 1.0 + float(np.tanh(s / 45.0))


# ── Core: compute AERSI for all stations given alpha and EPF threshold ─────────

def compute_all_aersi(alpha: float, epf_threshold: float,
                      epf_mode: str = "aqi") -> pd.Series:
    """
    epf_mode: 'aqi'  → threshold applies to AQI column
              'pm25' → threshold applies to PM2.5 concentration column
    Returns a Series indexed by station with AERSI values.
    """
    results = {}

    # Build station-day PL lookup
    pl_rows = []
    for (station, date), grp in rolling.groupby(["station", "date"]):
        pl = compute_pl(grp, alpha)
        meta = grp.iloc[0]
        pl_rows.append({
            "station": station,
            "date":    date,
            "PL":      pl,
            "AQI":     meta["AQI"],
        })
    pl_df = pd.DataFrame(pl_rows)

    for station, grp in pl_df.groupby("station"):
        grp        = grp.sort_values("date")
        aqi_series = grp["AQI"].dropna()
        d_obs      = len(aqi_series)

        # EPF — AQI-based or concentration-based
        if epf_mode == "aqi":
            epf = compute_epf(aqi_series, d_obs, epf_threshold)
        else:
            # concentration-based: use PM2.5 from rolling dataset
            st_rolling = rolling[rolling["station"] == station]
            pm25_days  = (
                st_rolling[st_rolling["pollutant_id"] == "PM2.5"]
                .groupby("date")["avg_value"]
                .mean()
                .dropna()
            )
            epf = compute_epf(pm25_days, len(pm25_days), epf_threshold)

        vsf = compute_vsf(aqi_series)

        # Most recent PL
        pl = grp.dropna(subset=["PL"])["PL"].iloc[-1] if grp["PL"].notna().any() else np.nan

        if pd.notna(pl) and pl > 0:
            aersi = (pl ** 0.50) * (epf ** 0.25) * (vsf ** 0.25)
        else:
            aersi = np.nan

        results[station] = aersi

    return pd.Series(results, name="AERSI")


# ── Test 1: Exponent sweep ─────────────────────────────────────────────────────

print("\n" + "="*60)
print("TEST 1 — SATURATION EXPONENT SENSITIVITY")
print("EPF threshold fixed at AQI > 100  |  Baseline alpha = 0.6")
print("="*60)

alphas   = [0.4, 0.5, 0.6, 0.7, 0.8]
baseline_aersi = None
alpha_results  = {}

for alpha in alphas:
    print(f"  Computing alpha = {alpha}...", end=" ", flush=True)
    aersi = compute_all_aersi(alpha=alpha, epf_threshold=BASELINE_THRESH, epf_mode="aqi")
    alpha_results[alpha] = aersi
    if alpha == BASELINE_ALPHA:
        baseline_aersi = aersi
    print("done")

print()
print(f"{'Alpha':<10} {'Spearman r':<14} {'p-value':<12} {'N stations':<12} {'Interpretation'}")
print("-"*65)

for alpha in alphas:
    aersi   = alpha_results[alpha]
    common  = baseline_aersi.dropna().index.intersection(aersi.dropna().index)
    r, p    = spearmanr(baseline_aersi[common], aersi[common])
    label   = "BASELINE" if alpha == BASELINE_ALPHA else (
              "Very high agreement" if r >= 0.97 else
              "High agreement"     if r >= 0.90 else
              "Moderate agreement")
    marker  = " ◀" if alpha == BASELINE_ALPHA else ""
    print(f"  {alpha:<8} {r:<14.4f} {p:<12.2e} {len(common):<12} {label}{marker}")


# ── Test 2: EPF threshold variants ────────────────────────────────────────────

print("\n" + "="*60)
print("TEST 2 — EPF THRESHOLD SENSITIVITY")
print("Saturation exponent fixed at alpha = 0.6  |  Baseline = AQI > 100")
print("="*60)

thresholds = [
    ("AQI > 100 (CPCB/EPA standard)",  100,  "aqi"),
    ("PM2.5 > 35 µg/m³ (WHO IT-1)",    35,   "pm25"),
    ("PM2.5 > 15 µg/m³ (WHO guideline)", 15, "pm25"),
]

threshold_results = {}
baseline_thresh_aersi = None

for label, thresh, mode in thresholds:
    print(f"  Computing {label}...", end=" ", flush=True)
    aersi = compute_all_aersi(alpha=BASELINE_ALPHA, epf_threshold=thresh, epf_mode=mode)
    threshold_results[label] = aersi
    if thresh == BASELINE_THRESH and mode == "aqi":
        baseline_thresh_aersi = aersi
    print("done")

print()
print(f"{'Threshold':<42} {'Spearman r':<14} {'p-value':<12} {'Interpretation'}")
print("-"*80)

for label, thresh, mode in thresholds:
    aersi  = threshold_results[label]
    common = baseline_thresh_aersi.dropna().index.intersection(aersi.dropna().index)
    r, p   = spearmanr(baseline_thresh_aersi[common], aersi[common])
    interp = "BASELINE" if thresh == BASELINE_THRESH and mode == "aqi" else (
             "Very high agreement" if r >= 0.97 else
             "High agreement"     if r >= 0.90 else
             "Moderate agreement" if r >= 0.80 else
             "Moderate divergence — note in paper")
    marker = " ◀" if thresh == BASELINE_THRESH and mode == "aqi" else ""
    print(f"  {label:<40} {r:<14.4f} {p:<12.2e} {interp}{marker}")


# ── Summary for paper ─────────────────────────────────────────────────────────

print("\n" + "="*60)
print("PAPER TABLE — COPY THIS INTO METHODS/APPENDIX")
print("="*60)

print("""
Table S1. Sensitivity of AERSI station rankings to saturation exponent (alpha)
and EPF threshold. Spearman rank correlation (r) computed against baseline
configuration (alpha = 0.6, AQI > 100) across all stations with valid scores.

Panel A: Saturation exponent sensitivity (EPF threshold = AQI > 100)
""")

print(f"  {'alpha':<8} {'r':<8} {'Interpretation'}")
print(f"  {'-'*40}")
for alpha in alphas:
    aersi  = alpha_results[alpha]
    common = baseline_aersi.dropna().index.intersection(aersi.dropna().index)
    r, _   = spearmanr(baseline_aersi[common], aersi[common])
    label  = "baseline" if alpha == BASELINE_ALPHA else ""
    print(f"  {alpha:<8} {r:<8.3f} {label}")

print("""
Panel B: EPF threshold sensitivity (alpha = 0.6)
""")
print(f"  {'Threshold':<42} {'r':<8} {'Interpretation'}")
print(f"  {'-'*55}")
for label, thresh, mode in thresholds:
    aersi  = threshold_results[label]
    common = baseline_thresh_aersi.dropna().index.intersection(aersi.dropna().index)
    r, _   = spearmanr(baseline_thresh_aersi[common], aersi[common])
    bl     = "baseline" if thresh == BASELINE_THRESH and mode == "aqi" else ""
    print(f"  {label:<42} {r:<8.3f} {bl}")

print("\nDone. Use the Paper Table section above for your methods appendix.")