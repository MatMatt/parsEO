"""Utilities to discover Copernicus Land Monitoring Service (CLMS) products.

This module provides a tiny HTML scraper for the public CLMS dataset
catalog (https://land.copernicus.eu/en/dataset-catalog).  It exposes two
functions:

- :func:`parse_html` which extracts dataset titles from a HTML page.
- :func:`fetch_clms_products` which downloads the catalog page and returns
  the list of dataset names.

The scraper is intentionally lightweight and relies solely on the Python
standard library, making it suitable for offline environments.  Network
access is only required when calling :func:`fetch_clms_products`.
"""
from __future__ import annotations

from html.parser import HTMLParser
from typing import Iterable, List
from urllib.request import urlopen

DATASET_CATALOG_URL = "https://land.copernicus.eu/en/dataset-catalog"


class _DatasetTitleParser(HTMLParser):
    """Internal helper to extract dataset titles from the catalog HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self.titles: List[str] = []

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, str | None]]) -> None:
        if tag == "h2":
            attrs_dict = dict(attrs)
            css = attrs_dict.get("class", "") or ""
            if "dataset-title" in css:
                self._capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._capture:
            self._capture = False

    def handle_data(self, data: str) -> None:
        if self._capture:
            text = data.strip()
            if text:
                self.titles.append(text)


def parse_html(html: str) -> List[str]:
    """Parse raw HTML from the CLMS catalog and return dataset titles."""
    parser = _DatasetTitleParser()
    parser.feed(html)
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for title in parser.titles:
        if title not in seen:
            seen.add(title)
            out.append(title)
    return out


def fetch_clms_products(url: str = DATASET_CATALOG_URL) -> List[str]:
    """Fetch the CLMS dataset catalog and return all product titles.

    Parameters
    ----------
    url:
        Optional catalog URL. The default points to the official CLMS
        dataset catalog.
    """
    with urlopen(url) as resp:  # noqa: S310 - controlled URL
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, "replace")
    return parse_html(html)
