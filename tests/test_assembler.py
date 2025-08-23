import sys
from pathlib import Path

import pytest

# Ensure src path for direct execution if package not installed
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parseo.assembler import assemble
from tests.conftest import load_schema_by_name


def test_assemble_wic_s2_schema():
    _, schema_path = load_schema_by_name("src/parseo/schemas", "wic_s2_filename_structure.json")
    fields = {
        "prefix": "CLMS_WSI",
        "product": "WIC",
        "pixel_spacing": "020m",
        "tile_id": "T33WXP",
        "sensing_datetime": "20201024T103021",
        "platform": "S2B",
        "version": "V100",
        "file_id": "WIC",
        "extension": ".tif",
    }
    out = assemble(schema_path, fields)
    assert out == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC_.tif"
