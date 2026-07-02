# Pseudo-GOT Microbenchmarks

One reference machine used during development:

```text
Linux intelnuczzk 5.15.0-119-generic #129-Ubuntu SMP Fri Aug 2 19:25:20 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
```

This package implements the first two layers of the pseudo-GOT performance methodology:

1. Layer 1 measures the primitive cost bounds of pgot-data and pgot-func.
2. Layer 2 measures how visible overhead changes with event placement under
   fixed ordinary work.

The code is intentionally synthetic and controlled. The goal is not to mimic a complete kernel function, but to isolate variables that explain the later real-function benchmarks.

## Portability

The benchmarks are intended to run on another Linux x86-64 machine, but the
absolute cycle numbers are machine-dependent. When moving to a new machine,
rebuild from source and record the new environment metadata.

Required for the main cycle benchmarks:

1. Linux on x86-64 with `rdtscp` support.
2. `make`, `gcc`, `bash`, and `python3`.
3. GCC support for the retpoline flags used by the retpoline builds:
   `-mindirect-branch=thunk-inline`, `-mindirect-branch-register`, and
   `-fcf-protection=none`.

Optional:

1. `perf` is only needed when `RUN_PERF=1`.
2. `sudo` or relaxed `kernel.perf_event_paranoid` may be needed for hardware
   counters.
3. CPU isolation, fixed governor, and turbo control are not required to execute
   the code, but they are recommended for paper-quality measurements.

Quick check on a new machine:

```bash
cd pgot_benchmarks
make clean
make
./run_experiment.sh list
CPU=0 ITERATIONS=1000 REPEATS=3 OUTER_RUNS=1 ./run_experiment.sh layer1-data-independent
```

If the CPU number is not known, omit `CPU=...`; the run will be unpinned and
the output metadata will record that.

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
  run_experiment.sh         select and run one experiment group
  run_all.sh                wrapper for ./run_experiment.sh all
  collect_env.sh            environment snapshot helper
  scripts/
    process_layer1_data_independent.py
                            data processing only
  results/
    layer1/<experiment>/    Layer 1 outputs grouped by experiment
    layer2/<experiment>/    Layer 2 outputs grouped by experiment
```

## Build And Run

```bash
cd pgot_benchmarks
make
ITERATIONS=1000000 REPEATS=31 CPU=2 ./run_experiment.sh layer2-data-placement
```

List available experiments with:

```bash
./run_experiment.sh list
```

Run everything with:

```bash
CPU=2 ITERATIONS=1000000 REPEATS=31 ./run_all.sh
```

Results are grouped by experiment. For example:

```text
results/layer2/data_placement/
  main/results.csv
  raw/
  perf/                    only when RUN_PERF=1

results/layer2/func_placement/
  main/results.csv
  raw/
  validation/
  perf/                    only when RUN_PERF=1

results/layer1/data_independent/
  main/run_summaries.csv
  raw/samples.csv
  processed/summary.csv
  processed/paper_table.csv
```

Layer 2 pgot-func validation includes objdump output and selected distributed-placement checks under the same experiment directory.

If CPU isolation is already configured on the machine, pass the isolated CPU through `CPU=...`. Otherwise omit it. The output CSV records the requested CPU, kernel command line, isolated CPU mask, governor, turbo/boost state, SMT state, Spectre v2 mitigation, CPU model, topology, and compiler.

For paper-quality runs, record and report the same settings in the paper:

```bash
cd pgot_benchmarks
CPU=2 ITERATIONS=1000000 REPEATS=31 ./run_experiment.sh layer2-func-placement
```

Recommended run conditions:

1. Pin to one CPU with `CPU=...`.
2. Prefer an isolated CPU, and report the `isolcpus`, `nohz_full`, and `rcu_nocbs` kernel settings if used.
3. Use a fixed frequency policy, preferably the `performance` governor.
4. Report whether turbo/boost is enabled or disabled.
5. Report the repeat count and IQR columns, not only the median.

Optional hardware-event collection is enabled per experiment:

```bash
RUN_PERF=1 PERF_ITERATIONS=5000000 PERF_REPEATS=7 CPU=2 \
  ./run_experiment.sh layer2-func-placement
```

This writes `perf stat -x,` CSV files under that experiment's `perf/` directory, for example:

```text
results/layer2/func_placement/perf/
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
experiment,events,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
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
experiment,chain_steps,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_step,direct_cycles_per_step,pgot_cycles_per_step,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
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
experiment,pgot_events,target_count,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
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

> Under the same total work, does visible pgot overhead depend only on the
> number of pgot events, or also on local placement density?

Layer 2 deliberately does not include dependent loads, random target traces, or
register-pressure experiments. Those variables belong either to Layer 1 bounds
or to later real-function analysis.

### 01_density_data

Measures pgot-data placement sensitivity with independent loads. The benchmark
keeps total ordinary work fixed at `base_work=64` and changes where the data
events appear in the statement stream.

Variables:

| Variable | Values |
|---|---|
| base work | fixed `64` |
| access pattern | independent |
| pgot events | `0, 1, 2, 4, 8, 16, 32` |
| placement | `dist1`, `dist2`, `dist4`, `dist8` |
| sample order | runner default `interleave` |

Placement means how many event groups are available. `dist1` clusters all data
events into one group; `dist8` distributes them across eight groups while
keeping the same total ordinary work.

### 02_density_func

Measures stable-target pgot-func placement sensitivity. The no-retpoline build
measures the low-cost predictable indirect-call case; the retpoline build
measures the protected indirect-call case.

Variables:

| Variable | Values |
|---|---|
| base work | `32, 64, 128` |
| pgot events | `0, 1, 2, 4, 8, 16` |
| placement | `dist1`, `dist2`, `dist4`, `dist8` |
| target pattern | stable target |
| build | no-retpoline, retpoline |

Layer 2 binaries also support single-case mode:

```bash
./layer2/02_density_func/bench_retpoline \
  --base-work 64 --placement dist8 --pgot-events 16 \
  --sample-order interleave --iterations 5000000 --repeats 31 --cpu 2
```

When `PGOT_RAW_DIR` is set, Layer 2 writes one raw CSV per case:

```text
repeat,direct_cycles,pgot_cycles,delta_cycles
```

Layer 2 CSV fields:

```text
experiment,...,base_work,placement,placement_groups,pgot_events,avg_events_per_group,max_events_per_group,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,overhead_percent,delta_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter
```

Interpretation:

| Metric | Meaning |
|---|---|
| `delta_cycles_per_iter` | absolute extra cycles introduced by pgot per benchmark iteration |
| `overhead_percent` | how much that extra work matters relative to the whole function |
| `delta_cycles_per_event` | whether the extra cost scales with the number of pgot events |

Do not report only one of these. Absolute overhead and relative overhead answer different questions.

## Recommended Paper Figures

Use Layer 1 for primitive bounds:

1. pgot-data independent vs dependent: `cycles_per_event`.
2. pgot-func stable target: direct vs pgot, no-ret vs retpoline.
3. pgot-func high-entropy trace: `cycles_per_call` and `branch-misses` versus target count.

Use Layer 2 for density:

1. For pgot-data, table or line plot of `delta_cycles_per_iter` versus
   `pgot_events`, separated by `placement`; use `base_work=64`.
2. For pgot-func, show `base_work=64` as the main result and use
   `base_work=32/128` as sensitivity checks.
3. For retpoline pgot-func, include objdump validation and optional perf
   evidence from the same `results/layer2/func_placement/` directory.
4. Report `delta_cycles_per_iter`, `overhead_percent`,
   `delta_cycles_per_event`, and IQR together; they answer different questions.

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
