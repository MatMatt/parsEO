"""STAC helpers backed by ``pystac-client``.

This module mirrors the utilities in :mod:`parseo.stac_dataspace` but relies on
``pystac-client`` for STAC catalog traversal.  Use these helpers when the extra
features of ``pystac-client`` are required.  For a lightweight alternative that
only depends on the Python standard library see
:mod:`parseo.stac_dataspace`.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

def list_collections_client(base_url: str, *, deep: bool = False) -> list[str]:
    """Return collection IDs from a STAC API using ``pystac-client``.

    Parameters mirror :func:`parseo.stac_dataspace.list_collections_http` but
    this variant requires the optional ``pystac-client`` dependency.  It is
    suitable when more advanced STAC handling is needed, at the cost of pulling
    in the external library.
    """
    try:
        from pystac_client import Client
    except Exception as exc:  # pragma: no cover - exercised when dependency missing
        raise SystemExit(
            "pystac-client is required for list_collections_client"
        ) from exc

    client = Client.open(base_url)
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


# Backwards compatible alias mirroring :mod:`parseo.stac_dataspace`
list_collections = list_collections_client


def search_stac_and_download(
    *,
    stac_url: str,
    collections: list[str],
    bbox: list[float] | tuple[float, float, float, float],
    datetime: str,
    dest_dir: str | Path,
) -> Path:
    """Download the first asset matching a STAC search.

    The search is performed via :mod:`pystac-client` and the asset is retrieved
    with :mod:`requests`. ``dest_dir`` is created if needed and the path to the
    downloaded file is returned.
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

    client = Client.open(stac_url)
    search = client.search(collections=collections, bbox=bbox, datetime=datetime)
    for item in search.get_items():
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
            with requests.get(href, stream=True) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
            return dest_path
    raise SystemExit("No matching assets found")
