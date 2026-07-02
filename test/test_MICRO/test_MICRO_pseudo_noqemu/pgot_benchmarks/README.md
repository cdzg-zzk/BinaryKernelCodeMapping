# Pseudo-GOT Microbenchmarks

Target machine recorded from the request:

```text
Linux intelnuczzk 5.15.0-119-generic #129-Ubuntu SMP Fri Aug 2 19:25:20 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
```

This package implements the first two layers of the pseudo-GOT performance methodology:

1. Layer 1 measures the primitive cost bounds of pgot-data and pgot-func.
2. Layer 2 measures how pgot event density is diluted by ordinary function work.

The code is intentionally synthetic and controlled. The goal is not to mimic a complete kernel function, but to isolate variables that explain the later real-function benchmarks.

## Directory Layout

```text
pgot_benchmarks/
  common/
    bench_common.h          common timing, median, CPU pinning
    data_tables.h           direct data slots and pseudo-GOT data slots
    targets.h               target functions and pseudo-GOT function slots
    common.mk               shared compiler flags
  layer1/
    01_data_independent/    pgot-data throughput-style loads
    02_data_dependent/      pgot-data dependent pointer-chasing loads
    03_func_stable/         fixed-target pgot-func, ret/no-ret builds
    04_func_entropy/        high-entropy target trace, ret/no-ret builds
  layer2/
    01_density_data/        base work vs pgot-data event density
    02_density_func/        base work vs pgot-func event density
  scripts/
    run_all.sh              build and run all cycle benchmarks
    perf_func_cases.sh      optional perf stat collection for pgot-func cases
```

## Build And Run

```bash
cd pgot_benchmarks
make
ITERATIONS=1000000 REPEATS=31 CPU=2 ./scripts/run_all.sh
```

The main CSV is written to:

```text
results/all_results.csv
```

Layer 2 raw repeat samples are written to:

```text
results/raw/
```

Layer 2 pgot-func validation artifacts are written to:

```text
results/validation/
```

This includes `objdump_layer2_func_retpoline.txt` and `perf stat` CSV files for selected retpoline cases.

If CPU isolation is already configured on the machine, pass the isolated CPU through `CPU=...`. Otherwise omit it. The output CSV records the requested CPU, kernel command line, isolated CPU mask, governor, turbo/boost state, SMT state, Spectre v2 mitigation, CPU model, topology, and compiler.

For paper-quality runs, record and report the same settings in the paper:

```bash
cd pgot_benchmarks
CPU=2 ITERATIONS=1000000 REPEATS=31 ./scripts/run_all.sh
```

Recommended run conditions:

1. Pin to one CPU with `CPU=...`.
2. Prefer an isolated CPU, and report the `isolcpus`, `nohz_full`, and `rcu_nocbs` kernel settings if used.
3. Use a fixed frequency policy, preferably the `performance` governor.
4. Report whether turbo/boost is enabled or disabled.
5. Report the repeat count and IQR columns, not only the median.

Optional hardware-event collection for function-call cases:

```bash
ITERATIONS=5000000 REPEATS=7 CPU=2 ./scripts/perf_func_cases.sh
```

This writes one `perf stat -x,` CSV per case under:

```text
results/perf/
```

The perf environment snapshot is written to:

```text
results/perf/environment.txt
```

Perf events may require adjusting `kernel.perf_event_paranoid`.

## Timing Method

The benchmark programs use:

```text
lfence; rdtscp
tested loop
rdtscp; lfence
```

Each case performs a warmup, then repeats the timed region multiple times and reports the median. This avoids relying on a single noisy run. The result fields include the iteration count and repeat count so that all measurements are reproducible.

The pseudo-GOT slot accesses use `volatile` loads in the benchmark code. This is intentional: otherwise the compiler can hoist a fixed pseudo-GOT slot out of a loop and accidentally remove the pgot event being measured.

## Layer 1: Primitive Cost Bounds

Layer 1 asks:

> What are the basic lower and upper cost bounds of pgot-data and pgot-func?

It does not try to model complete kernel functions.

### 01_data_independent

Measures direct data access versus pgot-data access when loads are independent.

Variables:

| Variable | Values |
|---|---|
| events per iteration | `1, 2, 4, 8, 16` |
| variant | `direct`, `pgot` |

Important interpretation:

Independent loads can be overlapped by out-of-order execution. Therefore, a near-zero delta is a meaningful result: it describes the lower-bound throughput case.

CSV fields:

```text
experiment,variant,events,iterations,repeats,cycles_per_iter,cycles_per_event,iqr_cycles_per_iter
```

### 02_data_dependent

Measures direct data access versus pgot-data access in a dependent chain.

Variables:

| Variable | Values |
|---|---|
| chain steps per iteration | `1, 2, 4, 8, 16` |
| variant | `direct`, `pgot` |

Important interpretation:

The next step depends on the previous loaded value, so the extra pgot slot load is harder to hide. This is the latency-oriented upper-bound case for pgot-data.

CSV fields:

```text
experiment,variant,chain_steps,iterations,repeats,cycles_per_iter,cycles_per_step,iqr_cycles_per_iter
```

### 03_func_stable

Measures fixed-target pgot-func while varying event count.

Builds:

| Binary | Meaning |
|---|---|
| `bench_noret` | ordinary indirect call build |
| `bench_retpoline` | retpoline-protected indirect call build |

Variables:

| Variable | Values |
|---|---|
| variant | `direct`, `pgot` |
| pgot events | `1, 2, 4, 8, 16` |
| target count | always `1` |
| target behavior | stable target only |

