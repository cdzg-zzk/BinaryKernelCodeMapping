#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPU="${CPU:-2}"
RESULT_DIR="${RESULT_DIR:-$SCRIPT_DIR/results}"
BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
WORK_DIR="${WORK_DIR:-$SCRIPT_DIR/work}"
MANIFEST="${MANIFEST:?MANIFEST is required}"
OUTER_RUNS="${OUTER_RUNS:-3}"
BENCH_SECONDS="${BENCH_SECONDS:-1}"
BLOCK_SIZES="${BLOCK_SIZES:-4096,65536,1048576}"
USER_DEFAULT="$BUILD_DIR/liblz4-default.so"
USER_NOSIMD="$BUILD_DIR/liblz4-nosimd.so"
KERNEL_USER_NATIVE="$BUILD_DIR/libkernel-userspace-native.so"
KERNEL_USER_NOSIMD="$BUILD_DIR/libkernel-userspace-nosimd.so"
BENCH="$BUILD_DIR/lz4-bench"
OFFICIAL_BENCH="$BUILD_DIR/official-lz4-bench"

mapfile -t kernel_candidates < <(
    find "$WORK_DIR/vkso/lib" -maxdepth 1 -type f -name 'lib*.so' \
        ! -name 'libshim.so' -print
)
(( ${#kernel_candidates[@]} == 1 )) || {
    echo "expected one generated kernel library, found ${#kernel_candidates[@]}" >&2
    exit 1
}
KERNEL_LIBRARY="${kernel_candidates[0]}"

common_args=(
    --user-default "$USER_DEFAULT"
    --user-nosimd "$USER_NOSIMD"
    --kernel-user-native "$KERNEL_USER_NATIVE"
    --kernel-user-nosimd "$KERNEL_USER_NOSIMD"
    --kernel "$KERNEL_LIBRARY"
)

if [[ "${GDB_CORRECTNESS:-0}" == 1 ]]; then
    taskset -c "$CPU" gdb -q -batch \
        -ex 'set environment VKSO_TRACE_CORRECTNESS=1' \
        -ex run -ex 'thread apply all bt full' \
        -ex 'info registers' -ex 'x/24i $rip-24' \
        --args "$BENCH" "${common_args[@]}" --correctness \
        >"$RESULT_DIR/correctness-gdb.log" 2>&1
    exit 1
else
    VKSO_TRACE_CORRECTNESS=1 taskset -c "$CPU" "$BENCH" \
        "${common_args[@]}" --correctness \
        >"$RESULT_DIR/correctness.log" \
        2>"$RESULT_DIR/correctness-trace.log"
fi

manifest_dir="$(dirname "$MANIFEST")"
corpus_files=()
while IFS= read -r entry; do
    [[ -z "$entry" || "$entry" == \#* ]] && continue
    if [[ "$entry" == /* ]]; then
        corpus_files+=("$entry")
    else
        corpus_files+=("$manifest_dir/$entry")
    fi
done <"$MANIFEST"
(( ${#corpus_files[@]} > 0 )) || {
    echo "manifest contains no corpus files: $MANIFEST" >&2
    exit 1
}

backend_names=(
    user-default
    user-nosimd
    kernel-userspace-native
    kernel-userspace-nosimd
    kernel-vkso
)
backend_paths=(
    "$USER_DEFAULT"
    "$USER_NOSIMD"
    "$KERNEL_USER_NATIVE"
    "$KERNEL_USER_NOSIMD"
    "$KERNEL_LIBRARY"
)
backend_apis=(user user kernel kernel kernel)
IFS=',' read -r -a block_sizes <<<"$BLOCK_SIZES"
official_logs="$RESULT_DIR/official-logs"
rm -rf "$official_logs"
mkdir -p "$official_logs"

for ((run = 0; run < OUTER_RUNS; ++run)); do
    for ((block_position = 0; block_position < ${#block_sizes[@]}; ++block_position)); do
        block_index=$(( (block_position + run) % ${#block_sizes[@]} ))
        block_size="${block_sizes[block_index]}"
        for ((position = 0; position < ${#backend_names[@]}; ++position)); do
            index=$(( (position + run) % ${#backend_names[@]} ))
            name="${backend_names[index]}"
            log="$official_logs/run-${run}__block-${block_size}__backend-${name}.log"
            {
                echo "run=$run"
                echo "backend=$name"
                echo "block_size=$block_size"
                echo "harness_seconds=$BENCH_SECONDS"
                taskset -c "$CPU" "$OFFICIAL_BENCH" \
                    --library "${backend_paths[index]}" \
                    --api "${backend_apis[index]}" \
                    --block-size "$block_size" \
                    --seconds "$BENCH_SECONDS" \
                    -- "${corpus_files[@]}"
            } >"$log" 2>&1
        done
    done
done

raw="$RESULT_DIR/raw.csv"
python3 "$SCRIPT_DIR/scripts/parse_official.py" \
    --logs "$official_logs" \
    --output "$raw"
python3 "$SCRIPT_DIR/scripts/summarize.py" \
    --input "$raw" \
    --csv "$RESULT_DIR/aggregate.csv" \
    --summary "$RESULT_DIR/summary.md"
python3 "$SCRIPT_DIR/scripts/analyze_paper.py" \
    --input "$raw" \
    --csv "$RESULT_DIR/pairwise.csv" \
    --report "$RESULT_DIR/paper-summary.md"

if [[ "${RUN_CLI_WORKFLOW:-0}" == 1 ]]; then
    python3 "$SCRIPT_DIR/../evaluation/lz4-cli/workflow.py" \
        --stock "$BUILD_DIR/cli/lz4-stock" \
        --adapted "$BUILD_DIR/cli/lz4-adapted" \
        --kernel "$KERNEL_LIBRARY" --same-source "$KERNEL_USER_NOSIMD" \
        --upstream "$USER_DEFAULT" --manifest "$MANIFEST" \
        --output "$RESULT_DIR/cli-workflow" --cpu "$CPU" --rounds 4 --block-ids 4 6
fi

readelf -dW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-dynamic.txt"
readelf -rW "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-relocations.txt"
nm -D "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-symbols.txt"
cp "$WORK_DIR/vkso/metadata/page_mappings.txt" \
    "$RESULT_DIR/kernel-page-mappings.txt"
cp "$WORK_DIR/vkso/metadata/resolved_symbol_addresses.txt" \
    "$RESULT_DIR/kernel-resolved-symbols.txt"
cp "$WORK_DIR/vkso/metadata/module_deps.txt" \
    "$RESULT_DIR/kernel-module-deps.txt"
printf 'path=%s\nruntime_page_view_sha256=%s\n' \
    "$KERNEL_LIBRARY" \
    "$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)" \
    >"$RESULT_DIR/kernel-hash-views.txt"
printf '%s\n' "$KERNEL_LIBRARY" >"$RESULT_DIR/kernel-library-path.txt"
sha256sum \
    "$OFFICIAL_BENCH" \
    "$USER_DEFAULT" \
    "$USER_NOSIMD" \
    "$KERNEL_USER_NATIVE" \
    "$KERNEL_USER_NOSIMD" \
    "$MODULE" \
    "$WORK_DIR/vkso/lib/libshim.so" \
    >"$RESULT_DIR/artifacts.sha256"
if [[ "${RUN_CLI_WORKFLOW:-0}" == 1 ]]; then
    sha256sum "$BUILD_DIR/cli/lz4-stock" "$BUILD_DIR/cli/lz4-adapted" \
        >>"$RESULT_DIR/artifacts.sha256"
fi
