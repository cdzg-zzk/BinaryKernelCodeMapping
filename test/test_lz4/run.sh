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
SYMBOLS="$SCRIPT_DIR/config/symbols.txt"
CORPUS="${CORPUS:-silesia}"
KERNEL_BUILD="/lib/modules/$(uname -r)/build"
MODULE="${MODULE:-$KMOD_DIR/vkso_lz4.ko}"
SHIM_LIST="${SHIM_LIST:-$REPO_ROOT/make_dll/shim.txt}"
loaded_by_us=0

sudo_validate() {
    if (( EUID == 0 )); then
        return
    fi
    sudo -v
}

cleanup() {
    if (( loaded_by_us )); then
        sudo rmmod vkso_lz4 2>/dev/null || true
    fi
}
trap cleanup EXIT

command -v taskset >/dev/null 2>&1 || {
    echo "taskset is required" >&2
    exit 1
}
[[ -d "$KERNEL_BUILD" ]] || {
    echo "running-kernel build directory not found: $KERNEL_BUILD" >&2
    exit 1
}

if [[ ! -f "$SCRIPT_DIR/vendor/lz4-1.9.3/lib/lz4.c" ]]; then
    "$SCRIPT_DIR/scripts/fetch_lz4.sh"
fi

case "$CORPUS" in
    silesia)
        if [[ ! -f "$SCRIPT_DIR/corpus/silesia/manifest.txt" ]]; then
            "$SCRIPT_DIR/scripts/fetch_silesia.sh"
        fi
        MANIFEST="$SCRIPT_DIR/corpus/silesia/manifest.txt"
        ;;
    smoke)
        python3 "$SCRIPT_DIR/scripts/generate_smoke_corpus.py" \
            --output "$RUNTIME_DIR/corpus/smoke" \
            --size-mib "${SMOKE_SIZE_MIB:-4}"
        MANIFEST="$RUNTIME_DIR/corpus/smoke/manifest.txt"
        ;;
    *)
        MANIFEST="$(realpath "$CORPUS")"
        ;;
esac

rm -rf "$RESULT_DIR"
mkdir -p "$RESULT_DIR"
"$REPO_ROOT/vkso" init "$WORK_DIR" --symbols "$SYMBOLS"
make -C "$SCRIPT_DIR" BUILD_DIR="$BUILD_DIR" clean all
python3 "$SCRIPT_DIR/scripts/audit_simd.py" \
    --default "$BUILD_DIR/liblz4-default.so" \
    --nosimd "$BUILD_DIR/liblz4-nosimd.so" \
    --kernel-native "$BUILD_DIR/libkernel-userspace-native.so" \
    --kernel-nosimd "$BUILD_DIR/libkernel-userspace-nosimd.so" \
    --output "$RESULT_DIR/simd-audit.md"

sudo_validate
if grep -q '^vkso_lz4 ' /proc/modules; then
    sudo rmmod vkso_lz4
fi
make -C "$KERNEL_BUILD" M="$KMOD_DIR" modules
# External-module Kbuild skips BTF when the headers tree has no local vmlinux.
# Add split BTF against the running kernel's base BTF so vkso can generate the
# function prototypes without changing the system headers tree.
pahole -J --btf_base /sys/kernel/btf/vmlinux "$MODULE"
sudo insmod "$MODULE"
loaded_by_us=1

mkdir -p "$WORK_DIR"

# A module can be reloaded at a different runtime address during one boot, while
# vkso's generic KRG cache key only identifies the module file.  Rebuild this
# test-local KRG every run so no stale module address can be reused.
rm -f "$WORK_DIR/vkso/metadata/out.krg" \
      "$WORK_DIR/vkso/metadata/out.krg.inputs"

