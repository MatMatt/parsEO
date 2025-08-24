"""Helpers for querying STAC APIs.

The Copernicus Data Space Ecosystem STAC root URL is available as
``CDSE_STAC_URL`` for convenience but is not used as a default.  All helper
functions require explicitly passing the ``base_url`` of the STAC service.
"""
from __future__ import annotations

from typing import Iterable, List
from urllib.parse import urljoin
import urllib.request
import json
import itertools

CDSE_STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/"


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:  # type: ignore[call-arg]
        return json.load(resp)


def list_collections(base_url: str) -> List[str]:
    """Return available collection IDs from the STAC API."""
    data = _read_json(urljoin(base_url, "collections"))
    return [c["id"] for c in data.get("collections", [])]


def iter_asset_filenames(
    collection_id: str,
    *,
    base_url: str,
    limit: int = 100,
) -> Iterable[str]:
    """Yield asset filenames from items of a collection."""
    url = urljoin(base_url, f"collections/{collection_id}/items?limit={limit}")
    data = _read_json(url)
    for feat in data.get("features", []):
        assets = feat.get("assets", {})
        for asset in assets.values():
            href = asset.get("href")
            if not href:
                continue
            yield href.rstrip("/").split("/")[-1]


def sample_collection_filenames(
    collection_id: str,
    samples: int = 5,
    *,
    base_url: str,
) -> List[str]:
    """Return ``samples`` filenames from the given collection."""
    return list(
        itertools.islice(
            iter_asset_filenames(collection_id, base_url=base_url), samples
        )
    )
