from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from functools import lru_cache
from importlib.resources import as_file
from importlib.resources import files
from pathlib import Path
import re
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Union

from ._json import load_json

SCHEMAS_ROOT = "schemas"


@lru_cache(maxsize=256)
def _load_json_from_path(path: Path) -> Dict:
    return load_json(path)


def _iter_schema_paths(pkg: str) -> Iterator[Path]:
    """Yield all schema JSON files recursively for *pkg*."""
    root = files(pkg).joinpath(SCHEMAS_ROOT)
    with as_file(root) as root_path:
        base = Path(root_path)
        if not base.exists():
            return
        yield from (p for p in base.rglob("*filename_v*.json") if p.is_file())


@lru_cache(maxsize=32)
def _get_schema_paths(pkg: str) -> list[Path]:
    return list(_iter_schema_paths(pkg))


def _family_tokens_from_name(family: str) -> tuple[str, ...]:
    fam = family.upper()
    tokens = {fam}
    m = re.fullmatch(r"S(\d+)([A-Z]*)", fam)
    if m:
        num, suffix = m.groups()
        tokens.add(f"SENTINEL-{num}{suffix}")
    return tuple(tokens)


@dataclass(frozen=True)
class _FamilyInfo:
    """Metadata about a mission family discovered from schema files."""

    tokens: tuple[str, ...]
    schema_path: Path
    version: Optional[str] = None
    status: Optional[str] = None
    versions: Dict[str, tuple[Path, Optional[str]]] = field(default_factory=dict)


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
        for ver, (p, st) in sorted(versions.items(), reverse=True):
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


def discover_families(pkg: str = __package__) -> Dict[str, dict]:
    """Return mapping of family name to version metadata."""

    info = _discover_family_info(pkg)
    out: Dict[str, dict] = {}
    for fam, meta in info.items():
        out[fam] = {
            "current": meta.version,
            "path": meta.schema_path,
            "versions": {
                ver: {"path": p, "status": st} for ver, (p, st) in meta.versions.items()
            },
        }
    return out


def list_schema_families(pkg: str = __package__) -> list[str]:
    """Return a sorted list of available mission families."""
    return sorted(discover_families(pkg).keys())


def list_schema_versions(family: str, pkg: str = __package__) -> list[dict]:
    """Return version descriptors for *family*."""
    fam = family.upper()
    info = discover_families(pkg)
    meta = info.get(fam)
    if meta is None:
        raise KeyError(f"Unknown family: {family}")
    versions = []
    for ver, data in sorted(meta["versions"].items()):
        versions.append(
            {
                "version": ver,
                "status": data.get("status"),
                "file": str(data.get("path")),
            }
        )
    return versions


@lru_cache(maxsize=256)
def get_schema_path(
    family: str, version: Union[str, None] = None, pkg: str = __package__
) -> Path:
    """Return filesystem path to schema for *family* and *version*.

    If *version* is ``None`` the schema version marked as ``current`` is used.
    """

    fam = family.upper()
    info = _discover_family_info(pkg)
    meta = info.get(fam)
    if meta is None:
        raise KeyError(f"Unknown family: {family}")

    if version is None:
        return meta.schema_path

    path_status = meta.versions.get(version)
    if path_status is None:
        avail = ", ".join(sorted(meta.versions))
        raise KeyError(
            f"Version {version!r} not found for family {family}. Available: {avail}"
        )
    path, _status = path_status
    return path


def clear_cache() -> None:
    """Clear internal caches used by the schema registry.

    This helper is primarily intended for tests that need to add or modify
    schema files at runtime.
    """

    _load_json_from_path.cache_clear()
    _get_schema_paths.cache_clear()
    _discover_family_info.cache_clear()
    get_schema_path.cache_clear()
