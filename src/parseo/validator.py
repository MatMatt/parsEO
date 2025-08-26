from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import List, Tuple

from . import parser


def validate_schema_examples(pkg: str = __package__) -> List[Tuple[Path, str, str]]:
    """Validate all schema examples by round-tripping them.

    Parameters
    ----------
    pkg:
        Package name that contains the ``schemas`` directory. Defaults to the
        current package.

    Returns
    -------
    list of tuple
        Empty when all examples parse and reassemble successfully.

    Raises
    ------
    RuntimeError
        If one or more examples fail to validate. The raised ``RuntimeError``
        summarises all failures as ``(schema_path, example, error)`` tuples.
    """
    failures: List[Tuple[Path, str, str]] = []

    # Discover schema files using the parser's helper
    paths = parser._get_schema_paths(pkg)

    # Import the package dynamically to access its public helpers
    pkg_mod = import_module(pkg)
    parse_auto = getattr(pkg_mod, "parse_auto")
    assemble_auto = getattr(pkg_mod, "assemble_auto")

    for path in paths:
        try:
            schema = parser._load_json_from_path(path)
        except Exception as exc:  # pragma: no cover - defensive
            failures.append((path, "<schema>", f"failed to load schema: {exc}"))
            continue

        examples = schema.get("examples") or []
        for example in examples:
            if not isinstance(example, str):
                continue
            try:
                result = parse_auto(example)
                rebuilt = assemble_auto(result.fields)
                if rebuilt != example:
                    failures.append(
                        (path, example, f"round-trip mismatch: {rebuilt!r}")
                    )
            except Exception as exc:  # pragma: no cover - depends on schemas
                failures.append((path, example, str(exc)))

    if failures:
        lines = [f"{p}: {ex} -> {err}" for p, ex, err in failures]
        raise RuntimeError(
            "Schema example validation failed:\n" + "\n".join(lines)
        )

    return failures
