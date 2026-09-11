# First-touch evidence and collection changes

Source and artifact audit on 2026-09-11. No benchmark was run and no cache was
dropped. Collector changes prepared after the audit are described below;
registration code remains unchanged.

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

The postprocessing views in item 3, integration with the full group B session,
and real collection remain pending. Any future figures must identify the
revised protocol; the new code does not supply missing evidence for the old
table. Whole-session costs, normal release and the separately planned boundary
observations remain group B work. This runner has not been added to a service.
