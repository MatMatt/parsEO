import sys
import types

import pytest
import parseo.stac_scraper as ss


class FakeCollection:
    def __init__(self, id):
        self.id = id


class FakeClient:
    @staticmethod
    def open(url):
        assert url == "http://base"
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
        assert url == "http://base"
        return FakeClientSearch()

    def search(self, **kwargs):
        assert kwargs["collections"] == ["C"]
        assert kwargs["bbox"] == [0, 0, 1, 1]
        assert kwargs["datetime"] == "2024"
        return FakeSearch()



def test_list_collections_client(monkeypatch):
    fake_pc = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)
    out = ss.list_collections_client("http://base")
    assert out == ["A", "B"]



def test_search_stac_and_download(monkeypatch, tmp_path):
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
        stac_url="http://base",
        collections=["C"],
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


def test_missing_pystac_client(monkeypatch, tmp_path):
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pystac_client":
            raise ModuleNotFoundError
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        ss.list_collections_client("http://base")
    with pytest.raises(ImportError):
        ss.search_stac_and_download(
            stac_url="http://base",
            collections=["C"],
            bbox=[0, 0, 1, 1],
            datetime="2024",
            dest_dir=tmp_path,
        )


def test_missing_requests(monkeypatch, tmp_path):
    fake_pc = types.SimpleNamespace(Client=FakeClientSearch)
    monkeypatch.setitem(sys.modules, "pystac_client", fake_pc)

    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ModuleNotFoundError
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        ss.search_stac_and_download(
            stac_url="http://base",
            collections=["C"],
            bbox=[0, 0, 1, 1],
            datetime="2024",
            dest_dir=tmp_path,
        )
