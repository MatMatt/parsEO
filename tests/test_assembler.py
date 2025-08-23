from pathlib import Path

from parseo import assemble


def test_assemble_clms_fsc_schema():
    schema = Path(__file__).resolve().parents[1] / "src/parseo/schemas/copernicus/clms/hr-wsi/fsc_filename_structure.json"
    fields = {
        "prefix": "CLMS_WSI",
        "product": "FSC",
        "pixel_spacing": "020m",
        "tile_id": "T32TNS",
        "sensing_datetime": "20211018T103021",
        "platform": "S2A",
        "version": "V100",
        "file_id": "FSCOG",
        "extension": ".tif",
    }
    result = assemble(schema, fields)
    assert result == "CLMS_WSI_FSC_020m_T32TNS_20211018T103021_S2A_V100_FSCOG_.tif"
