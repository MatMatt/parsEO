from parseo.parser import parse_auto
import parseo.parser as parser
import parseo.schema_registry as schema_registry
import pytest
from functools import lru_cache


def test_schema_paths_cached(monkeypatch):
    calls = {"n": 0}

    schema_registry.clear_cache()
    original_discover = parser._discover_family_info
    original_discover.cache_clear()

    def counting_discover(pkg: str):
        calls["n"] += 1
        return original_discover(pkg)

    wrapped = lru_cache(maxsize=None)(counting_discover)
    monkeypatch.setattr(parser, "_discover_family_info", wrapped)
    parser._discover_family_info.cache_clear()

    # Two parses should trigger only a single discovery of schema files
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

    monkeypatch.setattr(schema_registry, "_iter_schema_paths", fake_iter)
    schema_registry.clear_cache()

    res = parse_auto("ABC.SAFE")
    assert res.valid
    assert res.fields["id"] == "ABC"


def test_malformed_schema_surfaces_error(tmp_path, monkeypatch):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not-json", encoding="utf-8")

    def fake_iter(pkg: str):
        yield bad_path

    monkeypatch.setattr(schema_registry, "_iter_schema_paths", fake_iter)
    schema_registry.clear_cache()

    with pytest.raises(RuntimeError) as exc:
        parse_auto("whatever.SAFE")
    assert "Expecting value" in str(exc.value)


def test_current_schema_default_and_explicit_version(tmp_path, monkeypatch):
    import json

    schema_v1 = {
        "schema_id": "x:y:abc",
        "schema_version": "1.0.0",
        "status": "deprecated",
        "template": "ABC_{id}_v1.txt",
        "fields": {"id": {"pattern": "[A-Z]+"}},
    }
    schema_v2 = {
        "schema_id": "x:y:abc",
        "schema_version": "2.0.0",
        "status": "current",
        "template": "ABC_{id}_v2.txt",
        "fields": {"id": {"pattern": "[A-Z]+"}},
    }
    p1 = tmp_path / "abc_filename_v1_0_0.json"
    p2 = tmp_path / "abc_filename_v2_0_0.json"
    p1.write_text(json.dumps(schema_v1))
    p2.write_text(json.dumps(schema_v2))

    def fake_iter(pkg: str):
        yield from [p1, p2]

    monkeypatch.setattr(schema_registry, "_iter_schema_paths", fake_iter)
    schema_registry.clear_cache()

    res = parse_auto("ABC_X_v2.txt")
    assert res.valid
    assert res.version == "2.0.0"
    assert res.fields["id"] == "X"

    res_old = parse_auto("ABC_X_v1.txt")
    assert res_old.valid
    assert res_old.version == "1.0.0"
    assert res_old.fields["id"] == "X"

    schema_registry.clear_cache()


def test_validate_schema_accepts_single_path(tmp_path, monkeypatch, capsys):
    import json

    schema = {
        "template": "{id}.SAFE",
        "fields": {"id": {"pattern": "[A-Z]+"}},
        "examples": ["ABC.SAFE"],
    }
    schema_path = tmp_path / "abc.json"
    schema_path.write_text(json.dumps(schema))

    def fake_iter(pkg: str):
        yield schema_path

    monkeypatch.setattr(schema_registry, "_iter_schema_paths", fake_iter)
    schema_registry.clear_cache()

    # Silent mode should produce no output
    parser.validate_schema(paths=str(schema_path))
    captured = capsys.readouterr()
    assert captured.out == ""

    # Verbose mode should emit progress and summary
    parser.validate_schema(paths=str(schema_path), verbose=True)
    captured = capsys.readouterr()
    assert str(schema_path) in captured.out
    assert "ABC.SAFE" in captured.out
    assert "Validated 1 examples" in captured.out


def test_parsing_fails_without_current(tmp_path, monkeypatch):
    import json

    schema = {
        "schema_id": "x:y:abc",
        "schema_version": "1.0.0",
        "status": "deprecated",
        "template": "ABC_{id}.txt",
        "fields": {"id": {"pattern": "[A-Z]+"}},
    }
    p = tmp_path / "abc_filename_v1_0_0.json"
    p.write_text(json.dumps(schema))

    def fake_iter(pkg: str):
        yield p

    monkeypatch.setattr(schema_registry, "_iter_schema_paths", fake_iter)
    schema_registry.clear_cache()

    with pytest.raises(RuntimeError) as exc:
        parse_auto("ABC_X.txt")
    assert "current" in str(exc.value)
    schema_registry.clear_cache()


def test_parse_urban_atlas_lcu():
    name = "CLMS_UA_LCU_S2021_V025ha_DK004L3_AALBORG_03035_V01_R00_20240212"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "UA-LCU"
    assert result.fields == {
        "programme": "CLMS",
        "product": "UA",
        "variable": "LCU",
        "survey": "S2021",
        "type": "vector",
        "resolution": "025ha",
        "area_code": "DK004L3",
        "city": "AALBORG",
        "epsg_code": "03035",
        "version": "V01",
        "revision": "R00",
        "production_date": "20240212",
        "extension": None,
    }
    assert "type_code" not in result.fields


