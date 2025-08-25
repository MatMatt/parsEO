import sys
import types
import json
from pathlib import Path
import datetime

import pytest
import parseo.stac_scraper as ss

stac_url = "http://base"


@pytest.mark.parametrize(
    "alias, expected",
    [
        ("sentinel-2-l2a", "sentinel-2-l2a"),
        ("s2_l2a", "sentinel-2-l2a"),
        ("sentinel-2-l1c", "sentinel-2-l1c"),
        ("sentinel2_l1c", "sentinel-2-l1c"),
    ],
)
def test_norm_collection_id_aliases(alias, expected):
    assert ss._norm_collection_id(alias) == expected


class FakeCollection:
    def __init__(self, id):
        self.id = id


class FakeClient:
    @staticmethod
    def open(url):
        assert url == "http://base/"
        return FakeClient()

    def get_collections(self):
        return [FakeCollection("A"), FakeCollection("B")]

    def get_children(self):
        return []


class FakeAsset:
    def __init__(self, href, title=None):
        self.href = href
        self.title = title


class FakeItem:
    def __init__(self):
        self.assets = {"x": FakeAsset("http://example.com/file.bin", title="file.bin")}


class FakeSearch:
    def items(self):
        yield FakeItem()


class FakeClientSearch(FakeClient):
    expected: list[str] = []

    @staticmethod
    def open(url):
        assert url == "http://base/"
        return FakeClientSearch()

    def search(self, **kwargs):
        assert kwargs["collections"] == self.expected
        assert kwargs["bbox"] == [0, 0, 1, 1]
        assert kwargs["datetime"] == "2024"
        return FakeSearch()



@pytest.mark.parametrize("base_url", ["http://base", "http://base/"])
def test_list_collections_alias(monkeypatch, base_url):
    fake_pc = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)
    out = ss.list_collections(base_url)
    assert out == ["A", "B"]



@pytest.mark.parametrize("collections", [["s2_l2a"], "s2_l2a"])
def test_search_stac_and_download(monkeypatch, tmp_path, collections):
    FakeClientSearch.expected = ["sentinel-2-l2a"]

    fake_pc = types.SimpleNamespace(Client=FakeClientSearch)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=8192):
            yield b"data"

    def fake_get(url, stream=True):
        assert url == "http://example.com/file.bin"
        return FakeResp()

    fake_requests = types.SimpleNamespace(get=fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    dest = tmp_path / "dl"
    path = ss.search_stac_and_download(
        stac_url=stac_url,
        collections=collections,
        bbox=[0, 0, 1, 1],
        datetime="2024",
        dest_dir=dest,
    )
    assert path == dest / "file.bin"
    assert path.read_bytes() == b"data"


def test_search_stac_and_download_http_error(monkeypatch, tmp_path):
    FakeClientSearch.expected = ["C"]
    fake_pc = types.SimpleNamespace(Client=FakeClientSearch)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)

    class HTTPError(Exception):
        pass

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def raise_for_status(self):
            raise HTTPError("404")

        def iter_content(self, chunk_size=8192):
            yield b"data"

    def fake_get(url, stream=True):
        return FakeResp()

    fake_requests = types.SimpleNamespace(get=fake_get, HTTPError=HTTPError)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    with pytest.raises(FileNotFoundError):
        ss.search_stac_and_download(
            stac_url="http://base",
            collections=["C"],
            bbox=[0, 0, 1, 1],
            datetime="2024",
            dest_dir=tmp_path,
        )


def test_scrape_catalog(tmp_path):
    catalog = {
        "links": [
            {"rel": "item", "href": "item1.json"},
            {"rel": "item", "href": "item2.json"},
        ]
    }
    item1 = {
        "type": "Feature",
        "assets": {
            "data": {"href": "data1.tif"},
            "meta": {"href": "data1.json"},
        },
    }
    item2 = {
        "type": "Feature",
        "assets": {
            "data": {"href": "data2.tif"},
            "meta": {"href": "data2.xml"},
        },
    }
    (tmp_path / "catalog.json").write_text(json.dumps(catalog))
    (tmp_path / "item1.json").write_text(json.dumps(item1))
    (tmp_path / "item2.json").write_text(json.dumps(item2))
    (tmp_path / "data1.json").write_text(
        json.dumps(
            {
                "id": "ID1",
                "product_type": "PT1",
                "datetime": "2024-01-01",
                "tile": "T1",
                "orbit": "O1",
            }
        )
    )
    (tmp_path / "data2.xml").write_text(
        "<root><id>ID2</id><product_type>PT2</product_type>"
        "<datetime>2024-02-02</datetime><tile>T2</tile><orbit>O2</orbit></root>"
    )

    out = ss.scrape_catalog(tmp_path)
    assert out == [
        {
            "filename": "data1.tif",
            "id": "ID1",
            "product_type": "PT1",
            "datetime": "2024-01-01",
            "tile": "T1",
            "orbit": "O1",
        },
        {
            "filename": "data2.tif",
            "id": "ID2",
            "product_type": "PT2",
            "datetime": "2024-02-02",
            "tile": "T2",
            "orbit": "O2",
        },
    ]

    limited = ss.scrape_catalog(tmp_path, limit=1)
    assert len(limited) == 1


def test_temporal_midpoint_requires_timezone():
    start = datetime.datetime(2024, 1, 1)
    end = datetime.datetime(2024, 1, 2, tzinfo=datetime.UTC)
    with pytest.raises(ValueError):
        ss._temporal_midpoint(start, end)


def test_scrape_catalog_midpoint(tmp_path):
    catalog = {"links": [{"rel": "item", "href": "item.json"}]}
    item = {
        "type": "Feature",
        "assets": {"data": {"href": "data.tif"}, "meta": {"href": "meta.json"}},
    }
    meta = {
        "id": "ID3",
        "start_datetime": "2024-03-01T00:00:00Z",
        "end_datetime": "2024-03-03T00:00:00Z",
    }
    (tmp_path / "catalog.json").write_text(json.dumps(catalog))
    (tmp_path / "item.json").write_text(json.dumps(item))
    (tmp_path / "meta.json").write_text(json.dumps(meta))

    out = ss.scrape_catalog(tmp_path)
    assert out == [
        {
            "filename": "data.tif",
            "id": "ID3",
            "datetime": "2024-03-02T00:00:00Z",
        }
    ]
