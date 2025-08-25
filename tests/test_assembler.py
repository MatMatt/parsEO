from pathlib import Path

import pytest

from parseo import assemble, assemble_auto, clear_schema_cache, parse_auto


def test_assemble_clms_fsc_schema():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/clms/hr-wsi/fsc_filename_v0_0_0.json"
    )
    fields = {
        "prefix": "CLMS_WSI",
        "product": "FSC",
        "pixel_spacing": "020m",
        "tile_id": "T32TNS",
        "sensing_datetime": "20211018T103021",
        "platform": "S2A",
        "version": "V100",
        "file_id": "FSCOG",
        "extension": "tif",
    }
    result = assemble(schema, fields)
    assert result == "CLMS_WSI_FSC_020m_T32TNS_20211018T103021_S2A_V100_FSCOG.tif"


def test_assemble_missing_field_template_schema():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/clms/hr-wsi/fsc_filename_v0_0_0.json"
    )
    fields = {
        "prefix": "CLMS_WSI",
        "product": "FSC",
        "pixel_spacing": "020m",
        "tile_id": "T32TNS",
        "sensing_datetime": "20211018T103021",
        # "platform" is intentionally omitted
        "version": "V100",
        "file_id": "FSCOG",
        "extension": "tif",
    }
    msg = r"Missing field 'platform' for schema .*fsc_filename_v0_0_0\.json"
    with pytest.raises(ValueError, match=msg):
        assemble(schema, fields)


def test_assemble_auto_wic_schema():
    fields = {
        "prefix": "CLMS_WSI",
        "product": "WIC",
        "pixel_spacing": "020m",
        "tile_id": "T33WXP",
        "sensing_datetime": "20201024T103021",
        "platform": "S2B",
        "version": "V100",
        "file_id": "WIC",
        "extension": "tif",
    }
    result = assemble_auto(fields)
    assert result == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC.tif"


def test_assemble_auto_missing_field_template_schema():
    fields = {
        "prefix": "CLMS_WSI",
        "product": "WIC",
        "pixel_spacing": "020m",
        "tile_id": "T33WXP",
        "sensing_datetime": "20201024T103021",
        # missing "platform"
        "version": "V100",
        "file_id": "WIC",
        "extension": "tif",
    }
    msg = r"Missing field 'platform' for schema .*wic_s2_filename_v0_0_0\.json"
    with pytest.raises(ValueError, match=msg):
        assemble_auto(fields)

def test_assemble_auto_modis_schema():
    fields = {
        "platform": "MOD",
        "product": "09",
        "variant": "GA",
        "acq_date": "A2021123",
        "tile": "h18v04",
        "collection": "006",
        "proc_date": "2021132234506",
        "extension": "hdf",
    }
    result = assemble_auto(fields)
    assert result == "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"

    
def test_assemble_clms_fapar_schema():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/clms/hr-vpp/fapar/fapar_filename_v0_0_0.json"
    )
    fields = {
        "prefix": "CLMS_VPP",
        "product": "FAPAR",
        "resolution": "100m",
        "tile_id": "T32TNS",
        "start_date": "20210101",
        "end_date": "20210110",
        "version": "V100",
        "file_id": "FAPAR",
        "extension": "tif",
    }
    result = assemble(schema, fields)
    assert result == "CLMS_VPP_FAPAR_100m_T32TNS_20210101_20210110_V100_FAPAR.tif"


def test_assemble_auto_fapar_schema():
    fields = {
        "prefix": "CLMS_VPP",
        "product": "FAPAR",
        "resolution": "100m",
        "tile_id": "T32TNS",
        "start_date": "20210101",
        "end_date": "20210110",
        "version": "V100",
        "file_id": "FAPAR",
        "extension": "tif",
    }
    result = assemble_auto(fields)
    assert result == "CLMS_VPP_FAPAR_100m_T32TNS_20210101_20210110_V100_FAPAR.tif"


def test_assemble_clms_st_schema():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/clms/hr-vpp/st/st_filename_v0_0_0.json"
    )
    fields = {
        "prefix": "ST",
        "timestamp": "20240101T123045",
        "sensor": "S2",
        "tile_id": "E15N45-01234",
        "resolution": "010m",
        "version": "V100",
        "product": "PPI",
        "extension": "tif",
    }
    result = assemble(schema, fields)
    assert result == "ST_20240101T123045_S2_E15N45-01234_010m_V100_PPI.tif"


def test_assemble_auto_st_schema():
    fields = {
        "prefix": "ST",
        "timestamp": "20231231T000000",
        "sensor": "S2",
        "tile_id": "W05S20-98765",
        "resolution": "030m",
        "version": "V101",
        "product": "PPI",
        "extension": "tif",
    }
    result = assemble_auto(fields)
    assert result == "ST_20231231T000000_S2_W05S20-98765_030m_V101_PPI.tif"


def test_assemble_s2_invalid_processing_baseline():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json"
    )
    fields = {
        "platform": "S2A",
        "sensor": "MSI",
        "processing_level": "L1C",
        "sensing_datetime": "20201024T103021",
        "processing_baseline": "N512",  # invalid, should be N followed by 4 digits
        "relative_orbit": "R101",
        "mgrs_tile": "T03VUL",
        "generation_datetime": "20201024T103021",
    }
    with pytest.raises(ValueError):
        assemble(schema, fields)


def test_assemble_s2_invalid_generation_datetime():
    schema = (
        Path(__file__).resolve().parents[1]
        / "src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json"
    )
    fields = {
        "platform": "S2A",
        "sensor": "MSI",
        "processing_level": "L1C",
        "sensing_datetime": "20201024T103021",
        "processing_baseline": "N0511",
        "relative_orbit": "R101",
        "mgrs_tile": "T03VUL",
        "generation_datetime": "20201024",  # invalid format
    }
    with pytest.raises(ValueError):
        assemble(schema, fields)


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

@pytest.mark.parametrize("year", ["2012", "2018", "2024"])
def test_assemble_auto_hrl_imperviousness_schema(year):
    fields = {
        "product_code": "IMD",
        "reference_year": year,
        "resolution": "10m",
        "aoi_code": "E40N20",
        "epsg": "EPSG3035",
        "version": "100",
        "tile": "E40N20",
        "extension": "tif",
    }
    result = assemble_auto(fields)
    assert result == f"hrl_IMD_{year}_10m_E40N20_EPSG3035_v100_E40N20.tif"

