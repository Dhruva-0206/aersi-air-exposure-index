# AERSI — Air Exposure Severity Index
## Claude Code Reference File (CLAUDE.md)

---

## Project Identity

**Name:** AERSI — Air Exposure Severity Index
**Live system:** https://www.aersi.live
**GitHub:** https://github.com/Dhruva-0206/aersi-air-exposure-index
**Local root:** C:\Users\DHRUVA\Desktop\aersi-station-timeseries
**Purpose:** Daily-updating, station-level air quality severity index for India. Complements standard AQI by adding WHO-normalized pollution load, 30-day exposure persistence, and day-to-day volatility into a single composite score across 530+ CPCB monitoring stations.

---

## Repository Structure

```
aersi-station-timeseries/
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml        ← GitHub Actions CI/CD (runs daily 2:00 AM IST)
├── src/
│   ├── fetch/
│   │   └── fetch_snapshot.py         ← Step 1: CPCB API ingestion
│   ├── process/
│   │   ├── build_rolling.py          ← Step 2: 30-day rolling window construction
│   │   ├── compute_aqi.py            ← Step 3: CPCB sub-index AQI computation
│   │   └── compute_aersi.py          ← Step 4: AERSI score computation (CORE)
│   ├── map/
│   │   └── build_map.py              ← Step 5: Folium interactive map generation
│   ├── analysis/
│   │   ├── sensitivity_analysis.py  ← Spearman rank robustness tests
│   │   └── pipeline_tests.py        ← regression test suite (run after pipeline; exits nonzero on failure)
│   └── pipeline.py                  ← Orchestrator: runs all steps in sequence
├── data/
│   ├── snapshots/                   ← Raw daily CPCB CSVs (dated, immutable)
│   ├── rolling/
│   │   ├── last_30_days.csv         ← Merged rolling dataset
│   │   └── last_30_days_with_aqi.csv ← Rolling dataset + computed AQI
│   └── processed/
│       └── aersi_station_scores.csv ← Final scored output (one row per station)
├── outputs/
│   └── aersi_map.html               ← Generated interactive map
├── logs/                            ← Daily pipeline execution logs
├── index.html                       ← Homepage
├── map.html                         ← Full map page
├── explore.html                     ← Station explorer
├── why.html                         ← Why AERSI? page
├── methodology.html                 ← Full formula reference
├── about.html                       ← About page
├── 404.html                         ← Custom error page
├── css/style.css                    ← Global styles
├── js/
│   ├── main.js                      ← aersiCategory(), loadStationData(), fmt()
│   └── layout.js                    ← renderNav(), renderFooter()
├── logo.png                         ← AERSI logo (spiral on blue)
├── vercel.json                      ← Vercel deployment config
└── requirements.txt                 ← Python dependencies
```

---

## The AERSI Formula (DO NOT CHANGE)

```
AERSI = PL^0.50 × EPF^0.25 × VSF^0.25
```

### Component Definitions

**PL — Pollution Load** (input is the 30-day window mean, NOT a single day)
```python
C_bar_p = mean(C_p over all available days in window)  # 30-day window mean concentration per pollutant, before WHO normalization
N_p = C_bar_p / L_p                      # WHO normalization
f(N_p) = N_p ^ 0.6                       # Sub-linear saturation
w_adj_p = w_p / sum(w_q for present q)   # Weight renormalization over pollutants present in the window
PL = sum(w_adj_p × N_p^0.6)             # Weighted pollution load
# Readings are averaged within each date first, so duplicate snapshot rows
# cannot double-count a day. (Fixed 2026-07-06: PL previously used only the
# single most recent day, which made AERSI ~91% a one-day snapshot.)
```

**EPF — Exposure Persistence Factor**
```python
data_weight = (D_obs / 30) ^ 0.5
EPF = 1 + (D_exceed / max(D_obs, 1)) × data_weight
# D_exceed = days where AQI > 100 in rolling window
# D_obs = days with usable data
# Denominator is OBSERVED days, not 30 (fixed 2026-07-06): dividing by 30
# double-penalized sparse stations — data_weight already handles sparsity.
```

**VSF — Variability Severity Factor**
```python
S = median(|AQI_t - AQI_{t-1}|)   # only consecutive calendar-day pairs (exactly 1 day apart) are included in the diff
VSF = 1 + tanh(S / 45)
# Pairs spanning window gaps are excluded (fixed 2026-07-06 — a diff across a
# week-long gap is not a day-to-day change). If no consecutive pairs exist,
# VSF = 1.0 (baseline).
```

