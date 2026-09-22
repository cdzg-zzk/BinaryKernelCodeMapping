# Four-image VKSO reader experiment

The existing `experiment.sh boot/collect CASE` interface now also collects
Redis macrobench when `MACRO_ENABLED=1` in `experiment.conf`. Build and install
fresh packages before starting: the historical packages lack the new tools and
namespace-sharing implementation. See the [four-image command guide](../../macro-benchmark/README.md).
`build-all.sh` builds and verifies packages; it no longer launches QEMU tests
automatically. The separate existing QEMU entry remains a diagnostic tool.

The final reader experiment has four cases, always collected in this order:

1. raw vDSO, normal mitigation configuration;
2. VKSO, normal mitigation configuration;
3. raw vDSO, retpoline/rethunk disabled;
4. VKSO, retpoline/rethunk disabled.

`build-all.sh` constructs both package pairs from one base configuration and
one compiler environment. `verify-packages.sh` rejects implementation-external
raw/VKSO configuration differences and non-retpoline-related cross-variant
differences. It also requires byte-identical benchmark executables.

For the normal mitigation build, `reusable_text.txt` lists the static x86
thunks that runtime-patched VKSO branches may reach. The DSO builder treats
them as native dependency roots and maps their RX pages independently; the
list does not assume that those symbols remain on one physical page.

`experiment.sh` is the only reader collection entry point. It fixes all
parameters through `experiment.conf`, enforces the four-case order, verifies
the booted kernel and package identity, refuses overwrites, preserves failed
collections under `results/<run>/incomplete/`, and stores the complete raw
CSV, functional logs, interrupt snapshots and environment metadata. It does
not generate a performance conclusion.

The first `./experiment.sh boot raw-normal` automatically starts a new run.
After each reboot, use `./experiment.sh collect CASE`, then the same `boot` /
`collect` pair for the reported next case. An explicit `begin` is optional.
Uncommitted candidates remain reproducible because each package stores and
hash-checks its exact tracked `source.patch` relative to `git_commit`.

The independent Chinese report for the final completed four-image run
`20260728T013904Z-vkso-final`, including the Base2 optimization comparison,
is [`VKSO_READ性能实验报告_20260728.md`](VKSO_READ性能实验报告_20260728.md).

The final O4 cold-backend decision and the secondary-mapped ITS/reusable-text
fix are documented in
[`M11_O4_ITS.md`](../../vkso-timekeeper-unification/reports/M11_O4_ITS.md).
It compares the O3 baseline with both independent O4 normal bare-metal runs
and records the source-tree/hash provenance of the measured image.

The independent update-side report for the stabilized paired run
`20260728T031855Z-update-side` is
[`VKSO_UPDATE性能实验报告_20260728.md`](../update-bench/VKSO_UPDATE性能实验报告_20260728.md).
It measures the complete `timekeeping_update()` writer and explains the
performance difference between native `update_vsyscall()` and
`vkso_time_publish()`.

The independent read/update concurrency report for paired run
`20260728T043508Z-update-concurrent` is
[`VKSO_READ_UPDATE并发性能实验报告_20260728.md`](../update-bench/VKSO_READ_UPDATE并发性能实验报告_20260728.md).
It evaluates public readers, the complete update writer, and seq retry
behavior while read and update execute concurrently.

These three reports are complementary rather than interchangeable:
standalone READ measures direct public user-API batches with PMU counters,
UPDATE measures the complete idle writer, and CONCURRENT runs the same direct
reader batch while recording the complete writer. Operation/path selection,
argument initialization and duration-control syscalls are outside the inner
reader window (`direct-user-api-steady-batch-v3`). Each timed sample first
re-primes the exact path, and bare-metal collection disables user-space ASLR
with `setarch -R` so call-site/target layout is identical across repetitions.
The 31 standalone READ repetitions are distributed across seven fresh
processes; `perf-process-map.csv` preserves the process/local-repeat identity
while `perf.csv` retains the established schema and global repeat numbers.
The three clock readers shared by
READ and CONCURRENT therefore have the same measured call body; results from
older `invoke()`-based READ packages must not be mixed with this version.
CONCURRENT uses 500,000 measured calls per batch, matching READ.  After each
duration-control syscall it executes 10,000 unmeasured calls to restore the
exact reader path's predictor state.  Its load CSV records measured,
conditioning and total calls separately under
`direct-user-api-conditioned-load-v4`.

The four-image update and concurrency drivers use the same fixed interface as
the reader experiment. Use `./experiment-update.sh boot/collect CASE` for the
idle writer experiment and `./experiment-concurrent.sh boot/collect CASE` for
read/update concurrency. The first `boot raw-normal` starts its run; each
`collect` prints the next case, and the fourth collection validates and archives
the complete run.
