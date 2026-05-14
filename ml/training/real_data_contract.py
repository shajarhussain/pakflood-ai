"""Real-data contract for the PakFlood AI v3 prediction pipeline.

STRICT POLICY
=============
This module is the single source of truth for which real downloaded files are
required, where they must live on disk, and which Python dependencies must be
installed before any expensive processing starts. All v3 pipeline scripts call
``validate_dependencies()`` and ``validate_real_data_contract(required_keys=...)``
as cheap preflight after argparse resolves a non-help invocation.

No synthetic / mock / fallback data is generated anywhere in this pipeline. If a
required real file is missing or a required dependency is not importable, the
caller fails loudly with explicit remediation instructions.

CLI
---
``python ml/training/real_data_contract.py --check``        validate deps + files
``python ml/training/real_data_contract.py --print-manifest`` print the manifest

Only stdlib imports are permitted at module top (per the v3 universal CLI rule),
so ``--help`` works on a fresh checkout with no geospatial/ML packages installed.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DataMissingError(RuntimeError):
    """Raised when one or more required real-data files are absent.

    The exception message lists every missing path together with download URL,
    purpose, citation and the exact local filename/pattern it must satisfy.
    """

    def __init__(self, missing: list["FileSpec"]):
        self.missing = list(missing)
        super().__init__(self._format())

    def _format(self) -> str:
        lines = [
            "Real-data contract violated — the following required inputs are missing.",
            "No synthetic fallback is allowed in the v3 prediction pipeline.",
            "",
        ]
        for spec in self.missing:
            target = spec.path if spec.path else f"{spec.dir} (pattern: {spec.dir_pattern})"
            lines.append(f"  [{spec.key}] {spec.purpose}")
            lines.append(f"    expected: {target}")
            lines.append(f"    source:   {spec.source_org}")
            lines.append(f"    download: {spec.download_url}")
            lines.append(f"    cite:     {spec.citation}")
            lines.append("")
        lines.append("See docs/14_data_intake_manifest.md for step-by-step instructions.")
        return "\n".join(lines)


class DependencyMissingError(RuntimeError):
    """Raised when one or more required Python packages cannot be imported."""

    def __init__(self, missing: list[str]):
        self.missing = list(missing)
        cmd = "pip install -r ml/requirements.txt"
        msg = (
            "Required Python dependencies for the v3 prediction pipeline are "
            f"missing: {', '.join(missing)}.\n"
            f"Install them with:\n  {cmd}\n"
            "No silent feature-disabled fallback is allowed."
        )
        self.install_command = cmd
        super().__init__(msg)


# ---------------------------------------------------------------------------
# File specs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileSpec:
    key: str                       # short identifier, e.g. "boundaries"
    purpose: str                   # what this dataset is used for
    source_org: str                # organisation that publishes it
    download_url: str              # primary download page
    citation: str                  # short attribution string
    required: bool = True          # gate on the v3 pipeline
    path: Optional[Path] = None    # single-file targets
    dir: Optional[Path] = None     # directory targets (alongside dir_pattern)
    dir_pattern: Optional[str] = None  # glob pattern relative to dir
    common_problems: tuple[str, ...] = field(default_factory=tuple)

    def is_present(self) -> bool:
        if self.path is not None:
            return self.path.exists() and self.path.stat().st_size > 0
        if self.dir is not None:
            if not self.dir.exists():
                return False
            return any(self.dir.glob(self.dir_pattern or "*"))
        # Misconfigured spec — treat as missing so the user notices.
        return False


def _p(*parts: str) -> Path:
    return Path(*parts)


# ---------------------------------------------------------------------------
# The 8-row data manifest
# ---------------------------------------------------------------------------

REQUIRED_FILES: list[FileSpec] = [
    FileSpec(
        key="boundaries",
        purpose="District polygons for zonal stats, labels and district-day rows",
        source_org="HDX Pakistan Administrative Boundaries",
        download_url="https://data.humdata.org/dataset/cod-ab-pak",
        citation="HDX / COD-AB Pakistan (latest)",
        path=_p("data/real/raw/boundaries/pakistan_districts.geojson"),
        common_problems=(
            "If only shapefile is available, convert with: "
            "ogr2ogr -f GeoJSON pakistan_districts.geojson pakistan_districts.shp",
        ),
    ),
    FileSpec(
        key="flood_extents",
        purpose="Historical flood extent polygons — used as LABELS only, never features",
        source_org="HDX / UNOSAT Pakistan flood water extents",
        download_url="https://data.humdata.org/dataset?q=pakistan+flood+unosat",
        citation="UNITAR-UNOSAT Pakistan flood mapping products",
        path=_p("data/real/raw/flood_extents/unosat_flood_extents.geojson"),
        common_problems=(
            "Each feature must carry an event date in its properties (e.g. "
            "'event_date' or 'OBSERVED_AT'). Document the chosen key.",
        ),
    ),
    FileSpec(
        key="imerg_dir",
        purpose="Daily precipitation rasters (GeoTIFF) for rainfall features",
        source_org="NASA GPM IMERG",
        download_url="https://gpm.nasa.gov/data/imerg or via Google Earth Engine",
        citation="NASA GPM IMERG Final Run (latest available)",
        dir=_p("data/real/raw/rainfall_imerg"),
        dir_pattern="*.tif",
        common_problems=(
            "Filenames must contain a parseable date — recommended "
            "'imerg_YYYY-MM-DD.tif'. Confirm CRS is set; reproject if not EPSG:4326.",
        ),
    ),
    FileSpec(
        key="chirps_dir",
        purpose="Daily CHIRPS rainfall rasters for baseline/anomaly",
        source_org="UC Santa Barbara CHIRPS",
        download_url="https://www.chc.ucsb.edu/data/chirps",
        citation="Funk et al. 2015 CHIRPS",
        dir=_p("data/real/raw/rainfall_chirps"),
        dir_pattern="*.tif",
        common_problems=(
            "Daily CHIRPS arrives as .tif.gz; decompress before placing here.",
        ),
    ),
    FileSpec(
        key="glofas",
        purpose="Pre-aggregated district-day river discharge CSV (raw NetCDF NOT supported in v3)",
        source_org="Copernicus Emergency Management Service GloFAS",
        download_url="https://www.globalfloods.eu/ / Copernicus CDS",
        citation="Copernicus Emergency Management Service / GloFAS",
        path=_p("data/real/raw/glofas/glofas_district_daily.csv"),
        common_problems=(
            "Required columns: district_id, date, river_discharge_m3s, source.",
            "Optional: discharge_anomaly_pct (computed downstream if absent).",
        ),
    ),
    FileSpec(
        key="elevation",
        purpose="DEM raster for elevation and slope features",
        source_org="SRTM / Copernicus DEM",
        download_url="https://srtm.csi.cgiar.org/ or https://spacedata.copernicus.eu/",
        citation="USGS SRTM v3 / Copernicus DEM GLO-30",
        path=_p("data/real/raw/elevation/dem.tif"),
        common_problems=(
            "Mosaic individual tiles into a single GeoTIFF if needed.",
            "If --slope-raster is not provided, slope is derived on-the-fly from this DEM.",
        ),
    ),
    FileSpec(
        key="rivers",
        purpose="River network for distance-to-river and drainage density features",
        source_org="HydroSHEDS / HydroRIVERS",
        download_url="https://www.hydrosheds.org/products/hydrorivers",
        citation="Linke et al. 2019 / HydroRIVERS v1.0",
        path=_p("data/real/raw/rivers/hydrorivers_pakistan.geojson"),
        common_problems=(
            "Clip the global file to Pakistan before placing here to avoid loading the full HydroRIVERS dataset at runtime.",
        ),
    ),
    FileSpec(
        key="population",
        purpose="Population exposure (raster OR pre-aggregated district CSV)",
        source_org="WorldPop",
        download_url="https://hub.worldpop.org/geodata/listing?id=29",
        citation="WorldPop 2020 (100 m unconstrained)",
        path=_p("data/real/raw/population/worldpop_pakistan.tif"),
        common_problems=(
            "If the raster is unavailable, place a pre-aggregated CSV at "
            "data/real/raw/population/district_population_exposure.csv with columns: "
            "district_id, population_exposure_score, source.",
        ),
    ),
]


# ---------------------------------------------------------------------------
# Dependency contract
# ---------------------------------------------------------------------------

# Mapping of pip package name -> importable module name.
REQUIRED_DEPS: dict[str, str] = {
    "geopandas": "geopandas",
    "rasterio": "rasterio",
    "rasterstats": "rasterstats",
    "shapely": "shapely",
    "pyproj": "pyproj",
    "joblib": "joblib",
    "pyarrow": "pyarrow",
    "pandas": "pandas",
    "numpy": "numpy",
    "scikit-learn": "sklearn",
    "imbalanced-learn": "imblearn",
}


def validate_dependencies(deps: Optional[Iterable[str]] = None) -> None:
    """Try-import every required dep; raise DependencyMissingError if any fail."""
    missing: list[str] = []
    targets = list(deps) if deps is not None else list(REQUIRED_DEPS.keys())
    for pkg in targets:
        module = REQUIRED_DEPS.get(pkg, pkg)
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise DependencyMissingError(missing)


def list_required_files(required_keys: Optional[Iterable[str]] = None) -> list[FileSpec]:
    if required_keys is None:
        return [s for s in REQUIRED_FILES if s.required]
    keys = set(required_keys)
    return [s for s in REQUIRED_FILES if s.key in keys]


def validate_real_data_contract(
    required_keys: Optional[Iterable[str]] = None,
    strict: bool = True,
) -> dict:
    """Validate that the specified subset of required files is present.

    Each pipeline script passes only the keys it needs. ``required_keys=None``
    means: validate every file marked ``required=True`` in REQUIRED_FILES.
    """
    specs = list_required_files(required_keys)
    missing = [s for s in specs if not s.is_present()]
    if missing and strict:
        raise DataMissingError(missing)
    return {
        "checked": [s.key for s in specs],
        "missing": [s.key for s in missing],
        "ok": len(missing) == 0,
    }


def print_manifest_summary() -> None:
    print("PakFlood AI v3 — Real Data Intake Manifest")
    print("=" * 70)
    for spec in REQUIRED_FILES:
        target = spec.path if spec.path else f"{spec.dir} ({spec.dir_pattern})"
        print(f"[{spec.key:<14}] required={spec.required}")
        print(f"  purpose : {spec.purpose}")
        print(f"  expected: {target}")
        print(f"  source  : {spec.source_org}")
        print(f"  download: {spec.download_url}")
        print(f"  cite    : {spec.citation}")
        if spec.common_problems:
            for tip in spec.common_problems:
                print(f"  note    : {tip}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="real_data_contract",
        description=(
            "PakFlood AI v3 real-data contract. Validate that required Python "
            "dependencies and downloaded real-data files are present. Fails "
            "loudly with explicit remediation instructions when anything is "
            "missing. No synthetic fallback."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate dependencies and required-file contract for the full v3 "
            "pipeline. Exit non-zero if anything is missing."
        ),
    )
    mode.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print the full data-intake manifest and exit 0.",
    )
    parser.add_argument(
        "--keys",
        nargs="+",
        default=None,
        help=(
            "Optional subset of contract keys to check (e.g. boundaries "
            "imerg_dir). Defaults to all required keys."
        ),
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.print_manifest:
        print_manifest_summary()
        return 0

    # --check path: deps first, then files
    try:
        validate_dependencies()
    except DependencyMissingError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        report = validate_real_data_contract(required_keys=args.keys)
    except DataMissingError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print(f"OK — real-data contract satisfied. Checked: {report['checked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
