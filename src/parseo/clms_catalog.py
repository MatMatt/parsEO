"""Utilities to discover Copernicus Land Monitoring Service (CLMS) products.

This module provides a tiny HTML/XML scraper for the public CLMS dataset
catalog (https://land.copernicus.eu/en/dataset-catalog) and the portal
sitemap (https://land.copernicus.eu/en/portal-sitemap).  It exposes two
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
import os
from typing import Iterable
from typing import List
from typing import Union
from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.request import urlopen
from xml.etree import ElementTree


def _strip_namespace(tag: str) -> str:
    """Return the local XML tag name without namespace information."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _title_from_url(url: str) -> str:
    """Best-effort conversion of a dataset URL into a human readable label."""
    parsed = urlparse(url)
    path = unquote(parsed.path or "")
    path = path.strip("/")
    if not path:
        return url
    segment = path.split("/")[-1]
    segment = segment.strip()
    if not segment:
        return url
    label = segment.replace("-", " ").replace("_", " ").strip()
    return label or url


def _parse_portal_sitemap(xml: str) -> List[str]:
    """Extract dataset titles from the CLMS portal sitemap XML document."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []

    titles: List[str] = []
    seen: set[str] = set()

    for url_node in root.iter():
        if _strip_namespace(url_node.tag) != "url":
            continue

        loc_text = ""
        for child in url_node:
            if _strip_namespace(child.tag) == "loc" and child.text:
                loc_text = child.text.strip()
                break

        title_text = ""
        for descendant in url_node.iter():
            if descendant is url_node:
                continue
            if _strip_namespace(descendant.tag) == "title" and descendant.text:
                candidate = descendant.text.strip()
                if candidate:
                    title_text = candidate
                    break

        if not title_text and loc_text:
            title_text = _title_from_url(loc_text)

        if not title_text:
            continue

        normalized = " ".join(title_text.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            titles.append(normalized)

    return titles


class _DatasetTitleParser(HTMLParser):
    """Internal helper to extract dataset titles from the catalog HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self.titles: List[str] = []

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, Union[str, None]]]) -> None:
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
    """Parse raw HTML or XML from the CLMS catalog and return dataset titles."""
    parser = _DatasetTitleParser()
    parser.feed(html)
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for title in parser.titles:
        if title not in seen:
            seen.add(title)
            out.append(title)
    if out:
        return out
    return _parse_portal_sitemap(html)


def fetch_clms_products(url: Union[str, None] = None) -> List[str]:
    """Fetch the CLMS dataset catalog and return all product titles.

    If ``url`` is not provided, the environment variable
    ``CLMS_DATASET_CATALOG_URL`` is consulted.  A :class:`ValueError` is raised
    when no URL is available.
    """
    if url is None:
        url = os.getenv("CLMS_DATASET_CATALOG_URL")
        if url is None:
            raise ValueError(
                "Catalog URL not provided. Set CLMS_DATASET_CATALOG_URL or pass the 'url' parameter."
            )
    with urlopen(url) as resp:  # noqa: S310 - controlled URL
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, "replace")
    return parse_html(html)
