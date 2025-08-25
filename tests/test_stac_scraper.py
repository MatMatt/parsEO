import sys
import types
from pathlib import Path

import pytest
import parseo.stac_scraper as ss


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
    @staticmethod
    def open(url):
        assert url == "http://base/"
        return FakeClientSearch()

    def search(self, **kwargs):
        assert kwargs["collections"] == ["C"]
        assert kwargs["bbox"] == [0, 0, 1, 1]
        assert kwargs["datetime"] == "2024"
        return FakeSearch()



@pytest.mark.parametrize("base_url", ["http://base", "http://base/"])
def test_list_collections_alias(monkeypatch, base_url):
    fake_pc = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)
    out = ss.list_collections(base_url)
    assert out == ["A", "B"]



@pytest.mark.parametrize("collections", [["C"], "C"])
@pytest.mark.parametrize("stac_url", ["http://base", "http://base/"])
def test_search_stac_and_download(monkeypatch, tmp_path, collections, stac_url):
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
