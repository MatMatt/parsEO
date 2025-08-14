import argparse, json
from .parser import parse_auto

def main():
    ap = argparse.ArgumentParser(description="Parse EO filenames using bundled schemas.")
    ap.add_argument("filename", help="Filename to parse")
    args = ap.parse_args()

    result = parse_auto(args.filename)
    if result is None:
        print("No schema matched ")
        raise SystemExit(1)

    print(f"Matched schema: {result.schema_name}")
    print(json.dumps(result.fields, indent=2))
