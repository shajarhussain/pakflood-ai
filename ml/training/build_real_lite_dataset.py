"""Build the Gate B-Lite training CSV from downloaded public-API data.

Inputs (produced by download_real_lite_sources.py):
  - data/real_lite/raw/weather/*.csv               daily NASA POWER per district
  - data/real_lite/raw/reports/eonet_floods.json   EONET flood event-points

Output:
  - data/real_lite/training/pakistan_flood_prediction_real_lite.csv

Label policy (REAL, weak):
  Each EONET flood event-point is assigned to the nearest district centroid by
  great-circle distance. The matched (district, event_date) is marked with
  ``flood_report_today=1`` plus a ±N-day broadening window (default 3 days)
  to approximate the operational reality that satellite-flagged flood events
  typically span several days. Future-window labels are produced by EXPLICIT
  FORWARD SHIFTS (never rolling+shift), identical contract to strict v3:

      flood_next_24h = shift(-1)
      flood_next_72h = max(shift(-1), shift(-2), shift(-3))
      flood_next_7d  = max(shift(-1) … shift(-7))

No mock data, no mock_risk.json, no synthetic fallback.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional


DISTRICT_CENTROIDS: dict[str, tuple[float, float]] = {
    "PK-SD-SKR": (27.70, 68.85),
    "PK-SD-JCB": (28.45, 68.35),
    "PK-SD-LRK": (27.45, 67.90),
    "PK-PB-MUL": (30.30, 71.55),
    "PK-PB-RWP": (33.65, 73.05),
    "PK-PB-LHR": (31.55, 74.40),
    "PK-KP-PSH": (34.10, 71.70),
    "PK-BL-QTA": (30.20, 67.05),
    "PK-BL-NAS": (28.85, 68.15),
    "PK-GB-GIL": (36.00, 74.20),
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_real_lite_dataset",
        description=(
            "Join NASA POWER weather + EONET flood-event labels into one "
            "training CSV with forward-shift future-window labels and "
            "trailing rolling/lag rainfall features."
        ),
    )
    p.add_argument("--weather-dir", type=Path, default=Path("data/real_lite/raw/weather"))
    p.add_argument("--events",      type=Path, default=Path("data/real_lite/raw/reports/eonet_floods.json"))
    p.add_argument("--output",      type=Path, default=Path("data/real_lite/training/pakistan_flood_prediction_real_lite.csv"))
    p.add_argument("--event-window-days", type=int, default=3,
                   help="Mark observed_flood_today=1 within ±N days of an EONET event-point. Default 3.")
    p.add_argument("--max-event-distance-km", type=float, default=200.0,
                   help="Max great-circle distance from event-point to nearest district centroid. Default 200 km.")
    return p


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _future_max(s, horizons: list[int]):
    import pandas as pd
    shifted = pd.concat([s.shift(-h) for h in horizons], axis=1)
    return shifted.max(axis=1).fillna(0).astype(int)


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        import pandas as pd
    except ImportError as exc:
        print(f"ERROR: pandas required: {exc}", file=sys.stderr)
        return 2

    if not args.weather_dir.exists():
        print(f"ERROR: weather dir missing: {args.weather_dir}", file=sys.stderr)
        return 3
    if not args.events.exists():
        print(f"ERROR: events file missing: {args.events}", file=sys.stderr)
        return 3

    # ── 1. Load weather, concat all districts ─────────────────────────────
    frames = []
    for csv_path in sorted(args.weather_dir.glob("*.csv")):
        df = pd.read_csv(csv_path, parse_dates=["date"])
        frames.append(df)
    if not frames:
        print(f"ERROR: no weather CSVs in {args.weather_dir}", file=sys.stderr)
        return 4
    weather = pd.concat(frames, ignore_index=True).sort_values(["district_id", "date"])
    print(f"[lite-build] weather rows={len(weather):,}  districts={weather['district_id'].nunique()}")

    # NASA POWER returns -999 for missing — replace with 0 for rainfall, NaN for others.
    weather["rainfall_mm"]      = weather["rainfall_mm"].where(weather["rainfall_mm"] >= 0, 0.0)
    for c in ("temperature_c", "humidity_pct", "wind_speed_ms"):
        weather[c] = weather[c].where(weather[c] > -900)

    # ── 2. Build flood labels from EONET event-points ─────────────────────
    events = json.loads(args.events.read_text()).get("events", [])
    matched: list[dict] = []
    for ev in events:
        for g in ev.get("geometry", []):
            lat, lon, date_iso = g.get("lat"), g.get("lon"), (g.get("date") or "")[:10]
            if not (lat and lon and date_iso):
                continue
            # Nearest district
            best_id, best_km = None, float("inf")
            for did, (dlat, dlon) in DISTRICT_CENTROIDS.items():
                km = _haversine_km(lat, lon, dlat, dlon)
                if km < best_km:
                    best_id, best_km = did, km
            if best_id is None or best_km > args.max_event_distance_km:
                continue
            matched.append({
                "district_id": best_id,
                "event_date": pd.to_datetime(date_iso),
                "distance_km": round(best_km, 1),
                "event_id": ev.get("id"),
                "event_title": ev.get("title"),
            })
    matches_df = pd.DataFrame(matched)
    print(f"[lite-build] EONET event-points matched to a district within "
          f"{args.max_event_distance_km}km: {len(matches_df)}")

    # ── 3. Mark observed_flood_today within ±event_window_days ────────────
    weather["observed_flood_today"] = 0
    weather["label_source"] = "no_flood_reported"
    weather["label_confidence"] = 0.0
    for _, m in matches_df.iterrows():
        win = pd.Timedelta(days=args.event_window_days)
        mask = (
            (weather["district_id"] == m["district_id"]) &
            (weather["date"] >= m["event_date"] - win) &
            (weather["date"] <= m["event_date"] + win)
        )
        weather.loc[mask, "observed_flood_today"] = 1
        weather.loc[mask, "label_source"] = "EONET_v3"
        # Closer events = higher confidence (1.0 at 0 km, ~0.5 at max distance)
        conf = max(0.3, 1.0 - (m["distance_km"] / args.max_event_distance_km) * 0.7)
        weather.loc[mask, "label_confidence"] = pd.Series(
            [conf] * mask.sum()
        ).combine(
            weather.loc[mask, "label_confidence"].reset_index(drop=True),
            max,
        ).values
    print(f"[lite-build] positive district-days after window broadening: "
          f"{int(weather['observed_flood_today'].sum())}")

    # ── 4. Compute features per district AFTER sorting and reindexing ─────
    out_frames = []
    for did, g in weather.groupby("district_id"):
        g = g.sort_values("date").set_index("date").copy()
        # NASA POWER is already daily and contiguous, but be defensive:
        full = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full)
        g.index.name = "date"
        g["district_id"]   = did
        g["district_name"] = g["district_name"].ffill().bfill()
        g["province"]      = g["province"].ffill().bfill()
        g["rainfall_mm"]   = g["rainfall_mm"].fillna(0.0)
        for c in ("temperature_c", "humidity_pct", "wind_speed_ms"):
            g[c] = g[c].ffill().bfill()
        g["observed_flood_today"] = g["observed_flood_today"].fillna(0).astype(int)
        g["label_source"]    = g["label_source"].fillna("no_flood_reported")
        g["label_confidence"] = g["label_confidence"].fillna(0.0)

        r = g["rainfall_mm"]
        g["rainfall_1d_mm"]      = r
        g["rainfall_3d_mm"]      = r.rolling(3,  min_periods=1).sum()
        g["rainfall_7d_mm"]      = r.rolling(7,  min_periods=1).sum()
        g["rainfall_14d_mm"]     = r.rolling(14, min_periods=1).sum()
        g["rainfall_30d_mm"]     = r.rolling(30, min_periods=1).sum()
        g["precip_lag_1d"]       = r.shift(1)
        g["precip_lag_3d"]       = r.shift(3)
        g["precip_lag_7d"]       = r.shift(7)
        g["antecedent_precip_3d"]  = r.shift(1).rolling(3,  min_periods=1).sum()
        g["antecedent_precip_7d"]  = r.shift(1).rolling(7,  min_periods=1).sum()
        g["antecedent_precip_14d"] = r.shift(1).rolling(14, min_periods=1).sum()
        g["rainfall_anomaly_pct"]  = (
            (r - r.rolling(30, min_periods=7).mean())
            / r.rolling(30, min_periods=7).mean().replace(0, pd.NA) * 100
        ).fillna(0.0)

        # Forward-shift labels (no future leakage in features)
        obs = g["observed_flood_today"]
        g["flood_next_24h"] = obs.shift(-1).fillna(0).astype(int)
        g["flood_next_72h"] = _future_max(obs, [1, 2, 3])
        g["flood_next_7d"]  = _future_max(obs, [1, 2, 3, 4, 5, 6, 7])

        out_frames.append(g.reset_index())

    big = pd.concat(out_frames, ignore_index=True)
    big["feature_source_summary"] = (
        "NASA-POWER-daily(rainfall,T2M,RH2M,WS10M) + EONET-v3-flood-events"
    )

    cols = [
        "district_id", "district_name", "province", "date",
        "rainfall_1d_mm", "rainfall_3d_mm", "rainfall_7d_mm",
        "rainfall_14d_mm", "rainfall_30d_mm",
        "precip_lag_1d", "precip_lag_3d", "precip_lag_7d",
        "antecedent_precip_3d", "antecedent_precip_7d", "antecedent_precip_14d",
        "rainfall_anomaly_pct",
        "temperature_c", "humidity_pct", "wind_speed_ms",
        "observed_flood_today",
        "flood_next_24h", "flood_next_72h", "flood_next_7d",
        "label_source", "label_confidence", "feature_source_summary",
    ]
    big = big[cols].fillna(0.0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    big.to_csv(args.output, index=False)

    pos = int(big["flood_next_72h"].sum())
    print(f"[lite-build] wrote {args.output} rows={len(big):,} "
          f"flood_next_72h positive={pos} ratio={pos/len(big):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
