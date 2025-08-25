from .parser import parse_auto
from .assembler import assemble, assemble_auto, clear_schema_cache
from .stac_scraper import scrape_catalog

__all__ = [
    "parse_auto",
    "assemble",
    "assemble_auto",
    "clear_schema_cache",
    "scrape_catalog",
]

try:  # pragma: no cover - import failure handled for graceful degradation
    from . import parser  # noqa: F401  # import for side effect and re-export
except Exception:  # ImportError and others
    pass
else:
    __all__.append("parser")
