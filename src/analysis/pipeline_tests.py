"""
AERSI pipeline regression tests.

Run after the pipeline:  python src/analysis/pipeline_tests.py
Exits nonzero if any test fails, so it can gate the CI workflow.

Tests:
  1. Date parsing        — no silent NaT corruption, fresh window
  2. Formula             — AERSI = PL^0.50 x EPF^0.25 x VSF^0.25 exactly
  3. Geographic sanity   — NCR belt scores above clean southern states
  4. EPF bounds          — 1.0 <= EPF <= 2.0
  5. VSF bounds          — 1.0 <= VSF <= 2.0
  6. CF independence     — CF_data is stored but never enters the score
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROLLING_FILE = Path("data/rolling/last_30_days_with_aqi.csv")
SCORES_FILE  = Path("data/processed/aersi_station_scores.csv")

RESULTS = []


def report(name: str, passed: bool, detail: str):
    status = "PASS" if passed else "FAIL"
    RESULTS.append(passed)
    print(f"[{status}] {name}")
    print(f"       {detail}")


# ── Test 1: Date parsing ─────────────────────────────────────────────────────

def test_date_parsing():
    name = "Test 1: Date parsing"
    if not ROLLING_FILE.exists():
        report(name, False, f"{ROLLING_FILE} not found — run the pipeline first")
        return
    df = pd.read_csv(ROLLING_FILE, low_memory=False, usecols=["date"])
    total = len(df)
    # "NaT" strings are the footprint of the historical dayfirst bug;
    # empty/NaN cells count as unparsed too
    n_nat = int((df["date"].astype(str) == "NaT").sum() + df["date"].isna().sum())
    parsed = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    n_bad  = int(parsed.isna().sum())
    n_distinct = parsed.dropna().nunique()
    today = datetime.now(timezone.utc).date()
    oldest_allowed = today - timedelta(days=90)
    n_stale = int((parsed.dropna().dt.date < oldest_allowed).sum())

    ok = (
        total > 0
        and max(n_nat, n_bad) / total < 0.05
        and n_distinct >= 20
        and n_stale == 0
    )
    report(name, ok,
           f"NaT/unparseable: {max(n_nat, n_bad)}/{total} rows "
           f"({100 * max(n_nat, n_bad) / max(total, 1):.2f}%, limit 5%) | "
           f"distinct dates: {n_distinct} (need >= 20) | "
           f"rows older than 90 days: {n_stale} (need 0)")


# ── Test 2: Formula reconstruction ───────────────────────────────────────────

def test_formula():
    name = "Test 2: Formula reconstruction"
    df = pd.read_csv(SCORES_FILE).dropna(subset=["AERSI", "PL", "EPF", "VSF"])
    recon = (df["PL"] ** 0.50) * (df["EPF"] ** 0.25) * (df["VSF"] ** 0.25)
    err = (recon - df["AERSI"]).abs().max()
    report(name, err < 0.001,
           f"max |PL^0.50 * EPF^0.25 * VSF^0.25 - AERSI| = {err:.6f} "
           f"over {len(df)} stations (limit 0.001)")


# ── Test 3: Geographic sanity ────────────────────────────────────────────────

def test_geography():
    name = "Test 3: Geographic sanity"
    df = pd.read_csv(SCORES_FILE).dropna(subset=["AERSI"])
    # normalize state spelling variants like "Uttar_Pradesh"
    state = df["state"].astype(str).str.replace("_", " ", regex=False).str.strip()
    dirty = df.loc[state.isin(["Delhi", "Haryana", "Punjab"]), "AERSI"]
    clean = df.loc[state.isin(["Karnataka", "Kerala", "Maharashtra"]), "AERSI"]
    if len(dirty) == 0 or len(clean) == 0:
        report(name, False,
               f"missing stations: NCR-belt n={len(dirty)}, southern n={len(clean)}")
        return
    report(name, dirty.mean() > clean.mean(),
           f"mean AERSI Delhi+Haryana+Punjab = {dirty.mean():.3f} (n={len(dirty)}) "
           f"vs Karnataka+Kerala+Maharashtra = {clean.mean():.3f} (n={len(clean)})")


# ── Tests 4 & 5: Component bounds ────────────────────────────────────────────

def test_bounds(col: str, test_no: int):
    name = f"Test {test_no}: {col} bounds"
    df = pd.read_csv(SCORES_FILE).dropna(subset=[col])
    lo, hi = df[col].min(), df[col].max()
    n_out = int(((df[col] < 1.0) | (df[col] > 2.0)).sum())
    report(name, n_out == 0,
           f"range [{lo:.4f}, {hi:.4f}] over {len(df)} stations | "
           f"out of [1.0, 2.0]: {n_out} (need 0)")


# ── Test 6: CF independence ──────────────────────────────────────────────────

def test_cf_independence():
    name = "Test 6: CF independence"
    df = pd.read_csv(SCORES_FILE)
    if "CF_data" not in df.columns:
        report(name, False, "CF_data column missing from output CSV")
        return
    v = df.dropna(subset=["AERSI", "PL", "EPF", "VSF", "CF_data"])
    without_cf = (v["PL"] ** 0.50) * (v["EPF"] ** 0.25) * (v["VSF"] ** 0.25)
    err_without = (without_cf - v["AERSI"]).abs().max()
    # if CF secretly multiplied into the score, this would match instead:
    with_cf = without_cf * v["CF_data"]
    err_with = (with_cf - v["AERSI"]).abs().max()
    cf_varies = v["CF_data"].nunique() > 1
    ok = err_without < 0.001 and err_with > 0.01 and cf_varies
    report(name, ok,
           f"CF_data stored (distinct values: {v['CF_data'].nunique()}) | "
           f"AERSI matches formula WITHOUT CF (max err {err_without:.6f} < 0.001) | "
           f"formula WITH CF does NOT match (max err {err_with:.4f} > 0.01) "
           f"=> changing CF_data cannot change AERSI")


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 64)
    print("AERSI pipeline regression tests")
    print("=" * 64)
    test_date_parsing()
    test_formula()
    test_geography()
    test_bounds("EPF", 4)
    test_bounds("VSF", 5)
    test_cf_independence()
    print("=" * 64)
    n_pass = sum(RESULTS)
    print(f"{n_pass}/{len(RESULTS)} tests passed")
    sys.exit(0 if all(RESULTS) else 1)