def test_parse_clms_clcplus_type_mapping():
    name = "CLMS_CLCPLUS_RAS_S2023_R10m_E48N37_03035_V01_R00.tif"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "CLCPLUS"
    assert result.fields["type"] == "raster"
    assert result.fields["epsg_code"] == "03035"
    assert "type_code" not in result.fields



def test_parse_clms_hrl_nvlcc():
    name = "CLMS_HRLNVLCC_IMD_S2021_R10m_E09N27_03035_V01_R01.tif"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "NVLCC"
    assert result.fields == {
        "prefix": "CLMS",
        "theme": "HRLNVLCC",
        "variable": "IMD",
        "temporal_coverage": "S2021",
        "resolution": "R10m",
        "tile": "E09N27",
        "epsg_code": "03035",
        "version": "V01",
        "release": "R01",
        "extension": "tif",
    }


def test_parse_clms_hrl_nvlcc_unpadded_epsg():
    name = "CLMS_HRLNVLCC_IMD_S2021_R10m_E09N27_3035_V01_R01.tif"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "NVLCC"
    assert result.fields["epsg_code"] == "03035"


def test_parse_clms_hrl_small_woody_features():
    name = "SWF_2018_005m_E34N27_03035.tif"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "SMALL-WOODY-FEATURES"
    assert result.fields == {
        "variable": "SWF",
        "reference_year": "2018",
        "resolution": "005m",
        "tile": "E34N27",
        "epsg_code": "03035",
        "extension": "tif",
    }


def test_parse_clms_hrl_imperviousness():
    name = "IMD_2021_E042N018_010m_V100.tif"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "IMPERVIOUSNESS"
    assert result.fields == {
        "variable": "IMD",
        "reference_year": "2021",
        "eea_tile": "E042N018",
        "resolution": "010m",
        "version": "V100",
        "extension": "tif",
    }

def test_parse_clms_egms_l3_velocity_grid():
    name = "EGMS_L3_E28N49_100km_U_2018_2022_1.tiff"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "EGMS-L3"
    assert result.fields["product"] == "EGMS"
    assert result.fields["level"] == "L3"
    assert result.fields["tile"] == "E28N49"
    assert result.fields["tile_size"] == "100km"
    assert result.fields["component"] == "U"
    assert result.fields["start_year"] == "2018"
    assert result.fields["end_year"] == "2022"
    assert result.fields["version"] == "1"
    assert result.fields["extension"] == "tiff"


def test_parse_clms_egms_l2a_product_csv():
    name = "EGMS_L2a_088_0282_IW2_VV_2018_2022_1.csv"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "EGMS-L2A"
    assert result.fields["product"] == "EGMS"
    assert result.fields["level"] == "L2a"
    assert result.fields["track"] == "088"
    assert result.fields["burst"] == "0282"
    assert result.fields["swath"] == "IW2"
    assert result.fields["polarisation"] == "VV"
    assert result.fields["start_year"] == "2018"
    assert result.fields["end_year"] == "2022"
    assert result.fields["version"] == "1"
    assert result.fields["extension"] == "csv"


def test_parse_clms_egms_l2a_product_zip():
    name = "EGMS_L2a_124_0135_IW1_VH_2015_2020_2.zip"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "EGMS-L2A"
    assert result.fields["product"] == "EGMS"
    assert result.fields["level"] == "L2a"
    assert result.fields["track"] == "124"
    assert result.fields["burst"] == "0135"
    assert result.fields["swath"] == "IW1"
    assert result.fields["polarisation"] == "VH"
    assert result.fields["start_year"] == "2015"
    assert result.fields["end_year"] == "2020"
    assert result.fields["version"] == "2"
    assert result.fields["extension"] == "zip"


def test_parse_clms_egms_gnss_model():
    name = "EGMS_AEPND_V2023.1.csv"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "EGMS-GNSS-MODEL"
    assert result.fields["product"] == "EGMS"
    assert result.fields["variable"] == "AEPND"
    assert result.fields["issue_year"] == "V2023"
    assert result.fields["revision"] == "1"
    assert result.fields["extension"] == "csv"


def test_parse_modis_stac_mapping():
    name = "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "MODIS"
    assert result.fields["platform"] == "Terra"
    assert result.fields["instrument"] == "MODIS"
    assert result.fields["platform_code"] == "MOD"
    assert result.fields["product"] == "09"


def test_parse_landsat_stac_mapping():
    name = "LC08_L1TP_190026_20200101_20200114_02_T1.tar"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "LANDSAT"
    assert result.fields["platform"] == "landsat-8"
    assert result.fields["instrument"] == "OLI_TIRS"
    assert result.fields["platform_code"] == "LC08"
    assert result.fields["epsg_code"] == "32619"


def test_parse_sentinel2_epsg_lookup():
    name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    result = parse_auto(name)

    assert result.valid
    assert result.match_family == "S2"
    assert result.fields["mgrs_tile"] == "T03VUL"
    assert result.fields["epsg_code"] == "32603"
