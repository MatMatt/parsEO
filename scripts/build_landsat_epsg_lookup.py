"""Generate the Landsat path/row to EPSG lookup table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd


def derive_epsg(path: int, row: int, geometry) -> str:
    centroid = geometry.centroid
    lon = centroid.x
    lat = centroid.y
    zone = int((lon + 180) // 6) + 1
    prefix = "326" if lat >= 0 else "327"
    return f"EPSG:{prefix}{zone:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wrs_shapefile", type=Path, help="Path to WRS-2 descending shapefile")
    parser.add_argument("output", type=Path, help="Destination JSON file")
    args = parser.parse_args()

    wrs = gpd.read_file(args.wrs_shapefile)
    records = {}
    for _, record in wrs.iterrows():
        key = f"{int(record['PATH']):03d}{int(record['ROW']):03d}"
        epsg = derive_epsg(int(record["PATH"]), int(record["ROW"]), record.geometry)
        records[key] = epsg

    args.output.write_text(json.dumps(dict(sorted(records.items())), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
