# src/parseo/parser.py
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files, as_file
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
import json
import re
from functools import lru_cache

# Root folder inside the package where JSON schemas live
SCHEMAS_ROOT = "schemas"


@dataclass(frozen=True)
class ParseResult:
    """Result of a parsing attempt."""
    valid: bool
    fields: Dict[str, str]
    schema_path: str
    match_family: Optional[str] = None  # e.g., "S1", "S2", "LANDSAT"


# ---------------------------
# Schema discovery (recursive)
# ---------------------------

def _iter_schema_paths(pkg: str) -> Iterator[Path]:
    """
    Yield all *.json schema files recursively under `schemas/`.
    Zip-safe via importlib.resources so it works from wheels and editable installs.
    """
    root = files(pkg).joinpath(SCHEMAS_ROOT)
    # as_file gives us a real filesystem path even if resources are zipped
    with as_file(root) as root_path:
        base = Path(root_path)
        if not base.exists():
            return
        yield from (p for p in base.rglob("*.json") if p.is_file())


@dataclass(frozen=True)
class _FamilyInfo:
    tokens: Tuple[str, ...]
    schema_path: Path


def _extract_tokens_from_pattern(pattern: str) -> List[str]:
    pattern = pattern.lstrip("^")
    m = re.match(r"\(\?P<[^>]+>([^)]+)\)", pattern)
    if not m:
        return []
    raw = m.group(1)
    parts = [re.sub(r"\\.", "", p) for p in raw.split("|")]
    return [p for p in parts if len(p) >= 2]


@lru_cache(maxsize=1)
def _gather_family_info(pkg: str) -> Dict[str, _FamilyInfo]:
    root = files(pkg).joinpath(SCHEMAS_ROOT)
    with as_file(root) as root_path:
        base = Path(root_path)
        if not base.exists():
            return {}
        info: Dict[str, _FamilyInfo] = {}
        for idx_path in base.rglob("index.json"):
            idx = _load_json_from_path(idx_path)
            family = idx.get("family")
            versions = idx.get("versions", [])
            if not family or not versions:
                continue
            entry = next((v for v in versions if v.get("status") == "current"), versions[0])
            file = entry.get("file")
            if not file:
                continue
            schema_path = idx_path.parent / file
            try:
                schema = _load_json_from_path(schema_path)
            except Exception:
                continue
            patt = schema.get("filename_pattern")
            if not isinstance(patt, str):
                xparseo = schema.get("x-parseo", {})
                if isinstance(xparseo, dict):
                    patt = xparseo.get("parse_regex")
            tokens = _extract_tokens_from_pattern(patt) if isinstance(patt, str) else []
            if family not in tokens:
                tokens.append(family)
            info[family] = _FamilyInfo(tokens=tuple(t.upper() for t in tokens), schema_path=schema_path)
        return info


def _find_schema_by_hints(pkg: str, product: Optional[str]) -> Optional[Path]:
    if not product:
        return None
    info = _gather_family_info(pkg).get(product)
    return info.schema_path if info else None


# ---------------------------
# Core helpers
# ---------------------------

@lru_cache(maxsize=256)
def _load_json_from_path(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=512)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def _match_filename(name: str, schema: Dict) -> Optional[re.Match]:
    patt = schema.get("filename_pattern")
    if not isinstance(patt, str) or not patt:
        return None
    rx = _compile_pattern(patt)
    return rx.match(name)


def _extract_fields(name: str, schema: Dict) -> Dict[str, str]:
    """
    Extract named groups as fields from 'name' using the schema's regex.
    If the regex doesn't match, return an empty dict.
    """
    m = _match_filename(name, schema)
    return m.groupdict() if m else {}


def _try_validate(name: str, schema: Dict) -> bool:
    return _match_filename(name, schema) is not None


# ---------------------------
# Public API
# ---------------------------

def parse_auto(name: str) -> ParseResult:
    """
    Try to parse `name` by matching it against any schema under schemas/**.json.
    A quick 'family' hint is derived from the filename prefix (S1/S2/LANDSAT).
    Returns a ParseResult on success; raises RuntimeError if nothing matches.
    """
    pkg = __package__  # e.g., "parseo"

    info = _gather_family_info(pkg)
    token_map: Dict[str, str] = {
        tok: fam for fam, fi in info.items() for tok in fi.tokens
    }
    u = name.upper()
    product_hint = None
    for tok in sorted(token_map, key=len, reverse=True):
        if u.startswith(tok):
            product_hint = token_map[tok]
            break

    # Try hinted schema first (if any)
    hinted = _find_schema_by_hints(pkg, product_hint)
    if hinted and hinted.exists():
        try:
            schema = _load_json_from_path(hinted)
            if _try_validate(name, schema):
                return ParseResult(
                    valid=True,
                    fields=_extract_fields(name, schema),
                    schema_path=str(hinted),
                    match_family=product_hint,
                )
        except Exception:
            # If hinted schema is unreadable, fall back to brute force
            pass

    # Fallback: brute-force across all schemas (recursive)
    candidates = list(_iter_schema_paths(pkg))
    if not candidates:
        # No schema files packaged at all
        raise FileNotFoundError(f"No schemas packaged under {pkg}/{SCHEMAS_ROOT}.")

    first_error: Optional[Exception] = None
    for p in candidates:
        try:
            schema = _load_json_from_path(p)
        except Exception as e:
            if first_error is None:
                first_error = e
            continue
        if _try_validate(name, schema):
            return ParseResult(
                valid=True,
                fields=_extract_fields(name, schema),
                schema_path=str(p),
                match_family=product_hint,
            )

    # Nothing matched — provide a helpful error listing what we saw
    with as_file(files(pkg).joinpath(SCHEMAS_ROOT)) as rp:
        base = Path(rp)
        seen = [str(q.relative_to(base)) for q in base.rglob("*.json")] if base.exists() else []
    raise RuntimeError(
        "No schema matched the provided name. "
        f"Looked recursively under {pkg}/{SCHEMAS_ROOT}/ and found "
        f"{len(seen)} file(s): {seen[:8]}{'…' if len(seen) > 8 else ''}"
    )
