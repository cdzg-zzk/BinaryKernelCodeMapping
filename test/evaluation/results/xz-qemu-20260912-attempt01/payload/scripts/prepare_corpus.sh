#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# < 3 )); then
    echo "usage: $0 OUTPUT_DIR MANIFEST INPUT..." >&2
    exit 2
fi

output_dir="$1"
manifest="$2"
shift 2

rm -rf "$output_dir"
mkdir -p "$output_dir"
: >"$manifest"

index=0
for source in "$@"; do
    [[ -f "$source" ]] || {
        echo "input is not a regular file: $source" >&2
        exit 1
    }
    label="$(printf '%s' "$(basename "$source")" | tr -c 'A-Za-z0-9._-' '_')"
    plain="$output_dir/case-$(printf '%02d' "$index")-$label"
    compressed="$plain.xz"
    cp -- "$source" "$plain"
    xz --threads=1 --check=crc32 --x86 --lzma2=dict=1MiB \
        -c "$plain" >"$compressed"
    printf '%s,%s,%s\n' "$label" "$plain" "$compressed" >>"$manifest"
    index=$((index + 1))
done
