# LZ4 kernel/vkso benchmark

论文 6.3 的当前结果统一位于 [section63](../section63/README.md)，
方法、对照和适配记录见[方法说明](../section63/methods.md)。本目录保留
算法源码和单次运行入口；论文使用统一 runner 的三次完整部署统计。

This test compares the same block-compression workload through six backends:

- `kernel-vkso`: Linux 5.15 LZ4 machine code exported by a fresh, standard
  `vkso` build;
- `kernel-userspace-native`: the test's Linux 5.15 LZ4 source adaptation built
  as an ordinary user-space DSO with `-O3 -march=native`;
- `kernel-userspace-nosimd`: the same adapted kernel source with compiler SIMD
  disabled and test-local non-SIMD memory helpers;
- `kernel-userspace-libc`: the same algorithm source and compiler flags as
  `kernel-userspace-nosimd`, with external helpers resolved to libc;
- `user-default`: upstream LZ4 1.9.3 with `-O3 -march=native`;
- `user-nosimd`: the same upstream source with compiler SIMD disabled and the
  same test-local non-SIMD memory helpers.

The new libc baseline matches the registered carrier's helper implementation,
verified through actual GOT/PLT entries and private slots before timing. The
owner still uses Kbuild (-O2, kernel ABI and build-specific mitigations), while
the user DSO uses -O3/PIC and a compatibility header. This comparison does not
isolate PGOT or physical sharing alone. The existing REP baseline remains for
helper-policy comparison.

The measured timing core is the unmodified LZ4 1.9.3 `programs/bench.c`. A thin
adapter only opens the selected DSO and forwards the level-1 block compression
and decompression calls. This preserves the official harness's block splitting,
time-adaptive loops, fastest-complete-loop policy, and XXH64 validation.

All six backends are retained in the current campaign analysis.

## Prerequisites

The running kernel must have matching headers and `/sys/kernel/btf/vmlinux`.
The host also needs:

- GCC, GNU make, binutils, Python 3 with pyelftools, curl, unzip, and `taskset`;
- headers for `uname -r`;
- `pahole`/dwarves;
- sudo permission to load `vkso_lz4` and `page_cache_replace`.

The official LZ4 1.9.3 benchmark sources are vendored under
`vendor/lz4-1.9.3/` from the fixed upstream archive. A formal Silesia run
downloads the corpus once, verifies its fixed SHA-256 digest, and caches it.

## Run

From the repository root, a normal Silesia run is:

```sh
CPU=2 test/test_lz4/run.sh
```

Defaults are three outer rounds within one deployment, one-second official harness windows,
and 4 KiB/64 KiB/1 MiB blocks. Each round/block/backend starts a new process,
while the owner module and page registration remain active across rounds.
The archived reporting configuration uses:

```sh
CPU=2 OUTER_RUNS=7 BENCH_SECONDS=2 \
BLOCK_SIZES=4096,65536,1048576 test/test_lz4/run.sh
```

For a quick end-to-end check with generated data:

```sh
CORPUS=smoke SMOKE_SIZE_MIB=4 OUTER_RUNS=1 BENCH_SECONDS=1 \
BLOCK_SIZES=4096,65536 test/test_lz4/run.sh
```

To keep builds, module copies, and runtime files outside the repository:

```sh
tmpdir="$(mktemp -d /tmp/vkso-lz4.XXXXXX)"
cp -a test/test_lz4/kmod "$tmpdir/kmod"
RUNTIME_DIR="$tmpdir" KMOD_DIR="$tmpdir/kmod" \
RESULT_DIR="$PWD/test/test_lz4/results" \
CPU=2 OUTER_RUNS=7 BENCH_SECONDS=2 test/test_lz4/run.sh
```

`CORPUS` may also name a custom manifest. Each non-empty line is a file path
relative to the manifest directory; file boundaries are preserved.

## Complete lifecycle

`run.sh` performs the following work without a pre-existing `libkernel.so`:

1. Builds the five ordinary user-space DSOs and the official benchmark driver.
2. Rejects either complete no-SIMD DSO if it contains SIMD or imports external
   memory helpers. The new libc baseline requires a scalar algorithm body and
   three external memory imports; its helpers may use SIMD.
