import argparse, json, os, sys
from .parser import parse_auto

def main():
    ap = argparse.ArgumentParser(description="Parse EO filenames using bundled schemas.")
    ap.add_argument("filename", nargs="?", help="Filename to parse")
    ap.add_argument("--scan", metavar="DIR", help="Scan a directory of files")
    ap.add_argument("--debug", action="store_true", help="Verbose output")
    args = ap.parse_args()

    if args.scan:
        root = args.scan
        if not os.path.isdir(root):
            print(f"Not a directory: {root}", file=sys.stderr)
            sys.exit(2)
        ok = 0
        miss = 0
        for _, _, files in os.walk(root):
            for fn in files:
                res = parse_auto(fn)
                if res:
                    ok += 1
                    if args.debug:
                        print(f"[OK] {fn} -> {res.schema_name}")
                else:
                    miss += 1
                    print(f"[--] {fn} -> no match")
        print(f"Summary: {ok} matched, {miss} no match")
        return

    if not args.filename:
        ap.error("Provide a filename or use --scan DIR")

    result = parse_auto(args.filename)
    if result is None:
        print("No schema matched ❌")
        sys.exit(1)

    print(f"Matched schema: {result.schema_name}")
    print(json.dumps(result.fields, indent=2))

if __name__ == "__main__":
    main()
