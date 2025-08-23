"""Utility helpers for working with filename templates."""

from typing import Any, Dict, Optional


def merge_fields(
    fields: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge ``fields`` with optional ``defaults``.

    Parameters
    ----------
    fields:
        Mandatory mapping of field names to values.
    defaults:
        Optional default values.  When provided, they are updated with the
        values from ``fields`` and the merged dictionary is returned.

    Returns
    -------
    Dict[str, Any]
        The merged mapping of field values.
    """
    if defaults:
        merged = defaults.copy()
        merged.update(fields)
        return merged
    return dict(fields)
