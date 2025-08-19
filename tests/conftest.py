
import json, re, pathlib

def load_schema_by_name(root_dir: str, fname: str):
    root = pathlib.Path(root_dir)
    for p in root.rglob(fname):
        return json.loads(p.read_text(encoding="utf-8")), p
    raise FileNotFoundError(f"Could not locate schema file '{fname}' under {root_dir}")

def match_example(pattern: str, example: str):
    rx = re.compile(pattern)
    return bool(rx.match(example))
