# Layer1 Data-Dependent Kernel Module Benchmark

This directory contains the kernel-mode version of the Layer1 data-pgot
dependent primitive experiment.

## Goal

The experiment asks:

```text
For dependent pointer-chasing data access, how much visible cost does pgot add
compared with direct data access?
```

The tested statements are:

```text
direct: idx = chain_values[idx & MASK]
pgot:   p = pgot_chain_table[idx & MASK]; idx = *p
```

Unlike `01_data_independent`, each event depends on the result of the previous
event. This creates a true load-use dependency chain.

## Why Kernel Mode

The timed loop runs inside a kernel module init path. Module loading,
unloading, `dmesg` collection, and Python processing are outside the measured
loop. This keeps the measurement closer to the kernel-side pgot use case and
avoids userspace process/syscall effects inside the timed region.

## Event Definition

`event` means one pointer-chasing step in one benchmark iteration:

```c
/* direct event */
volatile u64 *direct_p = &chain_values[idx & MASK];
idx = *direct_p;

/* pgot event */
u64 * volatile *slot = pgot_chain_table;
volatile u64 *pgot_p = slot[idx & MASK];
idx = *pgot_p;
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

This avoids a runtime loop over events. The outer timing loop is still present
and is identical across cases.

## Measured Variants

The module measures two variants and derives one auxiliary view:

```text
scheduled
  Normal compiler-generated pointer-chasing sequence. This is the main result.

scheduled_empty_adjusted
  Derived from scheduled by subtracting an empty-loop baseline:
  direct_adjusted = direct - empty
  pgot_adjusted   = pgot   - empty
  delta           = pgot   - direct

barriered
  Diagnostic variant where every event ends with:
  asm volatile("" : "+r"(idx) :: "memory");
```

For this dependent benchmark, `scheduled_empty_adjusted` is diagnostic only.
The formal result should use raw paired delta and/or linear-regression slope.
The reason is that the measured empty loop is not an additive intercept for the
dependent pointer-chasing chain. If it is subtracted as if it were independent,
the absolute adjusted `direct` and `pgot` values contain an artificial
`-empty/event` term.

## Sampling Design

Each raw sample measures `empty`, `direct`, and `pgot` in an interleaved order.
The order rotates by repeat:

```text
repeat % 3 == 0: empty, direct, pgot
repeat % 3 == 1: pgot, empty, direct
repeat % 3 == 2: direct, pgot, empty
```

The paired delta is computed per repeat:

```text
delta = pgot_cycles - direct_cycles
```

Statistics are computed per `(variant, event)`. Outliers are marked using the
IQR rule on paired delta:

```text
[Q1 - 1.5 * IQR, Q3 + 1.5 * IQR]
```

## Run Commands

Run a smoke test:

```bash
CPU=2 ITERATIONS=1000 REPEATS=3 OUTER_RUNS=1 ./run.sh
```

Run a larger collection:

```bash
CPU=2 ITERATIONS=100000 REPEATS=31 OUTER_RUNS=100 ./run.sh
```

If sudo needs a password in non-interactive mode:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=100000 REPEATS=31 OUTER_RUNS=100 ./run.sh
```

## Outputs

Outputs are written to:

```text
results/layer1/02_data_dependent/
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
Layer1 data-pgot dependent measures the visible cost of adding a pgot slot load
inside a dependent pointer-chasing statement sequence.
```

It should not be described as pure architectural load latency. The primary
reported metric is raw paired `pgot - direct` delta, cross-checked by
linear-regression slope over event count. Empty-loop adjustment is kept as a
diagnostic view for baseline behavior, not as the main cost estimate.
