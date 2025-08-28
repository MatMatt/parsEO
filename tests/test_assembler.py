from pathlib import Path

import pytest

from parseo import assemble
from parseo import assemble_auto
from parseo import clear_schema_cache
from parseo import list_schema_versions


def test_assemble_missing_field_template_schema():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/clms/hr-wsi/fsc/fsc_filename_v0_0_0.json"
    )
    fields = {
        "prefix": "CLMS_WSI",
        "product": "FSC",
        "pixel_spacing": "020m",
        "mgrs_tile": "T32TNS",
        "sensing_datetime": "20211018T103021",
        # "platform" is intentionally omitted
        "version": "V100",
        "file_id": "FSCOG",
        "extension": "tif",
    }
    msg = r"Missing field 'platform' for schema .*fsc_filename_v0_0_0\.json"
    with pytest.raises(ValueError, match=msg):
        assemble(fields, schema_path=schema)


def test_assemble_auto_missing_optional_fields():
    fields = {
        "prefix": "CLMS_WSI",
        "product": "WIC",
        "pixel_spacing": "020m",
        "mgrs_tile": "T33WXP",
        "sensing_datetime": "20201024T103021",
        "platform": "S2B",
        "version": "V100",
        "file_id": "WIC",
    }
    name = assemble_auto(fields)
    assert name == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC"


def test_clear_schema_cache(tmp_path):
    clear_schema_cache()
    schema = tmp_path / "schema.json"
    schema.write_text('{"template": "{a}_{b}"}')
    fields = {"a": "x", "b": "y"}

    assert assemble(fields, schema_path=schema) == "x_y"

    schema.write_text('{"template": "{a}-{b}"}')

    # Cached schema remains in effect
    assert assemble(fields, schema_path=schema) == "x_y"

    clear_schema_cache()
    assert assemble(fields, schema_path=schema) == "x-y"


def test_list_schema_versions():
    versions = list_schema_versions("S2")
    assert any(v["version"] == "1.0.0" for v in versions)
    assert any(v["status"] == "current" for v in versions)


def test_assemble_with_family_s2():
    fields = {
        "platform": "S2B",
        "sensor": "MSI",
        "processing_level": "L2A",
        "sensing_datetime": "20241123T224759",
        "processing_baseline": "N0511",
        "relative_orbit": "R101",
        "mgrs_tile": "T03VUL",
        "generation_datetime": "20241123T230829",
        "extension": "SAFE",
    }
    name = assemble(fields, family="S2")
    assert (
        name
        == "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    )

