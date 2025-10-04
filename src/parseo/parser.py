# src/parseo/parser.py
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import as_file
from importlib.resources import files
from pathlib import Path
import re
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Union

from ._field_mappings import apply_schema_mappings
from .schema_registry import _discover_family_info
from .schema_registry import _get_schema_paths
from .schema_registry import _load_json_from_path
from .schema_registry import get_schema_path
from .schema_registry import list_schema_families
from .template import _field_regex
from .template import compile_template

# Root folder inside the package where JSON schemas live
SCHEMAS_ROOT = "schemas"


@dataclass(frozen=True)
class ParseResult:
    """Result of a parsing attempt."""
    valid: bool
    fields: Dict[str, str]
    version: Optional[str] = None
    status: Optional[str] = None
    match_family: Optional[str] = None  # e.g., "S1", "S2", "LANDSAT"


@dataclass
class ParseError(Exception):
    """Raised when a filename nearly matches a schema but fails on a field."""

    field: str
    expected: str
    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"Invalid value '{self.value}' for field '{self.field}': expected {self.expected}"
        )


# ---------------------------
# Core helpers
# ---------------------------


@lru_cache(maxsize=512)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def _pattern_from_schema(schema: Dict) -> Optional[str]:
    """Return a compiled regex pattern derived from a schema's template.

    The result is cached inside the schema object. If a ``template`` key is
    present it is compiled via :func:`compile_template`.
    """

    cached = schema.get("_compiled_pattern")
    if cached:
        return cached

    template = schema.get("template")
    if isinstance(template, str):
        fields = schema.get("fields", {})
        pattern, order = compile_template(template, fields)
        schema["_compiled_pattern"] = pattern
        if "fields_order" not in schema and order:
            schema["fields_order"] = order
        return pattern

    return None


def _match_filename(name: str, schema: Dict) -> Optional[re.Match]:
    patt = _pattern_from_schema(schema)
    if not isinstance(patt, str) or not patt:
        return None
    rx = _compile_pattern(patt)
    return rx.match(name)


