from pathlib import Path

from parseo import assemble, assemble_auto


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