This is the common case for the current pseudo-GOT design: each transformed
callsite normally resolves to one fixed target. `pgot_events` controls how many
function-call events are repeated in one loop iteration. In the `pgot` variant,
each event reloads `slot[0]` before calling the target, so the event count is a
real Pseudo-GOT event count rather than repeated calls through a hoisted function
pointer.

CSV fields:

```text
experiment,variant,pgot_events,target_count,iterations,repeats,cycles_per_iter,cycles_per_event,iqr_cycles_per_iter
```

For per-variant perf collection:

```bash
PGOT_VARIANT=pgot ./layer1/03_func_stable/bench_noret
PGOT_EVENTS=4 PGOT_VARIANT=pgot ./layer1/03_func_stable/bench_noret
```

### 04_func_entropy

Measures pgot-func under a high-entropy target trace.

Variables:

| Variable | Values |
|---|---|
| target count | `1, 2, 4, 8, 16` |
| build | no-retpoline, retpoline |
| trace length | `65536` |

This is not the normal pgot callsite behavior. It is a stress test that bounds
the unfavorable branch-target prediction case. Here `target_count` changes the
number of possible indirect-call targets; it is different from `pgot_events` in
`03_func_stable`. Simple round-robin traces are intentionally avoided because
modern predictors can learn short regular patterns.

The trace is generated once before each case from a fixed seed and then reused. It is long enough to avoid a tiny repeating pattern, while still being reproducible.

CSV fields:

```text
experiment,variant,target_count,iterations,repeats,trace_len,cycles_per_call,iqr_cycles_per_call
```

For per-target perf collection:

```bash
PGOT_TARGET_COUNT=8 ./layer1/04_func_entropy/bench_noret
```

## Layer 2: Density And Dilution

Layer 2 asks:

> Once pgot events are placed into a function body, how do absolute and relative overhead change as ordinary work increases?

Layer 2 deliberately does not include dependent loads, random target traces, or register-pressure experiments. Those variables belong either to Layer 1 bounds or to later real-function analysis.

### 01_density_data

Measures pgot-data event density with independent loads. The benchmark expands
`base_work` and data-load events directly inside the timed loop; it does not
call a generated body function once per iteration. This keeps the Layer 2
data-pgot result focused on statement-level density/dilution rather than
per-iteration call/return and body-function layout effects.

Variables:

| Variable | Values |
|---|---|
| base work | `0, 16, 64, 256, 512` |
| pgot events | `0, 1, 2, 4, 8, 16` |
| sample order | `separate`, `interleave` for targeted validation |

The default sample order is `separate`. `interleave` is intended for targeted
validation when checking whether small direct-vs-pgot deltas are caused by
sampling-phase drift.

### 02_density_func

Measures pgot-func event density with stable targets. Like `01_density_data`,
the benchmark expands `base_work` and call events directly inside the timed
loop. The no-retpoline build measures the low-cost predictable indirect-call
case; the retpoline build measures the protected indirect-call case.

Variables:

| Variable | Values |
|---|---|
| base work | `0, 16, 64, 256, 512` |
| pgot events | `0, 1, 2, 4, 8, 16` |
| build | no-retpoline, retpoline |
| placement controls | `post`, `pre`, `split`, `post_fenced`, `distributed`, `dist2`, `dist4`, `dist8` |

Layer 2 binaries also support single-case mode:

```bash
./layer2/02_density_func/bench_retpoline --base-work 64 --pgot-events 1 --iterations 5000000 --repeats 31 --cpu 2
```

`distributed` is a compatibility alias for `dist4`. The `dist2`, `dist4`, and
`dist8` placements split `base_work=64` into 2, 4, or 8 chunks and distribute
the requested pgot events across those chunks.

When `PGOT_RAW_DIR` is set, Layer 2 writes one raw CSV per case:

```text
repeat,direct_cycles,pgot_cycles,delta_cycles
```

Layer 2 CSV fields:

```text
experiment,base_work,pgot_events,iterations,repeats,direct_cycles_per_call,pgot_cycles_per_call,delta_cycles_per_call,overhead_percent,delta_cycles_per_event,direct_iqr_cycles_per_call,pgot_iqr_cycles_per_call
```

Interpretation:

| Metric | Meaning |
|---|---|
| `delta_cycles_per_call` | absolute extra cycles introduced by pgot |
| `overhead_percent` | how much that extra work matters relative to the whole function |
| `delta_cycles_per_event` | whether the extra cost scales with the number of pgot events |

Do not report only one of these. Absolute overhead and relative overhead answer different questions.

## Recommended Paper Figures

Use Layer 1 for primitive bounds:

1. pgot-data independent vs dependent: `cycles_per_event`.
2. pgot-func stable target: direct vs pgot, no-ret vs retpoline.
3. pgot-func high-entropy trace: `cycles_per_call` and `branch-misses` versus target count.

Use Layer 2 for density:

1. Heatmap of `overhead_percent` with `base_work` on one axis and `pgot_events` on the other.
2. Line plot of `delta_cycles_per_call` versus `pgot_events`.
3. Optional line plot of `delta_cycles_per_event`; if it is stable, the absolute cost is mostly event-count driven.

## Notes For Integrating With The Real System

The pseudo-GOT tables in this package are synthetic:

```c
pgot_data_table[i] -> &direct_values[i]
pgot_func_table[i] -> target_i
```

When integrating with your actual transformed kernel functions, keep the same measurement format:

```text
direct_cycles_per_call
pgot_cycles_per_call
delta_cycles_per_call
overhead_percent
dynamic_pgot_data_per_call
dynamic_pgot_func_per_call
```

That lets the real-function layer reuse the same interpretation as Layer 2.
