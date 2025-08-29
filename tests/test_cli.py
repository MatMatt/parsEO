import io
import json
import sys

import pytest

from parseo import cli
from parseo.parser import describe_schema
from parseo.parser import parse_auto
from parseo.schema_registry import list_schema_families


def _schema_example_args(family: str) -> tuple[str, list[str]]:
    info = describe_schema(family)
    example = info["examples"][0]
    fields = parse_auto(example).fields
    args = [f"{k}={v}" for k, v in fields.items() if v is not None]
    return example, args


def test_cli_reports_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.strip()
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version

    try:
        expected = version("parseo")
    except PackageNotFoundError:
        expected = "unknown"
    assert out == f"parseo version {expected}"


def test_cli_assemble_success(capsys):
    example, args = _schema_example_args("WIC")
    assert cli.main(["assemble", *args]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == example


def test_cli_assemble_fapar_success(capsys):
    example, args = _schema_example_args("VEGETATION-INDEX")
    assert cli.main(["assemble", *args]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == example

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
    fams = list_schema_families()
    assert "S2" in fams
    assert "S1" in fams


def test_cli_list_schemas_outputs_versions(capsys):
    assert cli.main(["list-schemas"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].split() == ["FAMILY", "VERSION", "STATUS", "FILE"]
    tokens = [line.split(maxsplit=3) for line in lines[1:]]
    entries = {t[0]: t for t in tokens}
    assert entries["S1"][1] == "1.0.0"
    assert entries["S2"][1] == "1.0.0"
    assert entries["S1"][2] == "current"
    assert entries["S2"][2] == "current"


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
