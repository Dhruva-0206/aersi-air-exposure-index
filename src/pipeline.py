"""
AERSI Daily Pipeline Orchestrator
Runs all steps in order, logs results, exits cleanly on failure.
Fetch step is non-fatal: falls back to the most recent snapshot within 3 days.
"""

import subprocess
import sys
import logging
from datetime import datetime, timedelta, timezone
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

SNAPSHOT_DIR = Path("data/snapshots")

# ── Steps ────────────────────────────────────────────────────────────────────

STEPS = [
    ("Fetch daily CPCB snapshot",    "src/fetch/fetch_snapshot.py"),
    ("Build rolling 30-day dataset", "src/process/build_rolling.py"),
    ("Compute daily AQI",            "src/process/compute_aqi.py"),
    ("Compute AERSI scores",         "src/process/compute_aersi.py"),
    ("Build interactive map",        "src/map/build_map.py"),
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def find_recent_snapshot(max_days_back: int = 3) -> Path | None:
    """Return the most recent snapshot file within max_days_back days, or None."""
    today_date = datetime.now(timezone.utc).date()
    for delta in range(max_days_back + 1):
        candidate = today_date - timedelta(days=delta)
        f = SNAPSHOT_DIR / f"cpcb_snapshot_{candidate}.csv"
        if f.exists():
            return f
    return None

def run_step(label: str, script: str) -> bool:
    """Run a pipeline step. Returns True on success, False on failure."""
    log.info(f"STEP: {label}")
    result = subprocess.run(
        [sys.executable, script],
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
        return False
    log.info(f"  OK\n")
    return True

# ── Run ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info(f"AERSI pipeline started  —  {today}")
    log.info("=" * 60)

    for label, script in STEPS:
        success = run_step(label, script)

        if not success:
            # Fetch failure is non-fatal if a recent snapshot exists
            if script == "src/fetch/fetch_snapshot.py":
                fallback = find_recent_snapshot(max_days_back=3)
                if fallback:
                    log.warning(
                        f"Fetch failed — falling back to most recent snapshot: {fallback.name}"
                    )
                    log.warning(
                        "Downstream steps will use this snapshot. Score freshness may be 1-3 days old."
                    )
                    log.info(f"  OK (fallback)\n")
                else:
                    log.error("Fetch failed and no recent snapshot found within 3 days.")
                    log.error("Pipeline halted.")
                    sys.exit(1)
            else:
                log.error("Pipeline halted.")
                sys.exit(1)

    log.info("=" * 60)
    log.info("Pipeline completed successfully")
    log.info(f"Log saved to: {log_file}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()