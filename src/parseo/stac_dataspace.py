Add configurable stac-url support
Aug 24MatMatt/parsEOcodex/add-configurable-stac-url-support-wbnsez
+191-0
View PR
1. In `src/parseo/stac_dataspace.py`, add a `base_url` parameter (defaulting to the existing constant) to `list_collections`, `iter_asset_filenames`, and `sample_collection_filenames`, and use it when building request URLs.
2. Update the `stac-sample` subcommand in `src/parseo/cli.py` to accept a `--stac-url` option and pass it through to `sample_collection_filenames`.
3. Extend unit tests in `tests/test_stac_dataspace.py` and `tests/test_cli.py` to cover the configurable endpoint.
4. Document the `--stac-url` option and examples in `README.md`.
Summary

    Introduced a Copernicus Data Space STAC helper module exposing CDSE_STAC_URL and allowing list_collections, iter_asset_filenames, and sample_collection_filenames to query any STAC endpoint via a configurable base_url parameter

Expanded the CLI with a new stac-sample subcommand and --stac-url option so users can sample asset filenames from arbitrary STAC services

Added unit tests covering the custom STAC URL path and documented the stac-sample usage, including the --stac-url option, in the README
Testing

    ✅ pytest

dont set a default stac catalog. ask every time to specify the endpoing (API)
Summary

    STAC helper functions now mandate an explicit base_url, with the Copernicus Data Space URL provided only as an optional constant rather than a default

The stac-sample CLI subcommand requires a --stac-url argument to specify the target STAC API endpoint

Documentation and tests were updated to reflect the mandatory STAC endpoint, including examples and error coverage when the URL is omitted
Testing

    ✅ pytest

