# Layer1 Data-Dependent Kmod Summary

## Reported Result

Use the raw scheduled paired delta as the primary result.

```text
For dependent pointer-chasing data access in this kernel-mode Layer1
microbenchmark, data-pgot adds about 5.02 cycles/event.
```

The raw scheduled result is stable across all tested event counts:

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6.021 | 11.038 | 5.017 | 0.000 | 5.022 | 16.3% |
| 2 | 6.021 | 11.038 | 5.017 | 0.000 | 5.021 | 31.3% |
| 4 | 6.021 | 11.038 | 5.017 | 0.017 | 5.020 | 1.6% |
| 6 | 6.021 | 11.049 | 5.028 | 0.022 | 5.020 | 0.2% |
| 8 | 6.021 | 11.046 | 5.025 | 0.012 | 5.020 | 0.6% |
| 10 | 6.024 | 11.044 | 5.020 | 0.010 | 5.019 | 1.1% |
| 12 | 6.024 | 11.043 | 5.019 | 0.007 | 5.019 | 1.6% |
| 14 | 6.025 | 11.043 | 5.018 | 0.007 | 5.019 | 1.3% |
| 16 | 6.025 | 11.043 | 5.018 | 0.005 | 5.018 | 1.6% |
| 18 | 6.024 | 11.042 | 5.018 | 0.003 | 5.018 | 3.5% |

Linear regression on raw scheduled `cycles/iteration` gives the same result:

| range | metric | intercept | slope cycles/event | R2 |
|---|---|---:|---:|---:|
| 1..18 | direct | -0.0149 | 6.0252 | 1.00000 |
| 1..18 | pgot | 0.0043 | 11.0428 | 1.00000 |
| 1..18 | delta | 0.0185 | 5.0175 | 1.00000 |

This is the main conclusion to report. The empty-loop-adjusted absolute
`direct` and `pgot` values are diagnostic only and should not be interpreted as
pure load latency.

## Experiment

This is the kernel-mode Layer1 data-pgot dependent experiment.

Measured statement semantics:

```text
direct: idx = chain_values[idx & MASK]
pgot:   p = pgot_chain_table[idx & MASK]; idx = *p
```

Each event depends on the previous event through `idx`, so the benchmark forms
a load-use dependency chain. The timed loop runs inside the kernel module.
Module loading, unloading, `dmesg` collection, and CSV processing are outside
the measured loop.

Formal run configuration:

```text
iterations=100000
repeats=31
outer_runs=100
events=1,2,4,6,8,10,12,14,16,18
measured_variants=scheduled,barriered
derived_variants=scheduled_empty_adjusted
cpu=2
sample_order=interleave
raw_delta=pgot_cycles-direct_cycles
outlier_filter=per-event IQR rule: [Q1-1.5*IQR, Q3+1.5*IQR]
```

Raw sample count:

```text
2 measured variants * 10 event counts * 31 repeats * 100 outer runs
= 62000 paired samples
```

All reported cycle values below are `cycles/event`.

## Why Raw Delta Is The Main Metric

The unified reporting rule for Layer1 data experiments is:

```text
Primary metric: raw paired delta and raw cycles/iteration slope.
Diagnostic view: empty-loop-adjusted absolute direct/pgot values.
```

For this dependent benchmark, the raw values are already linear in event count.
The regression intercept is close to zero, not close to the measured empty-loop
cost:

```text
direct intercept = -0.0149 cycles/iteration
pgot intercept   =  0.0043 cycles/iteration
empty loop       ~= 1.0040 cycles/iteration
```

Therefore the measured empty loop is not an independent additive intercept for
the dependent pointer-chasing sequence. Subtracting it as if it were independent
would introduce an artificial `-empty/event` term into the absolute
`cycles/event` values.

## Empty-Adjusted Diagnostic

The empty-adjusted view is still useful because it shows why subtracting the
empty loop should not be the main cost estimate here:

| event | empty/event | adjusted direct | adjusted pgot | delta |
|---:|---:|---:|---:|---:|
| 1 | 1.004 | 5.017 | 10.034 | 5.017 |
| 2 | 0.502 | 5.519 | 10.536 | 5.017 |
| 4 | 0.251 | 5.770 | 10.787 | 5.017 |
| 6 | 0.167 | 5.854 | 10.882 | 5.028 |
| 8 | 0.126 | 5.895 | 10.921 | 5.025 |
| 10 | 0.100 | 5.924 | 10.944 | 5.020 |
| 12 | 0.084 | 5.941 | 10.959 | 5.019 |
| 14 | 0.072 | 5.952 | 10.971 | 5.018 |
| 16 | 0.063 | 5.962 | 10.980 | 5.018 |
| 18 | 0.056 | 5.968 | 10.987 | 5.018 |

The adjusted `direct` and `pgot` values increase with event count because the
subtracted term is `empty/event`. This is not evidence that the dependent load
itself becomes slower. The raw direct and pgot medians remain essentially flat:

```text
raw direct ~= 6.02 cycles/event
raw pgot   ~= 11.04 cycles/event
raw delta  ~= 5.02 cycles/event
```

So the correct interpretation is:

```text
empty-adjusted absolute values diagnose the non-additivity of the empty-loop
baseline in this dependent chain; they are not the reported primitive cost.
```

## Barriered Diagnostic

