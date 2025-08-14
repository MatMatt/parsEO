from __future__ import annotations
import json, re
from dataclasses import dataclass
from importlib import resources
from typing import Optional, Dict, Any, List, Tuple

SCHEMA_PACKAGE = "filenamingapi.schemas"

@dataclass
class ParsedFilename:
    schema_name: str
    fields: Dict[str, str]

def _load_schema(package: str, resource: str) -> Dict[str, Any]:
    with resources.files(package).joinpath(resource).open("r", encoding="utf-8") as f:
        return json.load(f)

def parse_with_schema(filename: str, schema: Dict[str, Any]) -> Optional[Dict[str, str]]:
    pattern = schema.get("filename_pattern")
    if not pattern:
        return None
    rx = re.compile(pattern, re.VERBOSE)
    m = rx.match(filename)
    return m.groupdict() if m else None

def iter_bundled_schemas() -> List[Tuple[str, str]]:
    return [
        ("sentinel", "sentinel1_filename_structure_unified.json"),
        ("sentinel", "sentinel2_filename_structure.json"),
        ("sentinel", "sentinel3_filename_structure.json"),
        ("sentinel", "sentinel4_filename_structure.json"),
        ("sentinel", "sentinel5_filename_structure.json"),
        ("sentinel", "sentinel5p_filename_structure.json"),
        ("sentinel", "sentinel6_filename_structure.json"),
        ("landsat",  "landsat_filename_structure.json"),
        ("landsat",  "landsat4_filename_structure.json"),
        ("landsat",  "landsat5_filename_structure.json"),
        ("landsat",  "landsat7_filename_structure.json"),
        ("landsat",  "landsat8_filename_structure.json"),
        ("landsat",  "landsat9_filename_structure.json"),
    ]

def parse_auto(filename: str) -> Optional[ParsedFilename]:
    for subpkg, resource in iter_bundled_schemas():
        pkg = f"{SCHEMA_PACKAGE}.{subpkg}"
        schema = _load_schema(pkg, resource)
        fields = parse_with_schema(filename, schema)
        if fields is not None:
            return ParsedFilename(schema_name=f"{subpkg}/{resource}", fields=fields)
    return None
