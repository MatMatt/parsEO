from parseo.parser import parse_auto
import parseo.parser as parser
import pytest
from functools import lru_cache

def test_s2_example():
    name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S2B"
    assert res.fields["sensor"] == "MSI"
    assert res.fields["processing_level"] == "L2A"
    assert res.fields["sensing_datetime"] == "20241123T224759"
    assert res.fields["processing_baseline"] == "N0511"
    assert res.fields["relative_orbit"] == "R101"

def test_s1_example():
    name = "S1A_IW_SLC__1SDVV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S1A"
    assert res.fields["mode"] == "IW"
    assert res.fields["product"] == "SLC_"
    assert res.fields["level"] == "1SD"
    assert res.fields["pol"] == "VV"


def test_s3_example():
    name = "S3A_OLCI_L2_20250105T103021_080_SEG01.tif"
    res = parse_auto(name)
    assert res.match_family == "S3"
    assert res.fields["platform"] == "S3A"


def test_schema_paths_cached(monkeypatch):
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
    parser.parse_auto("S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE")
    parser.parse_auto("S1A_IW_SLC__1SDVV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE")

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

    res = parse_auto("ABC.SAFE")
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
        parse_auto("whatever.SAFE")
    assert "Expecting value" in str(exc.value)
