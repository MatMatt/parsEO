"""Utilities for translating between schema tokens and STAC values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Mapping

from ._epsg_lookup import landsat_path_row_to_epsg
from ._epsg_lookup import mgrs_tile_to_epsg


@dataclass(frozen=True)
class FieldMapping:
    """Represents a mapping between a filename token and STAC fields."""

    preserve_as: str
    token_map: Dict[str, Dict[str, Any]]


def _normalize_mapping_values(values: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for token, targets in values.items():
        if not isinstance(targets, Mapping):
            continue
        normalized[str(token)] = {str(k): v for k, v in targets.items()}
    return normalized


def get_schema_field_mappings(schema: Mapping[str, Any]) -> Dict[str, FieldMapping]:
    """Extract field mappings declared in *schema*."""

    fields = schema.get("fields", {})
    if not isinstance(fields, Mapping):
        return {}

    mappings: Dict[str, FieldMapping] = {}
    for field_name, spec in fields.items():
        if not isinstance(spec, Mapping):
            continue
        raw_map = spec.get("stac_map")
        if not isinstance(raw_map, Mapping):
            continue

        preserve_as = raw_map.get("preserve_original_as")
        values: Any
        if "values" in raw_map:
            values = raw_map.get("values")
        else:
            values = raw_map
        if not isinstance(values, Mapping):
            continue

        normalized = _normalize_mapping_values(values)
        if not normalized:
            continue

        if not isinstance(preserve_as, str) or not preserve_as:
            preserve_as = f"{field_name}_code"

        mappings[str(field_name)] = FieldMapping(preserve_as=preserve_as, token_map=normalized)

    return mappings


def apply_schema_mappings(
    extracted: Dict[str, Any], schema: Mapping[str, Any]
) -> Dict[str, Any]:
    """Augment *extracted* fields with STAC values defined in *schema*."""

    mappings = get_schema_field_mappings(schema)

    enriched = dict(extracted)
    for field_name, mapping in mappings.items():
        token = extracted.get(field_name)
        if token is None:
            continue

        enriched[mapping.preserve_as] = token

        targets = mapping.token_map.get(str(token))
        if not isinstance(targets, Mapping):
            continue

        for target_field, target_value in targets.items():
            enriched[target_field] = target_value

    schema_id = str(schema.get("schema_id", "")).lower()

    if "epsg_code" not in enriched:
        tile = enriched.get("mgrs_tile")
        if tile and "sentinel:s2" in schema_id:
            epsg = mgrs_tile_to_epsg(str(tile))
            if epsg:
                enriched["epsg_code"] = epsg

    if "epsg_code" not in enriched:
        path = enriched.get("wrs_path")
        row = enriched.get("wrs_row")
        if path and row and schema_id.startswith("usgs:landsat"):
            epsg = landsat_path_row_to_epsg(str(path), str(row))
            if epsg:
                enriched["epsg_code"] = epsg

    return enriched


def translate_fields_to_tokens(
    fields: Dict[str, Any], schema: Mapping[str, Any]
) -> Dict[str, Any]:
    """Translate STAC field values in *fields* back to schema tokens."""

    mappings = get_schema_field_mappings(schema)
    if not mappings:
        return fields

    translated = dict(fields)
    for field_name, mapping in mappings.items():
        token: Any = None

        preserved = fields.get(mapping.preserve_as)
        if preserved not in (None, ""):
            token = str(preserved)

        if token is None:
            current_value = fields.get(field_name)
            if isinstance(current_value, str) and current_value in mapping.token_map:
                token = current_value

        if token is None:
            for candidate, targets in mapping.token_map.items():
                if all(fields.get(k) == v for k, v in targets.items()):
                    token = candidate
                    break

        if token is None:
            continue

        translated[field_name] = token

    return translated

