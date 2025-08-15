from __future__ import annotations
import json, re, sys, pathlib
from typing import Any, Dict, List, Tuple, Set

TARGET_IDENTS = {"qc_tool.raster.naming", "qc_tool.vector.naming"}

# ---------- utils

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")

def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def walk_json(node: Any):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk_json(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_json(v)

# ---------- product key normalization (merge years, keep resolution)

YEAR_RE = re.compile(r"^(19|20)\d{2}$")
def base_key_from_stem(stem: str) -> str:
    tokens = re.split(r"[^A-Za-z0-9]+", stem)
    kept: List[str] = []
    res_token = None
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        if YEAR_RE.match(t):
            continue
        m = re.match(r"^r?(\d+)\s*(m|km)$", t.lower())
        if m:
            res_token = f"{m.group(1)}{m.group(2)}"
            continue
        kept.append(t.lower())
    if res_token and res_token not in kept:
        kept.append(res_token)
    key = "_".join(kept)
    key = slug(key) or slug(re.sub(r"(19|20)\d{2}", "", stem))
    return key

# ---------- pattern/extension collectors

def _strings_from_mixed_list(items):
    out = []
    for it in items:
        if isinstance(it, (str, int)):
            out.append(str(it))
        elif isinstance(it, dict):
            for k in ("pattern", "regex", "name_regex", "value", "name"):
                v = it.get(k)
                if isinstance(v, (str, int)):
                    out.append(str(v))
    return out

LIKELY_REGEX = re.compile(r"[\\\[\]\(\)\{\}\^\$\+\*\?\|]|\\d|\\w|\\s|[A-Za-z].*[_-].*")  # heuristic

def _collect_strings_recursively(x: Any) -> List[str]:
    """Very permissive fallback: collect string leaves under params."""
    found: List[str] = []
    if isinstance(x, dict):
        for v in x.values():
            found.extend(_collect_strings_recursively(v))
    elif isinstance(x, list):
        for v in x:
            found.extend(_collect_strings_recursively(v))
    elif isinstance(x, (str, int)):
        s = str(x).strip()
        if s:
            found.append(s)
    return found

PLACEHOLDER_MAP = {
    "year": r"(?:19|20)\d{2}", "yyyy": r"(?:19|20)\d{2}", "yy": r"\d{2}",
    "month": r"(?:0[1-9]|1[0-2])", "mm": r"(?:0[1-9]|1[0-2])",
    "day": r"(?:0[1-9]|[12]\d|3[01])", "dd": r"(?:0[1-9]|[12]\d|3[01])",
    "date": r"(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])",
    "tile": r"[A-Za-z0-9]+", "grid": r"[A-Za-z0-9]+",
    "product": r"[A-Za-z0-9_]+", "layer": r"[A-Za-z0-9_]+", "band": r"[A-Za-z0-9_]+",
    "version": r"v?\d+(?:\.\d+)*", "res": r"\d+(?:m|km)", "resolution": r"\d+(?:m|km)",
    "epsg": r"\d{4,5}", "crs": r"[A-Za-z0-9:_-]+",
}
TEMPLATE_TOKEN = re.compile(r"(\{[^{}]+\}|\<[^<>]+\>|\$\{[^{}]+\})")
LIKELY_REGEX_CHARS = re.compile(r"[\\\[\]\(\)\{\}\^\$\+\*\?\|]|\\d|\\w|\\s")
FILENAMEY = re.compile(r"[A-Za-z].*\d|\d.*[A-Za-z]|[_.-]")  # letters+digits or separators

def _template_to_regex(s: str) -> str:
    parts = []
    pos = 0
    for m in TEMPLATE_TOKEN.finditer(s):
        lit = s[pos:m.start()]
        if lit:
            parts.append(re.escape(lit))
        name = m.group(0).strip("{}<>$ ").strip().lower().replace("-", "_")
        parts.append(PLACEHOLDER_MAP.get(name, r".+"))
        pos = m.end()
    tail = s[pos:]
    if tail:
        parts.append(re.escape(tail))
    return "".join(parts)

def _gather_all_strings(x: Any) -> list[str]:
    out = []
    if isinstance(x, dict):
        for v in x.values():
            out.extend(_gather_all_strings(v))
    elif isinstance(x, list):
        for v in x:
            out.extend(_gather_all_strings(v))
    elif isinstance(x, (str, int)):
        s = str(x).strip()
        if s:
            out.append(s)
    return out

def collect_patterns(params: Dict[str, Any], debug_labels: list[str]) -> list[str]:
    raw = _gather_all_strings(params)  # everything, anywhere in params
    candidates: list[str] = []
    # 1) Prefer template-like or regex-like strings
    for s in raw:
        if TEMPLATE_TOKEN.search(s):
            candidates.append(_template_to_regex(s)); debug_labels.append("template->regex")
        elif LIKELY_REGEX_CHARS.search(s) or FILENAMEY.search(s):
            candidates.append(s)
    # 2) If still nothing, accept any >=4 chars as literal (escaped)
    if not candidates:
        for s in raw:
            if len(s) >= 4:
                candidates.append(re.escape(s))
        if candidates:
            debug_labels.append("fallback_literals")

    # normalize + anchor + dedupe
    out, seen = [], set()
    for rx in candidates:
        rx = rx.strip()
        if not rx:
            continue
        if not rx.startswith("^"): rx = "^" + rx
        if not rx.endswith("$"):   rx = rx + "$"
        if rx not in seen:
            seen.add(rx)
            out.append(rx)
    return out


def collect_extensions(params: Dict[str, Any]) -> list[str]:
    # common: formats / extensions
    for k in ("formats", "extensions", "allowed_extensions", "extension", "format"):
        v = params.get(k)
        if isinstance(v, list) and v:
            return [str(x) for x in v if isinstance(x, (str, int))]
        if isinstance(v, (str, int)):
            return [str(v)]
    # infer from any string suffixes like ".tif", ".gpkg"
    exts = set()
    for s in _gather_all_strings(params):
        m = re.search(r"(\.[A-Za-z0-9]{2,5})$", s.strip())
        if m:
            exts.add(m.group(1))
    return sorted(exts)


def merge_regex_alternation(patterns: List[str]) -> str:
    if not patterns:
        return r"^.+$"
    cores = []
    for p in patterns:
        c = p[1:] if p.startswith("^") else p
        c = c[:-1] if c.endswith("$") else c
        cores.append(f"(?:{c})")
    return "^" + "|".join(cores) + "$"

# ---------- main conversion

def convert_folder_to_reduced_schemas(
    src_dir: pathlib.Path,
    dst_root: pathlib.Path,
    verbose: bool = False
) -> Tuple[int, List[str]]:
    dst_root.mkdir(parents=True, exist_ok=True)
    wrote = 0
    written_paths: List[str] = []

    per_key_patterns: Dict[str, List[str]] = {}
    per_key_exts: Dict[str, Set[str]] = {}
    keys_with_hits: Set[str] = set()  # <-- NEW
    files_scanned = 0
    files_with_hits = 0

    for jf in sorted(src_dir.rglob("*.json")):
        files_scanned += 1
        try:
            data = read_json(jf)
        except Exception as e:
            if verbose:
                print(f"[WARN] Skipping unreadable {jf}: {e}")
            continue

        base_key = base_key_from_stem(jf.stem)
        added_p = 0
        added_e = 0
        file_hits = 0

        for obj in walk_json(data):
            if not (isinstance(obj, dict) and "check_ident" in obj):
                continue
            ident = obj.get("check_ident")
            if ident not in {"qc_tool.raster.naming", "qc_tool.vector.naming"}:
                continue

            file_hits += 1
            keys_with_hits.add(base_key)  # <-- NEW

            params = obj.get("params", {}) if isinstance(obj, dict) else {}
            dbg_labels: List[str] = []
            pats = collect_patterns(params, dbg_labels)
            exts = collect_extensions(params)

            if pats:
                per_key_patterns.setdefault(base_key, []).extend(pats)
                added_p += len(pats)
            if exts:
                per_key_exts.setdefault(base_key, set()).update(exts)
                added_e += len(exts)

            if verbose:
                via = ",".join(dbg_labels) if dbg_labels else "-"
                print(f"[HIT] {jf.name} → {base_key} ident={ident} patterns={len(pats)} via {via} exts={exts or '-'}")

        if file_hits:
            files_with_hits += 1
        if verbose and (added_p or added_e):
            print(f"[INFO] {jf.name}: +{added_p} pattern(s), +{added_e} extension(s)")

    # --- WRITE PHASE ---
    # Use union of keys where we saw hits and keys where we collected patterns
    all_keys = set(per_key_patterns.keys()) | keys_with_hits

    for base_key in sorted(all_keys):
        patterns = list(dict.fromkeys(per_key_patterns.get(base_key, [])))

        # If no patterns extracted, use a permissive fallback
        if not patterns:
            patterns = [r"^.+$"]

        combined = merge_regex_alternation(patterns)
        exts = sorted(per_key_exts.get(base_key, []))

        schema: Dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"CLMS {base_key} filename",
            "type": "object",
            "properties": {
                "filename": {"type": "string", "pattern": combined},
            },
            "required": ["filename"],
            "additionalProperties": False,
        }
        if exts:
            schema["properties"]["extension"] = {"type": "string", "enum": exts}
            schema["required"].append("extension")

        outfile = dst_root / f"{base_key}.filename.schema.json"
        outfile.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        wrote += 1
        written_paths.append(str(outfile))

        if verbose:
            print(f"[WRITE] {outfile.name} patterns={len(patterns)} exts={exts or '-'}")

    if verbose:
        print(f"[SUMMARY] scanned={files_scanned}, files_with_naming_checks={files_with_hits}, products_out={wrote}")

    return wrote, written_paths

def main():
    args = sys.argv[1:]

    if not args:
        src = pathlib.Path(input("Enter path to folder with QC product JSONs: ").strip()).expanduser().resolve()
        dst_root = pathlib.Path.cwd()
    else:
        src = pathlib.Path(args[0]).expanduser().resolve()
        if len(args) > 1 and not args[1].startswith("--"):
            dst_root = pathlib.Path(args[1]).expanduser().resolve()
        else:
            dst_root = pathlib.Path.cwd()

    if not src.exists() or not src.is_dir():
        print(f"ERROR: Not a directory: {src}")
        sys.exit(2)

    verbose = any(a == "--verbose" for a in args)

    dst_root.mkdir(parents=True, exist_ok=True)

    n, paths = convert_folder_to_reduced_schemas(src, dst_root, verbose=verbose)
    if n == 0:
        print("No naming schemas were generated. Check your source path and JSON contents.")
    else:
        print(f"Generated {n} schema file(s) in {dst_root}:")
        for p in paths:
            print("  ✓", p)

if __name__ == "__main__":
    main()
