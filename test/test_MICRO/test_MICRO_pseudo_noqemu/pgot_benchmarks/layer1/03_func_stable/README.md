# Layer1 Func-PGOT Stable-Target Kernel Module Benchmark

This directory contains the kernel-mode Layer1 func-pgot stable-target
primitive experiment.

## Goal

The experiment asks:

```text
For a stable function target, what part of func-pgot overhead comes from
ordinary indirect-call execution, and what part comes from the per-event pgot
function slot load?
```

The important point is that the old two-way comparison:

```text
direct call target_0
vs
slot load + indirect call target_0
```

does not isolate the pgot slot load. It also includes the difference between a
direct call and an indirect call. This benchmark therefore uses a four-way
mechanism split.

## Measured Paths

Each event is one function-call statement in one benchmark iteration.

```text
direct
  x = target_0(x)

cached_indirect
  f = pgot_func_table[0]       // loaded once before the timed loop
  x = f(x)                     // indirect call inside each event

slot_direct
  f = pgot_func_table[0]       // loaded once per event
  x = target_0(x)              // direct call still used

pgot
  f = pgot_func_table[0]       // loaded once per event
  x = f(x)                     // indirect call inside each event
```

The main deltas are:

```text
delta_cached_direct = cached_indirect - direct
  Stable indirect-call visible cost.

delta_slot_direct = slot_direct - direct
  Slot-load control in a direct-call stream.

delta_pgot_cached = pgot - cached_indirect
  Per-event pgot slot-load increment in an indirect-call stream.

delta_pgot_direct = pgot - direct
  Old-style end-to-end direct-vs-pgot comparison.
```

`delta_pgot_cached` is the closest test to the theoretical question:

```text
pgot_func ~= cached_indirect_call + slot_load
```

## Build Modes

The normal experiment builds two modules:

```text
no_retpoline
retpoline
```

The default build also uses:

```text
BENCH_NOTRACE=1
BENCH_ALIGN64=1
```

These controls remove fentry instrumentation from the measured target/body
functions and align them to 64-byte boundaries. Earlier diagnostic runs showed
that no-retpoline sub-cycle deltas are sensitive to function entry shape and
layout, so the default experiment excludes those external effects.

## Event Counts

The benchmark uses compile-time-expanded event bodies:

```text
1, 2, 4, 8, 16
```

There is no runtime inner loop over events. The only runtime loop is the
benchmark iteration loop.

## Sampling

Each raw sample measures:

```text
empty
direct
cached_indirect
slot_direct
pgot
```

The order rotates by repeat to reduce short-term drift and ordering bias.
Statistics are computed from paired deltas. Outliers are marked per
`(build,event)` with the IQR rule on `delta_pgot_direct`:

```text
[Q1 - 1.5 * IQR, Q3 + 1.5 * IQR]
```

## Run Commands

Smoke run:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000 REPEATS=3 OUTER_RUNS=1 ./run.sh
```

Formal run:

```bash
SUDO_PASSWORD='...' CPU=2 ITERATIONS=1000000 REPEATS=31 OUTER_RUNS=10 ./run.sh
```

The formal run writes:

```text
results/layer1/03_func_stable/
  metadata.txt
  raw.csv
  processed.csv
  paper_table.csv
  SUMMARY.md
```

`KEEP_BUILD=1` may be used temporarily when objdump validation is needed. The
`.build` directory contains copied `.ko` files only for static validation and
must not be kept as a result artifact.

## Diagnostic Runs

The result directory may also contain diagnostic runs:

```text
kmod_diag_lfence_split
  no-retpoline four-way split with lfence around call events.
```

This diagnostic intentionally changes the execution semantics. It is used to
prove that, when the pgot slot load is forced to complete before the indirect
call, the slot-load increment becomes visible and stable. It is not the normal
execution result.

## Interpretation Boundary

This benchmark measures visible cost in a generated call sequence. It is not a
pure architectural latency test.

For func-pgot, the pgot slot load feeds an indirect branch target. Unlike the
data-pgot load in Layer1/01, the branch target can be predicted by the CPU, so
the slot load can be removed from the visible critical path in normal
no-retpoline execution. The serialized lfence diagnostic is included to prove
that the load exists and can be exposed, not to replace the normal result.
