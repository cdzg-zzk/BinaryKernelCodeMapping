#!/usr/bin/env python3
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--replacement", required=True)
    args = ap.parse_args()

    path = Path(args.file)
    text = path.read_text()
    replacement = Path(args.replacement).read_text().rstrip() + "\n"

    start = text.find(args.start)
    end = text.find(args.end)
    if start != -1 and end != -1 and end > start:
        end += len(args.end)
        new_text = text[:start].rstrip() + "\n\n" + replacement + text[end:].lstrip()
    else:
        new_text = text.rstrip() + "\n\n" + replacement

    path.write_text(new_text)


if __name__ == "__main__":
    main()
