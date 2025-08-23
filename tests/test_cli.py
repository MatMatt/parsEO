import json
import os
import sys
import subprocess
from pathlib import Path

# Ensure src path is available when package isn't installed
SRC = str(Path(__file__).resolve().parents[1] / "src")
ENV = os.environ.copy()
ENV["PYTHONPATH"] = SRC + os.pathsep + ENV.get("PYTHONPATH", "")


def run_cli(args):
    cmd = [sys.executable, "-m", "parseo.cli"] + args
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV)


def test_parse_command():
    res = run_cli(["parse", "S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["valid"]
    assert data["fields"]["platform"] == "S1A"


def test_list_schemas_command():
    res = run_cli(["list-schemas"])
    assert res.returncode == 0
    lines = res.stdout.splitlines()
    assert any("copernicus/sentinel/s2/s2_filename_v1_0_0.json" in line for line in lines)


def test_assemble_command():
    args = [
        "assemble",
        "prefix=CLMS_WSI",
        "product=WIC",
        "pixel_spacing=020m",
        "tile_id=T33WXP",
        "sensing_datetime=20201024T103021",
        "platform=S2B",
        "version=V100",
        "file_id=WIC",
        "extension=.tif",
    ]
    res = run_cli(args)
    assert res.returncode == 0
    assert res.stdout.strip() == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC_.tif"