def _normalize_epsg_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize EPSG-related fields to consistently use 5-digit codes."""

    normalized = dict(fields)
    for key, value in fields.items():
        if not isinstance(key, str):
            continue
        key_lower = key.lower()
        if "epsg" not in key_lower and key_lower not in {"tile", "tile_id"}:
            continue
        if isinstance(value, str) and value.isdigit() and len(value) in {4, 5}:
            normalized[key] = value.zfill(5)
    return normalized


def _extract_fields(name: str, schema: Dict) -> Dict[str, str]:
    """
    Extract named groups as fields from 'name' using the schema's regex.
    If the regex doesn't match, return an empty dict.
    """
    m = _match_filename(name, schema)
    if not m:
        return {}
    extracted = m.groupdict()
    enriched = apply_schema_mappings(extracted, schema)
    return _normalize_epsg_fields(enriched)


def _try_validate(name: str, schema: Dict) -> bool:
    return _match_filename(name, schema) is not None


def _named_group_spans(pattern: str) -> Dict[str, tuple[int, int]]:
    spans: Dict[str, tuple[int, int]] = {}
    stack: list[tuple[Optional[str], int]] = []
    i = 0
    in_class = False
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            i += 2
            continue
        if in_class:
            if ch == "]":
                in_class = False
            i += 1
            continue
        if ch == "[":
            in_class = True
            i += 1
            continue
        if ch == "(":
            if pattern.startswith("(?P<", i):
                j = i + 4
                k = pattern.index(">", j)
                name = pattern[j:k]
                stack.append((name, i))
                i = k + 1
            else:
                stack.append((None, i))
                i += 1
            continue
        if ch == ")":
            name, start = stack.pop()
            if name:
                spans[name] = (start, i + 1)
            i += 1
            continue
        i += 1
    return spans


def _explain_match_failure(name: str, schema: Dict) -> Optional[tuple[str, str, str]]:
    pattern = _pattern_from_schema(schema)
    fields = schema.get("fields", {})
    order = schema.get("fields_order", [])
    if not pattern or not order:
        return None
    spans = _named_group_spans(pattern)
    for i, field in enumerate(order):
        next_start = spans[order[i + 1]][0] if i + 1 < len(order) else len(pattern) - 1
        prefix_pat = pattern[:next_start] + ".*$"
        if not _compile_pattern(prefix_pat).match(name):
            before_pat = pattern[:spans[field][0]]
            m_before = _compile_pattern(before_pat).match(name)
            start_pos = len(m_before.group(0)) if m_before else 0
            spec = fields.get(field, {})
            field_rx = re.compile(_field_regex(spec))
            m_field = field_rx.match(name[start_pos:])
            if m_field:
                # Field value itself satisfies the specification; mismatch must
                # stem from a later constant segment, so we cannot attribute
                # it to this field.
                return None
            end_pos = len(name)
            for sep in ["_", ".", "-"]:
                idx = name.find(sep, start_pos)
                if idx != -1:
                    end_pos = min(end_pos, idx)
            value = name[start_pos:end_pos]
            if "enum" in spec:
                expected = f"one of {spec['enum']}"
            elif "pattern" in spec:
                expected = f"pattern {spec['pattern']}"
            else:
                expected = "a different value"
            return field, expected, value
    return None


# ---------------------------
# Public API
# ---------------------------


def list_schemas(pkg: str = __package__) -> list[str]:
    """Return a list of available mission family names."""
    return list_schema_families(pkg)


def describe_schema(family: str, pkg: str = __package__) -> dict[str, Any]:
    """Return schema metadata and field descriptions for ``family``."""

    try:
        schema_path = get_schema_path(family, pkg=pkg)
    except KeyError as e:
        raise KeyError(str(e))

    schema = _load_json_from_path(schema_path)
    fields: Dict[str, Dict[str, Any]] = {}
    for name, spec in schema.get("fields", {}).items():
        if isinstance(spec, dict):
            fields[name] = {
                k: spec[k]
                for k in ("type", "enum", "pattern", "description")
                if k in spec
            }

    out: Dict[str, Any] = {
        "schema_id": schema.get("schema_id"),
        "description": schema.get("description"),
        "fields": fields,
    }

    template = schema.get("template")
    if isinstance(template, str):
        out["template"] = template

    examples = schema.get("examples")
    if isinstance(examples, list):
        out["examples"] = [e for e in examples if isinstance(e, str)]

    return out


def parse_auto(name: str) -> ParseResult:
    """
    Try to parse `name` by matching it against any schema under schemas/**.json.
    A quick 'family' hint is derived from the filename prefix by dynamically
    inspecting available schema files. Returns a ParseResult on success;
    raises RuntimeError if nothing matches.
    """
    pkg = __package__  # e.g., "parseo"
    info = _discover_family_info(pkg)

    # Quick family hint based on discovered tokens
    product_hint = None
    u = name.upper()
    for fam, meta in info.items():
        if any(u.startswith(tok) for tok in meta.tokens):
            product_hint = fam
            break

    near_miss: Optional[ParseError] = None

    # Try hinted schema first (if any)
    hinted_meta = info.get(product_hint) if product_hint else None
    hinted = hinted_meta.schema_path if hinted_meta else None
    if hinted and hinted.exists():
        try:
            schema = _load_json_from_path(hinted)
            if _try_validate(name, schema):
                return ParseResult(
                    valid=True,
                    fields=_extract_fields(name, schema),
                    version=hinted_meta.version if hinted_meta else None,
                    status=hinted_meta.status if hinted_meta else None,
                    match_family=product_hint,
                )
            mismatch = _explain_match_failure(name, schema)
            if mismatch:
                field, expected, value = mismatch
                near_miss = ParseError(field, expected, value)
        except ParseError as err:
            near_miss = err
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
            matched_family = None
            version = None
            status = None
            for fam_name, meta in info.items():
                if meta.schema_path == p:
                    matched_family = fam_name
                    version = meta.version
                    status = meta.status
                    break
                for ver, (path, st) in meta.versions.items():
                    if path == p:
                        matched_family = fam_name
                        version = ver
                        status = st
                        break
                if matched_family:
                    break
            return ParseResult(
                valid=True,
                fields=_extract_fields(name, schema),
                version=version,
                status=status,
                match_family=matched_family or product_hint,
            )
        if near_miss is None:
            mismatch = _explain_match_failure(name, schema)
            if mismatch:
                field, expected, value = mismatch
                near_miss = ParseError(field, expected, value)

    # Nothing matched — provide a helpful error listing what we saw
    with as_file(files(pkg).joinpath(SCHEMAS_ROOT)) as rp:
        base = Path(rp)
        seen = [str(q.relative_to(base)) for q in base.rglob("*filename_v*.json")] if base.exists() else []
    msg = (
        "No schema matched the provided name. "
        f"Looked recursively under {pkg}/{SCHEMAS_ROOT}/ and found "
        f"{len(seen)} file(s): {seen[:8]}{'…' if len(seen) > 8 else ''}"
    )
    if near_miss is not None:
        raise near_miss
    if first_error is not None:
        msg += f". First error while reading schemas: {first_error}"
        raise RuntimeError(msg) from first_error
    raise RuntimeError(msg)


def validate_schema(
    paths: Union[str, Path, Iterable[Union[str, Path]], None] = None,
    pkg: str = __package__,
    verbose: bool = False,
) -> None:
    """Validate example filenames declared in schema files.

    Parameters
    ----------
    paths: Union[str, Path, Iterable[Union[str, Path]]], optional
        Specific schema JSON file(s) to validate. Accepts either a single path
        or an iterable of paths. When omitted, all bundled schemas for *pkg*
        are checked.
    pkg: str, optional
        Package name from which to discover schemas when *paths* is ``None``.
    verbose: bool, optional
        When ``True``, print each schema path and example as they are validated,
        along with a summary count of successful validations.

    Raises
    ------
    ValueError
        If an example cannot be parsed or fails to reassemble to the original
        string.
    """

    _get_schema_paths.cache_clear()
    if paths is None:
        schema_paths = _get_schema_paths(pkg)
    elif isinstance(paths, (str, Path)):
        schema_paths = [Path(paths)]
    else:
        schema_paths = [Path(p) for p in paths]

    from .assembler import assemble  # local import to avoid cycle

    validated = 0
    for schema_path in schema_paths:
        if verbose:
            print(schema_path)
        schema = _load_json_from_path(schema_path)
        examples = schema.get("examples")
        if not isinstance(examples, list):
            continue
        for example in examples:
            if not isinstance(example, str):
                continue
            res = parse_auto(example)
            if not res.valid:
                raise ValueError(f"Parsing failed for {example}")
            fields = {k: v for k, v in res.fields.items() if v is not None}
            assembled = assemble(fields, schema_path=schema_path)
            if assembled != example:
                raise ValueError(f"Round trip failed for {example}")
            validated += 1
            if verbose:
                print(f"  {example}")
    if verbose:
        print(f"Validated {validated} examples")

