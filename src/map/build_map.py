"""
Step 5 — Build AERSI interactive station map
Bigger, more detailed popups with all pollutant data.
Light / dark mode, adaptive legend.
"""

import math
import pandas as pd
import folium
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

DATA_FILE   = Path("data/processed/aersi_station_scores.csv")
OUTPUT_FILE = Path("outputs/aersi_map.html")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Load ─────────────────────────────────────────────────────────────────────

df = pd.read_csv(DATA_FILE)

required = {"station", "city", "state", "latitude", "longitude", "PL", "AERSI", "EPF", "VSF"}
missing  = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.dropna(subset=["latitude", "longitude", "AERSI"])
print(f"Plotting {len(df)} stations")

# ── Helpers ───────────────────────────────────────────────────────────────────

def aersi_color(v):
    if v < 0.8:   return "#16a34a"
    elif v < 1.2: return "#65a30d"
    elif v < 2.0: return "#d97706"
    elif v < 3.0: return "#ea580c"
    else:         return "#dc2626"

def aersi_label(v):
    if v < 0.8:   return "Very Low"
    elif v < 1.2: return "Low"
    elif v < 2.0: return "Moderate"
    elif v < 3.0: return "High"
    else:         return "Extreme"

def fmt(v):
    try:
        f = float(v)
        return f"{f:.2f}" if not math.isnan(f) else "—"
    except:
        return "—"

# ── Map ───────────────────────────────────────────────────────────────────────

m = folium.Map(
    location=[22.5, 82.0],
    zoom_start=5,
    tiles=None,
    prefer_canvas=True,
    max_bounds=True,
    min_zoom=3,
)

folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    name="Light",
    control=True,
    max_zoom=19,
).add_to(m)

# ── Station markers ──────────────────────────────────────────────────────────

for _, row in df.iterrows():
    aersi = row["AERSI"]
    color = aersi_color(aersi)
    label = aersi_label(aersi)
    radius = min(12, 4.5 + math.sqrt(max(aersi, 0)) * 2.0)

    # Build pollutant rows if individual data exists
    pollutant_rows = ""
    for col, name in [
        ("PM2.5", "PM₂.₅"), ("PM10", "PM₁₀"), ("NO2", "NO₂"),
        ("OZONE", "Ozone"), ("SO2", "SO₂"), ("CO", "CO"), ("NH3", "NH₃")
    ]:
        if col in row and not pd.isna(row.get(col)):
            pollutant_rows += f"""
            <tr>
              <td style="color:#64748b;padding:3px 0;">{name}</td>
              <td style="text-align:right;font-weight:500;">{fmt(row[col])}</td>
              <td style="text-align:right;font-size:11px;color:#94a3b8;padding-left:6px;">µg/m³</td>
            </tr>"""

    pollutant_section = ""
    if pollutant_rows:
        pollutant_section = f"""
        <div style="margin-top:12px;">
          <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:6px;">Pollutants</div>
          <table style="width:100%;font-size:12px;border-collapse:collapse;">
            {pollutant_rows}
          </table>
        </div>"""

    popup_html = f"""
    <div style="
      font-family: 'Instrument Sans', system-ui, -apple-system, sans-serif;
      min-width: 280px;
      max-width: 320px;
      font-size: 13px;
      line-height: 1.5;
    ">
      <!-- Header -->
      <div style="
        background: {color}12;
        border-bottom: 2px solid {color};
        padding: 14px 16px;
        margin: -8px -8px 0 -8px;
        border-radius: 8px 8px 0 0;
      ">
        <div style="font-weight:700;font-size:15px;color:#0f1629;margin-bottom:2px;">{row['station']}</div>
        <div style="font-size:12px;color:#64748b;">{row.get('city','')}{', ' + row.get('state','') if row.get('city') and row.get('state') else row.get('state','')}</div>
      </div>

      <!-- AERSI Score -->
      <div style="padding:14px 16px;border-bottom:1px solid #f1f5f9;">
        <div style="display:flex;align-items:baseline;justify-content:space-between;">
          <div>
            <div style="font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#94a3b8;margin-bottom:4px;">AERSI Score</div>
            <div style="font-size:2rem;font-weight:800;color:{color};letter-spacing:-0.03em;line-height:1;">{fmt(aersi)}</div>
          </div>
          <div style="
            background:{color}15;
            color:{color};
            border:1px solid {color}30;
            border-radius:100px;
            padding:4px 12px;
            font-size:11px;
            font-weight:600;
            letter-spacing:0.04em;
          ">{label}</div>
        </div>
      </div>

      <!-- Components -->
      <div style="padding:12px 16px;border-bottom:1px solid #f1f5f9;">
        <div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:10px;">Components · PL × EPF × VSF</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
          <div style="background:#f8fafc;border-radius:8px;padding:8px;text-align:center;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#94a3b8;font-weight:500;margin-bottom:3px;">PL</div>
            <div style="font-size:15px;font-weight:700;color:#0f1629;">{fmt(row.get('PL'))}</div>
          </div>
          <div style="background:#f8fafc;border-radius:8px;padding:8px;text-align:center;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#94a3b8;font-weight:500;margin-bottom:3px;">EPF</div>
            <div style="font-size:15px;font-weight:700;color:#0f1629;">{fmt(row.get('EPF'))}</div>
          </div>
          <div style="background:#f8fafc;border-radius:8px;padding:8px;text-align:center;border:1px solid #e2e8f0;">
            <div style="font-size:10px;color:#94a3b8;font-weight:500;margin-bottom:3px;">VSF</div>
            <div style="font-size:15px;font-weight:700;color:#0f1629;">{fmt(row.get('VSF'))}</div>
          </div>
        </div>
      </div>

      <!-- Pollutants -->
      {f'<div style="padding:12px 16px;">{pollutant_section}</div>' if pollutant_section else ''}

      <!-- Footer -->
      <div style="padding:8px 16px;background:#f8fafc;border-radius:0 0 8px 8px;border-top:1px solid #f1f5f9;">
        <div style="font-size:10px;color:#94a3b8;text-align:center;">
          AERSI = PL x EPF x VSF · aersi.live
        </div>
      </div>
    </div>
    """

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.65,
        weight=1.2,
        popup=folium.Popup(popup_html, max_width=340),
        tooltip=f"<b>{row['station']}</b> — AERSI {fmt(aersi)} ({label})",
    ).add_to(m)

