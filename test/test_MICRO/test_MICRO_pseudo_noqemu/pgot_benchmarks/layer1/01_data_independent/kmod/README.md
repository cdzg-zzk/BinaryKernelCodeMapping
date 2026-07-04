# Layer1 Data-Independent Kernel Module Benchmark

This directory contains the kernel-mode version of the Layer1 data-pgot
independent primitive experiment.

## Goal

The experiment asks:

```text
For statement-level independent data access, how much visible cost does pgot
add compared with direct data access?
```

The tested statements are:

```text
direct: acc += direct_values[idx]
pgot:   p = pgot_data_table[idx]; acc += *p
```

`pgot` and `direct` use the same event count and the same source-level event
positions. The intended semantic difference is only that `pgot` performs one
extra slot load before dereferencing the real data pointer.

## Why Kernel Mode

The earlier userspace benchmark is useful for iteration, but this version runs
the timed loop inside a kernel module init path. This avoids userspace syscall
or process scheduling effects inside the measured region and makes the
microbenchmark closer to the kernel-side use case.

Module load/unload, `dmesg` collection, CSV processing, and Python statistics
are outside the measured loop.

## Event Definition

`event` means one data-access statement in one benchmark iteration:

```c
/* direct event */
acc += direct_values[idx];

/* pgot event */
p = pgot_data_table[idx];
acc += *p;
```

The reported `cycles/event` is:

```text
cycles per benchmark iteration / number of events in that iteration
```

It is not a function call cost.

## Compile-Time Expansion

Each event count is a separate compile-time-expanded body:

```text
1, 2, 4, 6, 8, 10, 12, 14, 16, 18
```

This avoids a runtime loop over events, so the benchmark does not mix event
control overhead into the measured direct-vs-pgot comparison. The outer timing
loop remains the same for all cases.

## Measured Variants

The module measures two real variants and derives one additional analysis view
from the same raw samples.

```text
scheduled
  Compiler-scheduled independent loads. This is the main result because it
  reflects the normal generated statement sequence.

scheduled_empty_adjusted
  Derived from scheduled by subtracting an empty-loop baseline:
  direct_adjusted = direct - empty
  pgot_adjusted   = pgot   - empty
  delta           = pgot   - direct

barriered
  Diagnostic variant where every event ends with:
  asm volatile("" : "+r"(acc) :: "memory");
```

`scheduled_empty_adjusted` removes the most obvious fixed loop cost, especially
for `event=1`. It still does not become a pure single-load latency test,
because the remaining cost can include compiler scheduling, reduction through
`acc`, frontend effects, register pressure, and code shape.

`barriered` is not the main primitive-cost result. It intentionally changes the
generated instruction schedule by blocking cross-event scheduling and shortening
live ranges. Its purpose is to explain whether observed non-monotonic behavior
comes from normal generated-code effects rather than only from the pgot slot
load.

## Sampling Design

Each raw sample measures `empty`, `direct`, and `pgot` in an interleaved order.
The order rotates by repeat:

```text
repeat % 3 == 0: empty, direct, pgot
repeat % 3 == 1: pgot, empty, direct
repeat % 3 == 2: direct, pgot, empty
```

This reduces bias from short-term drift in CPU frequency, thermal state, and
frontend/cache state. The paired delta is computed per repeat:

```text
delta = pgot_cycles - direct_cycles
```

Statistics are computed per `(variant, event)`. Outliers are marked using the
IQR rule on paired delta:

```text
[Q1 - 1.5 * IQR, Q3 + 1.5 * IQR]
```

The summary tables keep both raw mean delta and outlier-filtered median delta.
For very small deltas, the IQR can be zero or close to zero; in that case the
drop rate may look high even when raw mean and kept median agree.

## Run Commands

Run a smoke test:

```bash
CPU=2 ITERATIONS=1000 REPEATS=3 OUTER_RUNS=1 ./run.sh
```

Run a paper-style collection:

```bash
CPU=2 ITERATIONS=1000000 REPEATS=31 OUTER_RUNS=100 ./run.sh
```

If sudo needs a password in non-interactive mode:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000000 REPEATS=31 OUTER_RUNS=100 ./run.sh
```

## Outputs

Outputs are written to:

```text
results/layer1/01_data_independent/kmod/
  metadata.txt       experiment config and machine environment
  raw.csv            raw empty/direct/pgot paired samples
  processed.csv      processed statistics after outlier filtering
  paper_table.csv    compact table for reporting
  SUMMARY.md         human-readable interpretation and static evidence
```

For the current formal run, the raw data size is:

```text
2 measured variants * 10 event counts * 31 repeats * 100 outer runs
= 62000 paired samples
```

## Interpretation Boundary

The most defensible interpretation is:

```text
Layer1 data-pgot independent measures the visible cost of adding a pgot slot
load inside a generated statement sequence.
```

It should not be described as a pure architectural load latency measurement.
The generated code changes with event count, and those changes are part of the
evidence rather than noise to hide.
