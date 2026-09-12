#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPU="${CPU:-2}"
RESULT_DIR="${RESULT_DIR:-$SCRIPT_DIR/results}"
BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
WORK_DIR="${WORK_DIR:-$SCRIPT_DIR/work}"
MANIFEST="${MANIFEST:?MANIFEST is required}"
REPEATS="${REPEATS:-20}"
OUTER_RUNS="${OUTER_RUNS:-5}"

mapfile -t kernel_candidates < <(
    find "$WORK_DIR/vkso/lib" -maxdepth 1 -type f -name 'lib*.so' \
        ! -name 'libshim.so' -print
)
(( ${#kernel_candidates[@]} == 1 )) || {
    echo "expected one generated kernel library, found ${#kernel_candidates[@]}" >&2
    exit 1
}
KERNEL_LIBRARY="${kernel_candidates[0]}"
NATIVE_LIBRARY="$BUILD_DIR/libxz-native.so"
PAGE_MAP="$WORK_DIR/vkso/metadata/page_mappings.txt"

python3 "$SCRIPT_DIR/scripts/audit_kernel_dso.py" \
    --library "$KERNEL_LIBRARY" \
    --page-map "$PAGE_MAP" \
    --report "$RESULT_DIR/kernel-dso-audit.md"

bench_inputs=()
while IFS=, read -r label plain compressed; do
    [[ -z "$label" || "$label" == \#* ]] && continue
    bench_inputs+=("$label" "$plain" "$compressed")
done <"$MANIFEST"
(( ${#bench_inputs[@]} > 0 )) || {
    echo "corpus manifest is empty: $MANIFEST" >&2
    exit 1
}

export LD_LIBRARY_PATH="$WORK_DIR/vkso/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
taskset -c "$CPU" "$BUILD_DIR/xz-bench" \
    --native "$NATIVE_LIBRARY" \
    --kernel "$KERNEL_LIBRARY" \
    --repeats "$REPEATS" \
    --outer-runs "$OUTER_RUNS" \
    -- "${bench_inputs[@]}" >"$RESULT_DIR/raw.csv"

python3 "$SCRIPT_DIR/scripts/summarize.py" \
    --input "$RESULT_DIR/raw.csv" \
    --aggregate "$RESULT_DIR/aggregate.csv" \
    --summary "$RESULT_DIR/summary.md"

readelf -dW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-dynamic.txt"
readelf -rW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-relocations.txt"
nm -D "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-symbols.txt"
cp "$PAGE_MAP" "$RESULT_DIR/kernel-page-mappings.txt"
cp "$WORK_DIR/vkso/metadata/resolved_symbol_addresses.txt" \
    "$RESULT_DIR/kernel-resolved-symbols.txt"
cp "$WORK_DIR/vkso/metadata/module_deps.txt" \
    "$RESULT_DIR/kernel-module-deps.txt"
printf '%s\n' "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-library-path.txt"
printf 'runtime_page_view_sha256=%s\n' \
    "$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)" \
    >"$RESULT_DIR/kernel-hash-views.txt"
sha256sum "$BUILD_DIR/xz-bench" "$NATIVE_LIBRARY" \
    "$WORK_DIR/vkso/lib/libshim.so" >"$RESULT_DIR/artifacts.sha256"
