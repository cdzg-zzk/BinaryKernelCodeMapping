#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CACHE_DIR="$TEST_DIR/.cache"
VENDOR_DIR="$TEST_DIR/vendor/lz4-1.9.3"
ARCHIVE="$CACHE_DIR/lz4-1.9.3.tar.gz"
URL="https://github.com/lz4/lz4/archive/refs/tags/v1.9.3.tar.gz"
SHA256="030644df4611007ff7dc962d981f390361e6c97a34e5cbc393ddfbe019ffe2c1"

mkdir -p "$CACHE_DIR"
if [[ ! -f "$ARCHIVE" ]]; then
    curl -L --fail --retry 3 "$URL" -o "$ARCHIVE"
fi
printf '%s  %s\n' "$SHA256" "$ARCHIVE" | sha256sum -c -

tmp="$(mktemp -d "$CACHE_DIR/lz4-extract.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$ARCHIVE" -C "$tmp"
rm -rf "$VENDOR_DIR"
mkdir -p "$VENDOR_DIR/lib"
cp "$tmp/lz4-1.9.3/lib/lz4.c" "$VENDOR_DIR/lib/"
cp "$tmp/lz4-1.9.3/lib/lz4.h" "$VENDOR_DIR/lib/"
cp "$tmp/lz4-1.9.3/LICENSE" "$VENDOR_DIR/"
echo "vendored LZ4 1.9.3 into $VENDOR_DIR"

