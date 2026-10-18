"""YouTube RSS Ingestion Service for Pulzz (TV-Insights).

Polls official broadcast channels and star YouTube feeds without API keys or quota.
Upserts clips into Pulzz's `mediaclip` table and links them to `channel_id` or `star_id`.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adapters.providers.youtube_rss_provider import YouTubeRSSProvider, YouTubeVideoEntry

logger = logging.getLogger("pulzz.youtube_poller")

DEFAULT_DB_PATH = os.environ.get(
    "TVINSIGHTS_DB_PATH",
    r"C:\Users\aina_\.gemini\antigravity\scratch\tv-insights\tvinsights.db",
)

# High-profile African star channel handles to enrich star directory
STAR_CHANNEL_HANDLES: Dict[str, str] = {
    "toke-makinwa": "@TokeMoments",
    "bimbo-ademoye": "@BimboAdemoyeTV",
    "nedu-wazobia": "@TheHonestBunchPodcast",
    "funke-akindele": "@SceneoneTV",
    "ebuka-obi-uchendu": "@RubbinMindsTV",
}


@dataclass
class IngestionStats:
    channels_polled: int = 0
    stars_polled: int = 0
    clips_inserted: int = 0
    clips_updated: int = 0
    errors: int = 0


class YouTubePollerService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.provider = YouTubeRSSProvider(cache_handles=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def enrich_star_handles(self, conn: sqlite3.Connection) -> int:
        """Seed known star YouTube handles into star table if missing."""
        cur = conn.cursor()
        enriched = 0
        for slug, handle in STAR_CHANNEL_HANDLES.items():
            cur.execute(
                "SELECT id, youtube FROM star WHERE slug = ? AND (youtube IS NULL OR youtube = '');",
                (slug,),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE star SET youtube = ? WHERE id = ?;",
                    (handle, row["id"]),
                )
                enriched += 1
        conn.commit()
        return enriched

    def get_active_channels(self, conn: sqlite3.Connection) -> List[Tuple[int, str, str]]:
        """Returns list of (channel_id, slug, youtube_handle_or_id)."""
        cur = conn.cursor()
        cur.execute(
            "SELECT id, slug, youtube FROM channel WHERE active = 1 AND youtube IS NOT NULL AND youtube != '';"
        )
        return [(r["id"], r["slug"], r["youtube"]) for r in cur.fetchall()]

    def get_active_stars(self, conn: sqlite3.Connection) -> List[Tuple[int, str, str]]:
        """Returns list of (star_id, slug, youtube_handle_or_id)."""
        cur = conn.cursor()
        cur.execute(
            "SELECT id, slug, youtube FROM star WHERE active = 1 AND youtube IS NOT NULL AND youtube != '' AND youtube NOT LIKE 'UC_new%';"
        )
        return [(r["id"], r["slug"], r["youtube"]) for r in cur.fetchall()]

    def upsert_clip(
        self,
        conn: sqlite3.Connection,
        entry: YouTubeVideoEntry,
        channel_id: Optional[int] = None,
        star_id: Optional[int] = None,
    ) -> bool:
        """Insert or update video clip in mediaclip table. Returns True if inserted, False if updated."""
        cur = conn.cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        embed_url = f"https://www.youtube.com/embed/{entry.video_id}"

        cur.execute(
            "SELECT id FROM mediaclip WHERE external_id = ? LIMIT 1;",
            (entry.video_id,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE mediaclip
                SET title = ?, thumbnail_url = ?, fetched_at = ?, active = 1
                WHERE id = ?;
                """,
                (entry.title, entry.thumbnail, now_str, existing["id"]),
            )
            return False
        else:
            cur.execute(
                """
                INSERT INTO mediaclip (
                    title, kind, provider, video_url, embed_url, thumbnail_url,
                    channel_id, star_id, external_id, published_at, fetched_at, active
                ) VALUES (?, 'CLIP', 'youtube', ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    entry.title,
                    entry.link,
                    embed_url,
                    entry.thumbnail,
                    channel_id,
                    star_id,
                    entry.video_id,
                    entry.published,
                    now_str,
                ),
            )
            return True

    def sync_once(self) -> IngestionStats:
        """Runs a complete sync pass across all registered channels and stars."""
        stats = IngestionStats()
        conn = self._get_connection()

        try:
            # 1. Seed known star handles
            self.enrich_star_handles(conn)

            # 2. Ingest broadcaster channels
            channels = self.get_active_channels(conn)
            print(f"[+] Found {len(channels)} broadcast channels with YouTube configured.")

            for ch_id, slug, yt in channels:
                try:
                    snapshot = self.provider.poll_channel(yt)
                    if snapshot:
                        stats.channels_polled += 1
                        for entry in snapshot.entries:
                            is_new = self.upsert_clip(conn, entry, channel_id=ch_id)
                            if is_new:
                                stats.clips_inserted += 1
                            else:
                                stats.clips_updated += 1
                        print(f"    [OK] [{slug}] Ingested {len(snapshot.entries)} clips from {snapshot.channel_title}")
                    else:
                        print(f"    [WARN] [{slug}] Could not poll feed for '{yt}'")
                except Exception as exc:
                    stats.errors += 1
                    print(f"    [ERR] [{slug}] Error polling feed: {exc}")

            # 3. Ingest stars
            stars = self.get_active_stars(conn)
            print(f"[+] Found {len(stars)} stars with YouTube configured.")

            for s_id, slug, yt in stars:
                try:
                    snapshot = self.provider.poll_channel(yt)
                    if snapshot:
                        stats.stars_polled += 1
                        for entry in snapshot.entries:
                            is_new = self.upsert_clip(conn, entry, star_id=s_id)
                            if is_new:
                                stats.clips_inserted += 1
                            else:
                                stats.clips_updated += 1
                        print(f"    [OK] [Star: {slug}] Ingested {len(snapshot.entries)} clips from {snapshot.channel_title}")
                    else:
                        print(f"    [WARN] [Star: {slug}] Could not poll feed for '{yt}'")
                except Exception as exc:
                    stats.errors += 1
                    print(f"    [ERR] [Star: {slug}] Error polling feed: {exc}")

            conn.commit()
        finally:
            conn.close()

        return stats


if __name__ == "__main__":
    service = YouTubePollerService()
    print("=== Starting Pulzz YouTube Ingestion Sync ===")
    results = service.sync_once()
    print("\n=== Ingestion Completed ===")
    print(f"Channels Polled:  {results.channels_polled}")
    print(f"Stars Polled:     {results.stars_polled}")
    print(f"Clips Inserted:   {results.clips_inserted}")
    print(f"Clips Refreshed:  {results.clips_updated}")
    print(f"Errors/Skipped:   {results.errors}")
