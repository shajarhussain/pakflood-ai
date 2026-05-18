"""
Gemini-backed chat service for PakFlood AI.

Intent routing: detect what the user is asking about, fetch only the
relevant DB data, build a compact context string (<600 tokens), then
call Gemini.  History is trimmed to the last 5 exchanges so the prompt
stays cheap.
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
    "You are PakFlood AI Assistant — an expert on Pakistan flood risk, weather, "
    "and climate factors. You help users understand flood predictions, current and "
    "historical weather conditions, seasonal patterns, and district-level risk. "
    "Rules:\n"
    "- Answer concisely (2–6 sentences or a short list).\n"
    "- Use the provided data context when answering. If data is missing, say so.\n"
    "- When discussing weather, explain how each factor affects flood probability: "
    "e.g. high soil moisture + heavy rain = runoff with no absorption; "
    "low pressure systems bring sustained rainfall; monsoon season (June–Oct) "
    "dramatically elevates risk across Pakistan.\n"
    "- Unit hints in the data: pressure stored in Pa (divide by 100 for hPa); "
    "wind stored in m/s (multiply by 3.6 for km/h); "
    "evaporation is negative ERA5 convention (magnitude = drying rate).\n"
    "- Always note AI predictions are not official warnings — "
    "refer users to NDMA, PMD, or PDMA for emergencies."
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
        "weather", "rain", "rainfall", "temperature", "temp", "hot", "cold",
        "humidity", "humid", "monsoon", "precipitation", "wind", "windy",
        "soil moisture", "soil", "climate", "current conditions", "forecast",
        "pressure", "storm", "thunderstorm", "overcast", "cloud", "cloudy",
        "wet", "dry", "drizzle", "flood cause", "flood factor", "what cause",
        "why flood", "season", "seasonal", "evaporation", "saturated",
        "saturation", "how wet", "conditions today", "conditions now",
    },
    "model": {
        "model", "accuracy", "confidence", "algorithm", "machine learning",
        "xgboost", "features", "how does", "how accurate", "how it works",
        "what features", "factor", "contribute", "contribution",
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
    """Aggregate weather conditions across Pakistan from the latest zone batch."""
    try:
        repo = ZoneRepository()
        batch = await asyncio.to_thread(repo.get_latest_batch)
        if not batch:
            return "No weather data available."

        db = get_supabase()
        rows = await asyncio.to_thread(
            lambda: db.table("zone_grid_points")
            .select(
                "precipitation,precip_3day_avg,precip_7day_avg,"
                "temperature,temp_3day_avg,humidity,"
                "soil_moisture,soil_3day_avg,"
                "wind_speed,pressure,evaporation,is_monsoon"
            )
            .eq("batch_id", batch["id"])
            .limit(200)
            .execute()
        )
        pts = rows.data or []
        if not pts:
            return "Weather data unavailable."

        def avg(key: str) -> float:
            vals = [float(p[key]) for p in pts if p.get(key) is not None]
            return sum(vals) / len(vals) if vals else 0.0

        precip_1d   = avg("precipitation")
        precip_3d   = avg("precip_3day_avg")
        precip_7d   = avg("precip_7day_avg")
        temp        = avg("temperature")
        temp_3d     = avg("temp_3day_avg")
        humidity    = avg("humidity")
        soil        = avg("soil_moisture")
        soil_3d     = avg("soil_3day_avg")
        wind_ms     = avg("wind_speed")
        pressure_pa = avg("pressure")
        evap        = avg("evaporation")
        monsoon_pct = sum(1 for p in pts if p.get("is_monsoon")) / len(pts) * 100

        # Convert stored SI units back to human-readable
        wind_kmh     = wind_ms * 3.6
        pressure_hpa = pressure_pa / 100.0 if pressure_pa > 1000 else pressure_pa  # handle both Pa and hPa
        evap_mm      = abs(evap) * 1000 if abs(evap) < 1 else abs(evap)  # negative m → mm

        # Derive flood risk interpretation from weather conditions
        risk_hints: list[str] = []
        if precip_1d > 20:
            risk_hints.append("Heavy rainfall today — significant runoff likely")
        elif precip_1d > 5:
            risk_hints.append("Moderate rainfall today")
        if precip_7d > 50:
            risk_hints.append("Prolonged wet period — soils near saturation")
        if soil > 0.35:
            risk_hints.append("High soil moisture — reduced absorption capacity")
        if humidity > 80:
            risk_hints.append("High humidity — rain absorption by soil is limited")
        if monsoon_pct > 50:
            risk_hints.append("Monsoon season active — elevated flood risk nationwide")

        computed = (batch.get("completed_at") or "")[:16]
        lines = [
            f"Pakistan Weather Summary ({len(pts)} grid points, {computed}):",
            f"PRECIPITATION:",
            f"  Today: {precip_1d:.1f}mm | 3-day avg: {precip_3d:.1f}mm | 7-day avg: {precip_7d:.1f}mm",
            f"ATMOSPHERE:",
            f"  Temperature: {temp:.1f}°C (3-day avg: {temp_3d:.1f}°C)",
            f"  Humidity: {humidity:.0f}% | Pressure: {pressure_hpa:.0f} hPa",
            f"  Wind speed: {wind_kmh:.1f} km/h | Evaporation rate: {evap_mm:.2f} mm/day",
            f"SOIL:",
            f"  Soil moisture: {soil:.3f} (3-day avg: {soil_3d:.3f})",
            f"  Saturation level: {'High' if soil > 0.35 else 'Moderate' if soil > 0.2 else 'Low'}",
            f"SEASON:",
            f"  Monsoon active: {'Yes' if monsoon_pct > 50 else 'No'} ({monsoon_pct:.0f}% of points)",
        ]
        if risk_hints:
            lines.append("FLOOD RISK IMPLICATIONS:")
            for h in risk_hints:
                lines.append(f"  - {h}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("weather context error: %s", exc)
        return "Weather data temporarily unavailable."


async def _ctx_live_weather(lat: float, lng: float, location_name: str = "") -> str:
    """Fetch live current conditions from OpenWeatherMap for a specific point."""
    from app.core.config import settings as _settings
    if not _settings.OPENWEATHER_API_KEY:
        return ""
    try:
        import httpx as _httpx
        _OWM = "https://api.openweathermap.org/data/2.5/weather"
        _DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        async with _httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                _OWM,
                params={"lat": lat, "lon": lng,
                        "appid": _settings.OPENWEATHER_API_KEY, "units": "metric"},
            )
        if not res.is_success:
            return ""
        d = res.json()
        main    = d.get("main", {})
        wind    = d.get("wind", {})
        clouds  = d.get("clouds", {})
        wlist   = d.get("weather", [{}])
        name    = location_name or d.get("name") or f"{lat:.2f}°N,{lng:.2f}°E"
        wind_ms = wind.get("speed", 0)
        wind_dir = _DIRS[round(wind.get("deg", 0) / 45) % 8]
        return (
            f"Live Weather — {name} (OpenWeatherMap):\n"
            f"  Conditions: {wlist[0].get('description', '').title()}\n"
            f"  Temperature: {main.get('temp', 0):.1f}°C "
            f"(feels {main.get('feels_like', 0):.1f}°C)\n"
            f"  Humidity: {main.get('humidity', 0)}% | "
            f"Pressure: {main.get('pressure', 0)} hPa\n"
            f"  Wind: {wind_ms * 3.6:.1f} km/h {wind_dir} | "
            f"Cloud cover: {clouds.get('all', 0)}%\n"
            f"  Visibility: {round(d.get('visibility', 10000) / 1000, 1)} km"
        )
    except Exception as exc:
        logger.warning("Live weather fetch failed: %s", exc)
        return ""


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
        lines = ["District Risk & Weather Data:"]
        for d in districts[:2]:
            lat, lng = d["center_lat"], d["center_lng"]
            pt = await asyncio.to_thread(repo.get_nearest_zone_point, lat, lng, 1.2)
            if pt:
                risk  = pt.get("risk_level", "Unknown")
                prob  = float(pt.get("flood_prob") or 0) * 100
                conf  = float(pt.get("confidence") or 0) * 100
                prec  = pt.get("precipitation")
                hum   = pt.get("humidity")
                soil  = pt.get("soil_moisture")
                temp  = pt.get("temperature")
                wind  = pt.get("wind_speed")
                line  = (
                    f"- {d['name']} ({d['province']}): {risk} risk, "
                    f"flood prob {prob:.0f}% (confidence {conf:.0f}%)"
                )
                details: list[str] = []
                if prec  is not None: details.append(f"rain {float(prec):.1f}mm")
                if temp  is not None: details.append(f"temp {float(temp):.1f}°C")
                if hum   is not None: details.append(f"humidity {float(hum):.0f}%")
                if soil  is not None: details.append(f"soil {float(soil):.3f}")
                if wind  is not None: details.append(f"wind {float(wind)*3.6:.1f}km/h")
                if details:
                    line += f"\n  Weather: {', '.join(details)}"
                lines.append(line)
            else:
                lines.append(f"- {d['name']} ({d['province']}): no zone data")

        # Attach live OWM weather for the first matched district
        if districts:
            d0 = districts[0]
            live = await _ctx_live_weather(d0["center_lat"], d0["center_lng"], d0["name"])
            if live:
                lines.append("")
                lines.append(live)

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
        # If no specific district mentioned, include a live OWM snapshot for
        # central Pakistan (Lahore area) as a concrete reference point
        if not district:
            tasks.append(_ctx_live_weather(30.3753, 69.3451, "Central Pakistan"))
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
