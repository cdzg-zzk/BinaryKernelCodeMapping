# First-touch evidence and collection changes

The initial source/artifact audit on 2026-09-11 ran no benchmarks. The sections
below record subsequent collector changes and registered guest experiments;
the latest pressure scenario changes neither registration nor hash assembly.

## Reclaim-pressure scenario — 2026-09-12

The [pressure run](results/first-touch-pressure-qemu-20260912-attempt01/result.json),
boot `2a151ee4-32e8-47ff-aedb-cc16ac62bd65`, uses the same owner, full exporter,
registered carrier and native 338-byte XXH32 implementation as the raw run
below. It adds `--scenario pressure` to the existing `first_touch_qemu.py`
deployment flow. The original three-condition collector remains unchanged.
The [independent audit](results/first-touch-pressure-qemu-20260912-attempt01/independent-audit.json)
reconstructs all 30 paired trials and 60 calls.

The exact119 guest has 4 GiB RAM, two vCPUs and no swap. Both probes use CPU 1;
the controller and background worker use CPU 0. Before each pair, both targets
execute the full hash on `hello`, seed `0x1234`, then remove their function PTE
with `MADV_DONTNEED`. Pagemap confirms absence. After the intervening workload,
each probe records `mincore`, pagemap, call TSC, faults and the actual hash.
Post-call pagemap checks the installed PFN. Pair order is shuffled with seed
20260912; every call is retained without fault-class or latency filtering.
The independent 247-vector validator exits before probes start.

Baseline, pressure and recovery each contain ten pairs. Baseline and recovery
have no intervening background read. The pressure worker writes every byte of
an anonymous reservation, bounded before collection by
`min(MemAvailable - 512 MiB, 0.8 * MemTotal)`, rounded down to pages. This run
reserves 2,903,486,464 B (about 2.70 GiB). Worker smaps records 2,836,572 KiB of
anonymous memory, compared with 1,136 KiB before allocation and after release.
THP is disabled for this reservation only; observed `AnonHugePages` is zero.
Between preparation and each pair, the worker reads a fully written, fsynced
1 GiB ext4 file twice, then waits while retaining its anonymous allocation.
The ten windows last 0.830–0.980 seconds each. This measures an idle code page
after competing file-cache traffic, not overlapping application throughput.
Neither process drops caches or advises file-page eviction. All memory and
filesystem activity is confined to the private guest.

