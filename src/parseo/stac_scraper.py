"""STAC helpers backed by ``pystac-client``.

This module mirrors the utilities in :mod:`parseo.stac_dataspace` but relies on
``pystac-client`` for STAC catalog traversal.  Use these helpers when the extra
features of ``pystac-client`` are required.  For a lightweight alternative that
only depends on the Python standard library see
:mod:`parseo.stac_dataspace`.
"""
from __future__ import annotations

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
