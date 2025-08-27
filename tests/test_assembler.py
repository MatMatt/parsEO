from pathlib import Path

import pytest

from parseo import assemble, assemble_auto, clear_schema_cache


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
        assemble(schema, fields)


def test_assemble_auto_missing_field_template_schema():
    fields = {
        "prefix": "CLMS_WSI",
        "product": "WIC",
        "pixel_spacing": "020m",
        "mgrs_tile": "T33WXP",
        "sensing_datetime": "20201024T103021",
        # missing "platform"
        "version": "V100",
        "file_id": "WIC",
        "extension": "tif",
    }
    msg = r"Missing field 'platform' for schema .*wic_s2_filename_v0_0_0\.json"
    with pytest.raises(ValueError, match=msg):
        assemble_auto(fields)


def test_clear_schema_cache(tmp_path):
    clear_schema_cache()
    schema = tmp_path / "schema.json"
    schema.write_text('{"fields_order": ["a", "b"], "joiner": "_"}')
    fields = {"a": "x", "b": "y"}

    assert assemble(schema, fields) == "x_y"

    schema.write_text('{"fields_order": ["a", "b"], "joiner": "-"}')

    # Cached schema remains in effect
    assert assemble(schema, fields) == "x_y"

    clear_schema_cache()
    assert assemble(schema, fields) == "x-y"

