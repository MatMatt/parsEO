from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Union


def load_json(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a JSON file, handling optional UTF-8 BOM."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    return json.loads(text)
