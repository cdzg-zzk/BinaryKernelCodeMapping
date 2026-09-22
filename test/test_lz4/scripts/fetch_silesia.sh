#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CACHE_DIR="$TEST_DIR/.cache"
CORPUS_DIR="$TEST_DIR/corpus/silesia"
ARCHIVE="$CACHE_DIR/silesia.zip"
URL="http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip"
SHA256="0626e25f45c0ffb5dc801f13b7c82a3b75743ba07e3a71835a41e3d9f63c77af"

mkdir -p "$CACHE_DIR"
if [[ ! -f "$ARCHIVE" ]]; then
    curl -L --fail --retry 3 "$URL" -o "$ARCHIVE"
fi
printf '%s  %s\n' "$SHA256" "$ARCHIVE" | sha256sum -c -

rm -rf "$CORPUS_DIR"
mkdir -p "$CORPUS_DIR"
python3 - "$ARCHIVE" "$CORPUS_DIR" <<'PY'
import pathlib
import sys
import zipfile

archive = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[2])
with zipfile.ZipFile(archive) as source:
    source.extractall(destination)
files = sorted(path for path in destination.rglob("*") if path.is_file())
(destination / "manifest.txt").write_text(
    "".join(f"{path.relative_to(destination)}\n" for path in files),
    encoding="utf-8",
)
print(f"extracted {len(files)} files into {destination}")
PY

