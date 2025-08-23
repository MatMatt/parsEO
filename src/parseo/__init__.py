from .parser import parse_auto
from .assembler import assemble, assemble_auto

__all__ = ["parse_auto", "assemble", "assemble_auto"]

try:  # pragma: no cover - import failure handled for graceful degradation
    from . import parser  # noqa: F401  # import for side effect and re-export
except Exception:  # ImportError and others
    pass
else:
    __all__.append("parser")
