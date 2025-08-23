# src/parseo/parser.py
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files, as_file
from pathlib import Path
from typing import Dict, Iterator, Optional
import re
from functools import lru_cache
from ._json import load_json

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


@lru_cache(maxsize=32)
def _get_schema_paths(pkg: str) -> list[Path]:
    """Return all schema JSON paths for ``pkg``.

    The result is cached to avoid repeated filesystem scans when parsing
    multiple filenames.
    """
    return list(_iter_schema_paths(pkg))


def _find_schema_by_hints(pkg: str, product: Optional[str]) -> Optional[Path]:
    """
    Prefer a schema whose filename hints at the requested family (S1/S2/LANDSAT),
    but still search recursively.
    """
    if not product:
        return None
    tokens = {
        "S1": ("sentinel1", "s1_"),
        "S2": ("sentinel2", "s2_"),
        "LANDSAT": ("landsat",),
    }.get(product, tuple())
    for p in _get_schema_paths(pkg):
        name = p.name.lower()
        if any(tok in name for tok in tokens):
            return p
    return None


# ---------------------------
# Core helpers
# ---------------------------

@lru_cache(maxsize=256)
def _load_json_from_path(path: Path) -> Dict:
    return load_json(path)


@lru_cache(maxsize=512)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def _expand_pattern(schema: Dict) -> Optional[str]:
    """Expand ``filename_pattern`` placeholders using field definitions.

    A pattern may reference field names using ``{{field}}`` tokens. For each
    field definition, either an ``enum`` or a ``pattern`` is used to replace the
    corresponding token. Anchors (``^``/``$``) in field patterns are stripped so
    they integrate cleanly into the larger regex.
    """

    cached = schema.get("_expanded_pattern")
    if cached:
        return cached

    patt = schema.get("filename_pattern")
    if not isinstance(patt, str):
        return None

    fields = schema.get("fields", {})
    if not isinstance(fields, dict):
        schema["_expanded_pattern"] = patt
        return patt

    def field_regex(spec: Dict) -> str:
        if "enum" in spec:
            return "(?:" + "|".join(re.escape(v) for v in spec["enum"]) + ")"
        pattern = spec.get("pattern")
        if pattern is None:
            raise KeyError("Field spec missing 'pattern' or 'enum'")
        if pattern.startswith("^"):
            pattern = pattern[1:]
        if pattern.endswith("$"):
            pattern = pattern[:-1]
        return pattern

    for name, spec in fields.items():
        placeholder = f"{{{{{name}}}}}"
        if placeholder in patt:
            patt = patt.replace(placeholder, field_regex(spec))

    schema["_expanded_pattern"] = patt
    return patt


def _match_filename(name: str, schema: Dict) -> Optional[re.Match]:
    patt = _expand_pattern(schema)
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

    # Quick family hint
    u = name.upper()
    if u.startswith(("S1", "SENTINEL-1")):
        product_hint = "S1"
    elif u.startswith(("S2", "SENTINEL-2")):
        product_hint = "S2"
    elif u.startswith("LANDSAT"):
        product_hint = "LANDSAT"
    else:
        product_hint = None

    # Try hinted schema first (if any)
    hinted = _find_schema_by_hints(pkg, product=product_hint)
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
    candidates = _get_schema_paths(pkg)
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
    msg = (
        "No schema matched the provided name. "
        f"Looked recursively under {pkg}/{SCHEMAS_ROOT}/ and found "
        f"{len(seen)} file(s): {seen[:8]}{'…' if len(seen) > 8 else ''}"
    )
    if first_error is not None:
        msg += f". First error while reading schemas: {first_error}"
        raise RuntimeError(msg) from first_error
    raise RuntimeError(msg)
