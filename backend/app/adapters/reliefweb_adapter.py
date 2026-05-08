"""
ReliefWebAdapter — live adapter for humanitarian reports.

ReliefWeb is a public API (no authentication required).
API docs: https://reliefweb.int/help/api
"""
import re
from datetime import datetime, UTC

import httpx

from app.adapters.base_adapter import BaseAdapter, AdapterResult

_API_URL = "https://api.reliefweb.int/v1/reports"
_APP_NAME = "pakflood-ai-education"
_MAX_ARTICLES = 5


def _strip_html(html: str) -> str:
    """Remove HTML tags and truncate to 300 chars for summary."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300] + ("…" if len(text) > 300 else "")


def _parse_date(iso: str) -> str:
    """Return YYYY-MM-DD from an ISO-8601 string."""
    try:
        return iso[:10]
    except Exception:
        return iso


def _normalize(item: dict) -> dict:
    f = item.get("fields", {})
    sources = f.get("source", [])
    source_name = sources[0].get("name", "Unknown") if sources else "Unknown"
    countries = f.get("country", [f.get("primary_country", {})])
    country = countries[0].get("name", "Pakistan") if countries else "Pakistan"
    disaster_types = f.get("disaster_type", [])
    disaster_type = disaster_types[0].get("name", "Flood") if disaster_types else "Flood"
    raw_body = f.get("body-html") or f.get("body") or ""
    return {
        "title": f.get("title", ""),
        "source": source_name,
        "published_date": _parse_date(f.get("date", {}).get("created", "")),
        "url": f.get("url", f.get("url_alias", "")),
        "summary": _strip_html(raw_body) if raw_body else "",
        "country": country,
        "disaster_type": disaster_type,
    }


class ReliefWebAdapter(BaseAdapter):
    source_id = "reliefweb"
    name = "ReliefWeb Articles"
    description = "Humanitarian news and situation reports from reliefweb.int (public API)."
    features_created = ["article_count", "latest_headline", "source_links"]
    latency_hours = 1

    def _do_fetch(self) -> AdapterResult:
        params = {
            "appname": _APP_NAME,
            "filter[operator]": "AND",
            "filter[conditions][0][field]": "primary_country.name",
            "filter[conditions][0][value]": "Pakistan",
            "filter[conditions][1][field]": "disaster_type.name",
            "filter[conditions][1][value]": "Flood",
            "fields[include][]": ["title", "source", "date", "url", "body-html",
                                   "country", "disaster_type"],
            "sort[]": "date:desc",
            "limit": str(_MAX_ARTICLES),
        }
        with httpx.Client(timeout=self.request_timeout) as client:
            resp = client.get(_API_URL, params=params)
            resp.raise_for_status()

        payload = resp.json()
        items = payload.get("data", [])
        normalized = [_normalize(item) for item in items]

        return AdapterResult(
            source_id=self.source_id,
            status="fresh",
            data=normalized,
            fetched_at=datetime.now(UTC),
            latency_ms=0.0,   # filled in by BaseAdapter.fetch()
        )
