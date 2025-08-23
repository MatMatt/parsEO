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
        / "src/parseo/schemas/copernicus/clms/hr-vpp/fapar_filename_v0_0_0.json"
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