**CF — Data Confidence (METADATA ONLY — does NOT multiply into score)**
```python
CF_data = 0.5 × (k/5) + 0.3 × (D_obs/30) + 0.2 × 1.0
```

### WHO 2021 Limits and GBD-Derived Weights

| Pollutant | WHO Limit (µg/m³) | Weight | Source |
|-----------|-------------------|--------|--------|
| PM2.5     | 15                | 0.40   | GBD 2019 India DALYs — 31.1M |
| PM10      | 45                | 0.20   | Coarse PM respiratory literature |
| NO2       | 25                | 0.15   | Global IER comparative risk |
| OZONE     | 60                | 0.15   | GBD 2019 India DALYs — 3.06M |
| SO2       | 40                | 0.10   | Global comparative risk |

### Score Bands

| AERSI     | Category  |
|-----------|-----------|
| < 0.6     | Very Low  |
| 0.6–1.0   | Low       |
| 1.0–1.5   | Moderate  |
| 1.5–2.0   | High      |
| > 2.0     | Extreme   |

### Baseline Property
```
1.0^0.50 × 1.0^0.25 × 1.0^0.25 = 1.0
```
A station at exactly WHO limits, zero exceedances, zero volatility scores AERSI = 1.0.

---

## Data Pipeline — Step by Step

### Step 1: fetch_snapshot.py
- Authenticates with data.gov.in API using `DATA_GOV_API_KEY` env variable
- Resource ID: `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`
- Fetches all CPCB station readings (~3,300 records) with pagination (1,000 per page)
- Saves as `data/snapshots/cpcb_snapshot_YYYY-MM-DD.csv`
- Skips gracefully if today's snapshot already exists
- Retry logic: 5 attempts, 60s sleep between 502/503/504 errors
- Browser-like User-Agent headers to avoid IP blocking
- Fallback: if fetch fails but snapshot within 3 days exists, pipeline continues

### Step 2: build_rolling.py
- Scans snapshot archive, selects 30 most recent available snapshots
- Merges into single rolling dataset
- Flags missing days explicitly (does not fail on gaps)
- Normalizes column names (lowercase, stripped)

### Step 3: compute_aqi.py
- Parses `last_update` with format pinned to `%d-%m-%Y %H:%M:%S` — never inferred.
  (Fixed 2026-07-06: pandas format inference took whichever snapshot was newest;
  when its first row had day ≤ 12 the whole run silently swapped day/month and
  coerced day > 12 dates to NaT, corrupting EPF, VSF, and row selection.)
- Raises RuntimeError if more than 5% of dates parse to NaT; NaT count is
  printed on every run so it is visible in pipeline logs
- Applies CPCB official sub-index breakpoint methodology; brackets are matched
  as half-open intervals `(previous_hi, hi]` so non-integer readings cannot
  fall into the gaps between published integer breakpoints
- AQI = max sub-index per station-day, assigned only if at least one PM species
  (PM2.5 or PM10) AND at least one other pollutant are present — a documented
  relaxation of CPCB's official ≥3-pollutant rule; otherwise NaN
- Adds AQI column to rolling dataset

### Step 4: compute_aersi.py (CORE — most critical file)
- Computes PL per station from the 30-day window mean concentration per
  pollutant (averaged within each date first, then across dates), then WHO
  normalization, saturation, and weight renormalization
- Computes EPF per station (AQI exceedance persistence over observed days:
  D_exceed / max(D_obs, 1), with sqrt data-coverage dampening)
- Computes VSF per station (median absolute AQI change over consecutive
  calendar-day pairs only, tanh transform)
- Computes CF per station (metadata confidence label — never enters the score)
- Assembles final AERSI = PL^0.50 × EPF^0.25 × VSF^0.25 — one row per station
  by construction (no most-recent-row selection step)
- Outputs aersi_station_scores.csv with all sub-scores

### Step 5: build_map.py
- Reads scored CSV
- Generates Folium/Leaflet.js interactive HTML map
- Color-coded markers by severity band
- Per-station popups with AERSI, PL, EPF, VSF, confidence label
- Legend and status panel injected as raw HTML

### Orchestrator: pipeline.py
- Runs steps 1-5 in sequence
- Fetch step is NON-FATAL — pipeline continues with fallback data if fetch fails
- All other steps are fatal on failure
- Logs to logs/pipeline_YYYY-MM-DD.log

---

## GitHub Actions CI/CD

**File:** `.github/workflows/daily_pipeline.yml`
**Schedule:** 10:30 AM IST daily (05:00 UTC)
**Actions versions:** checkout@v5, setup-python@v6
**Timeout:** 60 minutes (required for 5 retry × 60s sleep logic)
**Secret required:** `DATA_GOV_API_KEY` in repo Settings → Secrets → Actions
**Deploy:** Vercel auto-deploys on every push to master
**Bot commit name:** aersi-bot

