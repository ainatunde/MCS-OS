"""YouTube RSS Provider for Pulzz & MCS-OS.

Zero-quota, zero-API-key real-time broadcaster feed ingestion.
Resolves YouTube handles to Channel IDs and parses public Atom/RSS XML feeds.
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Confirmed active Nigerian broadcaster channel IDs & aliases
BROADCASTER_REGISTRY: Dict[str, str] = {
    "channels_tv": "UCEXGDNclvmg6RW0vipJYsTQ",
    "@channelsweb": "UCEXGDNclvmg6RW0vipJYsTQ",
    "@channelstelevision": "UCEXGDNclvmg6RW0vipJYsTQ",
    "arise_news": "UCyEJX-kSj0kOOCS7Qlq2G7g",
    "@AriseNewsChannel": "UCyEJX-kSj0kOOCS7Qlq2G7g",
    "tvc_news": "UCgp4A6I8LCWrhUzn-5SbKvA",
    "@TVCNewsNigeria": "UCgp4A6I8LCWrhUzn-5SbKvA",
    "@ntanewsnow": "UC0tZqgM5UfJdK4gGjQhU9vg",
}


@dataclass
class YouTubeVideoEntry:
    video_id: str
    title: str
    link: str
    published: str
    updated: str
    views: int
    thumbnail: str
    description: str


@dataclass
class ChannelFeedSnapshot:
    channel_id: str
    channel_title: str
    rss_url: str
    polled_at: str
    total_entries: int
    entries: List[YouTubeVideoEntry]

    def to_dict(self) -> dict:
        return asdict(self)


class YouTubeRSSProvider:
    """Ingests real-time video and broadcast clips via YouTube RSS."""

    def __init__(self, cache_handles: bool = True):
        self._cache = dict(BROADCASTER_REGISTRY) if cache_handles else {}

    def resolve_channel_id(self, handle_or_url: str) -> Optional[str]:
        """Resolve a handle (@channelstelevision) or channel URL to UC... ID."""
        cleaned = handle_or_url.strip()
        if cleaned in self._cache:
            return self._cache[cleaned]

        if not cleaned.startswith("@") and not cleaned.startswith("http"):
            cleaned = "@" + cleaned

        url = cleaned if cleaned.startswith("http") else f"https://www.youtube.com/{cleaned}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode("utf-8", errors="ignore")
                for pattern in [
                    r'\"browseId\":\s*\"(UC[a-zA-Z0-9_-]{22})\"',
                    r'itemprop=\"identifier\"\s*content=\"(UC[a-zA-Z0-9_-]{22})\"',
                    r'\"externalId\":\s*\"(UC[a-zA-Z0-9_-]{22})\"',
                ]:
                    match = re.search(pattern, html)
                    if match:
                        channel_id = match.group(1)
                        self._cache[handle_or_url] = channel_id
                        return channel_id
        except Exception as exc:
            print(f"[YouTubeRSSProvider] Failed to resolve {handle_or_url}: {exc}")
        return None

    def poll_channel(self, channel_id_or_handle: str) -> Optional[ChannelFeedSnapshot]:
        """Poll the Atom XML feed for a given channel."""
        if channel_id_or_handle.startswith("UC") and len(channel_id_or_handle) == 24:
            channel_id = channel_id_or_handle
        else:
            channel_id = self.resolve_channel_id(channel_id_or_handle)

        if not channel_id:
            return None

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        req = urllib.request.Request(rss_url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
        except Exception as exc:
            print(f"[YouTubeRSSProvider] Failed to fetch feed for {channel_id}: {exc}")
            return None

        root = ET.fromstring(xml_data)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }

        title_elem = root.find("atom:title", ns)
        channel_title = title_elem.text if title_elem is not None else ""

        entries: List[YouTubeVideoEntry] = []
        for entry in root.findall("atom:entry", ns):
            vid_elem = entry.find("yt:videoId", ns)
            video_id = vid_elem.text if vid_elem is not None else ""

            t_elem = entry.find("atom:title", ns)
            title = t_elem.text if t_elem is not None else ""

            link_elem = entry.find("atom:link", ns)
            link = (
                link_elem.attrib.get("href")
                if link_elem is not None
                else f"https://www.youtube.com/watch?v={video_id}"
            )

            pub_elem = entry.find("atom:published", ns)
            published = pub_elem.text if pub_elem is not None else ""

            up_elem = entry.find("atom:updated", ns)
            updated = up_elem.text if up_elem is not None else ""

            views = 0
            thumbnail = ""
            desc = ""

            media_group = entry.find("media:group", ns)
            if media_group is not None:
                d_elem = media_group.find("media:description", ns)
                desc = d_elem.text if d_elem is not None else ""

                thumb_elem = media_group.find("media:thumbnail", ns)
                thumbnail = thumb_elem.attrib.get("url") if thumb_elem is not None else ""

                comm_elem = media_group.find("media:community", ns)
                if comm_elem is not None:
                    stats_elem = comm_elem.find("media:statistics", ns)
                    if stats_elem is not None:
                        views = int(stats_elem.attrib.get("views", 0))

            entries.append(
                YouTubeVideoEntry(
                    video_id=video_id,
                    title=title,
                    link=link,
                    published=published,
                    updated=updated,
                    views=views,
                    thumbnail=thumbnail,
                    description=desc,
                )
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        return ChannelFeedSnapshot(
            channel_id=channel_id,
            channel_title=channel_title,
            rss_url=rss_url,
            polled_at=now_iso,
            total_entries=len(entries),
            entries=entries,
        )


if __name__ == "__main__":
    provider = YouTubeRSSProvider()
    print("=== Pulzz YouTube RSS Ingestion Test ===")
    for key, cid in BROADCASTER_REGISTRY.items():
        snap = provider.poll_channel(cid)
        if snap:
            print(f"\n[+] {snap.channel_title} ({snap.channel_id})")
            print(f"    Polled: {snap.polled_at} | Feed Items: {snap.total_entries}")
            if snap.entries:
                latest = snap.entries[0]
                print(f"    Latest Clip: '{latest.title}'")
                print(f"    Published:   {latest.published} | Views: {latest.views}")
                print(f"    Watch URL:   {latest.link}")
