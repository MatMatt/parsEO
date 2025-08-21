# src/parseo/assembler.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def _load_schema(schema_path: str | Path) -> Dict[str, Any]:
    p = Path(schema_path)
    txt = p.read_text(encoding="utf-8")
    if txt.startswith("\ufeff"):
        txt = txt.lstrip("\ufeff")
    return json.loads(txt)


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