All ten pressure windows have positive scans and reclaim. Their combined
`pgscan_kswapd`/`pgscan_direct` deltas are 5,238,597/76 pages;
`pgsteal_kswapd`/`pgsteal_direct` are 5,238,524/76 pages.
`workingset_refault_file` increases by 5,242,880 pages. These repeated events
are not unique-page counts or net-memory savings. Memory PSI records stalls;
there is no OOM kill. Raw vmstat, meminfo, memory/I/O PSI, swaps and worker
smaps are retained per pair. Linux's
[reclaim description](https://www.kernel.org/doc/html/v5.15/admin-guide/mm/concepts.html#reclaim)
and [PSI interface](https://www.kernel.org/doc/html/v5.15/accounting/psi.html)
define these observations. `mincore` is a residency snapshot, as documented
in its [manual](https://man7.org/linux/man-pages/man2/mincore.2.html); actual
faults and post-call PFNs are recorded separately.

| Phase | Native resident before call | Stub resident before call | Native minor/major class | Stub minor/major class |
| --- | ---: | ---: | --- | --- |
| Baseline | 10/10 | 10/10 | 1/0 in 10 calls | 1/0 in 10 calls |
| Pressure | 10/10 | 10/10 | 1/0 in 10 calls | 1/0 in 10 calls |
| Recovery | 10/10 | 10/10 | 1/0 in 10 calls | 1/0 in 10 calls |

Both code pages remain resident despite substantial background reclaim.
This workload provides no evidence of avoided native major faults. The
controlled post-drop result cannot therefore be generalized to ordinary
memory pressure. Guest cycles remain in raw records and are not added to
Table 3 or used to estimate a physical-machine latency advantage.

All 60 hashes match the independent oracle. Each of the 30 Stub calls installs
the original kernel PFN, with owner reference one throughout. Separate
before/after PFN observations agree. Full 247-vector checks before and after
pressure pass; native, owner and loaded function bytes agree. The reservation
is released before session cleanup; the carrier restores and all test modules
unload without panic, BUG or WARNING.

This completes one registered pressure/recovery diagnostic. Physical-host
repetitions, full net-memory accounting and broader resident source-page
boundaries remain group B work. The archive's top-level `scope` retains the
generic raw-protocol label; `collection.scope`, the scenario marker and logs
identify pressure. This archive does not contain another 3,800-call matrix.

From the repository root:

```sh
python3 test/evaluation/first_touch_qemu.py --scenario pressure \
  --output test/evaluation/results/first-touch-pressure-NEW
python3 test/evaluation/first_touch_pressure_audit.py \
  test/evaluation/results/first-touch-pressure-NEW
```

The payload includes both C observers, the included original collector,
Python protocol/auditor, owner build sources, native/owner binaries, wrapper
and registration module. `pressure-config.json`, `pressure-events.jsonl` and
`pressure-trials.jsonl` retain configuration, worker commands and unfiltered
observations. Without observed reclaim, pressure collection is incomplete
even if every hash succeeds.

## Registered raw-protocol run — 2026-09-12

[The full run](results/first-touch-raw-qemu-20260912-attempt03/result.json),
boot `f86477f5-fd57-4b6b-90c2-4ce9ba96f497`, completes the revised Native/Stub
matrix in an exact119 private guest. Each of six target/condition groups
reaches five accepted batches with the original 100 calls, 90% retention
threshold and 20-attempt limit. The independent
[audit](results/first-touch-raw-qemu-20260912-attempt03/independent-audit.json)
replays all raw calls, decisions and printed statistics. No guest cycles are
inserted into the historical physical-machine table.

| Target / condition | Attempted batches | Prepared calls | IQR retained calls | Calls in accepted batches after IQR |
| --- | ---: | ---: | ---: | ---: |
| Native / hot | 5 | 500 | 482 | 482 |
| Native / PTE cold | 5 | 500 | 466 | 466 |
| Native / post-drop | 13 | 1,300 | 1,160 | 455 |
| Stub / hot | 5 | 500 | 493 | 493 |
| Stub / PTE cold | 5 | 500 | 477 | 477 |
| Stub / post-drop | 5 | 500 | 486 | 486 |

All 38 batches and 3,800 prepared calls are retained, including the eight
rejected native/post-drop batches. The all-prepared view retains 800 calls
from those rejected batches. The complete collection has 3,564 IQR-retained
calls and 2,859 calls in the accepted-batch filtered view. No preparation
failed. In this run all observed fault classes match their configured class:
hot 0/0, PTE cold 1/0, native post-drop 0/1 and Stub post-drop 1/0. This is a
frequency observation in one run, not a guarantee about future faults.
Acquisition order, raw TSC/fault counts, batch logs and the exact CPU-1 affinity
record are archived under `evidence/validation/first-touch.logs/`.

The existing XXH32 assembly is unchanged. Its full 338-byte body is identical
in the native ELF, cooperative owner ELF and the actual loaded native/registered
functions. Both entries match an independent libxxhash oracle on all 247 known
and boundary vectors, including the existing alignment and seed matrix. The
registered text page matches the kernel PFN after latency collection, active
owner reference is checked as one, release removes the source PFN from a fresh
mapping, and all test modules unload without kernel panic, BUG or WARNING.

The first-touch owner now has the same cooperative descriptor used by the
other module exports. Its assembly entry lacks a BTF FUNC prototype, so the
explicit `api.h` supplies the existing SysV declaration via `vkso --api-header`.
The actual exporter still performs closure checking, full carrier construction
and manager identity validation. The supplied header is compiled for syntax
and all requested names. Its ABI meaning is a caller contract, checked here
by actual bytes and independent full-function calls; it is not inferred from
missing BTF. Missing declarations and invalid C are rejected in the archived
header checks. This is an existing mechanism benchmark, not another success
in the fixed eight-case applicability denominator.

Two integration corrections precede this run. Attempt 01 stopped before
registration because header generation could not find the assembly prototype;
that failure and its checker PASS remain archived. Attempt 02 registered and
passed bytes/oracle/PFN checks but kept the native DSO mapped in the long-lived
functional validator. Its archived process maps contain that native mapping;
all 100 native/post-drop calls were minor faults, and the old statistics path
aborted on the empty expected class. The
[failed-run analysis](results/first-touch-raw-qemu-20260912-attempt02/failed-run-analysis.json)
retains those observations. The validator now runs in a separate process that
exits before sampling; the controller's pre-sampling maps are also retained.
No host cache-dropping command was run.

The raw protocol is now `first-touch-raw-v2`: a successfully measured batch
with zero expected-fault calls reports its counts, emits no conditional
latency statistics and is rejected with `no_expected_fault_samples`. It does
not terminate the remaining matrix and is rejected even at a zero retention
threshold. The analyzer supports both v1 and v2 and independently enforces this
rule. A compiled test of the real C statistics function exercises the complete
shell/analyzer empty-class path; all ten first-touch tests pass. The archived
[timed-region check](results/first-touch-raw-qemu-20260912-attempt03/timed-region-validation.json)
confirms that `measure_once` and `prepare_condition` are unchanged by this fix.

Registered-Stub collection and raw-result reconstruction are now exercised.
Formal physical-machine repetitions, matched whole-session setup/resource
accounting and memory pressure remain group B delivery. Earlier statements
below describe their original audit/preparation dates.

## What the existing table contains

The path is `matrix_bench/benchmark_first_touch.c` → `run_benchmarks.sh` →
`first_touch_results.csv` → `merge_latency_pmu.py` →
`first_touch_pmu_combined.csv` and the manuscript's Table 3.
All paths above are under [`test_first_call`](../test_first_call/).

The C benchmark measures one call after preparing its condition. It sorts the
samples, removes calls outside the expected minor/major-fault class, then
retains values within the expected-class P25/P75 bounds extended by 1.5 IQR.
Its quantile convention selects integer-indexed observations; its even-sized
median is the upper middle value.

The shell runner averages each statistic over accepted batches. Its default
acceptance threshold is 90% retained out of all attempted calls, including
both filtering stages. It targets five accepted batches, with at most twenty
attempts per target/condition. All six existing CSV rows report five accepted
batches. The following labels therefore describe the saved numbers:

| Saved field | Actual statistic |
| --- | --- |
| `Grand_Median` | Rounded arithmetic mean of accepted batch medians |
| `Grand_Mean` | Arithmetic mean of accepted batch means |
| `Avg_StdDev` | Mean of within-batch population standard deviations |
| `Avg_P25`, `Avg_P75`, `Avg_P95` | Rounded means of the corresponding batch order statistics |
| `Avg_Minor_Flt`, `Avg_Major_Flt` | Mean retained-sample fault counts, conditioned on the selected fault class |

`Grand_Median` is not a pooled median, and `Avg_P25`–`Avg_P75` is not the
interquartile interval of all calls. The manuscript and Markdown result table
now label these as mean batch statistics. Their numerical entries are unchanged.
The 53.5× comparison remains a ratio of those conditional batch aggregates.

## What cannot be recovered from the archive

The C executable does not print individual samples. Its stdout reports the
number of fault mismatches and retained samples for one batch, but the runner
captures this output in a shell variable and does not save it. Only accepted
batch statistics are added to the final CSV. No individual latency or rejected
batch log was found under `test/test_first_call/`; the retained ftrace files and
PMU aggregate CSV describe separate instrumented runs.

Consequently, the existing latency archive cannot establish total attempts,
fault-class frequencies, each exclusion count, unfiltered quantiles, pooled
quantiles or batch-to-batch variability. These quantities must not be inferred
from five accepted batches or from the PMU sample counts. The rows are useful
as conditional first-touch measurements, not unfiltered tail measurements.

The latency executable and runner also do not set CPU affinity themselves.
An invoking shell could have pinned them, but the latency CSV does not record
that invocation or inherited affinity. The manuscript's general CPU-2 setup
cannot be independently verified for this archived latency run from these
files. This is an evidence gap, not a finding that the old run used another CPU.
The revised setup therefore limits the CPU-2 statement to the other named
experiments. Table 2 retains the five accepted batches recorded in the CSV,
without treating the runner's default 100 calls as archived run metadata.

## Required changes in the group B collection

Use the full Native/Stub XXH32 experiment and existing three conditions.
Keep its single-call timed body and the separate PMU/ftrace diagnostics.

1. Save every call's attempt/sample identity, target/condition, TSC cycles,
   minor/major faults and preparation outcome before applying filters. Write
   the buffered records after sampling so file output does not enter the
   timed call. Preserve acquisition order independently of sorted statistics.
2. Save each attempted batch's stdout/stderr, return status, configured sample
   count, fault-class and IQR counts, acceptance decision and reason. Record
   failed preparations instead of silently dropping the attempt. Retain an
   incomplete result when the accepted-batch target is not met.
3. Report all prepared calls, expected-fault calls, IQR-retained calls and
   accepted-batch aggregates separately, with explicit denominators. Apply
   the existing filter as a sensitivity view; retain the unfiltered evidence.
   Do not treat a failed preparation as a latency sample.
4. Record and enforce the chosen CPU affinity and retain the actual kernel,
   DSO/owner identities, input size and collection parameters. Keep setup
   timing and PFN/resource observations in the same deployment record, with
   their own measurement windows.

## Prepared collector changes and remaining validation

`benchmark_first_touch.c` now accepts `-o`, preserving samples before sorting,
including a failed preparation row with empty measurement fields. Output is
written after sampling. The eviction helper now propagates `madvise` failure;
the revised protocol will stop and record that preparation failure. The
single-call TSC/getrusage measurement region remains unchanged in source.

`run_benchmarks.sh` now enforces and records CPU affinity, saves the executed
benchmark binary, retains every attempt's stdout/stderr/raw CSV, and writes
the decision ledger. It refuses existing outputs, stops on benchmark errors,
and marks an exhausted batch budget incomplete. The legacy aggregate schema
is preserved so existing table consumers still work.

Three synthetic-output orchestration tests passed, covering accepted/rejected
attempt retention, incomplete groups, failure logging and prevention of
overwriting existing results. Shell syntax validation also passed. These tests
do not load either DSO or measure performance. C compilation and an actual
registered-carrier validation are deferred until Clocktime collection ends.

`analyze_first_touch.py` now supplies the postprocessing views in item 3. It
reconstructs filtering independently from raw samples, checks the decision
ledger and stdout statistics, and separates pooled call distributions from
mean batch statistics. The all-prepared view includes observed calls from
rejected batches and counts each observed fault class; preparation failures
are recorded separately. Missing raw/ledger coverage cannot silently pass.

Six analysis tests and the three archiving tests passed. Synthetic archives
demonstrate that rejected-batch long latencies survive in the unfiltered view,
while fault and IQR exclusions remain explicit. They also exercise failed and
incomplete collections and modified/missing observations. A test exposed an
intermittent exit 141 caused by the shell parser closing its input early under
`pipefail`; its extraction functions now consume the complete input. This fix
does not change the acceptance criterion or numerical statistics.

Integration with the full group B session, registered-Stub validation,
and formal collection remain pending. Any future figures must identify the
revised protocol; the new code does not supply missing evidence for the old
table. Whole-session costs, normal release and the separately planned boundary
observations remain group B work. This runner has not been added to a service.

## Compiled native-path validation — 2026-09-12

The modified C collector compiled with `-O3 -Wall -Wextra -Werror -std=c11`.
After the Clocktime service stopped, an actual call to the existing
`so/libclone_xxh32.so` captured 20 hot-condition native observations in acquisition
order, all with successful preparation. A second invocation targeting the same
output file failed and left it byte-identical. Logs and the raw validation file
are in `test/evaluation/results/harness-validation-20260912/` from the repository
root. This validates compiled sample capture and exclusive output creation;
these observations are not a new Native/Stub performance comparison. Registered
Stub, eviction conditions and full session accounting remain unmeasured by
this check.
