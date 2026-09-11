# First-Touch Evaluation

This directory evaluates the first-touch behavior of two dynamically loaded
implementations of the same function:

- `native`: a normal userspace DSO, loaded from `../so/libclone_xxh32.so`.
- `stub`: a kernel-code-backed stub DSO, loaded from
  `../tmp/libzzk_xxh32_lkm.so`.

The static executable baseline is intentionally excluded. The paper question
here is whether the stub DSO preserves native DSO hot/minor-fault performance
while avoiding disk-backed major faults after cache dropping.

## Conditions

Each experiment uses the same three conditions:

| Condition | Setup | Expected native fault | Expected stub fault | Meaning |
|---|---|---:|---:|---|
| `hot` | The function page is already mapped. | 0 minor / 0 major | 0 minor / 0 major | Pure hot function-call cost. |
| `pte-cold` | The function page is warmed once, then its PTE is removed with `madvise(MADV_DONTNEED)`. | 1 minor / 0 major | 1 minor / 0 major | Cost of rebuilding the process PTE while the backing page remains resident. |
| `post-drop` | The PTE is removed, then `sync; echo 3 > /proc/sys/vm/drop_caches` is executed. | 0 minor / 1 major | 1 minor / 0 major | Native DSO takes a disk-backed major fault; stub DSO still maps kernel-resident code but may suffer colder cache/metadata state. |

Do not describe `stub/post-drop` as a symmetric cold major fault. It is a
post-`drop_caches` first touch that should remain a minor fault.

## Experiments

There are three sub-experiments.

### 1. Latency

`benchmark_first_touch` measures elapsed TSC cycles around one target function
call. This is the primary performance measurement used for the paper table.

The benchmark records:

- median, mean, standard deviation, P25, P75, and P95 latency cycles;
- minor and major page-fault counts around the measured call;
- expected-fault filtering before IQR filtering.

Output:

- `first_touch_results.csv`

The latency CSV contains batch aggregates. `Grand_Median` is the arithmetic
mean of accepted batch medians; `Avg_P25`, `Avg_P75` and `Avg_P95` likewise
average batch order statistics. Within a sorted, filtered batch of size `n`,
the benchmark selects zero-based indices `n/2`, `n/4`, `3*n/4` and `95*n/100`
using integer division. In particular, an even-sized batch uses its upper
middle observation as the median. These aggregates are not pooled quantiles.

The runner defaults to 100 calls per attempt, accepts a batch when at least
90% of all calls survive both fault-class and IQR filtering, and stops at five
accepted batches or 20 attempts per target/condition. The historical collector
kept only accepted-batch aggregates; its rejected attempts and unfiltered tails
cannot be reconstructed from the existing CSV. See the
[evidence and collection changes](../../evaluation/first-touch-evidence.md).

The revised latency collector adds `-o samples.csv`, writing every attempted
sample in acquisition order after sampling and before sorting/filtering. A
preparation status of 0 means a measured call, -1 means page eviction failed,
and -2 means cache dropping failed; failed preparations have empty measurement
fields. Page-eviction failures now stop the attempt instead of continuing with
an unprepared condition. File output is outside the timed call.

`run_benchmarks.sh` pins the latency process with `CPU` (default 2), preserves
the benchmark executable, records configuration and affinity, and saves each
attempt's raw CSV, stdout and stderr under `LOG_DIR`. `attempts.csv` records
filter counts and accepted/rejected/failed decisions. Existing output paths
are refused. Exhausting the attempt budget returns 2; benchmark failure stops
the run with its nonzero status. `complete.txt` appears only when every group
reaches the requested accepted-batch count.

Three synthetic-output tests passed for rejection/acceptance, incomplete
collection, failure retention and existing-file preservation. C compilation
and real Native/Stub validation of this revised protocol remain pending until
the active Clocktime campaign ends. No new latency results have been collected.

### 2. PMU

`benchmark_pmc` measures the same target/condition matrix, but enables hardware
performance counters around the measured call. It is kept separate from the
latency benchmark because `perf_event_open`, counter reset/enable/disable, and
counter reads can perturb the short hot path.

The PMU benchmark uses the same condition preparation and expected-fault
filtering as the latency benchmark.

It records:

- TSC cycles for cross-checking with the latency benchmark;
- hardware `cpu-cycles`;
- retired instructions;
- L1I, L1D, LLC, and iTLB misses;
- minor and major page-fault counts.

Output:

- `pmc_results.csv`
- per-group raw logs under `pmc_logs/`

Important interpretation: PMU `cpu-cycles` are on-CPU hardware-counted cycles.
They are not identical to elapsed TSC latency, especially for major faults where
the process may wait off-CPU.

### 3. ftrace

`benchmark_ftrace` captures the kernel function-graph trace for a controlled
minor-fault first touch. It is not part of the main performance table.

