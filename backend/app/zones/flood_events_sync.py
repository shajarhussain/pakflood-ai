"""
Sync Pakistan flood events from the GDACS RSS feed.

Called by zone_scheduler weekly, and by scripts/sync_flood_events.py on demand.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# ── GDACS RSS feeds ───────────────────────────────────────────────────────────

GDACS_RSS_FEEDS = [
    "https://www.gdacs.org/xml/rss.xml",
    "https://www.gdacs.org/xml/rss_7d.xml",
]

GDACS_NS = {
    "gdacs": "http://www.gdacs.org",
    "dc":    "http://purl.org/dc/elements/1.1/",
}

# ── Province / district extraction ───────────────────────────────────────────

PROVINCE_MAP = {
    "punjab":               "Punjab",
    "sindh":                "Sindh",
    "balochistan":          "Balochistan",
    "khyber pakhtunkhwa":   "KPK",
    "kpk":                  "KPK",
    "nwfp":                 "KPK",
    "gilgit":               "Gilgit-Baltistan",
    "gilgit-baltistan":     "Gilgit-Baltistan",
    "gilgit baltistan":     "Gilgit-Baltistan",
    "azad kashmir":         "Azad Kashmir",
    "ajk":                  "Azad Kashmir",
    "fata":                 "KPK",
    "islamabad":            "ICT",
}

KNOWN_DISTRICTS = [
    "Lahore","Karachi","Rawalpindi","Faisalabad","Multan","Gujranwala",
    "Peshawar","Quetta","Islamabad","Sialkot","Dadu","Larkana","Jacobabad",
    "Sukkur","Naseerabad","Jaffarabad","Dera Ismail Khan","Chitral","Swat",
    "Nowshera","Charsadda","Mansehra","Abbottabad","Muzaffarabad","Mirpur",
    "Hyderabad","Thatta","Badin","Tharparkar","Sanghar","Khairpur","Ghotki",
    "Rahim Yar Khan","Bahawalpur","Muzaffargarh","Layyah","Bhakkar","Mianwali",
    "Sargodha","Jhang","Khanewal","Pakpattan","Okara","Sahiwal","Narowal",
    "Kasur","Sheikhupura","Gujrat","Jhelum","Chakwal","Attock","Haripur",
    "Mardan","Swabi","Buner","Shangla","Kohistan","Battagram",
    "Upper Dir","Lower Dir","Bajaur","Malakand","Mohmand",
    "Karak","Bannu","Lakki Marwat","Tank","South Waziristan","North Waziristan",
    "Panjgur","Turbat","Gwadar","Khuzdar","Kalat","Mastung","Nushki",
    "Washuk","Chagai","Sibi","Dera Bugti","Kohlu","Barkhan",
    "Loralai","Musakhel","Zhob","Ziarat","Pishin","Killa Abdullah",
    "Diamer","Ghanche","Skardu","Gilgit","Hunza","Ghizer","Astore",
]

HISTORICAL_EVENTS = [
    {
        "event_id":           "hist-pak-2022",
        "year":               2022,
        "title":              "2022 Pakistan Floods - Worst in 30 Years",
        "affected_provinces": json.dumps(["Balochistan","KPK","Punjab","Sindh"]),
        "affected_districts": json.dumps(["Dadu","Jacobabad","Larkana","Sukkur","Naseerabad","Jaffarabad","Dera Ismail Khan","Swat","Nowshera"]),
        "peak_month":         "August 2022",
        "estimated_affected": 33000000,
        "damage_usd_billion": 30.0,
        "description":        "Catastrophic monsoon flooding covering one-third of Pakistan. Record rainfall - 780% above normal in Balochistan. Over 1,700 killed, 33 million affected, 2 million homes damaged. Declared a national emergency.",
    },
    {
        "event_id":           "hist-pak-2020",
        "year":               2020,
        "title":              "2020 Pakistan Monsoon Floods",
        "affected_provinces": json.dumps(["Balochistan","KPK","Punjab","Sindh"]),
        "affected_districts": json.dumps(["Dadu","Sukkur","Naseerabad","Charsadda","Nowshera","Peshawar"]),
        "peak_month":         "August 2020",
        "estimated_affected": 1500000,
        "damage_usd_billion": 1.0,
        "description":        "Widespread monsoon flooding across multiple provinces. More than 400 killed, 1.5 million affected. Balochistan particularly hard hit with flash floods destroying infrastructure.",
    },
    {
        "event_id":           "hist-pak-2015",
        "year":               2015,
        "title":              "2015 Pakistan Floods",
        "affected_provinces": json.dumps(["KPK","Punjab","Sindh"]),
        "affected_districts": json.dumps(["Chitral","Dir","Swat","Nowshera","Lahore","Sialkot"]),
        "peak_month":         "July 2015",
        "estimated_affected": 1600000,
        "damage_usd_billion": 1.5,
        "description":        "Severe flooding in Chitral (KPK) caused by glacial lake outbursts and heavy rain. Widespread flooding in Punjab affecting Lahore and Sialkot. Over 200 killed.",
    },
    {
        "event_id":           "hist-pak-2014",
        "year":               2014,
        "title":              "2014 Pakistan-India Floods",
        "affected_provinces": json.dumps(["Punjab","Azad Kashmir"]),
        "affected_districts": json.dumps(["Lahore","Sialkot","Gujranwala","Narowal","Muzaffarabad"]),
        "peak_month":         "September 2014",
        "estimated_affected": 2500000,
        "damage_usd_billion": 2.1,
        "description":        "Heavy monsoon rains caused severe flooding in Punjab and Azad Kashmir. Chenab, Jhelum and Ravi rivers overflowed. Over 367 killed in Pakistan, 2.5 million affected.",
    },
    {
        "event_id":           "hist-pak-2011",
        "year":               2011,
        "title":              "2011 Pakistan Floods",
        "affected_provinces": json.dumps(["Sindh","Balochistan","Punjab"]),
        "affected_districts": json.dumps(["Dadu","Larkana","Jacobabad","Sukkur","Thatta","Badin"]),
        "peak_month":         "August 2011",
        "estimated_affected": 9000000,
        "damage_usd_billion": 3.7,
        "description":        "Second consecutive year of catastrophic flooding. Sindh worst affected with 70% of the province inundated. Over 520 killed, 9 million affected. Many areas still recovering from 2010.",
    },
    {
        "event_id":           "hist-pak-2010",
        "year":               2010,
        "title":              "2010 Pakistan Floods - Worst in History",
        "affected_provinces": json.dumps(["Balochistan","KPK","Punjab","Sindh"]),
        "affected_districts": json.dumps(["Sukkur","Jacobabad","Dadu","Larkana","Dera Ismail Khan","Swat","Nowshera","Charsadda","Muzaffargarh","Rajanpur"]),
        "peak_month":         "August 2010",
        "estimated_affected": 20000000,
        "damage_usd_billion": 43.0,
        "description":        "Deadliest flood in Pakistan history. 20 million people displaced, over 1,700 killed. One-fifth of Pakistan's total land area inundated. Indus River ran at record levels. UN called it worse than 2004 tsunami.",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _extract_provinces(text: str) -> list[str]:
    text_lower = text.lower()
    found = set()
    for key, canonical in PROVINCE_MAP.items():
        if key in text_lower:
            found.add(canonical)
    return sorted(found)


def _extract_districts(text: str) -> list[str]:
    found = set()
    for d in KNOWN_DISTRICTS:
        if re.search(r"\b" + re.escape(d) + r"\b", text, re.IGNORECASE):
            found.add(d)
    return sorted(found)


def _peak_month(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%B %Y")
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%B %Y")
    except Exception:
        return ""


def _extract_affected(text: str) -> int | None:
    patterns = [
        r"([\d,\.]+)\s*million\s*(people|persons|affected|displaced)",
        r"([\d,\.]+)\s*(lakh)\s*(people|persons|affected|displaced)",
        r"([\d,\.]+)\s*thousand\s*(people|persons|affected|displaced)",
        r"affected\D{0,20}([\d,]+)\s*(people|persons)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                num = float(m.group(1).replace(",", ""))
                if "million" in pat.lower():
                    return int(num * 1_000_000)
                if "lakh" in pat.lower():
                    return int(num * 100_000)
                if "thousand" in pat.lower():
                    return int(num * 1_000)
                return int(num)
            except (ValueError, IndexError):
                pass
    return None


def _extract_damage(text: str) -> float | None:
    m = re.search(r"USD?\s*\$?([\d,\.]+)\s*(billion|million|mn)", text, re.IGNORECASE)
    if not m:
        return None
    try:
        num  = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        if unit == "billion":
            return round(num, 2)
        return round(num / 1000, 4)
    except ValueError:
        return None


def _build_row_from_rss(item: ET.Element) -> dict | None:
    def _tag(ns_key, local):
        return f"{{{GDACS_NS[ns_key]}}}{local}"

    etype = (item.findtext(_tag("gdacs", "eventtype")) or "").strip().upper()
    if etype != "FL":
        return None

    country = (item.findtext(_tag("gdacs", "country")) or "").lower()
    if "pakistan" not in country:
        return None

    event_id = item.findtext(_tag("gdacs", "eventid")) or ""
    if not event_id:
        return None

    name        = (item.findtext("title") or "").strip()
    description = _strip_html(item.findtext("description") or "")
    date_str    = item.findtext("pubDate") or item.findtext(_tag("dc", "date")) or ""

    year = None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            year = datetime.strptime(date_str.strip(), fmt).year
            break
        except (ValueError, AttributeError):
            pass
    if year is None:
        try:
            year = int(date_str[:4])
        except Exception:
            return None

    full_text = f"{name} {description}"
    return {
        "event_id":           f"gdacs-{event_id}",
        "year":               year,
        "title":              name or f"Pakistan Flood {year}",
        "affected_provinces": json.dumps(_extract_provinces(full_text)),
        "affected_districts": json.dumps(_extract_districts(full_text)),
        "peak_month":         _peak_month(date_str),
        "estimated_affected": _extract_affected(description),
        "damage_usd_billion": _extract_damage(description),
        "description":        description[:2000] if description else name,
    }


# ── Public sync function ──────────────────────────────────────────────────────

def sync_flood_events(verbose: bool = False) -> int:
    """
    Upsert historical baseline + latest GDACS RSS Pakistan flood events.
    Returns total number of events processed.
    """
    from app.core.supabase import get_supabase
    db = get_supabase()

    # 1. Upsert historical baseline
    if verbose:
        print(f"Upserting {len(HISTORICAL_EVENTS)} historical baseline events...")
    db.table("flood_events").upsert(HISTORICAL_EVENTS, on_conflict="event_id").execute()

    # 2. Fetch from GDACS RSS
    gdacs_rows: list[dict] = []
    for feed_url in GDACS_RSS_FEEDS:
        try:
            if verbose:
                print(f"  Fetching: {feed_url}")
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(feed_url)
                resp.raise_for_status()

            root  = ET.fromstring(resp.text)
            items = root.findall(".//item")
            if verbose:
                print(f"  Found {len(items)} RSS items")

            for item in items:
                row = _build_row_from_rss(item)
                if row:
                    gdacs_rows.append(row)

            break  # success — don't try the mirror

        except Exception as exc:
            logger.warning("GDACS RSS feed %s failed: %s", feed_url, exc)
            if verbose:
                print(f"  Failed ({exc}) — trying next mirror...")

    if gdacs_rows:
        seen: set[str] = set()
        deduped = [r for r in gdacs_rows if not (seen.add(r["event_id"]) or r["event_id"] in seen)]  # type: ignore[func-returns-value]
        # simpler dedup
        deduped_clean: list[dict] = []
        seen2: set[str] = set()
        for r in gdacs_rows:
            if r["event_id"] not in seen2:
                seen2.add(r["event_id"])
                deduped_clean.append(r)

        chunk_size = 20
        for i in range(0, len(deduped_clean), chunk_size):
            db.table("flood_events").upsert(
                deduped_clean[i:i + chunk_size], on_conflict="event_id"
            ).execute()
        if verbose:
            print(f"  Upserted {len(deduped_clean)} GDACS events")
        logger.info("Flood events sync: %d GDACS + %d historical", len(deduped_clean), len(HISTORICAL_EVENTS))
    else:
        if verbose:
            print("  No Pakistan flood events in current RSS window — historical baseline saved")
        logger.info("Flood events sync: no current GDACS events, historical baseline saved")

    return len(HISTORICAL_EVENTS) + len(gdacs_rows)
