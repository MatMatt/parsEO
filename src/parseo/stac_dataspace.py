"""Helpers for querying STAC APIs.

The Copernicus Data Space Ecosystem STAC root URL is available as
``CDSE_STAC_URL`` for convenience but is not used as a default.  All helper
functions require explicitly passing the ``base_url`` of the STAC service.
"""
from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urljoin
import urllib.error
import urllib.request
import json
import itertools

CDSE_STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/"


# Mapping of common collection aliases to their official STAC IDs.
# Keys are case-insensitive aliases as they might appear in user commands.
STAC_ID_ALIASES: dict[str, str] = {
    "SENTINEL2_L2A": "sentinel-2-l2a",
}


def _norm_collection_id(collection_id: str) -> str:
    """Return the official STAC collection ID for ``collection_id``."""
    return STAC_ID_ALIASES.get(collection_id.upper(), collection_id)


def _norm_base(base_url: str) -> str:
    """Return ``base_url`` with exactly one trailing slash."""
    return base_url.rstrip("/") + "/"


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:  # type: ignore[call-arg]
        return json.load(resp)


def list_collections(base_url: str) -> list[str]:
    """Return available collection IDs from the STAC API."""
    base = _norm_base(base_url)
    url = urljoin(base, "collections")
    try:
        data = _read_json(url)
    except urllib.error.HTTPError as err:
        raise SystemExit(f"HTTP error {err.code} for {err.geturl()}") from err
    return [c["id"] for c in data.get("collections", [])]


def iter_asset_filenames(
    collection_id: str,
    *,
    base_url: str,
    limit: int = 100,
) -> Iterable[str]:
    """Yield asset filenames from items of a collection."""
    base = _norm_base(base_url)
    url = urljoin(base, f"collections/{collection_id}/items?limit={limit}")
    try:
        data = _read_json(url)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise SystemExit(
                f"Collection '{collection_id}' not found at {base}. "
                "Use `parseo stac-sample <collection> --stac-url <url>` with a valid collection ID."
            ) from err
        raise SystemExit(f"HTTP error {err.code} for {err.geturl()}") from err
    for feat in data.get("features", []):
        assets = feat.get("assets", {})
        for asset in assets.values():
            href = asset.get("href")
            if not href:
                continue
            yield href.rstrip("/").split("/")[-1]


def iter_collection_tree(
    collection_id: str,
    *,
    base_url: str,
    limit: int = 100,
) -> Iterable[tuple[str, str]]:
    """Yield ``(collection_id, filename)`` pairs for all leaf collections.

    The function follows ``links`` with ``rel="child"`` starting from
    ``collection_id`` until it reaches leaf collections.  For each leaf it
    yields filenames from :func:`iter_asset_filenames`.
    """
    base = _norm_base(base_url)
    url = urljoin(base, f"collections/{collection_id}")
    try:
        data = _read_json(url)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise SystemExit(
                f"Collection '{collection_id}' not found at {base}. "
                "Use `parseo stac-sample <collection> --stac-url <url>` with a valid collection ID."
            ) from err
        raise SystemExit(f"HTTP error {err.code} for {err.geturl()}") from err

    children = [
        link.get("href", "").rstrip("/").split("/")[-1]
        for link in data.get("links", [])
        if link.get("rel") == "child"
    ]

    if children:
        for child in children:
            yield from iter_collection_tree(child, base_url=base, limit=limit)
    else:
        for fn in itertools.islice(
            iter_asset_filenames(collection_id, base_url=base, limit=limit), limit
        ):
            yield collection_id, fn


def sample_collection_filenames(
    collection_id: str,
    samples: int = 5,
    *,
    base_url: str,
) -> dict[str, list[str]]:
    """Return ``samples`` filenames for each leaf collection.

    ``collection_id`` may be the official STAC ID or any alias defined in
    :data:`STAC_ID_ALIASES`.  When ``collection_id`` has child collections, a
    sample is collected from each leaf.
    """
    collection_id = _norm_collection_id(collection_id)
    out: dict[str, list[str]] = {}
    for cid, fn in iter_collection_tree(collection_id, base_url=base_url, limit=samples):
        lst = out.setdefault(cid, [])
        if len(lst) < samples:
            lst.append(fn)
    return out
