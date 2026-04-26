# AERSI — Air Exposure Severity Index

Station-level rolling air exposure severity index for India.
Moves beyond snapshot AQI to capture **intensity, persistence, and volatility**
of pollution exposure over a 30-day rolling window.

---

## Formula

```
AERSI = PL × EPF × VSF
```

| Component | Meaning | Range |
|-----------|---------|-------|
| **PL** — Pollution Load | WHO-normalized weighted pollutant concentration | 0 → ∞ |
| **EPF** — Exposure Persistence Factor | How often AQI > 100, confidence-weighted | 1.0 → 2.0 |
| **VSF** — Variability Severity Factor | Daily AQI swing via tanh-bounded std dev | 1.0 → 2.0 |

**Baseline:** AERSI = 1.0 means exactly at WHO thresholds, no exceedances, zero volatility.

---

## Project Structure

```
aersi/
├── .github/workflows/daily_pipeline.yml   ← automated daily run
├── src/
│   ├── pipeline.py                        ← orchestrator
│   ├── fetch/fetch_snapshot.py            ← CPCB API fetch
│   ├── process/
│   │   ├── build_rolling.py               ← merge 30-day window
│   │   ├── compute_aqi.py                 ← CPCB AQI calculation
│   │   └── compute_aersi.py               ← new formula
│   └── map/build_map.py                   ← interactive map
├── data/snapshots/                        ← daily CSVs (committed)
├── outputs/                               ← map HTML
├── logs/                                  ← daily run logs
├── requirements.txt
└── .env                                   ← API key (never commit)
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/aersi.git
cd aersi
pip install -r requirements.txt
```

### 2. Add your API key

Create a `.env` file in the project root:

```
DATA_GOV_API_KEY=your_key_here
```

Get your key at: https://data.gov.in → Register → API Key

### 3. Run manually

```bash
python src/pipeline.py
```

---

## GitHub Actions — Automated Daily Run

The pipeline runs automatically every day at **10:30 AM IST** via GitHub Actions.

### Setup (one time only)

1. Push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `DATA_GOV_API_KEY` — Value: your API key
5. Done. The Action runs daily and commits new snapshots back to the repo.

### Manual trigger

Go to **Actions → AERSI Daily Pipeline → Run workflow**

---

## Score Reference

| AERSI | Category | Meaning |
|-------|----------|---------|
| < 0.8 | Very Low | Cleaner than WHO guidelines |
| 0.8 – 1.2 | Low | Near safety threshold |
| 1.2 – 2.0 | Moderate | Concerning cumulative exposure |
| 2.0 – 3.0 | High | Significant exposure risk |
| > 3.0 | Extreme | Persistent, intense, volatile pollution |