Use it to explain the kernel path behind `pte-cold`, for example whether native
and stub take different `handle_mm_fault()` subpaths such as memcg/lruvec
accounting. Because function-graph tracing adds large instrumentation overhead,
do not use ftrace timings as the primary latency result.

Output:

- `ftrace_native_ptecold.log`
- `ftrace_stub_ptecold.log`

## Build

Build the benchmark binaries:

```sh
cd /home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench
make
```

The default DSO paths are:

```sh
STUB_DSO=/home/zzk/BinaryKernelCodeMapping/test/test_first_call/tmp/libzzk_xxh32_lkm.so
NATIVE_DSO=/home/zzk/BinaryKernelCodeMapping/test/test_first_call/so/libclone_xxh32.so
```

Override them if the generated files are in different locations; pass these
variables through `sudo env` alongside the output settings below:

```sh
export STUB_DSO=/path/to/libzzk_xxh32_lkm.so
export NATIVE_DSO=/path/to/libclone_xxh32.so
```

## Run Full Latency + PMU Evaluation

After Clocktime collection ends, rebuild and validate the revised collector
on the first-touch kernel with the actual owner/carrier registered. Use fresh
output paths for a new latency and PMU collection, for example:

```sh
sudo env LATENCY_CSV=first-touch-new.csv LOG_DIR=first-touch-new.logs \
  PMC_CSV=pmc-new.csv PMC_LOG_DIR=pmc-new.logs COMBINED_CSV=combined-new.csv \
  CPU=2 TASKSET_CPU=2 ./run_full_evaluation.sh
```

This executes:

1. `run_benchmarks.sh`, which writes `LATENCY_CSV` and the full latency records in `LOG_DIR`.
2. `run_pmc_matrix.sh`, which writes `PMC_CSV` and `PMC_LOG_DIR`.
3. `merge_latency_pmu.py`, which writes `COMBINED_CSV`.

The combined CSV is the main table source for the paper:

```sh
first_touch_pmu_combined.csv
```

To generate a Markdown table from the current results, use the existing
combined CSV as the source. The current checked output is:

```sh
first_touch_pmu_table.md
```

## Run Individual Experiments

Run latency only:

```sh
sudo env CSV_FILE=first-touch-new.csv LOG_DIR=first-touch-new.logs CPU=2 ./run_benchmarks.sh
```

Run PMU only:

```sh
sudo ./run_pmc_matrix.sh
```

Merge existing latency and PMU CSV files:

```sh
./merge_latency_pmu.py \
  --latency first_touch_results.csv \
  --pmu pmc_results.csv \
  -o first_touch_pmu_combined.csv
```

Run ftrace minor-fault path comparison:

```sh
sudo ./benchmark_ftrace -t native -s pte-cold -o ftrace_native_ptecold.log
sudo ./benchmark_ftrace -t stub -s pte-cold -o ftrace_stub_ptecold.log
```

`benchmark_ftrace` intentionally focuses on `pte-cold`. It captures the
minor-fault path without `drop_caches` noise and without looping over many
samples.

## Useful Knobs

The scripts accept environment variables:

| Variable | Default | Used by | Meaning |
|---|---:|---|---|
| `STUB_DSO` | `../tmp/libzzk_xxh32_lkm.so` | all | Stub DSO path. |
| `NATIVE_DSO` | `../so/libclone_xxh32.so` | all | Native DSO path. |
| `CONDITIONS_OVERRIDE` | `hot pte-cold post-drop` | latency, PMU | Restrict conditions, for example `CONDITIONS_OVERRIDE='hot pte-cold'`. |
| `NUM_RUNS` | `100` | latency | Samples per latency batch. |
| `CPU` | `2` | latency | Enforced benchmark CPU affinity. |
| `CSV_FILE` | `first_touch_results.csv` | latency | New aggregate output path. |
| `LOG_DIR` | CSV stem plus `.logs` | latency | New directory for all attempts and configuration. |
| `TARGET_SUCCESSES` | `5` | latency | Number of accepted latency batches per group. |
| `MAX_ATTEMPTS` | `20` | latency | Maximum latency batch attempts per group. |
| `PMC_RUNS` | `30` | PMU | Samples per PMU group. |
| `TASKSET_CPU` | `1` | PMU | CPU used by `taskset -c`. |

`post-drop` requires root because it writes `/proc/sys/vm/drop_caches`. PMU
usually also requires root or a permissive `perf_event_paranoid` setting.

## Expected Result Shape

A valid run should have:

- `hot`: both targets report 0 minor and 0 major faults, with near-identical
  latency.
- `pte-cold`: both targets report 1 minor and 0 major faults, with near-identical
  latency.
- `native/post-drop`: 0 minor and 1 major fault, with much larger latency.
- `stub/post-drop`: 1 minor and 0 major faults, with latency higher than
  `stub/pte-cold` but far lower than `native/post-drop`.

If `Fault_Mismatches` is nonzero, inspect the per-group log before using that
row in the paper.
