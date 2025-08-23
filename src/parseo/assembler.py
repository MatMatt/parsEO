# src/parseo/assembler.py
from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, Dict

from ._json import load_json


SCHEMAS_ROOT = "schemas"


def _load_schema(schema_path: str | Path) -> Dict[str, Any]:
    return load_json(schema_path)


def assemble(schema_path: str | Path, fields: Dict[str, Any]) -> str:
    """
    Assemble a filename using a JSON schema:
      - schema['fields_order'] defines the order of fields
      - Optional schema['joiner'] defines how parts are joined (default '_')
      - If a field is missing in 'fields', raise a clear error
      - If the last field is literally named 'extension' and looks like '.ext',
        no extra dot is added; it is appended as-is
    """
    sch = _load_schema(schema_path)
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

    # If the last part looks like an extension (e.g., '.SAFE'), it is already included.
    # Otherwise, the schema can include 'extension' in fields_order to ensure correctness.
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
