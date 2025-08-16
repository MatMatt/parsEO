# src/parseo/cli.py
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Mapping

from .parser import parse_auto


def _schema_name_from(result: Any) -> str | None:
    """
    Extract a friendly schema 'name' from the result, if possible.
    We prefer the basename of schema_path. Works for both ParseResult objects and dicts.
    """
    schema_path = None
    if hasattr(result, "schema_path"):
        schema_path = getattr(result, "schema_path")
    elif isinstance(result, Mapping):
        schema_path = result.get("schema_path")
    if not schema_path:
        return None
    return os.path.basename(str(schema_path))


def _fields_from(result: Any) -> dict:
    """Get fields dict from ParseResult or a plain dict fallback."""
    if hasattr(result, "fields"):
        return getattr(result, "fields") or {}
    if isinstance(result, Mapping):
        return dict(result.get("fields") or {})
    return {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="parseo",
        description="Parse EO filenames using bundled schemas."
    )
    ap.add_argument("filename", nargs="?", help="Single filename to parse")
    ap.add_argument("--scan", metavar="DIR", help="Scan a directory of files")
    ap.add_argument("--json", action="store_true", help="Output full JSON result")
    ap.add_argument("--debug", action="store_true", help="Verbose output")
    args = ap.parse_args(argv)

    # Directory scan mode
    if args.scan:
        root = args.scan
        if not os.path.isdir(root):
            print(f"Not a directory: {root}", file=sys.stderr)
            return 2

        ok = 0
        miss = 0
        errs = 0

        for dirpath, _, files in os.walk(root):
            for fn in files:
                path = os.path.join(dirpath, fn)
                try:
                    res = parse_auto(fn)  # or pass the full name `path` if your parser expects it
                    fields = _fields_from(res)
                    schema_name = _schema_name_from(res) or "<unknown schema>"
                    if fields:
                        ok += 1
                        if args.debug:
                            print(f"[OK] {fn} -> {schema_name}")
                    else:
                        # Treat as miss if no fields came back
                        miss += 1
                        if args.debug:
                            print(f"[MISS] {fn} -> no fields/schema")
                except Exception as e:
                    errs += 1
                    print(f"[ERR] {fn}: {e}", file=sys.stderr)

        print(f"Summary: {ok} matched, {miss} no match, {errs} errors")
        # Non-zero exit if anything failed or missed
        return 0 if (errs == 0 and miss == 0) else 1

    # Single-file mode
    if not args.filename:
        ap.error("Provide a filename or use --scan DIR")

    try:
        res = parse_auto(args.filename)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    fields = _fields_from(res)
    if not fields:
        print("No schema matched ❌", file=sys.stderr)
        return 1

    if args.json:
        payload = res.__dict__ if hasattr(res, "__dict__") else (
            res if isinstance(res, Mapping) else {"fields": fields, "schema_path": _schema_name_from(res)}
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        schema_name = _schema_name_from(res) or "<unknown schema>"
        print(f"Matched schema: {schema_name}")
        print(json.dumps(fields, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
