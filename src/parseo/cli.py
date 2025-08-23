# src/parseo/cli.py
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from parseo.parser import parse_auto, describe_schema, list_schemas  # parser helpers


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
        version = getattr(res, "version", None)
        if version:
            out["version"] = version
        status = getattr(res, "status", None)
        if status:
            out["status"] = status
        mfam = getattr(res, "match_family", None)
        if mfam:
            out["match_family"] = mfam
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