The barriered variant is a diagnostic control, not the reported result. Its raw
delta is nearly identical to scheduled:

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6.021 | 11.038 | 5.017 | 0.000 | 5.022 | 15.8% |
| 2 | 6.021 | 11.038 | 5.017 | 0.000 | 5.020 | 30.7% |
| 4 | 6.021 | 11.038 | 5.017 | 0.017 | 5.020 | 1.8% |
| 6 | 6.021 | 11.049 | 5.028 | 0.023 | 5.020 | 0.1% |
| 8 | 6.021 | 11.046 | 5.025 | 0.014 | 5.020 | 0.4% |
| 10 | 6.025 | 11.045 | 5.020 | 0.010 | 5.019 | 0.7% |
| 12 | 6.024 | 11.043 | 5.019 | 0.008 | 5.019 | 0.7% |
| 14 | 6.025 | 11.043 | 5.018 | 0.008 | 5.019 | 0.4% |
| 16 | 6.025 | 11.043 | 5.018 | 0.005 | 5.018 | 1.5% |
| 18 | 6.024 | 11.042 | 5.018 | 0.003 | 5.018 | 2.6% |

Unlike the independent benchmark, inserting barriers does not materially change
the dependent result. This is expected because the pointer-chasing dependency
already serializes the events.

## Static Assembly Evidence

### Source-Level Semantic Check

Simplified event semantics:

```c
volatile u64 *direct_p = &chain_values[idx & MASK];
idx = *direct_p;

u64 * volatile *slot = pgot_chain_table;
volatile u64 *pgot_p = slot[idx & MASK];
idx = *pgot_p;
```

The next `idx` is produced by the current load, so each event is dependent on
the previous event.

### Pgot Slot Load Is Present

`objdump -dr --disassemble=body_pgot_4 bench_kmod.ko` shows the expected
two-load pattern per pgot event:

```asm
and    $0xfff,%eax
mov    0x0(,%rax,8),%rax   # pgot_chain_table slot
mov    (%rax),%rax         # dereference chain value
and    $0xfff,%eax
mov    0x0(,%rax,8),%rax   # next pgot_chain_table slot
mov    (%rax),%rax         # next dereference
```

The direct body uses one chain load per event:

```asm
and    $0xfff,%eax
mov    0x0(,%rax,8),%rax   # chain_values[idx]
```

This validates that the pgot body was not optimized into the direct body.

### No High-Event Stack-Frame Artifact

The following table was extracted from:

```bash
objdump -dr bench_kmod.ko
```

| body | event | bytes | explicit stack frame | table loads | deref loads |
|---|---:|---:|---|---:|---:|
| direct | 1 | 60 | none | 1 | 0 |
| direct | 2 | 73 | none | 2 | 0 |
| direct | 4 | 110 | none | 4 | 0 |
| direct | 6 | 123 | none | 6 | 0 |
| direct | 8 | 158 | none | 8 | 0 |
| direct | 10 | 188 | none | 10 | 0 |
| direct | 12 | 214 | none | 12 | 0 |
| direct | 14 | 235 | none | 14 | 0 |
| direct | 16 | 266 | none | 16 | 0 |
| direct | 18 | 303 | none | 18 | 0 |
| pgot | 1 | 63 | none | 1 | 1 |
| pgot | 2 | 79 | none | 2 | 2 |
| pgot | 4 | 125 | none | 4 | 4 |
| pgot | 6 | 157 | none | 6 | 6 |
| pgot | 8 | 186 | none | 8 | 8 |
| pgot | 10 | 218 | none | 10 | 10 |
| pgot | 12 | 250 | none | 12 | 12 |
| pgot | 14 | 282 | none | 14 | 14 |
| pgot | 16 | 314 | none | 16 | 16 |
| pgot | 18 | 346 | none | 18 | 18 |
| direct_barriered | 16 | 266 | none | 16 | 0 |
| direct_barriered | 18 | 303 | none | 18 | 0 |
| pgot_barriered | 16 | 314 | none | 16 | 16 |
| pgot_barriered | 18 | 341 | none | 18 | 18 |

Evidence implications:

- Direct has one dependent chain load per event.
- Pgot has one slot load plus one dereference load per event.
- No explicit stack frame appears as event count grows.
- Scheduled and barriered high-event bodies are structurally similar.

Therefore the stable `~5.02 cycles/event` delta is not a codegen artifact from
stack-frame growth or spill behavior. It is the visible cost of adding the pgot
slot-load level to the dependent chain.

## Data Quality Notes

- Each `(variant, event)` has `3100` raw samples before filtering.
- The raw mean delta and kept median delta agree closely for all scheduled
  events.
- The low-event drop rate is high because the delta distribution is narrow and
  quantized; this does not change the median or slope conclusion.
- Regression over all scheduled events has `R2 = 1.00000` for direct, pgot, and
  delta, which strongly supports the linear event-cost interpretation.

## Conclusion

The most defensible statement for the paper is:

```text
In the kernel-mode Layer1 dependent pointer-chasing benchmark, data-pgot adds
about 5.02 cycles/event. This value is supported by both paired raw delta and
linear-regression slope over all event counts. Empty-loop-adjusted absolute
direct/pgot values are diagnostic only: the measured empty loop is not an
additive intercept for the dependent chain, so subtracting it creates an
artificial -empty/event trend. Static assembly confirms that pgot performs one
slot load plus one dereference per event and that no high-event stack-frame
artifact explains the result.
```

Do not describe this result as pure architectural load latency. It is the
visible overhead of pgot in a generated dependent pointer-chasing statement
sequence.
