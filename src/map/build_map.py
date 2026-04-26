"""
Step 5 — Build AERSI interactive station map
Light / dark mode, adaptive legend, station popups.
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

required = {"station", "city", "state", "latitude", "longitude",
            "PL", "AERSI", "EPF", "VSF"}
missing  = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns in AERSI scores: {missing}")

df = df.dropna(subset=["latitude", "longitude", "AERSI"])
print(f"Plotting {len(df)} stations")

# ── Color mapping ────────────────────────────────────────────────────────────

def aersi_color(value: float) -> str:
    if value < 0.8:   return "#16a34a"   # very low  — green
    elif value < 1.2: return "#84cc16"   # low       — lime
    elif value < 2.0: return "#eab308"   # moderate  — yellow
    elif value < 3.0: return "#f97316"   # high      — orange
    else:             return "#dc2626"   # extreme   — red

def aersi_label(value: float) -> str:
    if value < 0.8:   return "Very Low"
    elif value < 1.2: return "Low"
    elif value < 2.0: return "Moderate"
    elif value < 3.0: return "High"
    else:             return "Extreme"

# ── Map ──────────────────────────────────────────────────────────────────────

m = folium.Map(location=[22.8, 79.2], zoom_start=4.8, tiles=None)

folium.TileLayer("cartodbpositron",   name="Light Mode", control=True).add_to(m)
folium.TileLayer("cartodbdarkmatter", name="Dark Mode",  control=True).add_to(m)

# ── Station markers ──────────────────────────────────────────────────────────

for _, row in df.iterrows():
    aersi = row["AERSI"]
    radius = min(11, 4 + math.sqrt(aersi) * 2.2)
    color  = aersi_color(aersi)

    def fmt(v):
        return "—" if pd.isna(v) else f"{v:.2f}"

    popup_html = f"""
    <div style="font-family:Arial,sans-serif; font-size:13px; min-width:220px;">
        <b style="font-size:15px;">{row['station']}</b><br>
        <span style="color:#6b7280;">{row['city']}, {row['state']}</span>
        <hr style="margin:8px 0; border-color:#e5e7eb;">

        <div style="margin-bottom:6px;">
            <span style="font-size:18px; font-weight:bold; color:{color};">
                {aersi:.2f}
            </span>
            <span style="color:#6b7280; font-size:12px;">
              AERSI — {aersi_label(aersi)}
            </span>
        </div>

        <table style="width:100%; font-size:12px; border-collapse:collapse;">
            <tr>
                <td style="color:#6b7280; padding:2px 0;">Pollution Load (PL)</td>
                <td style="text-align:right; font-weight:bold;">{fmt(row['PL'])}</td>
            </tr>
            <tr>
                <td style="color:#6b7280; padding:2px 0;">Persistence (EPF)</td>
                <td style="text-align:right; font-weight:bold;">{fmt(row['EPF'])}</td>
            </tr>
            <tr>
                <td style="color:#6b7280; padding:2px 0;">Volatility (VSF)</td>
                <td style="text-align:right; font-weight:bold;">{fmt(row['VSF'])}</td>
            </tr>
        </table>

        <p style="font-size:11px; color:#9ca3af; margin-top:8px; margin-bottom:0;">
            AERSI = PL × EPF × VSF<br>
            Temporal factors stabilize as data accumulates.
        </p>
    </div>
    """

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        weight=0.5,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{row['station']} — AERSI {aersi:.2f}",
    ).add_to(m)

# ── Legend + status + dark mode adapter ──────────────────────────────────────

legend_html = """
<style>
#aersi-legend, #aersi-status {
    position: fixed;
    z-index: 9999;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.22);
    font-family: Arial, sans-serif;
    transition: background 0.3s, color 0.3s;
}
#aersi-legend {
    bottom: 30px; left: 30px;
    padding: 14px 16px;
    font-size: 13px;
    line-height: 1.8;
}
#aersi-status {
    bottom: 30px; right: 30px;
    padding: 10px 14px;
    font-size: 12px;
    line-height: 1.6;
}
.leaflet-control-layers, .leaflet-bar {
    border-radius: 6px !important;
    box-shadow: 0 0 10px rgba(0,0,0,0.2) !important;
    transition: background 0.3s;
}
</style>

<div id="aersi-legend">
    <b style="font-size:14px;">AERSI — Air Exposure Severity Index</b>
    <br><br>
    <span style="color:#16a34a;">●</span> &lt; 0.8 &nbsp; Very Low Exposure<br>
    <span style="color:#84cc16;">●</span> 0.8–1.2 &nbsp; Low Exposure<br>
    <span style="color:#eab308;">●</span> 1.2–2.0 &nbsp; Moderate Exposure<br>
    <span style="color:#f97316;">●</span> 2.0–3.0 &nbsp; High Exposure<br>
    <span style="color:#dc2626;">●</span> &gt; 3.0 &nbsp; Extreme Exposure<br>
    <br>
    <i style="font-size:11px; opacity:0.7;">AERSI = PL × EPF × VSF</i>
</div>

<div id="aersi-status">
    <b>Data status</b><br>
    Rolling window: <b>30-day</b><br>
    Updated daily at 10:30 AM IST
</div>

<script>
function adaptTheme() {
    const isDark = !!document.querySelector(
        '.leaflet-tile-loaded[src*="dark"]'
    );

    const bg    = isDark ? "#1f2937" : "#ffffff";
    const color = isDark ? "#e5e7eb" : "#111827";
    const border = isDark ? "1px solid #374151" : "1px solid #d1d5db";

    ["aersi-legend", "aersi-status"].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.style.background = bg; el.style.color = color; }
    });

    document.querySelectorAll(
        ".leaflet-control-layers, .leaflet-bar a"
    ).forEach(el => {
        el.style.background = bg;
        el.style.color      = color;
        el.style.border     = border;
    });
}

setTimeout(adaptTheme, 800);
document.addEventListener("click", () => setTimeout(adaptTheme, 300));
</script>
"""

m.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(position="topright", collapsed=False).add_to(m)

# ── Save ─────────────────────────────────────────────────────────────────────

m.save(OUTPUT_FILE)

print(f"Map saved: {OUTPUT_FILE}")
print(f"Stations plotted: {len(df)}")
