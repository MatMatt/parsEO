import sys
import builtins
import pytest

from parseo import cli


def test_cli_assemble_success(capsys):
    sys.argv = [
        "parseo",
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
    assert cli.main() == 0
    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC_.tif"
    )


def test_cli_assemble_missing_assembler(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "parseo.assembler":
            raise ModuleNotFoundError
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.argv = [
        "parseo",
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
    with pytest.raises(SystemExit) as exc:
        cli.main()
    msg = str(exc.value)
    assert "requires parseo.assembler" in msg
    assert "standard parseo installation" in msg