3. Builds the namespaced test module, adds split BTF against the running kernel,
   loads it, and deliberately deletes the test-local KRG cache.
4. Runs the normal project `vkso exec` path: resolve runtime addresses, analyze
   the requested closures, construct a fresh sparse DSO and shim, and replace
   the mapped pages.
5. Verifies that the new same-source DSO and carrier bridges resolve to the same
   libc helper addresses, then runs 6 × 6 × 12 cross-backend correctness cases, then runs the official
   harness for every backend/block/outer-run combination on one pinned CPU.
6. Restores replaced pages before unloading the test module. A failed restoration
   retains recovery state and owner references and returns a failure.

Do not use `VKSO_SKIP_CHECK=1` for reported measurements. It is only a local
debugging shortcut after an unchanged DSO has already passed closure checks.

## Correctness and statistics

All six compressors are crossed with all six decompressors on 12
boundary-focused sizes. Return values, output bytes, and guard regions are
checked. The official harness independently verifies the decompressed Silesia
content with XXH64 for every measured case.

Backend and block order rotate between outer runs. Raw official throughput is
kept for every case. Pairwise comparisons first divide results from the same
outer run, then report the median and P10–P90 of those paired ratios. This avoids
forming a ratio from two independently aggregated medians.

Important no-SIMD caveat: the native variants may call glibc IFUNC memory
helpers, whereas the no-SIMD variants use test-local `rep movsb`/`rep stosb`
helpers. That is necessary to guarantee that the complete no-SIMD call path
does not execute SIMD, but it means native/no-SIMD is not a pure one-variable
SIMD ablation.

## Outputs

The selected result directory contains:

- `raw.csv`, `aggregate.csv`, and `summary.md`: official measurements and
  per-backend summaries;
- `pairwise.csv` and `paper-summary.md`: run-paired comparisons and concise
  paper-ready conclusions;
- `correctness.log` and `official-logs/`: cross-backend and official XXH64
  correctness evidence;
- `simd-audit.md`: instruction and unresolved-helper audit for four ordinary
  DSOs;
- `metadata.txt`: source hashes, flags, parameters, CPU, compiler, and kernel;
- `kernel-dynamic.txt`, `kernel-relocations.txt`, `kernel-symbols.txt`, and
  `kernel-*-*.txt`: generated DSO, runtime-address, page-map, and dependency
  evidence;
- `artifacts.sha256`: post-run-verifiable hashes of the actual harness, DSOs,
  module, generated sparse kernel DSO, and shim;
- `kernel-hash-views.txt`: separate hashes of the kernel DSO while its file
  pages expose live kernel contents and after restoration to sparse holes.

The parser rejects an incomplete or extra official result matrix.

## Kernel-source adaptation

`kmod/` contains the Linux 5.15 implementation used for both the module and the
two ordinary kernel-source DSOs. Test-local conditional compatibility headers
provide user-space types and unaligned helpers; the algorithm source remains
shared.

Adaptations are confined to `test/test_lz4/`:

- public entry points are namespaced as `vkso_LZ4_*`;
- fentry and return/indirect thunks are omitted for the copied user-space code;
- decompressor table bases are obtained with RIP-relative `lea` before indexed
  access, avoiding absolute kernel-rodata relocations;
- `symbols.txt` exports only the two benchmark APIs, while closure analysis
  redirects the non-top-level `memcpy`, `memmove`, and `memset` dependencies
  through the normal project shim;
- the generated explicit page map contains only reusable closure pages; no
  owner-module page anchors are exported.

The formal run must show `DT_NEEDED: libshim.so` and a dependency report of
`shim: memcpy memmove memset`.

## Interpretation boundary

This is an in-memory LZ4 block component benchmark. It excludes filesystem I/O,
syscalls, allocation, and kernel/user copies, so it is not a complete
application macrobenchmark. Differences between Linux 5.15 and LZ4 1.9.3 also
include algorithm version, control flow, copy strategy, ABI, and compiler
decisions; they cannot be attributed to SIMD alone.
