#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPU="${CPU:-2}"
RESULT_DIR="${RESULT_DIR:-$SCRIPT_DIR/results}"
BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
WORK_DIR="${WORK_DIR:-$SCRIPT_DIR/work}"
OUTER_RUNS="${OUTER_RUNS:-11}"
SAMPLE_MS="${SAMPLE_MS:-10}"
CORRECTNESS_VECTORS="${CORRECTNESS_VECTORS:-128}"
MODULE="${MODULE:?MODULE is required}"

mapfile -t kernel_candidates < <(
    find "$WORK_DIR/vkso/lib" -maxdepth 1 -type f -name 'lib*.so' \
        ! -name 'libshim.so' -print
)
(( ${#kernel_candidates[@]} == 1 )) || {
    echo "expected one generated kernel library, found ${#kernel_candidates[@]}" >&2
    exit 1
}
KERNEL_LIBRARY="${kernel_candidates[0]}"

diagnostic_args=()
if [[ "${BCH_ALIGNED_INPUTS:-0}" == 1 ]]; then
    diagnostic_args+=(--aligned-inputs)
fi
taskset -c "$CPU" "$BUILD_DIR/bch-bench" "${diagnostic_args[@]}" \
    --kernel "$KERNEL_LIBRARY" \
    --kernel-native "$BUILD_DIR/libbch-kernel-native.so" \
    --standalone "$BUILD_DIR/libbch-author-standalone.so" \
    --correctness-vectors "$CORRECTNESS_VECTORS" \
    --outer "$OUTER_RUNS" \
    --sample-ms "$SAMPLE_MS" \
    --output "$RESULT_DIR/raw.csv" \
    >"$RESULT_DIR/benchmark.stdout.log" \
    2>"$RESULT_DIR/correctness-and-progress.log"

python3 "$SCRIPT_DIR/scripts/summarize.py" \
    --input "$RESULT_DIR/raw.csv" \
    --aggregate "$RESULT_DIR/aggregate.csv" \
    --paired "$RESULT_DIR/paired.csv" \
    --summary "$RESULT_DIR/summary.md"

readelf -dW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-dynamic.txt"
readelf -rW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-relocations.txt"
nm -D "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-symbols.txt"
nm -u "$MODULE" >"$RESULT_DIR/owner-module-undefined.txt"
readelf -rW "$MODULE" >"$RESULT_DIR/owner-module-relocations.txt"
objdump -drwC "$MODULE" >"$RESULT_DIR/owner-module-objdump.txt"
diff -u "$SCRIPT_DIR/vendor/linux-5.15/lib/bch.c" \
    "$SCRIPT_DIR/adapted/bch.c" >"$RESULT_DIR/kernel-source-adaptation.diff" || true

for name in page_mappings.txt resolved_symbol_addresses.txt module_deps.txt \
            functions_checker.log functions_checker_summary.txt; do
    if [[ -f "$WORK_DIR/vkso/metadata/$name" ]]; then
        cp "$WORK_DIR/vkso/metadata/$name" "$RESULT_DIR/kernel-$name"
    fi
done

python3 "$SCRIPT_DIR/scripts/audit_kernel_dso.py" \
    --library "$KERNEL_LIBRARY" \
    --module "$MODULE" \
    --page-map "$WORK_DIR/vkso/metadata/page_mappings.txt" \
    --output "$RESULT_DIR/kernel-dso-audit.md"

printf '%s\n' "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-library-path.txt"
printf 'path=%s\nruntime_page_view_sha256=%s\n' \
    "$KERNEL_LIBRARY" "$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)" \
    >"$RESULT_DIR/kernel-hash-views.txt"
sha256sum \
    "$BUILD_DIR/bch-bench" \
    "$BUILD_DIR/libbch-kernel-native.so" \
    "$BUILD_DIR/libbch-author-standalone.so" \
    "$WORK_DIR/vkso/lib/libshim.so" \
    "$MODULE" \
    >"$RESULT_DIR/artifacts.sha256"

# The complete user workload has ended; measure the same still-registered owner.
if [[ "${RUN_KERNEL_COST:-0}" == 1 ]]; then
    sudo -n python3 "$SCRIPT_DIR/../evaluation/kernel_cost_host.py" collect \
        --prepared "$RESULT_DIR/kernel-cost-prepared" --output "$RESULT_DIR/kernel-cost"
fi
