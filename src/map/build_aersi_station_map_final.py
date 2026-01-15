import pandas as pd
import folium
from pathlib import Path
import math

# I/O paths
DATA_FILE = Path("data/processed/aersi_station_scores.csv")
OUTPUT_FILE = Path("outputs/aersi_station_map_final.html")

# Load station-level data
df = pd.read_csv(DATA_FILE)

required_cols = {
    "station", "city", "state",
    "latitude", "longitude",
    "PL", "AERSI", "EPF", "VSF"
}

missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df = df.dropna(subset=["latitude", "longitude", "AERSI"])

# Color mapping 
def aersi_color(value):
    if value < 0.8:
        return "#16a34a"   # very low
    elif value < 1.2:
        return "#84cc16"   # low
    elif value < 2.0:
        return "#eab308"   # moderate
    elif value < 3.0:
        return "#f97316"   # high
    else:
        return "#dc2626"   # extreme

# Initialize map
m = folium.Map(
    location=[22.8, 79.2],
    zoom_start=4.8,
    tiles=None
)

light_layer = folium.TileLayer(
    tiles="cartodbpositron",
    name="Light Mode",
    control=True
)

dark_layer = folium.TileLayer(
    tiles="cartodbdarkmatter",
    name="Dark Mode",
    control=True
)

light_layer.add_to(m)
dark_layer.add_to(m)

# Plot stations
for _, row in df.iterrows():
    aersi_value = row["AERSI"]
    radius = min(11, 4 + math.sqrt(aersi_value) * 2.2)

    popup_html = f"""
    <div style="font-size:13px;">
        <b style="font-size:14px;">{row['station']}</b><br>
        {row['city']}, {row['state']}<br><br>

        <b style="font-size:14px;">AERSI:</b> {aersi_value:.2f}<br>
        <span style="color:#555;">Pollution Load (PL):</span> {row['PL']:.2f}<br>
        <span style="color:#555;">EPF:</span> {'—' if pd.isna(row['EPF']) else f"{row['EPF']:.2f}"}<br>
        <span style="color:#555;">VSF:</span> {'—' if pd.isna(row['VSF']) else f"{row['VSF']:.2f}"}<br><br>

        <i style="color:#777;">
            Temporal factors stabilize as more data accumulates.
        </i>
    </div>
    """

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=radius,
        color=aersi_color(aersi_value),
        fill=True,
        fill_color=aersi_color(aersi_value),
        fill_opacity=0.58,
        weight=0.45,
        popup=folium.Popup(popup_html, max_width=320)
    ).add_to(m)

# the html part
legend_html = """
<style>
.legend-box {
    position: fixed;
    bottom: 30px;
    left: 30px;
    z-index: 9999;
    padding: 14px 16px;
    border-radius: 8px;
    font-size: 13px;
    box-shadow: 0 0 14px rgba(0,0,0,0.25);
}

.status-box {
    position: fixed;
    bottom: 30px;
    right: 30px;
    z-index: 9999;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    box-shadow: 0 0 10px rgba(0,0,0,0.25);
}

.leaflet-control-layers,
.leaflet-bar {
    border-radius: 6px !important;
    box-shadow: 0 0 10px rgba(0,0,0,0.25) !important;
}

.leaflet-control-layers-toggle,
.leaflet-bar a {
    border-radius: 6px !important;
}
</style>

<div id="legend" class="legend-box">
    <b>AERSI — Air Exposure Severity Index</b><br><br>

    <span style="color:#16a34a;">●</span> &lt; 0.8 — Very Low Exposure<br>
    <span style="color:#84cc16;">●</span> 0.8–1.2 — Low Exposure<br>
    <span style="color:#eab308;">●</span> 1.2–2.0 — Moderate Exposure<br>
    <span style="color:#f97316;">●</span> 2.0–3.0 — High Exposure<br>
    <span style="color:#dc2626;">●</span> &gt; 3.0 — Extreme Exposure<br><br>

    <i>AERSI = PL × EPF × VSF</i>
</div>

<div id="status" class="status-box">
    <b>Data status</b><br>
    Rolling window: <b>Early-stage</b><br>
    Updated daily at 10:30 AM IST
</div>

<script>
function adaptUI() {
    const isDark =
        document.querySelector('.leaflet-tile-loaded[src*="dark"]') !== null;

    const legend = document.getElementById("legend");
    const status = document.getElementById("status");

    const layerCtrl = document.querySelector(".leaflet-control-layers");
    const zoomButtons = document.querySelectorAll(".leaflet-bar a");

    if (isDark) {
        legend.style.background = "#1f2937";
        legend.style.color = "#e5e7eb";
        status.style.background = "#1f2937";
        status.style.color = "#e5e7eb";

        if (layerCtrl) {
            layerCtrl.style.background = "#1f2937";
            layerCtrl.style.color = "#e5e7eb";
            layerCtrl.style.border = "1px solid #374151";
        }

        zoomButtons.forEach(btn => {
            btn.style.background = "#1f2937";
            btn.style.color = "#e5e7eb";
            btn.style.border = "1px solid #374151";
        });
    } else {
        legend.style.background = "white";
        legend.style.color = "#111827";
        status.style.background = "white";
        status.style.color = "#111827";

        if (layerCtrl) {
            layerCtrl.style.background = "white";
            layerCtrl.style.color = "#111827";
            layerCtrl.style.border = "1px solid #d1d5db";
        }

        zoomButtons.forEach(btn => {
            btn.style.background = "white";
            btn.style.color = "#111827";
            btn.style.border = "1px solid #d1d5db";
        });
    }
}

setTimeout(adaptUI, 800);
document.addEventListener("click", () => setTimeout(adaptUI, 300));
</script>
"""

m.get_root().html.add_child(folium.Element(legend_html))

# Layer controls 
folium.LayerControl(
    position="topright",
    collapsed=False
).add_to(m)

# Saving
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
m.save(OUTPUT_FILE)

print("AERSI map generated successfully")
print(f"Output file: {OUTPUT_FILE}")
print(f"Stations plotted: {len(df)}")
