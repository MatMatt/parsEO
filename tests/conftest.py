import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

def load_schema_by_name(root_dir: str, fname: str):
    root = pathlib.Path(root_dir)
    for p in root.rglob(fname):
        return json.loads(p.read_text(encoding="utf-8")), p
    raise FileNotFoundError(f"Could not locate schema file '{fname}' under {root_dir}")

def match_example(pattern: str, example: str):
    rx = re.compile(pattern)
    return bool(rx.match(example))


def schema_examples_list():
    """Return a list of (schema_path, example) tuples for all schemas."""
    root = pathlib.Path(__file__).resolve().parents[1] / "src/parseo/schemas"
    examples = []
    for p in root.rglob("*.json"):
        if p.name == "index.json":
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for ex in data.get("examples", []):
            examples.append((p, ex))
    return examples
