"""STAC helper utilities.

Functions in this module either use :mod:`pystac-client` for interacting with
remote STAC APIs or rely solely on the Python standard library for lightweight
catalog scraping.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import urllib.request
import xml.etree.ElementTree as ET
import datetime

def _norm_base(base_url: str) -> str:
    """Return ``base_url`` with exactly one trailing slash."""
    return base_url.rstrip("/") + "/"

# Mapping of common collection aliases to their official STAC IDs.
#
# Lookups are performed case-insensitively by normalizing the user supplied
# identifier with ``str.upper`` and checking against these keys.  The mapped
# values retain the canonical casing required by the STAC API.
STAC_ID_ALIASES: dict[str, str] = {
    "SENTINEL2_L2A": "sentinel-2-l2a",
    "S2_L2A": "sentinel-2-l2a",
    "SENTINEL2_L1C": "sentinel-2-l1c",
    "S2_L1C": "sentinel-2-l1c",
}


def _temporal_midpoint(
    start: datetime.datetime, end: datetime.datetime | None = None
) -> datetime.datetime:
    """Return the midpoint between ``start`` and ``end``.

    ``end`` defaults to the current UTC time. Both datetimes must be
    timezone-aware.
    """

    if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
        raise ValueError("start must be timezone-aware")
    if end is None:
        end = datetime.datetime.now(datetime.UTC)
    if end.tzinfo is None or end.tzinfo.utcoffset(end) is None:
        raise ValueError("end must be timezone-aware")
    return start + (end - start) / 2

def _norm_collection_id(collection_id: str) -> str:
    """Return the official STAC collection ID for ``collection_id``."""
    cid_upper = collection_id.upper()
    return STAC_ID_ALIASES.get(cid_upper, collection_id)

def list_collections_client(base_url: str, *, deep: bool = False) -> list[str]:
    """Return collection IDs from a STAC API using ``pystac-client``.

    When ``deep`` is ``True`` the traversal follows child catalogs in addition
    to the top-level ``/collections`` endpoint.
    """
    try:
        from pystac_client import Client
    except Exception as exc:  # pragma: no cover - exercised when dependency missing
        raise SystemExit(
            "pystac-client is required for list_collections_client"
        ) from exc

    base = _norm_base(base_url)
    client = Client.open(base)
    collections = {c.id for c in client.get_collections()}
    if not deep:
        return sorted(collections)

    # Breadth-first traversal of child catalogs.
    to_visit = list(client.get_children())
    visited: set[str] = set()
    while to_visit:
        child = to_visit.pop()
        href = getattr(child, "href", None) or getattr(child, "target", None)
        if not href or href in visited:
            continue
        visited.add(href)
        sub_client = Client.open(href)
        collections.update(c.id for c in sub_client.get_collections())
        to_visit.extend(sub_client.get_children())

    return sorted(collections)


# Backwards compatible alias for ``list_collections_client``
list_collections = list_collections_client


def search_stac_and_download(
    *,
    stac_url: str,
    collections: str | list[str],
    bbox: list[float] | tuple[float, float, float, float],
    datetime: str,
    dest_dir: str | Path,
) -> Path:
    """Download the first asset matching a STAC search.

    The search is performed via :mod:`pystac-client` and the asset is retrieved
    with :mod:`requests`. ``dest_dir`` is created if needed and the path to the
    downloaded file is returned.

    ``collections`` may be a single string or a list of strings. A lone
    string will be wrapped in a list before querying. ``datetime`` should be
    an ISO 8601 string with timezone information, optionally expressing a
    range (e.g., ``2024-01-01T00:00:00Z/2024-01-02T00:00:00Z``).

    Raises
    ------
    FileNotFoundError
        If the STAC search yields no downloadable assets or all downloads
        fail.
    """

    try:
        from pystac_client import Client
    except Exception as exc:  # pragma: no cover - exercised when dependency missing
        raise SystemExit(
            "pystac-client is required for search_stac_and_download"
        ) from exc

    try:
        import requests
    except Exception as exc:  # pragma: no cover - exercised when dependency missing
        raise SystemExit("requests is required for search_stac_and_download") from exc
    if isinstance(collections, str):
        collections = [collections]

    collections = [_norm_collection_id(c) for c in collections]

    stac_url = _norm_base(stac_url)
    client = Client.open(stac_url)
    search = client.search(collections=collections, bbox=bbox, datetime=datetime)
    for item in search.items():
        for asset in item.assets.values():
            href = getattr(asset, "href", None)
            if not href:
                continue
            name = getattr(asset, "title", None)
            if not name:
                name = Path(urlparse(href).path).name
            dest_dir_path = Path(dest_dir)
            dest_dir_path.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir_path / name
            try:
                with requests.get(href, stream=True) as resp:
                    resp.raise_for_status()
                    with open(dest_path, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                fh.write(chunk)
                return dest_path
            except requests.HTTPError:
                continue
    raise FileNotFoundError("No matching assets found")


def scrape_catalog(root: str | Path, *, limit: int = 100) -> list[dict[str, str]]:
    """Recursively walk a STAC catalog and gather metadata for data assets.

    Parameters
    ----------
    root:
        Path or URL to a STAC catalog, collection or item.  When a directory is
        supplied ``catalog.json`` is assumed to be the starting point.
    limit:
        Maximum number of asset entries to return.

    Returns
    -------
    list of dict
        Each dictionary contains the asset ``filename`` plus any of the fields
        ``id``, ``product_type``, ``datetime``, ``tile`` and ``orbit`` extracted
        from adjacent metadata files. When ``start_datetime`` and
        ``end_datetime`` are available, ``datetime`` is set to their temporal
        midpoint, using the current UTC time if only ``start_datetime`` is
        present.
    """

    results: list[dict[str, str]] = []

    def is_url(path: str) -> bool:
        return urlparse(path).scheme in {"http", "https"}

    def resolve(base: str, href: str) -> str:
        if is_url(base):
            base_dir = base if base.endswith("/") else base.rsplit("/", 1)[0] + "/"
            return urljoin(base_dir, href)
        base_path = Path(base)
        if base_path.is_dir():
            return str(base_path / href)
        return str(base_path.parent / href)

    def read_text(path: str) -> str:
        if is_url(path):
            with urllib.request.urlopen(path) as resp:  # type: ignore[call-arg]
                return resp.read().decode("utf-8")
        return Path(path).read_text(encoding="utf-8")

    def parse_metadata(path: str) -> dict[str, str]:
        try:
            text = read_text(path)
        except Exception:
            return {}
        out: dict[str, str] = {}
        if path.lower().endswith(".json"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return {}

            def grab(*names: str) -> str | None:
                for name in names:
                    if name in data:
                        return data[name]
                    if "properties" in data and name in data["properties"]:
                        return data["properties"][name]
                return None

            out_fields = {
                "id": grab("id", "ID"),
                "product_type": grab("product_type", "productType"),
                "datetime": grab("datetime", "date"),
                "tile": grab("tile", "mgrs:tile", "s2:mgrs_tile"),
                "orbit": grab("orbit", "s2:orbit"),
            }
            if not out_fields.get("datetime"):
                start = grab("start_datetime")
                end = grab("end_datetime")
                if start:
                    try:
                        start_dt = datetime.datetime.fromisoformat(
                            start.replace("Z", "+00:00")
                        )
                        end_dt = (
                            datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
                            if end
                            else None
                        )
                        out_fields["datetime"] = _temporal_midpoint(
                            start_dt, end_dt
                        ).isoformat().replace("+00:00", "Z")
                    except Exception:
                        pass
            return {k: v for k, v in out_fields.items() if v}

        # XML parsing
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return {}

        def find_text(*names: str) -> str | None:
            for name in names:
                elem = root.find(f".//{name}")
                if elem is not None and elem.text:
                    return elem.text
            return None

        out_fields = {
            "id": find_text("id", "ID"),
            "product_type": find_text("product_type", "productType"),
            "datetime": find_text("datetime", "date"),
            "tile": find_text("tile", "TILE"),
            "orbit": find_text("orbit", "ORBIT"),
        }
        if not out_fields.get("datetime"):
            start = find_text("start_datetime")
            end = find_text("end_datetime")
            if start:
                try:
                    start_dt = datetime.datetime.fromisoformat(
                        start.replace("Z", "+00:00")
                    )
                    end_dt = (
                        datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
                        if end
                        else None
                    )
                    out_fields["datetime"] = _temporal_midpoint(
                        start_dt, end_dt
                    ).isoformat().replace("+00:00", "Z")
                except Exception:
                    pass
        return {k: v for k, v in out_fields.items() if v}

    def scrape(node: str) -> None:
        if len(results) >= limit:
            return
        text = read_text(node)
        data = json.loads(text)
        if data.get("type") == "Feature":
            assets = data.get("assets", {})
            meta: dict[str, str] = {}
            for asset in assets.values():
                href = asset.get("href")
                if not href:
                    continue
                if href.lower().endswith((".json", ".xml", "manifest.safe", ".safe")):
                    meta.update(parse_metadata(resolve(node, href)))
            for asset in assets.values():
                href = asset.get("href")
                if not href or href.lower().endswith((".json", ".xml", "manifest.safe", ".safe")):
                    continue
                filename = Path(urlparse(href).path).name
                entry = {"filename": filename}
                entry.update(meta)
                results.append(entry)
                if len(results) >= limit:
                    return
        else:
            for link in data.get("links", []):
                if link.get("rel") in {"child", "item"}:
                    href = link.get("href")
                    if href:
                        scrape(resolve(node, href))
                        if len(results) >= limit:
                            return

    start = str(root)
    if not is_url(start):
        p = Path(start)
        if p.is_dir():
            start = str(p / "catalog.json")
    scrape(start)
    return results


def sample_collection_filenames(
    collection: str,
    samples: int = 5,
    *,
    base_url: str,
    asset_role: str | None = None,
) -> dict[str, list[str]]:
    """Return sample asset filenames from a STAC collection.
    Users should call :func:`scrape_catalog` instead.
    """

    try:  # pragma: no cover - exercised when dependency missing
        from pystac_client import Client
    except Exception as exc:  # pragma: no cover - same as above
        raise SystemExit(
            "pystac-client is required for sample_collection_filenames"
        ) from exc

    cid = _norm_collection_id(collection)
    base = _norm_base(base_url)
    client = Client.open(base)

    search = client.search(collections=[cid], max_items=samples)
    results: list[str] = []

    for item in search.items():
        asset = None
        if asset_role:
            for a in item.assets.values():
                roles = a.roles or []
                if asset_role in roles:
                    asset = a
                    break
        if asset is None and item.assets:
            asset = next(iter(item.assets.values()))
        if not asset:
            continue
        href = asset.href or ""
        name = asset.title or Path(urlparse(href).path).name
        results.append(name)

    return {cid: results}
