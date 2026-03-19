#!/usr/bin/env python3
import pathlib
import sys


BEGIN_PREFIX = "@@BEGIN_FILE@@ path="
END_MARKER = "@@END_FILE@@"
FATAL_MARKER = "@@FATAL@@"


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} SERIAL_LOG OUT_DIR", file=sys.stderr)
        return 1

    serial_log = pathlib.Path(argv[1]).resolve()
    out_dir = pathlib.Path(argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    text = serial_log.read_text(errors="replace")
    current_path = None
    buffer = []
    files_written = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if FATAL_MARKER in line:
            print(f"fatal marker found in serial log: {line}", file=sys.stderr)
            return 2
        if line.startswith(BEGIN_PREFIX):
            if current_path is not None:
                print(f"nested begin marker in serial log: {line}", file=sys.stderr)
                return 3
            relpath = line[len(BEGIN_PREFIX):].strip()
            current_path = out_dir / relpath
            current_path.parent.mkdir(parents=True, exist_ok=True)
            buffer = []
            continue
        if line == END_MARKER:
            if current_path is None:
                print("end marker without begin marker", file=sys.stderr)
                return 4
            current_path.write_text("".join(buffer))
            files_written += 1
            current_path = None
            buffer = []
            continue
        if current_path is not None:
            buffer.append(line + "\n")

    if current_path is not None:
        print("serial log ended before end marker", file=sys.stderr)
        return 5
    if files_written == 0:
        print("no structured files found in serial log", file=sys.stderr)
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
