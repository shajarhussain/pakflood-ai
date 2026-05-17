"""
Sync Pakistan flood events from GDACS (Global Disaster Alert and Coordination System).

API used: GDACS RSS feed by the United Nations — https://www.gdacs.org
  - Free, no API key required
  - Official UN disaster data updated in near real-time
  - RSS: https://www.gdacs.org/xml/rss.xml  (7-day rolling window of active events)

Usage (from backend/ directory):
    python scripts/sync_flood_events.py

Safe to re-run — upserts on event_id so no duplicates are created.
Also called automatically by the background scheduler every 7 days.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.zones.flood_events_sync import sync_flood_events  # noqa: E402

if __name__ == "__main__":
    total = sync_flood_events(verbose=True)
    print(f"\nDone. {total} total flood events processed.")
