from pathlib import Path

from parseo import assemble, assemble_auto, parse_auto


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "src/parseo/schemas/copernicus/cz/cz_filename_v0_0_0.json"

def test_assemble_cz_schema():
    schema = _schema_path()
    fields = {
        "prefix": "CZ",
        "year": "2012",
        "delivery_unit": "DU001",
        "projection": "3035",
        "version": "V010",
        "format": "fgdb",
        "extension": "zip",
    }
    result = assemble(schema, fields)
    assert result == "CZ_2012_DU001_3035_V010_fgdb.zip"

def test_cz_roundtrip_auto():
    name = "CZ_2018_DU002_3035_V020_fgdb.zip"
    res = parse_auto(name)
    assert res.fields["year"] == "2018"
    assert res.fields["delivery_unit"] == "DU002"
    assert res.fields["projection"] == "3035"
    assert res.fields["version"] == "V020"
    assert res.fields["format"] == "fgdb"
    assert assemble_auto(res.fields) == name

def test_cz_vector_roundtrip_auto():
    name = "CZ_2012_DU123_3035_V100_geoPackage.gpkg"
    res = parse_auto(name)
    assert res.fields["format"] == "geoPackage"
    assert res.fields["extension"] == "gpkg"
    assert assemble_auto(res.fields) == name
