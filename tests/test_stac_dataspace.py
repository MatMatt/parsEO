import pytest
import urllib.error
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


def test_list_collections_deep(monkeypatch):
    calls = []

    responses = {
        "http://x/collections": {"collections": [{"id": "top"}]},
        "http://x/": {
            "links": [
                {"rel": "child", "href": "A"},
                {"rel": "child", "href": "cat"},
            ]
        },
        "http://x/A": {"type": "Collection", "id": "A"},
        "http://x/cat": {"links": [{"rel": "child", "href": "B"}]},
        "http://x/cat/B": {"type": "Collection", "id": "B"},
    }

    def fake_read_json(url):
        calls.append(url)
        return responses[url]

    monkeypatch.setattr(sd, "_read_json", fake_read_json)

    out = sd.list_collections(base_url="http://x", deep=True)
    assert set(out) == {"top", "A", "B"}
    assert set(calls) == set(responses)


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


def test_iter_asset_filenames_resolves_templates(monkeypatch):
    def fake_read_json(url):
        return {
            "features": [
                {
                    "properties": {"name": "F", "suffix": "tif"},
                    "assets": {
                        "templated": {"href": "http://files/$name.$suffix"},
                        "missing": {"href": "http://files/$missing.$suffix"},
                        "plain": {"href": "http://files/plain.tif"},
                    },
                }
            ]
        }

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    out = list(sd.iter_asset_filenames("C1", base_url="http://y"))
    assert out == ["F.tif", "plain.tif"]


def test_sample_collection_filenames_custom_base_url(monkeypatch):
    called = {}

    def fake_iter_tree(collection_id, *, base_url, limit):
        called["collection"] = collection_id
        called["base_url"] = base_url
        called["limit"] = limit
        yield (collection_id, "f1")
        yield (collection_id, "f2")
        yield (collection_id, "f3")

    monkeypatch.setattr(sd, "iter_collection_tree", fake_iter_tree)
    res = sd.sample_collection_filenames("COL", 2, base_url="http://z")
    assert called == {
        "collection": "COL",
        "base_url": "http://z",
        "limit": 2,
    }
    assert res == {"COL": ["f1", "f2"]}


def test_sample_collection_filenames_alias(monkeypatch):
    calls = []

    def fake_iter_tree(collection_id, *, base_url, limit):
        calls.append(collection_id)
        yield (collection_id, "a")
        yield (collection_id, "b")

    monkeypatch.setattr(sd, "iter_collection_tree", fake_iter_tree)
    alias_res = sd.sample_collection_filenames(
        "SENTINEL2_L2A", base_url="http://z"
    )
    official_res = sd.sample_collection_filenames(
        "sentinel-2-l2a", base_url="http://z"
    )
    assert alias_res == official_res == {"sentinel-2-l2a": ["a", "b"]}
    assert calls == ["sentinel-2-l2a", "sentinel-2-l2a"]


def test_sample_collection_filenames_nested(monkeypatch):
    """Ensure nested child collections are sampled."""

    collections = {
        "ROOT": [{"rel": "child", "href": "collections/C1"}, {"rel": "child", "href": "collections/C2"}],
        "C1": [],
        "C2": [{"rel": "child", "href": "collections/C3"}],
        "C3": [],
    }

    def fake_read_json(url):
        cid = url.split("/")[-1]
        return {"links": collections[cid]}

    monkeypatch.setattr(sd, "_read_json", fake_read_json)

    def fake_iter_asset(collection_id, *, base_url, limit=100):
        return iter({
            "C1": ["a1", "a2"],
            "C3": ["c1", "c2"],
        }[collection_id])

    monkeypatch.setattr(sd, "iter_asset_filenames", fake_iter_asset)
    res = sd.sample_collection_filenames("ROOT", 1, base_url="http://x")
    assert res == {"C1": ["a1"], "C3": ["c1"]}


def test_list_collections_requires_base_url():
    with pytest.raises(TypeError):
        sd.list_collections()


def test_iter_asset_filenames_bad_collection(monkeypatch):
    def fake_read_json(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    with pytest.raises(SystemExit) as exc:
        list(sd.iter_asset_filenames("BAD", base_url="http://u"))
    assert (
        str(exc.value)
        == "Collection 'BAD' not found at http://u/. Use `parseo stac-sample <collection> --stac-url <url>` with a valid collection ID."
    )

