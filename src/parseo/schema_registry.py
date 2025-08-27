from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path
from typing import Dict, Iterator, Optional
import json
import re

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


@lru_cache(maxsize=1)
def _load_index(pkg: str) -> Dict[str, list[dict]]:
    res = files(pkg).joinpath(SCHEMAS_ROOT, "index.json")
    with as_file(res) as p:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"Schema index not found for package {pkg}")
        return json.loads(path.read_text())


def get_schema_path(family: str, version: str | None = None, pkg: str = __package__) -> Path:
    """Return filesystem path to schema for *family* and *version*.

    If *version* is ``None``, the entry marked as ``status == 'current'`` is used.
    """

    fam = family.upper()
    index = _load_index(pkg)
    entries = index.get(fam)
    if entries is None:
        raise KeyError(f"Unknown family: {family}")

    chosen = None
    if version is None:
        for ent in entries:
            if ent.get("status") == "current":
                chosen = ent
                break
    else:
        for ent in entries:
            if ent.get("version") == version:
                chosen = ent
                break
    if chosen is None:
        avail = ", ".join(e.get("version") for e in entries)
        if version is None:
            raise RuntimeError(
                f"No version marked as 'current' for family {family}. Available: {avail}"
            )
        raise KeyError(
            f"Version {version!r} not found for family {family}. Available: {avail}"
        )

    res = files(pkg).joinpath(SCHEMAS_ROOT, chosen["file"])
    with as_file(res) as p:
        return Path(p)
