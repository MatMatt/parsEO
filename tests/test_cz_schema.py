from pathlib import Path

from parseo import assemble, assemble_auto, parse_auto


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "src/parseo/schemas/copernicus/cz/cz_filename_v0_0_0.json"


def test_assemble_cz_schema():
    schema = _schema_path()
    fields = {
        "prefix": "CZ",
        "product": "FOO",
        "tile_id": "T32TNS",
        "date": "20210101",
        "version": "V100",
        "extension": "gpkg",
    }
    result = assemble(schema, fields)
    assert result == "CZ_FOO_T32TNS_20210101_V100.gpkg"


def test_cz_roundtrip_auto():
    name = "CZ_FOO_T32TNS_20210101_V100.gpkg"
    res = parse_auto(name)
    assert res.fields["product"] == "FOO"
    assert res.fields["tile_id"] == "T32TNS"
    assert res.fields["date"] == "20210101"
    assert res.fields["version"] == "V100"
    assert assemble_auto(res.fields) == name


def test_cz_vector_roundtrip_auto():
    name = "CZ_BAR_T32TNS_20210202_V101.zip"
    res = parse_auto(name)
    assert res.fields["product"] == "BAR"
    assert res.fields["extension"] == "zip"
    assert assemble_auto(res.fields) == name