---

## Frontend JavaScript Logic

### aersiCategory() in main.js — MUST match formula exactly
```javascript
if (v < 0.6)  → "Very Low"   color: #16a34a
if (v < 1.0)  → "Low"        color: #65a30d
if (v < 1.5)  → "Moderate"   color: #d97706
if (v < 2.0)  → "High"       color: #ea580c
else          → "Extreme"    color: #dc2626
```

### Stat cards in index.html
```javascript
extreme = AERSI >= 2.0
high    = AERSI >= 1.5 && AERSI < 2.0
clean   = AERSI < 0.6
```

---

## Known Issues and Constraints

1. **API reliability:** data.gov.in returns HTTP 502 intermittently from GitHub Actions runner IPs. User-Agent spoofing mitigates but does not eliminate this. Fallback to 3-day-old snapshot is the safety net.

2. **Data gaps:** 105 missing days in Jan-May 2026 due to API outage period. Documented in data validation report. Not a code bug.

3. **CF_quality = 1.0:** Sensor quality component is hardcoded to 1.0 pending CPCB sensor metadata availability.

4. **EPF/VSF AQI dependency:** Both EPF and VSF use AQI not raw concentrations. This is a deliberate design choice for regulatory comparability, not a bug. Sensitivity analyses (Spearman r ≥ 0.996) confirm rankings are robust.

5. **Unicode:** The infinity symbol ∞ caused UnicodeEncodeError on Windows cp1252. Replaced with "inf" string in compute_aersi.py. Do not reintroduce Unicode symbols in print statements.

6. **Staleness:** Rolling window reflects only the last 30 available snapshots. If pipeline fails for 3+ consecutive days, scores go stale. The website serves whatever was last committed.

---

## Security Considerations

### API Key
- `DATA_GOV_API_KEY` must NEVER be committed to the repository
- Stored in `.env` locally (gitignored) and GitHub Actions Secrets
- The `.env` file is in `.gitignore` — verify this is intact before any commit

### Data Integrity
- Snapshot CSVs are raw government data — treat as untrusted input
- `pd.to_numeric(errors='coerce')` is applied to all numeric columns to prevent injection via malformed values
- No user-supplied data enters the computation pipeline

### Deployment
- Vercel serves static files only — no server-side execution
- No authentication required — all data is public government data
- No PII collected or stored anywhere in the pipeline

### GitHub Actions
- Pipeline runs as `aersi-bot` with git config user.name
- Only commits to master branch
- Workflow has no write permissions beyond the repository itself

---

## Validation Results (from sensitivity_analysis.py)

> NOTE: These numbers predate the 2026-07-06 methodology fixes (windowed PL,
> EPF denominator, VSF gap handling). Re-run sensitivity_analysis.py before
> citing them in a paper.

### Exponent Sensitivity (alpha sweep 0.4–0.8)
| Alpha | Spearman r vs baseline |
|-------|------------------------|
| 0.4   | 0.988                  |
| 0.5   | 0.998                  |
| 0.6   | 1.000 (baseline)       |
| 0.7   | 0.999                  |
| 0.8   | 0.996                  |

### EPF Threshold Sensitivity
| Threshold              | Spearman r |
|------------------------|------------|
| AQI > 100 (baseline)   | 1.000      |
| PM2.5 > 35 µg/m³       | 0.997      |
| PM2.5 > 15 µg/m³       | 0.996      |

**Station rankings are robust across all tested parameter variations.**

---

## Research Status

- **Phase 1 (Complete):** Formula design, parameter justification, sensitivity analysis, website deployment
- **Phase 2 (In Progress):** Health validation — testing AERSI vs AQI in predicting respiratory outcomes
- **Collaborators:** Prof. Prashant Kumar (University of Surrey, GCARE), Prof. Sagnik Dey (IIT Delhi) — in communication
- **Published:** IEEE survey paper (INDIACom 2026) — DOI: 10.23919/INDIACom70271.2026.11526638
- **Target papers:** Data in Brief (dataset paper), Environmental Modelling & Software (methods paper), ML forecasting paper

---

## What NOT to Change

