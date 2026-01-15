import subprocess
import sys
from datetime import datetime

print("\nAERSI daily pipeline started")
print(f"Start time: {datetime.now()}\n")

PYTHON = sys.executable

STEPS = [
    ("Fetch CPCB daily snapshot", "src/fetch/fetch_daily_snapshot.py"),
    ("Build rolling 30-day dataset", "src/process/build_rolling_30_days.py"),
    ("Compute AERSI", "src/process/compute_aersi.py"),
    ("Build AERSI map", "src/map/build_aersi_station_map_final.py"),
]

for label, script in STEPS:
    print(f"\n{label}")
    print("-" * len(label))

    result = subprocess.run([PYTHON, script])

    if result.returncode != 0:
        print(f"\nPipeline stopped due to error in: {script}")
        sys.exit(1)

print("\nAERSI daily pipeline completed successfully")
