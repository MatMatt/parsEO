import sys
import builtins
import io
import pytest
import json

from parseo import cli
from parseo.parser import list_schemas


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
        "extension=tif",
    ]
    assert cli.main() == 0
    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC.tif"
    )


def test_cli_assemble_fapar_success(capsys):
    sys.argv = [
        'parseo',
        'assemble',
        'prefix=CLMS_VPP',
        'product=FAPAR',
        'resolution=100m',
        'tile_id=T32TNS',
        'start_date=20210101',
        'end_date=20210110',
        'version=V100',
        'file_id=FAPAR',
        'extension=tif',
    ]
    assert cli.main() == 0
    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == 'CLMS_VPP_FAPAR_100m_T32TNS_20210101_20210110_V100_FAPAR.tif'
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
        "extension=tif",
    ]
    with pytest.raises(SystemExit) as exc:
        cli.main()
    msg = str(exc.value)
    assert "requires parseo.assembler" in msg
    assert "standard parseo installation" in msg


def test_fields_json_invalid_string():
    sys.argv = ["parseo", "assemble", "--fields-json", "{"]
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert "--fields-json is not valid JSON" in str(exc.value)


def test_fields_json_invalid_stdin(monkeypatch):
    sys.argv = ["parseo", "assemble", "--fields-json", "-"]
    monkeypatch.setattr(sys, "stdin", io.StringIO("{"))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert "--fields-json '-' is not valid JSON" in str(exc.value)


def test_list_schemas_exposes_known_families():
    fams = list_schemas()
    assert "S2" in fams
    assert "S1" in fams
    assert "HR-WSI" in fams


def test_cli_list_schemas_outputs_families(capsys):
    assert cli.main(["list-schemas"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "S1" in out
    assert "S2" in out
    assert "HR-WSI" in out
    assert all("index.json" not in line for line in out)


def test_cli_schema_info(capsys):
    assert cli.main(["schema-info", "S2"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["schema_id"] == "copernicus:sentinel:s2"
    assert "platform" in data["fields"]
    assert data["fields"]["platform"]["description"] == "Spacecraft unit"
    assert isinstance(data.get("template"), str)
    assert isinstance(data.get("examples"), list)
    assert data["examples"]
    assert all(isinstance(x, str) for x in data["examples"])

def test_cli_stac_sample_custom_url(monkeypatch, capsys):
    calls = {}

    def fake_sample(collection, samples=5, *, base_url, asset_role=None):
        calls["collection"] = collection
        calls["samples"] = samples
        calls["base_url"] = base_url
        calls["asset_role"] = asset_role
        return {"C1": ["a"], "C2": ["b"]}

    monkeypatch.setattr(cli, "sample_collection_filenames", fake_sample)
    sys.argv = [
        "parseo",
        "stac-sample",
        "COL",
        "--samples",
        "2",
        "--stac-url",
        "http://example",
        "--asset-role",
        "data",
    ]
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["C1:", "  a", "C2:", "  b"]
    assert calls == {
        "collection": "COL",
        "samples": 2,
        "base_url": "http://example",
        "asset_role": "data",
    }

def test_cli_stac_sample_requires_url(capsys):
    with pytest.raises(SystemExit):
        cli.main(["stac-sample", "COL"])
    err = capsys.readouterr().err
    assert "--stac-url" in err


def test_cli_list_stac_collections(monkeypatch, capsys):
    called = {}

    def fake_list_collections_http(*, base_url, deep=False):
        called["base_url"] = base_url
        called["deep"] = deep
        return ["A", "B"]

    monkeypatch.setattr(cli, "list_collections_http", fake_list_collections_http)
    sys.argv = [
        "parseo",
        "list-stac-collections",
        "--stac-url",
        "http://example",
    ]
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["A", "B"]
    assert called == {"base_url": "http://example", "deep": False}


def test_cli_list_stac_collections_deep(monkeypatch, capsys):
    called = {}

    def fake_list_collections_http(*, base_url, deep=False):
        called["base_url"] = base_url
        called["deep"] = deep
        return ["X"]

    monkeypatch.setattr(cli, "list_collections_http", fake_list_collections_http)
    sys.argv = [
        "parseo",
        "list-stac-collections",
        "--stac-url",
        "http://example",
        "--deep",
    ]
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["X"]
    assert called == {"base_url": "http://example", "deep": True}


def test_kv_pairs_to_dict_duplicate_key():
    with pytest.raises(SystemExit) as exc:
        cli._kv_pairs_to_dict(["a=1", "a=2"])
    assert "Duplicate field 'a'" in str(exc.value)


def test_cli_assemble_duplicate_key(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "parseo",
            "assemble",
            "prefix=CLMS_WSI",
            "prefix=OTHER",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert "Duplicate field 'prefix'" in str(exc.value)
