"""Daemon runner for hourly YouTube RSS polling."""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.youtube_poller_service import YouTubePollerService


def run_loop(interval_seconds: int = 3600):
    service = YouTubePollerService()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting hourly YouTube RSS daemon (interval: {interval_seconds}s)...")
    while True:
        try:
            stats = service.sync_once()
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] Completed sync: "
                f"{stats.channels_polled} channels, {stats.stars_polled} stars polled | "
                f"{stats.clips_inserted} new clips, {stats.clips_updated} refreshed."
            )
        except Exception as exc:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Sync cycle error: {exc}")

        print(f"Sleeping for {interval_seconds} seconds until next cycle...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    run_loop(interval)
