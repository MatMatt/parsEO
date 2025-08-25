"""Utility helpers for working with filename templates."""

import re
from typing import Any, Dict, List, Optional, Tuple


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
        Optional default values. When provided, they are updated with the
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


def _field_regex(spec: Optional[Dict[str, Any]]) -> str:

    """Return a regex for a field spec.

    If *spec* is missing or empty, a permissive pattern ``.+`` is used.
    Anchors in patterns are stripped so they integrate into larger regexes.
    """
    if not spec:
        return ".+"
    if "enum" in spec:
        return "(?:" + "|".join(re.escape(v) for v in spec["enum"]) + ")"
    pattern = spec.get("pattern")
    if pattern is None:
        raise KeyError("Field spec missing 'pattern' or 'enum'")
    if pattern.startswith("^"):
        pattern = pattern[1:]
    if pattern.endswith("$"):
        pattern = pattern[:-1]
    return pattern

def compile_template(
    template: str, fields: Dict[str, Dict[str, Any]]
) -> Tuple[str, List[str]]:

    """Compile *template* into a regex pattern and extract field order.

    ``{field}`` placeholders are replaced using patterns or enums from
    *fields*. Optional segments can be denoted with ``[ ... ]`` and will be
    converted into non-capturing optional groups. The returned pattern is
    anchored with ``^`` and ``$``.
    """
    order: List[str] = []

    def _compile(segment: str) -> str:
        result = ""
        i = 0
        while i < len(segment):
            ch = segment[i]
            if ch == "{":
                j = segment.index("}", i)
                name = segment[i + 1 : j]
                if name not in order:
                    order.append(name)
                regex = _field_regex(fields.get(name))
                result += f"(?P<{name}>{regex})"
                i = j + 1
            elif ch == "[":
                depth = 1
                j = i + 1
                while j < len(segment) and depth:
                    if segment[j] == "[":
                        depth += 1
                    elif segment[j] == "]":
                        depth -= 1
                    j += 1
                inner = segment[i + 1 : j - 1]
                result += f"(?:{_compile(inner)})?"
                i = j
            else:
                result += re.escape(ch)
                i += 1
        return result

    pattern = "^" + _compile(template) + "$"
    return pattern, order
