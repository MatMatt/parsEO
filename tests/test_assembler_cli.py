import json
import subprocess
import sys

from parseo.assembler import assemble
from parseo.parser import parse_auto


def test_assemble_roundtrip(tmp_path):
    """assemble() should rebuild filenames from parsed fields."""
    # Example without extension to avoid joiner issues around extensions
    name = "S2A_MSIL1C_20230715T103021_N0400_R052_T32TNS_20230715T103555"
    res = parse_auto(name)
    assert res.valid

    schema = {
        "fields_order": [
            "platform",
            "processing_level",
            "datetime",
            "version",
            "sat_relative_orbit",
            "mgrs_tile",
            "generation_datetime",
        ],
        "joiner": "_",
    }

    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))

    rebuilt = assemble(schema_path, res.fields)
    assert rebuilt == name


def test_cli_parse():
    name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    cmd = [sys.executable, "-m", "parseo.cli", "parse", name]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(cp.stdout)
    assert data["valid"] is True
    assert data["fields"]["platform"] == "S2B"


def test_cli_list_schemas():
    cmd = [sys.executable, "-m", "parseo.cli", "list-schemas"]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "copernicus/sentinel/s2/s2_filename_v1_0_0.json" in cp.stdout.splitlines()


def test_cli_assemble(tmp_path):
    # Use a CLMS example since it includes fields_order for auto selection
    name = "CLMS_WSI_GFSC_060m_T32TNS_20211018P7D_COMB_V100_GF-QA.tif"
    res = parse_auto(name)
    fields_file = tmp_path / "fields.json"
    fields_file.write_text(json.dumps(res.fields))

    cmd = [sys.executable, "-m", "parseo.cli", "assemble", "--fields-json", "-"]
    cp = subprocess.run(
        cmd,
        input=fields_file.read_text(),
        capture_output=True,
        text=True,
        check=True,
    )
    expected = assemble(res.schema_path, res.fields)
    assert cp.stdout.strip() == expected

