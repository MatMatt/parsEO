from parseo.parser import parse_auto
from parseo import assemble_auto
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
    name = "S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S1A"
    assert res.fields["instrument_mode"] == "IW"
    assert res.fields["product_type"] == "SLC_"
    assert res.fields["processing_level"] == "1SD"
    assert res.fields["polarization"] == "V"
    assert res.version == "1.0.0"
    assert res.status == "current"


def test_s3_example():
    name = "S3A_OLCI_L2_20250105T103021_080_SEG01.tif"
    res = parse_auto(name)
    assert res.match_family == "S3"
    assert res.fields["platform"] == "S3A"


def test_near_miss_reports_field():
    name = "S2X_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    with pytest.raises(parser.ParseError) as exc:
        parse_auto(name)
    msg = str(exc.value)
    assert "platform" in msg
    assert "S2X" in msg
    assert "S2A" in msg


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
    parser.parse_auto("S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE")

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

def test_modis_example():
    parser._get_schema_paths.cache_clear()
    name = "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "MOD"
    assert res.fields["product"] == "09"
    assert res.fields["variant"] == "GA"
    assert res.fields["acq_date"] == "A2021123"
    assert res.fields["tile"] == "h18v04"
    assert res.fields["collection"] == "006"
    assert res.fields["proc_date"] == "2021132234506"
    assert res.fields["extension"] == "hdf"


def test_hrvpp_st_example():
    name = "ST_20240101T123045_S2_E15N45-01234_010m_V100_PPI.tif"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["prefix"] == "ST"
    assert res.fields["timestamp"] == "20240101T123045"
    assert res.fields["sensor"] == "S2"
    assert res.fields["tile_id"] == "E15N45-01234"
    assert res.fields["resolution"] == "010m"
    assert res.fields["version"] == "V100"
    assert res.fields["product"] == "PPI"
    assert res.fields["extension"] == "tif"

def test_hrvpp_st_variant():
    name = "ST_20231231T000000_S2_W05S20-98765_030m_V101_PPI.tif"
    res = parse_auto(name)
    assert res.fields["tile_id"] == "W05S20-98765"
    assert res.fields["version"] == "V101"

