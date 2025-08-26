import parseo.parser as parser
import pytest
from functools import lru_cache

from tests.conftest import schema_examples_list


def _get_s2_example():
    for path, ex in schema_examples_list():
        if "sentinel" in str(path.parent.parent).lower() and "s2" in path.name.lower():
            return ex
    pytest.skip("No S2 schema example available")


def test_near_miss_reports_field():
    example = _get_s2_example()
    expected = example.split("_")[0]
    bad_name = example.replace(expected, "S2X", 1)
    with pytest.raises(parser.ParseError) as exc:
        parser.parse_auto(bad_name)
    msg = str(exc.value)
    assert "platform" in msg
    assert "S2X" in msg
    assert expected in msg


def test_schema_paths_cached(monkeypatch):
    examples = [ex for _, ex in schema_examples_list()[:2]]
    if len(examples) < 2:
        pytest.skip("Need at least two schema examples")
    calls = {"n": 0}

    original_discover = parser._discover_family_info
    original_discover.cache_clear()

    def counting_discover(pkg: str):
        calls["n"] += 1
        return original_discover(pkg)

    wrapped = lru_cache(maxsize=None)(counting_discover)
    monkeypatch.setattr(parser, "_discover_family_info", wrapped)
    parser._discover_family_info.cache_clear()

    # Two parses should trigger only a single scan of index.json files
    parser.parse_auto(examples[0])
    parser.parse_auto(examples[1])

    assert calls["n"] == 1


def test_parse_bom_schema(tmp_path, monkeypatch):
    import json

    schema = {
        "template": "{id}.SAFE",
        "fields": {"id": {"enum": ["ABC"]}},
    }
    bom_path = tmp_path / "bom_schema.json"
    bom_path.write_text("\ufeff" + json.dumps(schema), encoding="utf-8")

    def fake_iter(pkg: str):
        yield bom_path

    monkeypatch.setattr(parser, "_iter_schema_paths", fake_iter)
    parser._get_schema_paths.cache_clear()

    res = parser.parse_auto("ABC.SAFE")
    assert res.valid
    assert res.fields["id"] == "ABC"


def test_malformed_schema_surfaces_error(tmp_path, monkeypatch):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not-json", encoding="utf-8")

    def fake_iter(pkg: str):
        yield bad_path

    monkeypatch.setattr(parser, "_iter_schema_paths", fake_iter)
    parser._get_schema_paths.cache_clear()

    with pytest.raises(RuntimeError) as exc:
        parser.parse_auto("whatever.SAFE")
    assert "Expecting value" in str(exc.value)
