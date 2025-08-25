# src/parseo/assembler.py
from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
import re
from typing import Any, Dict
from functools import lru_cache

from ._json import load_json
from .template import compile_template, _field_regex


SCHEMAS_ROOT = "schemas"


@lru_cache(maxsize=None)
def _load_schema(schema_path: str | Path) -> Dict[str, Any]:
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


def assemble(schema_path: str | Path, fields: Dict[str, Any]) -> str:
    """Assemble a filename using a JSON schema.

    Schemas may define a ``template`` string following parseo's mini-template
    syntax. If present, the template is used for rendering the final filename.
    Otherwise the legacy ``fields_order`` + ``joiner`` approach is used.
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

    if isinstance(sch.get("template"), str):
        template = sch["template"]
        if not sch.get("fields_order"):
            _, order = compile_template(template, sch.get("fields", {}))
            sch["fields_order"] = order
        try:
            return _assemble_from_template(template, fields)
        except KeyError as exc:
            name = exc.args[0]
            raise ValueError(
                f"Missing field '{name}' for schema {schema_path}"
            ) from exc

    order = sch.get("fields_order")
    if not order or not isinstance(order, list):
        raise ValueError(f"Schema {schema_path} missing 'fields_order' list.")

    joiner = sch.get("joiner", "_")

    parts: list[str] = []
    for key in order:
        if key not in fields:
            raise ValueError(f"Missing field '{key}' required by schema {schema_path}.")
        val = fields[key]
        if not isinstance(val, (str, int, float)):
            raise ValueError(f"Field '{key}' must be string/number, got {type(val).__name__}.")
        parts.append(str(val))

    filename = joiner.join(parts)
    return filename


def _iter_schema_paths() -> list[Path]:
    """Return all packaged schema JSON paths."""
    base = files(__package__).joinpath(SCHEMAS_ROOT)
    with as_file(base) as bp:
        root = Path(bp)
        return list(root.rglob("*.json"))


def _select_schema_by_first_compulsory(fields: Dict[str, Any]) -> Path:
    """Select the most appropriate schema based on provided fields.

    Eligibility requires that the user provided the first compulsory field
    listed in ``fields_order``. Among eligible schemas the one with the
    largest overlap of provided keys is chosen. A longer ``fields_order``
    acts as a tie breaker.
    """
    best: tuple[int, int, str] | None = None
    best_path: Path | None = None
    seen_first_keys: set[str] = set()

    for p in _iter_schema_paths():
        try:
            sch = _load_schema(p)
        except Exception:
            continue

        order = sch.get("fields_order") or []
        if not order and isinstance(sch.get("template"), str):
            _, order = compile_template(sch["template"], sch.get("fields", {}))
            sch["fields_order"] = order
        if not order:
            continue

        first_key = order[0]
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
    return assemble(str(schema_path), fields)
