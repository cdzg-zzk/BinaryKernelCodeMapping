#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CPU="${CPU:-2}"
RUNTIME_DIR="${RUNTIME_DIR:-$SCRIPT_DIR}"
RESULT_DIR="${RESULT_DIR:-$RUNTIME_DIR/results}"
WORK_DIR="${WORK_DIR:-$RUNTIME_DIR/work}"
BUILD_DIR="${BUILD_DIR:-$RUNTIME_DIR/build}"
KMOD_DIR="${KMOD_DIR:-$SCRIPT_DIR/kmod}"
KERNEL_BUILD="${KERNEL_BUILD:-/lib/modules/$(uname -r)/build}"
MODULE="${MODULE:-$KMOD_DIR/vkso_xz.ko}"
SYMBOLS="$SCRIPT_DIR/config/symbols.txt"
SHIM_LIST="${SHIM_LIST:-$REPO_ROOT/make_dll/shim.txt}"
DATA_BINDINGS="${DATA_BINDINGS:-$SCRIPT_DIR/config/data-bindings.json}"
CORPUS_DIR="$WORK_DIR/corpus"
MANIFEST="$CORPUS_DIR/manifest.csv"
loaded_by_us=0

cleanup() {
    local status=$?
    trap - EXIT
    if (( loaded_by_us )); then
        if (( status == 0 )); then
            sudo rmmod vkso_xz || status=1
        else
            echo "Run failed; retaining vkso_xz until registration recovery is verified" >&2
        fi
    fi
    exit "$status"
}
trap cleanup EXIT

for command in gcc make pahole xz taskset readelf nm python3; do
    command -v "$command" >/dev/null || {
        echo "required command not found: $command" >&2
        exit 1
    }
done
[[ -d "$KERNEL_BUILD" ]] || {
    echo "running-kernel build directory not found: $KERNEL_BUILD" >&2
    exit 1
}
[[ -r /sys/kernel/btf/vmlinux ]] || {
    echo "/sys/kernel/btf/vmlinux is required" >&2
    exit 1
}

if [[ -n "${INPUTS:-}" ]]; then
    read -r -a input_candidates <<<"$INPUTS"
else
    input_candidates=(/bin/bash /usr/bin/python3 /usr/lib/x86_64-linux-gnu/libc.so.6)
fi
inputs=()
for candidate in "${input_candidates[@]}"; do
    [[ -f "$candidate" ]] && inputs+=("$candidate")
done
(( ${#inputs[@]} > 0 )) || {
    echo "no usable corpus inputs" >&2
    exit 1
}

rm -rf "$RESULT_DIR"
mkdir -p "$RESULT_DIR" "$WORK_DIR"
make -C "$SCRIPT_DIR" BUILD_DIR="$BUILD_DIR" clean all
"$SCRIPT_DIR/scripts/prepare_corpus.sh" "$CORPUS_DIR" "$MANIFEST" "${inputs[@]}"

# A custom WORK_DIR must be a complete VKSO workspace, not merely a corpus
# directory.  init preserves the explicit symbol list and creates the empty
# shared-data declaration plus the standard include/lib/metadata directories.
"$REPO_ROOT/vkso" init "$WORK_DIR" --symbols "$SYMBOLS"

if (( EUID != 0 )); then
    sudo -v
fi
if grep -q '^vkso_xz ' /proc/modules; then
    sudo rmmod vkso_xz
fi
make -C "$KERNEL_BUILD" M="$KMOD_DIR" modules
pahole -J --skip_encoding_btf_enum64 --btf_base /sys/kernel/btf/vmlinux "$MODULE"
if [[ "${RUN_KERNEL_COST:-0}" == 1 ]]; then
    python3 "$REPO_ROOT/test/evaluation/kernel_cost_host.py" prepare xz \
        --owner-source "$KMOD_DIR" --output "$RESULT_DIR/kernel-cost-prepared" --cpu "$CPU" \
        --manifest "$MANIFEST"
fi
sudo insmod "$MODULE"
loaded_by_us=1

# Module runtime addresses may change on every reload. Never reuse this test's
# KRG cache across module loads.
rm -f "$WORK_DIR/vkso/metadata/out.krg" \
      "$WORK_DIR/vkso/metadata/out.krg.inputs"

{
    echo "benchmark=linux-5.15-xz-embedded-single-call"
    echo "cpu=$CPU"
    echo "repeats=${REPEATS:-20}"
    echo "outer_runs=${OUTER_RUNS:-7}"
    echo "inputs=${inputs[*]}"
    echo "module=$MODULE"
    echo "xz_options=--threads=1 --check=crc32 --x86 --lzma2=dict=1MiB"
    echo "native_flags=-O2 -fPIC"
    echo "repo_commit=$(git -C "$REPO_ROOT" rev-parse HEAD)"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sha256sum \
        "$SCRIPT_DIR/Makefile" \
        "$SCRIPT_DIR/run.sh" \
        "$SCRIPT_DIR/run_under_replacement.sh" \
        "$SCRIPT_DIR/config/symbols.txt" \
        "$DATA_BINDINGS" \
        "$SCRIPT_DIR/src/xz-bench.c" \
        "$SCRIPT_DIR/scripts/prepare_corpus.sh" \
        "$SCRIPT_DIR/scripts/audit_kernel_dso.py" \
        "$SCRIPT_DIR/scripts/summarize.py" \
        "$REPO_ROOT/vkso" \
        "$REPO_ROOT/make_dll/build_PIC_so.py" \
        "$REPO_ROOT/make_dll/build_LKM_so.py" \
        "$REPO_ROOT/page_cache_replace/manager.cpp" \
        "$REPO_ROOT/page_cache_replace/page_cache_replace.c"
    sha256sum "$KMOD_DIR"/xz_*.c "$KMOD_DIR"/xz_*.h
    uname -a
    gcc --version | sed -n '1p'
    lscpu
} >"$RESULT_DIR/metadata.txt"

vkso_args=(
    exec "$WORK_DIR"
    --symbols "$SYMBOLS"
    --module "$MODULE"
    --owner-ko "$MODULE"
    --shim-list "$SHIM_LIST"
    --data-bindings "$DATA_BINDINGS"
)
if [[ "${VKSO_SKIP_CHECK:-0}" == 1 ]]; then
    vkso_args+=(--skip-check)
fi
vkso_args+=(-- "$SCRIPT_DIR/run_under_replacement.sh")

CPU="$CPU" RESULT_DIR="$RESULT_DIR" BUILD_DIR="$BUILD_DIR" \
WORK_DIR="$WORK_DIR" MANIFEST="$MANIFEST" \
REPEATS="${REPEATS:-20}" OUTER_RUNS="${OUTER_RUNS:-7}" \
    "$REPO_ROOT/vkso" "${vkso_args[@]}"

KERNEL_LIBRARY="$(<"$RESULT_DIR/kernel-library-path.txt")"
printf 'restored_sparse_file_sha256=%s\n' \
    "$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)" \
    >>"$RESULT_DIR/kernel-hash-views.txt"
sha256sum "$KERNEL_LIBRARY" "$MODULE" >>"$RESULT_DIR/artifacts.sha256"
echo "completed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >>"$RESULT_DIR/metadata.txt"
echo "results written to $RESULT_DIR"
