import pytest
import parseo.stac_dataspace as sd


def test_list_collections_custom_base_url(monkeypatch):
    urls = []

    def fake_read_json(url):
        urls.append(url)
        return {"collections": [{"id": "abc"}]}

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    out = sd.list_collections(base_url="http://x")
    assert urls == ["http://x/collections"]
    assert out == ["abc"]


def test_iter_asset_filenames_custom_base_url(monkeypatch):
    urls = []

    def fake_read_json(url):
        urls.append(url)
        return {
            "features": [
                {"assets": {"a": {"href": "http://files/file1.tif"}}}
            ]
        }

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    out = list(sd.iter_asset_filenames("C1", base_url="http://y", limit=1))
    assert urls == ["http://y/collections/C1/items?limit=1"]
    assert out == ["file1.tif"]


def test_sample_collection_filenames_custom_base_url(monkeypatch):
    called = {}

    def fake_iter(collection_id, *, base_url, limit=100):
        called["collection"] = collection_id
        called["base_url"] = base_url
        return iter(["f1", "f2", "f3"])

    monkeypatch.setattr(sd, "iter_asset_filenames", fake_iter)
    res = sd.sample_collection_filenames("COL", 2, base_url="http://z")
    assert called == {"collection": "COL", "base_url": "http://z"}
    assert res == ["f1", "f2"]


def test_list_collections_requires_base_url():
    with pytest.raises(TypeError):
        sd.list_collections()
