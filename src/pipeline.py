"""
AERSI Daily Pipeline Orchestrator
Runs all steps in order, logs results, exits cleanly on failure.
"""

import subprocess
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Logging setup ────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
log_file = LOG_DIR / f"pipeline_{today}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pipeline")

# ── Steps ────────────────────────────────────────────────────────────────────

STEPS = [
    ("Fetch daily CPCB snapshot",    "src/fetch/fetch_snapshot.py"),
    ("Build rolling 30-day dataset", "src/process/build_rolling.py"),
    ("Compute daily AQI",            "src/process/compute_aqi.py"),
    ("Compute AERSI scores",         "src/process/compute_aersi.py"),
    ("Build interactive map",        "src/map/build_map.py"),
]

# ── Run ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info(f"AERSI pipeline started  —  {today}")
    log.info("=" * 60)

    python = sys.executable

    for label, script in STEPS:
        log.info(f"STEP: {label}")

        result = subprocess.run(
            [python, script],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                log.info(f"  {line}")

        if result.returncode != 0:
            log.error(f"FAILED: {script}")
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines():
                    log.error(f"  {line}")
            log.error("Pipeline halted.")
            sys.exit(1)

        log.info(f"  OK\n")

    log.info("=" * 60)
    log.info("Pipeline completed successfully")
    log.info(f"Log saved to: {log_file}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()