# ── Controls & Legend ────────────────────────────────────────────────────────

legend_html = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

#aersi-legend {
    position: fixed;
    bottom: 28px;
    left: 28px;
    z-index: 9999;
    background: white;
    border: 1px solid rgba(13,110,253,0.12);
    border-radius: 14px;
    padding: 16px 18px;
    font-family: 'Instrument Sans', system-ui, sans-serif;
    font-size: 13px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.10);
    min-width: 200px;
}

#aersi-legend-title {
    font-weight: 700;
    font-size: 13px;
    color: #0f1629;
    margin-bottom: 2px;
    letter-spacing: -0.01em;
}

#aersi-legend-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #94a3b8;
    margin-bottom: 12px;
    letter-spacing: 0.04em;
}

.aersi-legend-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 12px;
    color: #3d4f6e;
}

.aersi-legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

#aersi-status {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 9999;
    background: white;
    border: 1px solid rgba(13,110,253,0.12);
    border-radius: 10px;
    padding: 10px 14px;
    font-family: 'Instrument Sans', system-ui, sans-serif;
    font-size: 11px;
    color: #64748b;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    line-height: 1.6;
}

.live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: #16a34a;
    border-radius: 50%;
    margin-right: 4px;
    animation: pulse-live 2s infinite;
}

@keyframes pulse-live {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
</style>

<div id="aersi-legend">
  <div id="aersi-legend-title">AERSI Severity Index</div>
  <div id="aersi-legend-sub">AERSI = PL x EPF x VSF</div>
  <div class="aersi-legend-row"><div class="aersi-legend-dot" style="background:#16a34a;"></div> &lt; 0.8 &nbsp; Very Low</div>
  <div class="aersi-legend-row"><div class="aersi-legend-dot" style="background:#65a30d;"></div> 0.8–1.2 &nbsp; Low</div>
  <div class="aersi-legend-row"><div class="aersi-legend-dot" style="background:#d97706;"></div> 1.2–2.0 &nbsp; Moderate</div>
  <div class="aersi-legend-row"><div class="aersi-legend-dot" style="background:#ea580c;"></div> 2.0–3.0 &nbsp; High</div>
  <div class="aersi-legend-row"><div class="aersi-legend-dot" style="background:#dc2626;"></div> &gt; 3.0 &nbsp; Extreme</div>
</div>

<div id="aersi-status">
  <span class="live-dot"></span><strong>aersi.live</strong><br>
  Updated daily · 10:30 AM IST<br>
  Rolling 30-day window
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

# Restrict map to one world copy so stations don't ghost at repeated longitudes
bounds_fix = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  var checkMap = setInterval(function() {
    if (window.L) {
      var maps = [];
      document.querySelectorAll('.leaflet-container').forEach(function(el) {
        if (el._leaflet_map) maps.push(el._leaflet_map);
      });
      maps.forEach(function(map) {
        map.setMaxBounds([[-10, 50], [40, 100]]);
        map.options.maxBoundsViscosity = 1.0;
        clearInterval(checkMap);
      });
    }
  }, 200);
});
</script>
"""
m.get_root().html.add_child(folium.Element(bounds_fix))

# ── Save ─────────────────────────────────────────────────────────────────────

m.save(OUTPUT_FILE)
print(f"Map saved: {OUTPUT_FILE}")
print(f"Stations plotted: {len(df)}")