- The formula structure: `AERSI = PL^0.50 × EPF^0.25 × VSF^0.25`
- The score band thresholds: 0.6, 1.0, 1.5, 2.0
- The WHO limits for any pollutant
- The GBD-derived weights: PM2.5=0.40, PM10=0.20, NO2=0.15, OZONE=0.15, SO2=0.10
- The CF structure — it must remain metadata only, never multiplying into the score
- The JavaScript category thresholds in main.js — must match Python bands exactly
- The aersi-bot git config
- The 30-day window-mean input to PL — do NOT revert to single-day (2026-07-06 fix)
- The EPF denominator `max(D_obs, 1)` — do NOT revert to `/30` (2026-07-06 fix)
- The consecutive-day-only rule in VSF diffs (2026-07-06 fix)
- The pinned date format `%d-%m-%Y %H:%M:%S` in compute_aqi.py — never let
  pandas infer it (2026-07-06 fix; inference is what corrupted the July run)

---

## Methodology Audit — Findings and Resolutions (audit completed 2026-07-06)

A deep audit was run against the 10 original questions. Outcomes:

1. **PL weight renormalization with missing pollutants** — VERIFIED CORRECT.
   Weights renormalize over pollutants present in the window.
2. **EPF sqrt dampening** — dampening was correct, but the persistence fraction
   divided by 30 calendar days instead of observed days, double-penalizing
   sparse stations. **FIXED**: now `D_exceed / max(D_obs, 1) × data_weight`.
3. **VSF median vs mean** — median confirmed. But diffs spanning window gaps
   were counted as day-to-day changes. **FIXED**: only consecutive calendar-day
   pairs (exactly 1 day apart) enter the median; VSF = 1.0 if none exist.
4. **CF_data weights and independence** — VERIFIED CORRECT (0.5/0.3/0.2, stored
   but never multiplied into AERSI). Enforced by regression test 6.
5. **NaN AERSI stored as 0/placeholder** — VERIFIED SAFE: NaN stays NaN.
6. **Rolling window staleness** — CONFIRMED LIMITATION: the window is the 30
   most recent *available* snapshots, which spanned Jan–May during the 2026
   outage. Regression test 1 now fails if any window date is older than 90 days.
7. **Fallback date comparison** — VERIFIED: timezone-aware (UTC) throughout.
8. **Silent numeric coercion** — FOUND CRITICAL BUG: `last_update` was parsed
   without an explicit format; pandas inferred it from the first row of the
   newest snapshot, silently swapping day/month (day ≤ 12) or coercing to NaT
   (day > 12). In the 2026-07-01 published run, 540/543 stations had date
   "NaT", collapsing all days into one pseudo-day and corrupting EPF, VSF, and
   final row selection (38% of stations were in the wrong severity band).
   **FIXED**: format pinned to `%d-%m-%Y %H:%M:%S` — never inferred — plus a
   RuntimeError gate if >5% of dates are NaT, and regression test 1.
9. **Map popup confidence label** — VERIFIED: read from CF data, not hardcoded.
10. **Partially written snapshot CSVs** — STILL OPEN (accepted risk): a crash
    mid-write leaves a truncated file that the next run treats as complete
    (fetch skips when the file exists). Mitigation if it ever bites: write to a
    temp file and rename atomically.

Additional finding beyond the original questions (**FIXED 2026-07-06**): PL used
only the single most recent day per station, so ~91% of AERSI's variance came
from one day's reading, contradicting the 30-day exposure claim. PL now uses
the 30-day window mean per pollutant. Post-fix variance shares: PL 77%,
EPF 14%, VSF 9%; Spearman(AERSI, latest-day AQI) dropped from 0.94 to ~0.72.
Also fixed: AQI breakpoint gaps (half-open interval matching) and
single-pollutant AQI (now requires one PM species + one other pollutant).

Run `python src/analysis/pipeline_tests.py` after any pipeline change — it
regression-tests all of the above and exits nonzero on failure.

---

## For Security Audit — Key Areas to Check

1. **API key exposure:** Is DATA_GOV_API_KEY referenced anywhere in committed files, logs, or HTML?
2. **CSV injection:** Are any raw API values written to CSV and then read without sanitization?
3. **Path traversal:** Does build_rolling.py safely construct file paths from snapshot filenames?
4. **Dependency vulnerabilities:** Check requirements.txt versions against known CVEs (pandas, folium, requests, numpy)
5. **Git history:** Has the API key ever been committed to git history even if now removed?
6. **Vercel config:** Does vercel.json expose any paths that should be private?
7. **Data staleness attack:** Could an attacker corrupt a snapshot CSV to manipulate AERSI scores?
8. **.env file:** Is it definitively gitignored? Check .gitignore explicitly.
9. **GitHub Actions secret masking:** Is the API key properly masked in all log outputs?
10. **HTML injection:** Does build_map.py sanitize station names and city names before injecting into popup HTML f-strings?

