from parseo.parser import parse_auto
import parseo.parser as parser

def test_s2_example():
    name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S2B"
    assert res.fields["processing_level"] == "MSIL2A"

def test_s1_example():
    name = "S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S1A"
    assert res.fields["sar_instrument_mode"] == "IW"
    assert res.fields["processing_level"] == "1SDV"


def test_schema_paths_cached(monkeypatch):
    calls = {"n": 0}

    original_iter = parser._iter_schema_paths

    def counting_iter(pkg: str):
        calls["n"] += 1
        yield from original_iter(pkg)

    monkeypatch.setattr(parser, "_iter_schema_paths", counting_iter)
    parser._get_schema_paths.cache_clear()

    # Two parses should trigger only a single scan of schema files
    parser.parse_auto("S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE")
    parser.parse_auto("S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE")

    assert calls["n"] == 1


def test_parse_bom_schema(tmp_path, monkeypatch):
    import json

    schema = {"filename_pattern": r"^(?P<id>ABC)\.SAFE$"}
    bom_path = tmp_path / "bom_schema.json"
    bom_path.write_text("\ufeff" + json.dumps(schema), encoding="utf-8")

    def fake_iter(pkg: str):
        yield bom_path

    monkeypatch.setattr(parser, "_iter_schema_paths", fake_iter)
    parser._get_schema_paths.cache_clear()

    res = parse_auto("ABC.SAFE")
    assert res.valid
    assert res.fields["id"] == "ABC"
