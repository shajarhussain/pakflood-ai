"""
Gemini-backed chat service for PakFlood AI.

Intent routing: detect what the user is asking about, fetch only the
relevant DB data, build a compact context string (<500 tokens), then
call gemini-1.5-flash.  History is trimmed to the last 5 exchanges so
the prompt stays cheap.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings
from app.core.supabase import get_supabase
from app.zones.zone_repository import ZoneRepository

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are PakFlood AI Assistant — an expert on Pakistan flood risk. "
    "You help users understand flood predictions, historical events, weather, "
    "and district-level risk analysis. "
    "Rules: answer concisely (2–5 sentences or a short list). "
    "Use the provided data context when answering. "
    "If data is missing, say so clearly. "
    "Always note that AI predictions are not official warnings — "
    "refer users to NDMA, PMD, or PDMA for emergency decisions."
)

# ── Intent keywords ───────────────────────────────────────────────────────────

_INTENTS: dict[str, set[str]] = {
    "events": {
        "event", "historical", "history", "past", "2010", "2011", "2014", "2022",
        "disaster", "damage", "billion", "affected", "worst", "record flood",
        "monsoon flood", "casualties",
    },
    "zones": {
        "zone", "risk", "severe", "heatmap", "prediction", "probability", "chance",
        "high risk", "moderate", "nationwide", "distribution", "most affected",
        "dangerous", "safe", "where is flood",
    },
    "weather": {
        "weather", "rain", "rainfall", "temperature", "humidity", "monsoon",
        "precipitation", "wind", "soil moisture", "climate", "current conditions",
    },
    "model": {
        "model", "accuracy", "confidence", "algorithm", "machine learning",
        "xgboost", "features", "how does", "how accurate", "how it works",
    },
}


def _detect_intents(msg: str) -> set[str]:
    lower = msg.lower()
    found = {intent for intent, kws in _INTENTS.items() if any(k in lower for k in kws)}
    return found or {"general"}


# ── District name cache ───────────────────────────────────────────────────────

_district_names: list[str] | None = None


async def _load_district_names() -> list[str]:
    global _district_names
    if _district_names is not None:
        return _district_names
    try:
        db = get_supabase()
        result = await asyncio.to_thread(
            lambda: db.table("districts").select("name").execute()
        )
        _district_names = [r["name"].lower() for r in (result.data or [])]
    except Exception as exc:
        logger.warning("Could not load district names: %s", exc)
        _district_names = []
    return _district_names


async def _find_district(msg: str) -> str | None:
    names = await _load_district_names()
    lower = msg.lower()
    # Longer names first to prefer "dera ghazi khan" over "khan"
    for name in sorted(names, key=len, reverse=True):
        if name in lower:
            return name
    return None


# ── Context builders ──────────────────────────────────────────────────────────

async def _ctx_events() -> str:
    try:
        db = get_supabase()
        rows = await asyncio.to_thread(
            lambda: db.table("flood_events")
            .select("year,title,estimated_affected,damage_usd_billion,affected_provinces,peak_month,description")
            .order("year", desc=True)
            .execute()
        )
        if not rows.data:
            return "No historical flood event data available."

        lines = ["Pakistan Historical Flood Events:"]
        for r in rows.data:
            provinces = r.get("affected_provinces") or "[]"
            if isinstance(provinces, str):
                provinces = json.loads(provinces)
            parts = [f"{r['year']}: {r['title']}"]
            if r.get("estimated_affected"):
                parts.append(f"{r['estimated_affected'] / 1e6:.0f}M affected")
            if r.get("damage_usd_billion"):
                parts.append(f"${r['damage_usd_billion']}B damage")
            if provinces:
                parts.append(f"provinces: {', '.join(provinces)}")
            if r.get("peak_month"):
                parts.append(f"peak: {r['peak_month']}")
            lines.append("- " + " | ".join(parts))
            if r.get("description"):
                lines.append(f"  {r['description'][:180]}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("events context error: %s", exc)
        return "Historical event data temporarily unavailable."


async def _ctx_zones() -> str:
    try:
        repo = ZoneRepository()
        batch = await asyncio.to_thread(repo.get_latest_batch)
        if not batch:
            return "No zone risk data computed yet."

        db = get_supabase()
        # Fetch a 500-row sample for stats — enough for accurate distribution
        rows = await asyncio.to_thread(
            lambda: db.table("zone_grid_points")
            .select("risk_level,flood_prob")
            .eq("batch_id", batch["id"])
            .limit(500)
            .execute()
        )
        points = rows.data or []
        if not points:
            return "Zone data is empty."

        counts: dict[str, int] = {}
        prob_sum: dict[str, float] = {}
        for p in points:
            lvl = p.get("risk_level") or "Unknown"
            counts[lvl] = counts.get(lvl, 0) + 1
            prob_sum[lvl] = prob_sum.get(lvl, 0.0) + float(p.get("flood_prob") or 0)

        total = batch["total_points"]
        computed = (batch.get("completed_at") or "")[:16]
        lines = [f"Flood Risk Distribution ({total} grid points, {computed}):"]
        for lvl in ("Severe", "High", "Moderate", "Low"):
            c = counts.get(lvl, 0)
            if c == 0:
                continue
            avg = prob_sum.get(lvl, 0) / c * 100
            # Scale sample count to full population
            est = int(c / len(points) * total)
            lines.append(f"- {lvl}: ~{est} points, avg probability {avg:.0f}%")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("zones context error: %s", exc)
        return "Zone data temporarily unavailable."


async def _ctx_weather() -> str:
    try:
        repo = ZoneRepository()
        batch = await asyncio.to_thread(repo.get_latest_batch)
        if not batch:
            return "No weather data available."

        db = get_supabase()
        rows = await asyncio.to_thread(
            lambda: db.table("zone_grid_points")
            .select(
                "precipitation,precip_7day_avg,temperature,humidity,"
                "soil_moisture,wind_speed,is_monsoon"
            )
            .eq("batch_id", batch["id"])
            .limit(150)
            .execute()
        )
        pts = rows.data or []
        if not pts:
            return "Weather data unavailable."

        def avg(key: str) -> float:
            vals = [float(p[key]) for p in pts if p.get(key) is not None]
            return sum(vals) / len(vals) if vals else 0.0

        monsoon_pct = sum(1 for p in pts if p.get("is_monsoon")) / len(pts) * 100
        computed = (batch.get("completed_at") or "")[:16]
        return (
            f"Current Weather (Pakistan avg, {len(pts)} sample points, {computed}):\n"
            f"- 24h precipitation: {avg('precipitation'):.1f}mm\n"
            f"- 7-day precipitation: {avg('precip_7day_avg'):.1f}mm\n"
            f"- Temperature: {avg('temperature'):.1f}°C\n"
            f"- Humidity: {avg('humidity'):.0f}%\n"
            f"- Soil moisture: {avg('soil_moisture'):.3f}\n"
            f"- Wind speed: {avg('wind_speed'):.1f} km/h\n"
            f"- Monsoon season: {'Yes' if monsoon_pct > 50 else 'No'} ({monsoon_pct:.0f}% of points)"
        )
    except Exception as exc:
        logger.error("weather context error: %s", exc)
        return "Weather data temporarily unavailable."


async def _ctx_district(name: str) -> str:
    try:
        db = get_supabase()
        result = await asyncio.to_thread(
            lambda: db.table("districts")
            .select("district_id,name,province,center_lat,center_lng")
            .ilike("name", f"%{name}%")
            .limit(3)
            .execute()
        )
        districts = result.data or []
        if not districts:
            return f"District '{name}' not found in the database."

        repo = ZoneRepository()
        lines = ["District Risk Data:"]
        for d in districts[:2]:
            pt = await asyncio.to_thread(
                repo.get_nearest_zone_point,
                d["center_lat"], d["center_lng"], 1.2,
            )
            if pt:
                risk = pt.get("risk_level", "Unknown")
                prob = float(pt.get("flood_prob") or 0) * 100
                lines.append(
                    f"- {d['name']} ({d['province']}): {risk} risk, "
                    f"flood probability {prob:.0f}%"
                )
            else:
                lines.append(f"- {d['name']} ({d['province']}): no zone data")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("district context error: %s", exc)
        return "District data temporarily unavailable."


async def _ctx_model() -> str:
    return (
        "PakFlood AI Model:\n"
        "- Algorithm: XGBoost classifier\n"
        "- 14 features: precipitation (1-day, 3-day avg, 7-day avg), temperature, "
        "soil moisture, humidity, wind speed, evaporation, pressure, is_monsoon, "
        "month, day_of_year\n"
        "- Output: flood probability (0–100%), risk level (Low/Moderate/High/Severe), "
        "confidence score, top-3 contributing factors\n"
        "- Weather source: Open-Meteo API (real-time)\n"
        "- Zone grid: ~3,685 points across Pakistan at 0.5° resolution, "
        "refreshed every 3 hours"
    )


async def _ctx_general() -> str:
    try:
        repo = ZoneRepository()
        batch = await asyncio.to_thread(repo.get_latest_batch)
        mins = await asyncio.to_thread(repo.get_minutes_since_last_computation)
        total = batch["total_points"] if batch else 0
        age = f"{int(mins or 0)}min ago" if mins is not None else "not yet computed"
        return (
            f"PakFlood AI: Pakistan flood risk prediction system.\n"
            f"- Covers all 142+ districts across Punjab, Sindh, KP, Balochistan, AJK\n"
            f"- Zone grid: {total} prediction points at 0.5° resolution\n"
            f"- Last updated: {age}\n"
            f"- Data: real-time weather + ML prediction + historical flood events"
        )
    except Exception:
        return (
            "PakFlood AI: Pakistan flood risk prediction covering all districts. "
            "Uses real-time weather + ML prediction + historical event data."
        )


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_reply(message: str, history: list[dict]) -> str:
    """
    Route the user message to relevant DB context, then call Gemini.

    history: list of {"role": "user"|"model", "content": str}.
    Only the last 5 exchanges (10 items) are sent to keep token cost low.
    """
    if not settings.GEMINI_API_KEY:
        return (
            "AI chat is not configured — please set GEMINI_API_KEY in the "
            "backend .env file. You can get a free key at "
            "https://aistudio.google.com/app/apikey"
        )

    intents = _detect_intents(message)
    district = await _find_district(message)

    # Build only the context slices that are relevant
    tasks: list = []
    if "events" in intents:
        tasks.append(_ctx_events())
    if "zones" in intents:
        tasks.append(_ctx_zones())
    if "weather" in intents:
        tasks.append(_ctx_weather())
    if "model" in intents:
        tasks.append(_ctx_model())
    if district:
        tasks.append(_ctx_district(district))
    if not tasks:
        tasks.append(_ctx_general())

    ctx_parts = await asyncio.gather(*tasks, return_exceptions=True)
    context = "\n\n".join(
        str(p) for p in ctx_parts if not isinstance(p, Exception)
    )

    # Inject context into the user turn so it never inflates system tokens
    user_turn = (
        f"[Relevant data from the PakFlood AI database]\n{context}\n\n"
        f"[User question]\n{message}"
        if context else message
    )

    try:
        from google import genai                    # lazy — optional dependency
        from google.genai import types as gtypes
    except ModuleNotFoundError:
        return "google-genai is not installed. Run: pip install google-genai"

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Keep last 5 exchanges (10 messages) to cap history tokens
    trimmed = history[-10:]
    gem_history = [
        gtypes.Content(
            role=h["role"],
            parts=[gtypes.Part.from_text(text=h["content"])],
        )
        for h in trimmed
    ]

    def _call() -> str:
        session = client.chats.create(
            model="gemini-2.5-flash",
            config=gtypes.GenerateContentConfig(
                system_instruction=_SYSTEM,
                max_output_tokens=512,
            ),
            history=gem_history,
        )
        resp = session.send_message(user_turn)
        return resp.text

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return (
                "The AI assistant is temporarily rate-limited. "
                "Please wait a moment and try again."
            )
        if "403" in msg or "API_KEY" in msg.upper():
            return "Invalid or missing Gemini API key. Please check GEMINI_API_KEY in backend/.env."
        logger.error("Gemini error: %s", exc)
        return "The AI assistant encountered an error. Please try again shortly."
