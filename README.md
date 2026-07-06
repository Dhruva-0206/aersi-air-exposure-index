# AERSI — Air Exposure Severity Index

AERSI is a station-level, daily-updating air quality severity index for India. It complements standard AQI — which reports a single day's conditions — by combining WHO-normalized pollution load, 30-day exposure persistence, and day-to-day volatility into one composite severity score across CPCB monitoring stations nationwide. AERSI is live at [aersi.live](https://www.aersi.live).

## Formula

```
AERSI = PL^0.50 × EPF^0.25 × VSF^0.25
```

- **PL — Pollution Load**: WHO-normalized, soft-saturated, weight-renormalized pollutant concentration, computed from the 30-day rolling window mean per pollutant.
- **EPF — Exposure Persistence Factor**: how often AQI exceeded 100 over the observed rolling window, dampened by data coverage.
- **VSF — Variability Severity Factor**: median absolute day-to-day AQI change over consecutive calendar-day pairs, tanh-bounded.

Pollutant weights (PM2.5 0.40, PM10 0.20, NO2 0.15, Ozone 0.15, SO2 0.10) are derived from India-specific attributable DALYs in the Global Burden of Disease Study 2019 for PM2.5 and ozone, with the remaining pollutants estimated from global comparative-risk literature and renormalized. Full derivation in [methodology.html](methodology.html).

## Live System

- 543 stations scored daily across India
- Automated pipeline via GitHub Actions — updated 10:30 AM IST
- Interactive map, station explorer, and full methodology reference at [aersi.live](https://www.aersi.live)

## Data Source

CPCB via data.gov.in (Resource ID: `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`)
Rolling 30-day window · ~530 active monitoring stations

## Validation

- Formula reconstruction error < 0.001 across all stations
- Spearman(AERSI, latest-day AQI) = 0.719 — genuinely complementary, not redundant
- Exponent sensitivity: r = 0.993–0.999 across alpha 0.4–0.8
- EPF threshold sensitivity: r = 0.987–0.990 across WHO and CPCB thresholds
- Geographic validation: NCR belt (1.79) consistently above southern states (1.08)

## Repository Structure

```
aersi-station-timeseries/
├── data/
│   ├── snapshots/       raw daily CPCB CSVs (dated, immutable)
│   ├── rolling/         merged 30-day rolling dataset
│   └── processed/       final scored output (aersi_station_scores.csv)
├── src/
│   ├── fetch/           Step 1 — CPCB API ingestion
│   ├── process/         Steps 2–4 — rolling window, AQI, AERSI computation
│   ├── map/             Step 5 — interactive map generation
│   ├── analysis/        sensitivity analysis and regression test suite
│   └── pipeline.py      orchestrator — runs all steps in sequence
├── outputs/             generated interactive map (aersi_map.html)
├── css/, js/            frontend styles and shared layout/logic
├── *.html               website pages (index, map, explore, why,
│                        methodology, about, privacy)
└── .github/workflows/   daily pipeline CI/CD
```

## License

- **Code**: MIT License
- **Dataset** (`data/processed/`): CC BY 4.0
- **Raw CPCB data**: GODL-India

See [LICENSE](LICENSE) for full terms.

## Citation

If you use AERSI or this dataset in your research, please cite:

```
[placeholder — DOI will be added after Zenodo upload]
```

Also cite the IEEE survey paper:

> Marne P.M., Bhosale S.N., Chakrabarty D. "Air Quality Index in the Era of Data Science: A Survey of Methods, Technologies and Exposure Trends." INDIACom 2026. DOI: 10.23919/INDIACom70271.2026.11526638
