#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CPU="${CPU:-2}"
RESULT_DIR="${RESULT_DIR:-$SCRIPT_DIR/results}"
WORK_DIR="${WORK_DIR:-$SCRIPT_DIR/work}"
BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
KMOD_DIR="$SCRIPT_DIR/kmod"
KERNEL_BUILD="/lib/modules/$(uname -r)/build"
MODULE="${MODULE:-$KMOD_DIR/vkso_bch.ko}"
SYMBOLS="$SCRIPT_DIR/config/symbols.txt"
SHIM_LIST="${SHIM_LIST:-$REPO_ROOT/make_dll/shim.txt}"
loaded_by_us=0

sudo_cmd() {
    if (( EUID == 0 )); then
        "$@"
    elif [[ -n "${SUDO_PASSWORD:-}" ]]; then
        printf '%s\n' "$SUDO_PASSWORD" | sudo -S "$@"
    else
        sudo "$@"
    fi
}

cleanup() {
    if (( loaded_by_us )); then
        sudo_cmd rmmod vkso_bch 2>/dev/null || true
    fi
}
trap cleanup EXIT

for command in gcc make pahole taskset readelf nm objdump python3; do
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

rm -rf "$RESULT_DIR"
mkdir -p "$RESULT_DIR" "$WORK_DIR"
"$REPO_ROOT/vkso" init "$WORK_DIR" --symbols "$SYMBOLS"
make -C "$SCRIPT_DIR" BUILD_DIR="$BUILD_DIR" clean all

if (( EUID != 0 )); then
    sudo_cmd -v
fi
if grep -q '^vkso_bch ' /proc/modules; then
    sudo_cmd rmmod vkso_bch
fi
make -C "$KERNEL_BUILD" M="$KMOD_DIR" clean modules
pahole -J --btf_base /sys/kernel/btf/vmlinux "$MODULE"
sudo_cmd insmod "$MODULE"
loaded_by_us=1

# Owner-module runtime addresses may change on every reload.
rm -f "$WORK_DIR/vkso/metadata/out.krg" \
      "$WORK_DIR/vkso/metadata/out.krg.inputs"

{
    echo "benchmark=parrot-tu_bench-method-linux-5.15-bch-vkso"
    echo "cpu=$CPU"
    echo "outer_runs=${OUTER_RUNS:-11}"
    echo "sample_ms=${SAMPLE_MS:-10}"
    echo "correctness_vectors=${CORRECTNESS_VECTORS:-128}"
    echo "parameters=m13t4,m13t8"
    echo "data_length_rule=(1<<(m-1))/8"
    echo "timing_clock=CLOCK_PROCESS_CPUTIME_ID"
    echo "backend_order=rotated_per_outer_run"
    echo "backends=kernel-vkso,kernel-native,author-standalone"
    echo "kernel_source=Ubuntu linux-source-5.15.0/lib/bch.c"
    echo "author_source=https://github.com/Parrot-Developers/bch"
    echo "author_commit=99cd350e77a3ee713cc7b10ba26e53e508bee453"
    echo "author_harness=Documentation/bch/tu_bench.c"
    echo "kernel_native_flags=-O2 -fPIC scalar no-retpoline"
    echo "author_flags=-O3 -fPIC -mtune=native"
    echo "kernel_helpers=__kmalloc:shim,kfree:shim,memcpy:shim,memset:shim"
    echo "repo_commit=$(git -C "$REPO_ROOT" rev-parse HEAD)"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sha256sum \
        "$SCRIPT_DIR/vendor/linux-5.15/lib/bch.c" \
        "$SCRIPT_DIR/adapted/bch.c" \
        "$SCRIPT_DIR/vendor/parrot-bch/lib/bch.c" \
        "$SCRIPT_DIR/vendor/parrot-bch/Documentation/bch/tu_bench.c"
    uname -a
    gcc --version | sed -n '1p'
    lscpu
    for state_file in \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_driver" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_min_freq" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_max_freq" \
        /sys/devices/system/cpu/intel_pstate/no_turbo; do
        [[ -r "$state_file" ]] && echo "$state_file=$(<"$state_file")"
    done
} >"$RESULT_DIR/metadata.txt"

vkso_args=(
    exec "$WORK_DIR"
    --symbols "$SYMBOLS"
    --module "$MODULE"
    --owner-ko "$MODULE"
    --shim-list "$SHIM_LIST"
)
if [[ "${VKSO_SKIP_CHECK:-0}" == 1 ]]; then
    vkso_args+=(--skip-check)
fi
vkso_args+=(-- "$SCRIPT_DIR/run_under_replacement.sh")

CPU="$CPU" RESULT_DIR="$RESULT_DIR" BUILD_DIR="$BUILD_DIR" \
WORK_DIR="$WORK_DIR" MODULE="$MODULE" \
OUTER_RUNS="${OUTER_RUNS:-11}" SAMPLE_MS="${SAMPLE_MS:-10}" \
CORRECTNESS_VECTORS="${CORRECTNESS_VECTORS:-128}" \
    "$REPO_ROOT/vkso" "${vkso_args[@]}"

KERNEL_LIBRARY="$(<"$RESULT_DIR/kernel-library-path.txt")"
printf 'restored_sparse_file_sha256=%s\n' \
    "$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)" \
    >>"$RESULT_DIR/kernel-hash-views.txt"
sha256sum "$KERNEL_LIBRARY" >>"$RESULT_DIR/artifacts.sha256"
echo "completed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >>"$RESULT_DIR/metadata.txt"
echo "results written to $RESULT_DIR"
