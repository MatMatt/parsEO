# src/filenamingapi/tools/generate_schemas_from_clms.py
from __future__ import annotations
import json, re, sys, pathlib, hashlib
from typing import Dict, Any, List

# How to point the script to the QC repo:
#   - pass path as first CLI arg, e.g.:
#       python -m filenamingapi.tools.generate_schemas_from_clms ../copernicus_quality_tools
#   - or set env var CLMS_QC_REPO
QC_SUBPATH = "product_definitions"

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")

def _infer_parts_from_regex(rx: str):
    """
    Returns (properties, required) for the 'parts' object from named groups in the regex.
    """
    try:
        names = re.compile(rx).groupindex  # {group_name: index}
    except re.error:
        names = {}
    props = {k: {"type": "string"} for k in names}
    req = list(names)
    return props, req

def _variant_name(chk: Dict[str, Any], idx: int) -> str:
    # Prefer an id/label if present, else stable hash suffix
    for key in ("id", "name", "label", "layer", "band"):
        v = chk.get(key)
        if isinstance(v, str) and v.strip():
            return _slug(v)
    # fallback: hash of the params to avoid collisions
    h = hashlib.sha1(json.dumps(chk.get("params", {}), sort_keys=True).encode()).hexdigest()[:8]
    return f"variant_{idx:02d}_{h}"

def _make_schema(product: str, chk: Dict[str, Any]) -> Dict[str, Any]:
    params = chk.get("params", {})
    rx = params.get("pattern") or params.get("regex") or r".+"
    extensions = params.get("extensions") or params.get("allowed_extensions") or []
    case_sensitive = bool(params.get("case_sensitive", True))

    parts_props, parts_required = _infer_parts_from_regex(rx)

    schema: Dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"CLMS {product} filename",
        "type": "object",
        "properties": {
            "filename": {"type": "string", "pattern": rx},
            "extension": (
                {"type": "string", "enum": extensions}
                if extensions else {"type": "string"}
            ),
            "parts": {
                "type": "object",
                "properties": parts_props,
                "required": parts_required,
                "additionalProperties": False
            },
        },
        "required": ["filename"] + (["extension"] if extensions else []),
        "additionalProperties": False,
        # Non-standard extensions to preserve QC intent
        "x-source": {
            "origin": "eea/copernicus_quality_tools",
            "check_ident": chk.get("check_ident"),
        },
        "x-validation": {
            "case_sensitive": case_sensitive
        }
    }

    # Pass through known optional constraints if present in QC params
    for k in ("min_length", "max_length"):
        if k in params:
            schema["properties"]["filename"][k.replace("length", "Length")] = params[k]

    # If QC lists allowed product codes or tiles, map to enums if we can detect them
    for k in ("product", "tile", "layer"):
        vals = params.get(f"allowed_{k}s") or params.get(f"{k}s")
        if isinstance(vals, list) and vals and isinstance(vals[0], str):
            schema["properties"].setdefault("parts", {}).setdefault("properties", {}) \
                  .setdefault(k, {"type": "string"})["enum"] = vals
            if "required" in schema["properties"]["parts"] and k not in schema["properties"]["parts"]["required"]:
                schema["properties"]["parts"]["required"].append(k)

    return schema

def main():
    import sys
    import pathlib

    if len(sys.argv) > 1:
        src = pathlib.Path(sys.argv[1]).expanduser().resolve()
    else:
        src = pathlib.Path(input("Enter path to the folder containing QC product definition JSONs: ")).expanduser().resolve()

    if not src.exists():
        print(f"ERROR: Path not found: {src}")
        sys.exit(2)
    if not src.is_dir():
        print(f"ERROR: Not a directory: {src}")
        sys.exit(2)

    repo_root = pathlib.Path(__file__).parents[3]
    dst_root = repo_root / "src" / "filenamingapi" / "schemas"
    dst_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for f in sorted(src.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Skipping {f.name}: {e}")
            continue

        product = _slug(f.stem)
        checks: List[Dict[str, Any]] = data.get("checks", data if isinstance(data, list) else [])
        naming = [c for c in checks if c.get("check_ident") == "qc_tool.raster.naming"]
        if not naming:
            continue

        outdir = dst_root / product
        outdir.mkdir(parents=True, exist_ok=True)

        for i, chk in enumerate(naming, start=1):
            schema = _make_schema(product, chk)
            variant = _variant_name(chk, i)
            out = outdir / f"{variant}.schema.json"
            out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            count += 1
            print(f"✓ {product}/{variant}.schema.json")

    if count == 0:
        print("No naming schemas were generated. Check your path.")
    else:
        print(f"Generated {count} schema file(s) in {dst_root}")

if __name__ == "__main__":
    main()