S C:\Users\Mattiuzzi\Documents\parsEO> parseo stac-sample S2 --samples 3 --stac-url https://catalogue.dataspace.copernicus.eu/stac/
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Scripts\parseo.exe\__main__.py", line 6, in <module>
  File "C:\Users\Mattiuzzi\Documents\parsEO\src\parseo\cli.py", line 183, in main
    for fn in sample_collection_filenames(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\Documents\parsEO\src\parseo\stac_dataspace.py", line 54, in sample_collection_filenames
    return list(
           ^^^^^
  File "C:\Users\Mattiuzzi\Documents\parsEO\src\parseo\stac_dataspace.py", line 37, in iter_asset_filenames
    data = _read_json(url)
           ^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\Documents\parsEO\src\parseo\stac_dataspace.py", line 19, in _read_json        
    with urllib.request.urlopen(url) as resp:  # type: ignore[call-arg]
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 215, in urlopen
    return opener.open(url, data, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 521, in open
    response = meth(req, response)
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 630, in http_response
    response = self.parent.error(
               ^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 559, in error
    return self._call_chain(*args)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 492, in _call_chain
    result = func(*args)
             ^^^^^^^^^^^
  File "C:\Users\Mattiuzzi\AppData\Local\Programs\Python\Python312\Lib\urllib\request.py", line 639, in http_error_default
    raise HTTPError(req.full_url, code, msg, hdrs, fp)
urllib.error.HTTPError: HTTP Error 404: Not Found
PS C:\Users\Mattiuzzi\Documents\parsEO>
Summary

    Normalized STAC helper functions now force a single trailing slash on the base URL before building request paths, letting users omit the slash without causing 404s

Documentation clarifies that --stac-url works with or without a trailing slash and demonstrates usage with the Sentinel‑2 L2A collection
Testing

    ✅ pytest


README.md
+16-0
@@ -139,50 +139,66 @@ from parseo import assemble, parse_auto
app = FastAPI()


@app.get("/parse")
def parse_endpoint(name: str):
    res = parse_auto(name)
    return res.model_dump()


@app.post("/assemble")
def assemble_endpoint(schema: str, fields: dict):
    filename = assemble(schema, fields)
    return {"filename": filename}
```

Start the server and open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
to access Swagger UI:

```bash
uvicorn main:app --reload
```

The interactive page lets you call `/parse` and `/assemble` directly from the
browser to verify your API.

### Sample filenames from a STAC collection

The ``stac-sample`` subcommand prints a few asset filenames from a STAC
collection. The STAC API root must always be provided via ``--stac-url``
(with or without a trailing slash):

```bash
parseo stac-sample SENTINEL2_L2A --samples 3 --stac-url https://catalogue.dataspace.copernicus.eu/stac
```

A different STAC service can be targeted by supplying its URL:

```bash
parseo stac-sample my-collection --samples 2 --stac-url https://stac.example.com
```

---

## Command Line Interface

Use the CLI to parse filenames, list available schemas, and assemble filenames from fields.
The `assemble` subcommand relies on the `parseo.assembler` module, which ships with the
standard parseo installation. If you run `parseo assemble` in an environment where this
module was intentionally omitted, the CLI will exit with:

```
The 'assemble' command requires parseo.assembler, which is part of the standard parseo installation.
```

Reinstall parseo with assembler support or provide your own `parseo/assembler.py`
implementing `assemble(schema_path, fields)` to enable this command.

```bash
# Parse a filename
parseo parse S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE

# List available schemas
parseo list-schemas
# -> CLC
#    LANDSAT
#    S1
src/parseo/cli.py
+23-0
# src/parseo/cli.py
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from parseo.parser import parse_auto, describe_schema, list_schemas  # parser helpers
from parseo.stac_dataspace import sample_collection_filenames


# ---------- small utilities ----------

def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="parseo", description="parsEO CLI")
    sp = ap.add_subparsers(dest="cmd", required=True)

    # parse
    p_parse = sp.add_parser("parse", help="Parse a filename")
    p_parse.add_argument("filename")

    # list-schemas
    sp.add_parser("list-schemas", help="List available schema families")

    # schema-info
    p_info = sp.add_parser("schema-info", help="Show details for a mission family")
    p_info.add_argument("family", help="Mission family name, e.g. 'S2'")

    # list-clms-products
    sp.add_parser(
        "list-clms-products",
        help="List product names available in the CLMS dataset catalog",
    )

    # stac-sample
    p_stac = sp.add_parser(
        "stac-sample",
        help="Print sample asset filenames from a STAC collection",
    )
    p_stac.add_argument("collection", help="STAC collection ID")
    p_stac.add_argument(
        "--samples", type=int, default=5, help="Number of filenames to list"
    )
    p_stac.add_argument(
        "--stac-url",
        required=True,
        help="Base URL of the STAC API",
    )

    # assemble
    p_asm = sp.add_parser(
        "assemble",
        help=(
            "Assemble a filename from fields. "
            "Provide key=value pairs OR pipe a JSON object to stdin. "
            "Schema is auto-selected using the schema's first compulsory field (fields_order[0])."
        ),
    )
    p_asm.add_argument(
        "fields",
        nargs="*",
        help="key=value pairs (optional if you pipe a JSON object to stdin).",
    )
    p_asm.add_argument(
        "--fields-json",
        help="JSON string with fields, or '-' to read JSON from stdin.",
    )

    return ap


def _kv_pairs_to_dict(pairs: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in pairs:
@@ -141,49 +157,56 @@ def main(argv: List[str] | None = None) -> int:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "list-schemas":
        for fam in list_schemas():
            print(fam)
        return 0

    if args.cmd == "schema-info":
        try:
            info = describe_schema(args.family)
        except KeyError as e:
            raise SystemExit(str(e))
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "list-clms-products":
        try:
            from parseo.clms_catalog import fetch_clms_products
        except Exception as exc:  # pragma: no cover - import-time failures
            raise SystemExit(f"Failed to load CLMS catalog scraper: {exc}")
        for name in fetch_clms_products():
            print(name)
        return 0

    if args.cmd == "stac-sample":
        for fn in sample_collection_filenames(
            args.collection, args.samples, base_url=args.stac_url
        ):
            print(fn)
        return 0

    if args.cmd == "assemble":
        # Lazy import so 'parse' doesn’t require assembler module
        try:
            from parseo.assembler import assemble_auto
        except ModuleNotFoundError:
            raise SystemExit(
                "The 'assemble' command requires parseo.assembler, which is part of the "
                "standard parseo installation.\n"
                "If it is missing, reinstall parseo with assembler support or provide a "
                "'parseo/assembler.py' implementing 'assemble_auto(fields)'. "
                "You can still use 'parse' or 'list-schemas'."
            )

        fields = _resolve_fields(args)
        out = assemble_auto(fields)
        print(out)
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
src/parseo/stac_dataspace.py
New
+65-0
"""Helpers for querying STAC APIs.

The Copernicus Data Space Ecosystem STAC root URL is available as
``CDSE_STAC_URL`` for convenience but is not used as a default.  All helper
functions require explicitly passing the ``base_url`` of the STAC service.
"""
from __future__ import annotations

from typing import Iterable, List
from urllib.parse import urljoin
import urllib.request
import json
import itertools

CDSE_STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/"


def _norm_base(base_url: str) -> str:
    """Return ``base_url`` with exactly one trailing slash."""
    return base_url.rstrip("/") + "/"


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:  # type: ignore[call-arg]
        return json.load(resp)


def list_collections(base_url: str) -> List[str]:
    """Return available collection IDs from the STAC API."""
    base = _norm_base(base_url)
    data = _read_json(urljoin(base, "collections"))
    return [c["id"] for c in data.get("collections", [])]


def iter_asset_filenames(
    collection_id: str,
    *,
    base_url: str,
    limit: int = 100,
) -> Iterable[str]:
    """Yield asset filenames from items of a collection."""
    base = _norm_base(base_url)
    url = urljoin(base, f"collections/{collection_id}/items?limit={limit}")
    data = _read_json(url)
    for feat in data.get("features", []):
        assets = feat.get("assets", {})
        for asset in assets.values():
            href = asset.get("href")
            if not href:
                continue
            yield href.rstrip("/").split("/")[-1]


def sample_collection_filenames(
    collection_id: str,
    samples: int = 5,
    *,
    base_url: str,
) -> List[str]:
    """Return ``samples`` filenames from the given collection."""
    return list(
        itertools.islice(
            iter_asset_filenames(collection_id, base_url=base_url), samples
        )
    )
tests/test_cli.py
+36-0
@@ -98,25 +98,61 @@ def test_fields_json_invalid_stdin(monkeypatch):
def test_list_schemas_exposes_known_families():
    fams = list_schemas()
    assert "S2" in fams
    assert "S1" in fams


def test_cli_list_schemas_outputs_families(capsys):
    assert cli.main(["list-schemas"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "S1" in out
    assert "S2" in out
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

    def fake_sample(collection, samples=5, *, base_url):
        calls["collection"] = collection
        calls["samples"] = samples
        calls["base_url"] = base_url
        return ["a", "b"]

    monkeypatch.setattr(cli, "sample_collection_filenames", fake_sample)
    sys.argv = [
        "parseo",
        "stac-sample",
        "COL",
        "--samples",
        "2",
        "--stac-url",
        "http://example",
    ]
    assert cli.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["a", "b"]
    assert calls == {
        "collection": "COL",
        "samples": 2,
        "base_url": "http://example",
    }


def test_cli_stac_sample_requires_url(capsys):
    with pytest.raises(SystemExit):
        cli.main(["stac-sample", "COL"])
    err = capsys.readouterr().err
    assert "--stac-url" in err
tests/test_stac_dataspace.py
New
+51-0
import pytest
import parseo.stac_dataspace as sd


def test_list_collections_custom_base_url(monkeypatch):
    urls = []

    def fake_read_json(url):
        urls.append(url)
        return {"collections": [{"id": "abc"}]}

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    out = sd.list_collections(base_url="http://x")
    assert urls == ["http://x/collections"]
    assert out == ["abc"]


def test_iter_asset_filenames_custom_base_url(monkeypatch):
    urls = []

    def fake_read_json(url):
        urls.append(url)
        return {
            "features": [
                {"assets": {"a": {"href": "http://files/file1.tif"}}}
            ]
        }

    monkeypatch.setattr(sd, "_read_json", fake_read_json)
    out = list(sd.iter_asset_filenames("C1", base_url="http://y", limit=1))
    assert urls == ["http://y/collections/C1/items?limit=1"]
    assert out == ["file1.tif"]


def test_sample_collection_filenames_custom_base_url(monkeypatch):
    called = {}

    def fake_iter(collection_id, *, base_url, limit=100):
        called["collection"] = collection_id
        called["base_url"] = base_url
        return iter(["f1", "f2", "f3"])

    monkeypatch.setattr(sd, "iter_asset_filenames", fake_iter)
    res = sd.sample_collection_filenames("COL", 2, base_url="http://z")
    assert called == {"collection": "COL", "base_url": "http://z"}
    assert res == ["f1", "f2"]


def test_list_collections_requires_base_url():
    with pytest.raises(TypeError):
        sd.list_collections()
