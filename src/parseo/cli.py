# src/parseo/cli.py
from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files, as_file
from pathlib import Path
from typing import List, Dict, Any

from parseo.parser import parse_auto  # existing parser entrypoint
from ._json import load_json

SCHEMAS_ROOT = "schemas"


# ---------- small utilities ----------

def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="parseo", description="parsEO CLI")
    sp = ap.add_subparsers(dest="cmd", required=True)

    # parse
    p_parse = sp.add_parser("parse", help="Parse a filename")
    p_parse.add_argument("filename")

    # list-schemas
    sp.add_parser("list-schemas", help="List packaged schema JSON files")

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
        if "=" not in p:
            raise SystemExit(f"Invalid field '{p}'. Use key=value.")
        k, v = p.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise SystemExit(f"Invalid field '{p}': empty key.")
        out[k] = v
    return out


def _stdin_text() -> str:
    if sys.stdin and not sys.stdin.closed and not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _iter_schema_json_paths():
    """Yield Path objects for all packaged *.json schemas."""
    base = files("parseo").joinpath(SCHEMAS_ROOT)
    with as_file(base) as bp:
        root = Path(bp)
        yield from root.rglob("*.json")


def _select_schema_by_first_compulsory(fields: Dict[str, Any]) -> Path:
    """
    Auto-pick the best schema using:
      - eligible if user provided the schema's FIRST field (fields_order[0])
      - among eligibles, pick the one with largest overlap (#keys in fields_order)
      - tie-breaker: longer fields_order (more specific) wins
    """
    best = None  # (overlap, len(order), str(path))
    best_path: Path | None = None
    seen_first_keys = set()

    for p in _iter_schema_json_paths():
        try:
            sch = load_json(p)
        except Exception:
            continue

        order = sch.get("fields_order") or []
        if not order:
            continue

        first_key = order[0]
        seen_first_keys.add(first_key)

        if first_key not in fields:
            continue

        overlap = sum(1 for k in fields.keys() if k in order)
        key = (overlap, len(order), str(p))
        if (best is None) or (key > best):
            best = key
            best_path = p

    if not best_path:
        sample = ", ".join(sorted(seen_first_keys)) or "<no schemas found>"
        raise SystemExit(
            "[assemble] Could not select a schema. "
            "Include the schema's FIRST compulsory field among your inputs.\n"
            f"Examples of first fields from packaged schemas: {sample}"
        )

    return best_path


def _resolve_fields(args) -> Dict[str, Any]:
    """
    Merge sources in priority:
      1) --fields-json if provided (string or '-')
      2) JSON from stdin if available and no positional fields
      3) positional key=value pairs
    """
    # 1) --fields-json
    if args.fields_json:
        if args.fields_json == "-":
            raw = _stdin_text()
            if not raw.strip():
                raise SystemExit("--fields-json '-' set but stdin is empty.")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise SystemExit(f"--fields-json '-' is not valid JSON: {e}")
        else:
            try:
                return json.loads(args.fields_json)
            except json.JSONDecodeError as e:
                raise SystemExit(f"--fields-json is not valid JSON: {e}")

    # 2) stdin JSON (only if no positional fields were given)
    if not args.fields:
        raw = _stdin_text()
        if raw.strip():
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Stdin is not valid JSON: {e}")

    # 3) positional k=v pairs
    if args.fields:
        return _kv_pairs_to_dict(args.fields)

    raise SystemExit(
        "No fields provided. Supply key=value pairs, "
        "or pass --fields-json, or pipe a JSON object via stdin."
    )


# ---------- main ----------

def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = _build_arg_parser()
    args = ap.parse_args(argv)

    if args.cmd == "parse":
        res = parse_auto(args.filename)
        out = {
            "valid": bool(getattr(res, "valid", False)),
            "fields": getattr(res, "fields", None),
        }
        spath = getattr(res, "schema_path", None)
        if spath:
            out["schema_path"] = spath
        mfam = getattr(res, "match_family", None)
        if mfam:
            out["match_family"] = mfam
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "list-schemas":
        base = files("parseo").joinpath(SCHEMAS_ROOT)
        with as_file(base) as bp:
            root = Path(bp)
            for p in root.rglob("*.json"):
                print(p.relative_to(root))
        return 0

    if args.cmd == "assemble":
        # Lazy import so 'parse' doesn’t require assembler module
        try:
            from parseo.assembler import assemble as assemble_with_schema
        except ModuleNotFoundError:
            raise SystemExit(
                "The 'assemble' command requires parseo.assembler, which is part of the "
                "standard parseo installation.\n"
                "If it is missing, reinstall parseo with assembler support or provide a "
                "'parseo/assembler.py' implementing 'assemble(schema_path, fields)'. "
                "You can still use 'parse' or 'list-schemas'."
            )

        fields = _resolve_fields(args)
        schema_path = _select_schema_by_first_compulsory(fields)
        out = assemble_with_schema(str(schema_path), fields)
        print(out)
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
