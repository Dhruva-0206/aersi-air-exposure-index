# 🌏 AERSI — Air Exposure Severity Index (India)

AERSI is a **station-level, rolling air exposure severity index** designed to move beyond single-moment AQI readings and instead capture **how intense, persistent, and volatile air pollution exposure is over time**.

This project focuses on **India**, where air quality often fluctuates rapidly and long-term exposure risks are not well represented by snapshot AQI values alone.

---

## 🧭 Why This Project?

Traditional air quality metrics (like AQI) answer:

> **“How bad is the air right now?”**

But they do **not** answer:

- How frequently a location experiences unsafe air  
- Whether pollution levels are stable or highly volatile  
- How exposure accumulates over time  
- How persistent pollution episodes are  

**AERSI bridges this gap** by introducing a rolling, exposure-aware severity index that **improves automatically as historical data accumulates**.

---

## 🧠 What is AERSI?

**AERSI (Air Exposure Severity Index)** is a composite index designed to represent **air exposure severity**, not just instantaneous air quality.

It is structured around **three components**:

| Component | Meaning | Status |
|--------|--------|--------|
| **PL** | Pollution Load (current intensity) | ✅ Active |
| **EPF** | Exposure Persistence Factor | ⚠️ Partial (data-limited) |
| **VSF** | Variability Severity Factor | ⚠️ Partial (data-limited) |

---

## 🧮 AERSI Formula (Current Implementation)

### Overall Index
AERSI = PL × EPF × VSF

---

## 🔬 Pollution Load (PL)

### Pollutant Normalization
Each pollutant is normalized using WHO guideline limits:

Nₚ = Cₚ / WHOₚ

Where:
- `Cₚ` = Observed pollutant concentration
- `WHOₚ` = WHO guideline limit for that pollutant

---

### Pollution Load Calculation
PL = 0.35·N_PM2.5 + 0.25·N_PM10 + 0.15·N_NO2 + 0.15·N_O3 + 0.10·N_SO2

> These weights reflect the **relative health burden** of pollutants based on epidemiological literature, with fine particulates (PM₂.₅) carrying the highest weight.

---

## ⏱ Exposure Persistence Factor (EPF)

EPF captures **how often unsafe air occurs** over a rolling window.

EPF = 1 + (D_exceed / W)

Where:
- `D_exceed` = Number of days AQI exceeds the safe threshold
- `W` = Rolling window size (target: 30 days)

📌 *Currently stabilizing as more data accumulates.*

---

## 📈 Variability Severity Factor (VSF)

VSF captures **volatility in pollution levels**, penalizing locations with unstable air quality.

VSF = 1 + (σ / μ)

Where:
- `σ` = Rolling standard deviation of AQI
- `μ` = Rolling mean AQI

📌 *Low during early data stages, becomes meaningful as historical depth increases.*

---

## 🗺️ Visualization

- Interactive **station-level map of India**
- Clean, non-clustered markers for clarity
- Adaptive **light / dark mode**
- Scientifically backed color thresholds
- Detailed station popups with PL, EPF, VSF, and AERSI

📍 Output file:
outputs/aersi_station_map_final.html

---

## 🔁 Data Pipeline

CPCB Snapshot API
↓
Daily Snapshot Storage
↓
Rolling 30-Day Dataset
↓
AERSI Computation
↓
Interactive Map Output

- Data is fetched **once daily**
- Rolling datasets grow until 30 days, then stabilize
- Older data is **retained** for long-term analysis

---

## ⚠️ Data Status & Accuracy

- The project is currently in **early-stage data collection**
- **PL is fully reliable**
- **EPF and VSF improve progressively** as historical depth increases
- Index accuracy stabilizes after ~30 days of continuous data

> Until then, AERSI primarily reflects **WHO-normalized pollution intensity**, with temporal factors gradually activating.

---

## Project Status

This project is currently in its early data accumulation phase.

- Pollution Load (PL) is fully active and WHO-aligned
- Temporal severity factors (EPF, VSF) are partially active and stabilize as more data is collected
- Index accuracy improves significantly after 30+ days of continuous data

Future updates will include:
- Fully stabilized EPF and VSF
- Health correlation analysis
- Interactive dashboards and deeper temporal insights

---

## 🔮 Planned Enhancements

- Full EPF & VSF activation after 30-day window
- Deeper temporal analytics (seasonality, trends)
- Health impact correlation (hospital / mortality datasets)
- Public dashboard (Power BI / web-based)
- Regional and city-level aggregation
- Long-term historical analysis

---

## 📌 Disclaimer

AERSI is a **research-driven exposure severity index**, not an official regulatory metric.  
It is intended for **analysis, visualization, and public awareness**, not for medical or legal use.

---

## 🤝 Contributions & Feedback

Ideas, critiques, and discussions are welcome.  
This project is evolving as data accumulates and methodologies improve.

---

**Author:** Dhruva  
**Focus:** Environmental data science · air quality analytics · public health exposure  
