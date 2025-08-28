# src/parseo/assembler.py
from __future__ import annotations

from functools import lru_cache
from importlib.resources import as_file
from importlib.resources import files
from pathlib import Path
import re
from typing import Any
from typing import Dict
from typing import Union

from ._json import load_json
from .template import compile_template, _field_regex
from .schema_registry import get_schema_path


SCHEMAS_ROOT = "schemas"


@lru_cache(maxsize=None)
def _load_schema(schema_path: Union[str, Path]) -> Dict[str, Any]:
    return load_json(str(schema_path))


def clear_schema_cache() -> None:
    """Clear the cached schemas."""
    _load_schema.cache_clear()


def _assemble_from_template(template: str, fields: Dict[str, Any]) -> str:
    """Render *template* using *fields*.

    Optional segments denoted by ``[ ... ]`` are dropped if any enclosed field
    is missing. ``{field}`` placeholders are replaced by values from *fields*.
    """

    def render(segment: str) -> str:
        result = ""
        i = 0
        while i < len(segment):
            ch = segment[i]
            if ch == "{":
                j = segment.index("}", i)
                name = segment[i + 1 : j]
                if name not in fields:
                    raise KeyError(name)
                result += str(fields[name])
                i = j + 1
            elif ch == "[":
                depth = 1
                j = i + 1
                while j < len(segment) and depth:
                    if segment[j] == "[":
                        depth += 1
                    elif segment[j] == "]":
                        depth -= 1
                    j += 1
                inner = segment[i + 1 : j - 1]
                try:
                    result += render(inner)
                except KeyError:
                    pass
                i = j
            else:
                result += ch
                i += 1
        return result

    return render(template)


def _assemble_schema(schema_path: Union[str, Path], fields: Dict[str, Any]) -> str:
    """Assemble a filename using a JSON schema.

    Schemas must define a ``template`` string following parseo's mini-template
    syntax. The template is rendered using the provided *fields* and optional
    segments are dropped if any enclosed field is missing.
    """

    sch = _load_schema(schema_path)

    # Validate provided fields against schema definitions
    specs = sch.get("fields", {})
    for name, value in fields.items():
        spec = specs.get(name)
        if not spec:
            continue
        if "enum" in spec and str(value) not in spec["enum"]:
            raise ValueError(
                f"Field '{name}' must be one of {spec['enum']}, got {value!r}."
            )
        if "pattern" in spec:
            pattern = _field_regex({"pattern": spec["pattern"]})
            regex = re.compile(f"^{pattern}$")
            if not regex.match(str(value)):
                raise ValueError(
                    f"Field '{name}' with value {value!r} does not match pattern {spec['pattern']}."
                )

    template = sch.get("template")
    if not isinstance(template, str):
        raise ValueError(f"Schema {schema_path} missing 'template' string.")

    try:
        return _assemble_from_template(template, fields)
    except KeyError as exc:
        name = exc.args[0]
        raise ValueError(
            f"Missing field '{name}' for schema {schema_path}"
        ) from exc


def assemble(
    fields: Dict[str, Any],
    family: Union[str, None] = None,
    version: Union[str, None] = None,
    schema_path: Union[str, Path, None] = None,
) -> str:
    """Assemble a filename from *fields*.

    Provide either a *schema_path* or a schema *family* (with optional
    *version*) to select the schema. If neither is given the schema is
    auto-selected based on the supplied *fields*.
    """

    if schema_path is not None:
        return _assemble_schema(schema_path, fields)
    if family is not None:
        resolved = get_schema_path(family, version=version)
        return _assemble_schema(resolved, fields)
    return assemble_auto(fields)


def _iter_schema_paths() -> list[Path]:
    """Return all packaged schema JSON paths."""
    base = files(__package__).joinpath(SCHEMAS_ROOT)
    with as_file(base) as bp:
        root = Path(bp)
        return list(root.rglob("*.json"))


def _select_schema_by_first_compulsory(fields: Dict[str, Any]) -> Path:
    """Select the most appropriate schema based on provided fields.

    Eligibility requires the user to provide the first compulsory field as
    derived from the schema's template. Among eligible schemas the one with the
    largest overlap of provided keys is chosen. A longer field order acts as a
    tie breaker.
    """
    best: Union[tuple[int, int, str], None] = None
    best_path: Union[Path, None] = None
    seen_first_keys: set[str] = set()

    for p in _iter_schema_paths():
        try:
            sch = _load_schema(p)
        except Exception:
            continue

        template = sch.get("template")
        if not isinstance(template, str):
            continue
        _, order = compile_template(template, sch.get("fields", {}))
        sch["fields_order"] = order
        if not order:
            continue

        specs = sch.get("fields", {})
        first_key = None
        for name in order:
            spec = specs.get(name, {})
            enums = spec.get("enum")
            field_val = fields.get(name)
            if enums is not None:
                enums = [str(e) for e in enums]
                if len(enums) == 1 and field_val == enums[0]:
                    continue
                if field_val is not None and field_val not in enums:
                    first_key = None
                    break
                first_key = name
                break
            else:
                first_key = name
                break
        if not first_key:
            continue

        seen_first_keys.add(first_key)

        if first_key not in fields:
            continue

        overlap = sum(1 for k in fields.keys() if k in order)
        key = (overlap, len(order), str(p))
        if best is None or key > best:
            best = key
            best_path = p

    if not best_path:
        sample = ", ".join(sorted(seen_first_keys)) or "<no schemas found>"
        raise ValueError(
            "Could not select a schema. "
            "Include the schema's FIRST compulsory field among your inputs.\n"
            f"Examples of first fields from packaged schemas: {sample}"
        )

    return best_path


def assemble_auto(fields: Dict[str, Any]) -> str:
    """Assemble a filename by auto-selecting the appropriate schema."""
    schema_path = _select_schema_by_first_compulsory(fields)
    return _assemble_schema(str(schema_path), fields)
