from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json(path: str | Path) -> Dict[str, Any]:
    """Load a JSON file, handling optional UTF-8 BOM."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    return json.loads(text)
