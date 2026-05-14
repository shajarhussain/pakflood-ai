"""Build district-day future-window flood labels (PakFlood AI v3).

Reads district boundaries and UNOSAT/HDX flood extent polygons. Computes
flooded_area_km2 per district per event date using a projected metric CRS
(default EPSG:6933 for national equal-area). Then builds a continuous
district × date grid and creates future-window labels via EXPLICIT FORWARD
SHIFTS (never rolling+shift), so:

    flood_next_24h = observed_flood_today.shift(-1)
    flood_next_72h = max(shift(-1), shift(-2), shift(-3))
    flood_next_7d  = max(shift(-1) … shift(-7))

Output schema:
    district_id, district_name, province, date,
    observed_flood_today,
    flood_next_24h, flood_next_72h, flood_next_7d,
    flooded_area_km2, district_area_km2, flooded_area_pct_of_district,
    label_source, metric_crs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


REQUIRED_CONTRACT_KEYS = ["boundaries", "flood_extents"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_flood_labels",
        description=(
            "Generate future-window flood labels by intersecting historical "
            "UNOSAT flood extents with Pakistan districts in a projected metric CRS."
        ),
    )
    p.add_argument("--boundaries", required=True, type=Path)
    p.add_argument("--flood-extents", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--metric-crs", default="EPSG:6933",
                   help="Projected CRS for area. Default EPSG:6933 (national). "
                        "EPSG:32642 acceptable for regional UTM testing.")
    p.add_argument("--flood-area-threshold-pct", type=float, default=0.5,
                   help="Min flooded_area_pct_of_district to mark observed_flood_today=1")
    p.add_argument("--start-date", required=True, help="ISO YYYY-MM-DD inclusive")
    p.add_argument("--end-date", required=True, help="ISO YYYY-MM-DD inclusive")
    p.add_argument("--date-property", default="event_date",
                   help="GeoJSON property holding the event date (default 'event_date').")
    return p


def _future_max(series, horizons: list[int]):
    """Forward-shift max over the listed positive horizons.

    Never uses rolling+shift — explicit ``s.shift(-h)`` only.
    """
    import pandas as pd
    shifted = pd.concat([series.shift(-h) for h in horizons], axis=1)
    return shifted.max(axis=1).fillna(0).astype(int)


def run(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    from ml.training.real_data_contract import (
        validate_dependencies, validate_real_data_contract,
        DataMissingError, DependencyMissingError,
    )
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr); return 2
    try:
        validate_real_data_contract(required_keys=REQUIRED_CONTRACT_KEYS)
    except DataMissingError as exc:
        print(str(exc), file=sys.stderr); return 3

    import geopandas as gpd
    import pandas as pd
    from pyproj import CRS

    boundaries = gpd.read_file(args.boundaries)
    extents = gpd.read_file(args.flood_extents)
    if boundaries.crs is None or extents.crs is None:
        print("ERROR: boundaries and flood extents must both have CRS set", file=sys.stderr); return 4

    target_crs = CRS.from_user_input(args.metric_crs)
    if target_crs.is_geographic:
        print(f"ERROR: --metric-crs {args.metric_crs} is geographic. Refusing area calculation.",
              file=sys.stderr); return 4

    # Hard guard ALSO checks original frames before any .area access downstream.
    if boundaries.crs.is_geographic and boundaries.crs == target_crs:
        print("ERROR: target CRS is geographic", file=sys.stderr); return 4

    if args.date_property not in extents.columns:
        print(f"ERROR: flood extents file has no '{args.date_property}' property. "
              f"Available columns: {list(extents.columns)}", file=sys.stderr); return 4

    extents["event_date"] = pd.to_datetime(extents[args.date_property]).dt.strftime("%Y-%m-%d")

    boundaries_m = boundaries.to_crs(target_crs)
    extents_m = extents.to_crs(target_crs)
    if boundaries_m.crs.is_geographic:
        raise RuntimeError("Refusing area calculation in geographic CRS — internal guard failed")

    boundaries_m["district_area_m2"] = boundaries_m.geometry.area
    boundaries_m["district_area_km2"] = boundaries_m["district_area_m2"] / 1e6

    observed_rows = []
    for event_date, group in extents_m.groupby("event_date"):
        try:
            inter = gpd.overlay(boundaries_m, group, how="intersection", keep_geom_type=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[labels] overlay failed for {event_date}: {exc}", file=sys.stderr)
            continue
        if inter.empty:
            continue
        inter["flooded_area_m2"] = inter.geometry.area
        agg = inter.groupby("district_id", as_index=False)["flooded_area_m2"].sum()
        agg = agg.merge(boundaries_m[["district_id", "district_name", "province", "district_area_km2", "district_area_m2"]],
                        on="district_id", how="left")
        agg["flooded_area_km2"] = agg["flooded_area_m2"] / 1e6
        agg["flooded_area_pct_of_district"] = agg["flooded_area_m2"] / agg["district_area_m2"] * 100.0
        agg["observed_flood_today"] = (agg["flooded_area_pct_of_district"] >= args.flood_area_threshold_pct).astype(int)
        agg["date"] = event_date
        observed_rows.append(agg.drop(columns=["flooded_area_m2", "district_area_m2"]))

    observed_df = (pd.concat(observed_rows, ignore_index=True)
                   if observed_rows else
                   pd.DataFrame(columns=["district_id", "district_name", "province", "date",
                                         "flooded_area_km2", "district_area_km2",
                                         "flooded_area_pct_of_district", "observed_flood_today"]))

    # Continuous district × date grid
    all_dates = pd.date_range(args.start_date, args.end_date, freq="D").strftime("%Y-%m-%d")
    static = boundaries_m[["district_id", "district_name", "province", "district_area_km2"]].drop_duplicates()
    grid = static.assign(key=1).merge(
        pd.DataFrame({"date": all_dates, "key": 1}), on="key", how="outer"
    ).drop(columns="key")

    merged = grid.merge(
        observed_df[["district_id", "date", "flooded_area_km2", "flooded_area_pct_of_district", "observed_flood_today"]],
        on=["district_id", "date"], how="left",
    )
    merged["observed_flood_today"] = merged["observed_flood_today"].fillna(0).astype(int)
    merged["flooded_area_km2"] = merged["flooded_area_km2"].fillna(0.0)
    merged["flooded_area_pct_of_district"] = merged["flooded_area_pct_of_district"].fillna(0.0)

    # Sort to ensure shift respects per-district chronology
    merged = merged.sort_values(["district_id", "date"]).reset_index(drop=True)

    def per_district(group):
        g = group["observed_flood_today"]
        group = group.copy()
        group["flood_next_24h"] = g.shift(-1).fillna(0).astype(int)
        group["flood_next_72h"] = _future_max(g, [1, 2, 3])
        group["flood_next_7d"]  = _future_max(g, [1, 2, 3, 4, 5, 6, 7])
        return group

    merged = merged.groupby("district_id", group_keys=False).apply(per_district)

    merged["label_source"] = "UNOSAT_HDX_v3"
    merged["metric_crs"] = str(target_crs)

    cols = [
        "district_id", "district_name", "province", "date",
        "observed_flood_today",
        "flood_next_24h", "flood_next_72h", "flood_next_7d",
        "flooded_area_km2", "district_area_km2", "flooded_area_pct_of_district",
        "label_source", "metric_crs",
    ]
    out = merged[cols]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)
    print(f"[labels] wrote {args.output} rows={len(out)} metric_crs={target_crs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
