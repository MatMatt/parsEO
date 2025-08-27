# src/parseo/parser.py
from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files, as_file
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Iterable
import re
from functools import lru_cache
from ._json import load_json
from .template import compile_template, _field_regex

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


@dataclass(frozen=True)
class ParseError(Exception):
    """Raised when a filename nearly matches a schema but fails on a field."""

    field: str
    expected: str
    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"Invalid value '{self.value}' for field '{self.field}': expected {self.expected}"
        )


@dataclass(frozen=True)
class _FamilyInfo:
    """Metadata about a mission family discovered from schema files."""

    tokens: tuple[str, ...]
    schema_path: Path
    version: Optional[str] = None
    status: Optional[str] = None
    versions: Dict[str, tuple[Path, Optional[str]]] = field(default_factory=dict)


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
        yield from (p for p in base.rglob("*filename_v*.json") if p.is_file())


@lru_cache(maxsize=32)
def _get_schema_paths(pkg: str) -> list[Path]:
    """Return all schema JSON paths for ``pkg``.

    The result is cached to avoid repeated filesystem scans when parsing
    multiple filenames.
    """
    return list(_iter_schema_paths(pkg))


def _family_tokens_from_name(family: str) -> tuple[str, ...]:
    """Return tokens used to hint the family from a filename prefix."""

    fam = family.upper()
    tokens = {fam}
    m = re.fullmatch(r"S(\d+)([A-Z]*)", fam)
    if m:
        num, suffix = m.groups()
        tokens.add(f"SENTINEL-{num}{suffix}")
    return tuple(tokens)


@lru_cache(maxsize=1)
def _discover_family_info(pkg: str) -> Dict[str, _FamilyInfo]:
    """Scan schema JSON files to discover mission families and versions."""

    families: Dict[str, Dict[str, tuple[Path, Optional[str]]]] = {}
    for path in _get_schema_paths(pkg):
        if "filename_v" not in path.name:
            continue
        try:
            data = _load_json_from_path(path)
        except Exception:
            continue
        schema_id = data.get("schema_id")
        version = data.get("schema_version")
        status = data.get("status", "current")
        if not isinstance(schema_id, str) or not isinstance(version, str):
            continue
        family = schema_id.split(":")[-1].upper()
        fam_versions = families.setdefault(family, {})
        fam_versions[version] = (path, status)

    info: Dict[str, _FamilyInfo] = {}

    for family, versions in families.items():
        current_version = None
        current_path = None
        current_status = None
        for ver, (p, st) in versions.items():
            if st == "current":
                current_version = ver
                current_path = p
                current_status = st
                break
        if current_path is None:
            available = ", ".join(sorted(versions))
            raise RuntimeError(
                f"No schema version marked as 'current' for family {family}. "
                f"Available versions: {available}"
            )
        info[family] = _FamilyInfo(
            tokens=_family_tokens_from_name(family),
            schema_path=current_path,
            version=current_version,
            status=current_status,
            versions=versions,
        )
    return info


# ---------------------------
# Core helpers
# ---------------------------

@lru_cache(maxsize=256)
def _load_json_from_path(path: Path) -> Dict:
    return load_json(path)


@lru_cache(maxsize=512)
def _compile_pattern(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def _pattern_from_schema(schema: Dict) -> Optional[str]:
    """Return a compiled regex pattern derived from schema's template.

    The result is cached inside the schema object. If a ``template`` key is
    present it is compiled via :func:`compile_template`. Otherwise a legacy
    ``filename_pattern`` is used as-is.
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

    patt = schema.get("filename_pattern")
    if isinstance(patt, str):
        schema["_compiled_pattern"] = patt
        return patt

    return None


def _match_filename(name: str, schema: Dict) -> Optional[re.Match]:
    patt = _pattern_from_schema(schema)
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
                value = m_field.group(0)
            else:
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

    info = _discover_family_info(pkg)
    return sorted(info.keys())


def describe_schema(family: str, pkg: str = __package__) -> dict[str, Any]:
    """Return schema metadata and field descriptions for ``family``."""

    info = _discover_family_info(pkg)
    meta = info.get(family.upper())
    if meta is None:
        raise KeyError(f"Unknown family: {family}")

    schema = _load_json_from_path(meta.schema_path)
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
                raise ParseError(field, expected, value)
        except ParseError:
            raise
        except Exception:
            # If hinted schema is unreadable, fall back to brute force
            pass

    # Fallback: brute-force across all schemas (recursive)
    candidates = _get_schema_paths(pkg)
    if not candidates:
        # No schema files packaged at all
        raise FileNotFoundError(f"No schemas packaged under {pkg}/{SCHEMAS_ROOT}.")

    first_error: Optional[Exception] = None
    near_miss: Optional[ParseError] = None
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


def validate_schema_examples(
    paths: Iterable[str | Path] | None = None,
    pkg: str = __package__,
) -> None:
    """Validate example filenames declared in schema files.

    Parameters
    ----------
    paths: Iterable[str | Path], optional
        Specific schema JSON files to validate. When omitted, all bundled
        schemas for *pkg* are checked.
    pkg: str, optional
        Package name from which to discover schemas when *paths* is ``None``.

    Raises
    ------
    ValueError
        If an example cannot be parsed or fails to reassemble to the original
        string.
    """

    _get_schema_paths.cache_clear()
    schema_paths = [Path(p) for p in paths] if paths else _get_schema_paths(pkg)

    from .assembler import assemble  # local import to avoid cycle

    for schema_path in schema_paths:
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
            assembled = assemble(schema_path, fields)
            if assembled != example:
                raise ValueError(f"Round trip failed for {example}")

