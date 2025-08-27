from .parser import parse_auto, validate_schema
from .assembler import assemble, assemble_auto, clear_schema_cache
from .schema_registry import (
    list_schema_families,
    list_schema_versions,
    get_schema_path,
)

__all__ = [
    "parse_auto",
    "assemble",
    "assemble_auto",
    "clear_schema_cache",
    "validate_schema",
    "list_schema_families",
    "list_schema_versions",
    "get_schema_path",
]

try:  # pragma: no cover - import failure handled for graceful degradation
    from . import parser  # noqa: F401  # import for side effect and re-export
except Exception:  # ImportError and others
    pass
else:
    __all__.append("parser")