{
    echo "benchmark=lz4-1.9.3-official-bench-vs-linux-5.15-kbuild-vkso"
    echo "cpu=$CPU"
    echo "corpus=$CORPUS"
    echo "manifest=$MANIFEST"
    echo "runtime_dir=$RUNTIME_DIR"
    echo "build_dir=$BUILD_DIR"
    echo "work_dir=$WORK_DIR"
    echo "module=$MODULE"
    echo "kernel_lz4_compress_sha256=$(sha256sum "$KMOD_DIR/lz4_compress.c" | cut -d' ' -f1)"
    echo "kernel_lz4_decompress_upstream_sha256=145d6abcfc755879d1e27d95c380d9ac17a84d99bfc6ee18026e680e747caac2"
    echo "kernel_lz4_decompress_adapted_sha256=$(sha256sum "$KMOD_DIR/lz4_decompress.c" | cut -d' ' -f1)"
    echo "kernel_lz4defs_sha256=$(sha256sum "$KMOD_DIR/lz4defs.h" | cut -d' ' -f1)"
    echo "userspace_kernel_compat_sha256=$(sha256sum "$SCRIPT_DIR/userspace_kernel/kernel_compat.h" | cut -d' ' -f1)"
    echo "userspace_scalar_mem_sha256=$(sha256sum "$SCRIPT_DIR/userspace_kernel/scalar_mem.c" | cut -d' ' -f1)"
    echo "official_adapter_sha256=$(sha256sum "$SCRIPT_DIR/src/official_backend_adapter.c" | cut -d' ' -f1)"
    echo "kernel_memory_helpers=memcpy:shim,memset:shim,memmove:shim"
    echo "outer_runs=${OUTER_RUNS:-3}"
    echo "official_harness_seconds=${BENCH_SECONDS:-1}"
    echo "block_sizes=${BLOCK_SIZES:-4096,65536,1048576}"
    echo "backends=user-default,user-nosimd,kernel-userspace-native,kernel-userspace-nosimd,kernel-vkso"
    echo "native_flags=-O3 -fPIC -march=native"
    echo "nosimd_flags=-O3 -fPIC -fno-tree-vectorize -fno-tree-slp-vectorize -fno-tree-loop-vectorize -fno-tree-loop-distribute-patterns -fno-builtin -mno-mmx -mno-3dnow -mno-sse -mno-sse2 -mno-sse3 -mno-ssse3 -mno-sse4 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2 -mno-avx512f -mno-avx512bw -mno-avx512dq -mno-avx512vl"
    echo "nosimd_memory_helpers=test-local scalar memcpy/memmove/memset"
    echo "official_bench_sha256=$(sha256sum "$SCRIPT_DIR/vendor/lz4-1.9.3/programs/bench.c" | cut -d' ' -f1)"
    echo "lz4_source=https://github.com/lz4/lz4/archive/refs/tags/v1.9.3.tar.gz"
    echo "lz4_source_sha256=030644df4611007ff7dc962d981f390361e6c97a34e5cbc393ddfbe019ffe2c1"
    if [[ "$CORPUS" == silesia ]]; then
        echo "corpus_source=http://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip"
        echo "corpus_source_sha256=0626e25f45c0ffb5dc801f13b7c82a3b75743ba07e3a71835a41e3d9f63c77af"
    fi
    echo "repo_commit=$(git -C "$REPO_ROOT" rev-parse HEAD)"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    uname -a
    gcc --version | sed -n '1p'
    lscpu
    for state_file in \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_driver" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_min_freq" \
        "/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_max_freq" \
        /sys/devices/system/cpu/intel_pstate/no_turbo; do
        if [[ -r "$state_file" ]]; then
            echo "$state_file=$(<"$state_file")"
        fi
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

CPU="$CPU" RESULT_DIR="$RESULT_DIR" MANIFEST="$MANIFEST" \
BUILD_DIR="$BUILD_DIR" WORK_DIR="$WORK_DIR" MODULE="$MODULE" \
OUTER_RUNS="${OUTER_RUNS:-3}" BENCH_SECONDS="${BENCH_SECONDS:-1}" \
BLOCK_SIZES="${BLOCK_SIZES:-4096,65536,1048576}" \
    "$REPO_ROOT/vkso" "${vkso_args[@]}"

KERNEL_LIBRARY="$(<"$RESULT_DIR/kernel-library-path.txt")"
[[ -f "$KERNEL_LIBRARY" ]] || {
    echo "restored kernel DSO not found: $KERNEL_LIBRARY" >&2
    exit 1
}
restored_kernel_hash="$(sha256sum "$KERNEL_LIBRARY" | cut -d' ' -f1)"
printf 'restored_sparse_file_sha256=%s\n' "$restored_kernel_hash" \
    >>"$RESULT_DIR/kernel-hash-views.txt"
sha256sum "$KERNEL_LIBRARY" >>"$RESULT_DIR/artifacts.sha256"

echo "completed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >>"$RESULT_DIR/metadata.txt"
echo "results written to $RESULT_DIR"
