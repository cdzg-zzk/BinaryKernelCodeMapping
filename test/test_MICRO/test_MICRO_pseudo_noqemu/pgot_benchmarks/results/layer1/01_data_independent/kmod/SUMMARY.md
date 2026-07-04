# Layer1 Data-Independent Kmod Summary

## Reported Result

Use the raw scheduled paired delta in the stable region `event=4..10` as the
primary result.

```text
For independent statement-level data access in this kernel-mode Layer1
microbenchmark, data-pgot adds about 0.50 cycles/event in the normal scheduled
sequence.
```

The stable raw scheduled region is:

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.502 | 1.004 | 0.501 | 0.002 | 0.503 | 2.7% |
| 6 | 0.502 | 1.004 | 0.502 | 0.002 | 0.502 | 2.0% |
| 8 | 0.502 | 1.004 | 0.502 | 0.001 | 0.504 | 2.5% |
| 10 | 0.502 | 1.004 | 0.502 | 0.001 | 0.503 | 3.0% |

Linear regression on raw scheduled `cycles/iteration` over `event=4..10`
supports the same conclusion:

| range | metric | intercept | slope cycles/event | R2 |
|---|---|---:|---:|---:|
| 4..10 | direct | 0.0001 | 0.5017 | 1.00000 |
| 4..10 | pgot | -0.0018 | 1.0044 | 1.00000 |
| 4..10 | delta | -0.0052 | 0.5026 | 1.00000 |

This is the result to report. The other event ranges are used as evidence for
why the stable region is selected:

| event range | role in interpretation |
|---|---|
| `event=1..2` | low-event region affected by fixed loop/timing floor and short-sequence effects |
| `event=4..10` | primary stable scheduled region |
| `event>=12` | affected by register pressure and explicit stack-frame allocation |
| `event=18` | generated-code/scheduling artifact, not a bottom-level hardware rule |

The empty-loop-adjusted and barriered variants are diagnostic views. They
explain the low-event and high-event behavior, but they are not the primary
cost estimate.

## Experiment

This is the kernel-mode Layer1 data-pgot independent experiment.

Measured statement semantics:

```text
direct: acc += direct_values[idx]
pgot:   p = pgot_data_table[idx]; acc += *p
```

The timed loop runs inside the kernel module. Module loading, module unloading,
`dmesg` collection, and CSV processing are outside the measured loop.

Formal run configuration:

```text
iterations=1000000
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

Result files:

```text
raw.csv          raw empty/direct/pgot paired samples
processed.csv    full processed statistics
paper_table.csv  compact reporting table
metadata.txt     environment and run configuration
```

All reported cycle values below are `cycles/event`.

## Detailed Results And Evidence

### Scheduled

This is the main measurement because it keeps the compiler's normal scheduled
statement sequence.

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.241 | 1.341 | 0.100 | 0.000 | 0.100 | 45.6% |
| 2 | 0.669 | 1.003 | 0.334 | 0.001 | 0.335 | 33.3% |
| 4 | 0.502 | 1.004 | 0.501 | 0.002 | 0.503 | 2.7% |
| 6 | 0.502 | 1.004 | 0.502 | 0.002 | 0.502 | 2.0% |
| 8 | 0.502 | 1.004 | 0.502 | 0.001 | 0.504 | 2.5% |
| 10 | 0.502 | 1.004 | 0.502 | 0.001 | 0.503 | 3.0% |
| 12 | 0.544 | 1.087 | 0.543 | 0.001 | 0.544 | 3.6% |
| 14 | 0.610 | 1.306 | 0.696 | 0.001 | 0.695 | 3.3% |
| 16 | 0.659 | 1.370 | 0.711 | 0.000 | 0.711 | 3.6% |
| 18 | 0.713 | 1.321 | 0.612 | 0.016 | 0.613 | 0.0% |

Observed behavior:

- `event=4..10` is stable at about `0.50 cycles/event`.
- `event=12..16` increases to `0.54..0.71 cycles/event`.
- `event=18` falls back to `0.61 cycles/event`.

We use `event=4..10` as the primary stable region for estimating visible
data-pgot overhead:

| event range | role in interpretation |
|---|---|
| `event=1..2` | affected by fixed loop overhead and short-sequence pipeline/throughput amortization |
| `event=4..10` | primary stable scheduled region |
| `event>=12` | affected by register pressure and explicit stack-frame allocation |
| `event=18` | generated-code/scheduling artifact, not a bottom-level hardware rule |

Interpretation:

The scheduled result measures visible cost in a generated statement sequence,
not an isolated hardware load latency. The stable `event=4..10` region is the
cleanest evidence for the visible pgot slot-load cost in this benchmark shape.
The higher-event changes are tied to generated-code changes, especially
increased register pressure and stack-frame use shown by static assembly
evidence below. The `event=18` drop is therefore not a bottom-level hardware
rule; it is a generated-code/scheduling artifact.

### Scheduled Empty Adjusted

This derived view subtracts the empty-loop baseline from direct and pgot:

```text
direct_adjusted = direct - empty
pgot_adjusted   = pgot   - empty
delta           = pgot   - direct
```

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.238 | 0.338 | 0.100 | 0.000 | 0.100 | 45.6% |
| 2 | 0.168 | 0.501 | 0.334 | 0.001 | 0.335 | 33.3% |
| 4 | 0.251 | 0.752 | 0.501 | 0.002 | 0.503 | 2.7% |
| 6 | 0.335 | 0.837 | 0.502 | 0.002 | 0.502 | 2.0% |
| 8 | 0.376 | 0.879 | 0.502 | 0.001 | 0.504 | 2.5% |
| 10 | 0.401 | 0.904 | 0.502 | 0.001 | 0.503 | 3.0% |
| 12 | 0.460 | 1.004 | 0.543 | 0.001 | 0.544 | 3.6% |
| 14 | 0.538 | 1.234 | 0.696 | 0.001 | 0.695 | 3.3% |
| 16 | 0.596 | 1.308 | 0.711 | 0.000 | 0.711 | 3.6% |
| 18 | 0.657 | 1.265 | 0.612 | 0.016 | 0.613 | 0.0% |

Observed behavior:

- `event=1` direct drops from `1.241` to `0.238 cycles/event`, so the empty
  baseline removes the fixed loop/timing overhead that dominates low-event
  cases.
- `event=2` adjusted direct is lower than `event=1` because fixed costs are
  better amortized and two independent direct loads can overlap more effectively.
- Low-event points are affected not only by fixed loop overhead, but also by
  short-sequence pipeline-fill and throughput-amortization effects. This is why
  `event=2` can remain lower than `event=1` even after empty-loop adjustment.
- For `event>2`, adjusted direct gradually increases. This shows that the
  remaining cost still includes the generated statement sequence, the `acc`
  reduction chain, frontend/code-size effects, and register pressure. It is not
  a pure single-load primitive latency.

Interpretation:

`scheduled_empty_adjusted` is useful for explaining the empty-loop issue, but it
should not be used to claim a bottom-level direct-load cost. Its main role is to
show that the pgot-vs-direct delta is unchanged by empty-loop subtraction while
the absolute direct/pgot per-event values at low event counts are strongly
affected by fixed loop overhead.

### Barriered

This diagnostic variant inserts a compiler barrier after every event. It is a
diagnostic control, not the reported primitive-cost result, because the inserted
barriers change the statement scheduling semantics.

| event | direct med | pgot med | delta med | delta IQR | raw mean delta | drop rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.241 | 1.341 | 0.100 | 0.001 | 0.101 | 24.3% |
| 2 | 1.003 | 1.004 | 0.000 | 0.000 | 0.001 | 36.5% |
| 4 | 1.003 | 1.003 | 0.000 | 0.002 | 0.001 | 0.8% |
| 6 | 1.004 | 1.004 | 0.000 | 0.002 | 0.002 | 1.5% |
| 8 | 1.004 | 1.004 | 0.000 | 0.000 | 0.002 | 1.9% |
| 10 | 1.004 | 1.004 | 0.000 | 0.000 | 0.003 | 3.5% |
| 12 | 1.004 | 1.004 | 0.000 | 0.000 | 0.003 | 6.0% |
| 14 | 1.004 | 1.004 | 0.000 | 0.000 | 0.003 | 6.6% |
| 16 | 1.004 | 1.004 | 0.000 | 0.000 | 0.003 | 3.3% |
| 18 | 1.004 | 1.004 | 0.000 | 0.000 | 0.004 | 3.0% |

Observed behavior:

- For `event>=2`, direct and pgot both sit around `1.0 cycles/event`.
- The measured delta is essentially zero after filtering, and the raw mean
  delta is only about `0.001..0.004 cycles/event`.

Interpretation:

The barrier changes the benchmark semantics. It prevents the compiler from
building a wide scheduled load/add sequence and forces an event-by-event shape.
The result is dominated by the barriered `acc` dependency/template, so direct
and pgot become nearly identical. This is evidence that the scheduled variant's
non-monotonic behavior is strongly affected by code generation and scheduling.
It is not evidence that pgot has no slot-load cost in the normal scheduled
sequence. Therefore, `barriered` should be cited as diagnostic evidence only,
while the normal scheduled result should be used for the reported visible
overhead.

## Static Assembly Evidence

### Source-Level Semantic Check

The source macros force the intended comparison. Simplified event semantics:

```c
volatile u64 *direct_p = &direct_values[idx];
acc += *direct_p;

u64 * volatile *slot = pgot_data_table;
volatile u64 *pgot_p = slot[idx];
acc += *pgot_p;
```

The `volatile` qualifiers prevent the direct data load and the pgot table load
from being optimized away or folded into a constant.

### Pgot Slot Load Is Present

`objdump -dr --disassemble=body_pgot_4 bench_kmod.ko` shows the expected
two-load pattern per pgot event:

```asm
mov    0x0(%rip),%rdx     # pgot_data_table slot
mov    (%rdx),%rdx        # dereference data pointer
mov    0x0(%rip),%rsi     # next pgot_data_table slot
mov    (%rsi),%r8         # dereference data pointer
```

The matching direct body uses only direct data loads from `direct_values`:

```asm
mov    0x0(%rip),%rdx
mov    0x0(%rip),%r9
mov    0x0(%rip),%r8
mov    0x0(%rip),%rsi
```

This validates that the pgot body was not optimized into the direct body.

### Generated-Code Shape Changes With Event Count

The following table was extracted from:

```bash
objdump -dr bench_kmod.ko
```

It records function size, number of `push/pop` instructions, and explicit stack
frame allocation (`sub ..., %rsp`).

| body | event | bytes | push/pop | stack frame |
|---|---:|---:|---:|---|
| direct | 1 | 62 | 1/1 | none |
| direct | 2 | 61 | 1/1 | none |
| direct | 4 | 92 | 1/1 | none |
| direct | 6 | 104 | 1/1 | none |
| direct | 8 | 138 | 3/3 | none |
| direct | 10 | 173 | 5/5 | none |
| direct | 12 | 200 | 6/6 | `sub $0x8,%rsp` |
| direct | 14 | 233 | 6/6 | `sub $0x18,%rsp` |
| direct | 16 | 264 | 6/6 | `sub $0x28,%rsp` |
| direct | 18 | 293 | 6/6 | `sub $0x38,%rsp` |
| pgot | 1 | 54 | 1/1 | none |
| pgot | 2 | 78 | 1/1 | none |
| pgot | 4 | 91 | 1/1 | none |
| pgot | 6 | 125 | 1/1 | none |
| pgot | 8 | 166 | 3/3 | none |
| pgot | 10 | 207 | 5/5 | none |
| pgot | 12 | 239 | 6/6 | `sub $0x8,%rsp` |
| pgot | 14 | 286 | 6/6 | `sub $0x18,%rsp` |
| pgot | 16 | 311 | 6/6 | `sub $0x28,%rsp` |
| pgot | 18 | 347 | 6/6 | `sub $0x38,%rsp` |
| direct_barriered | 16 | 223 | 1/1 | none |
| pgot_barriered | 16 | 271 | 1/1 | none |
| direct_barriered | 18 | 232 | 1/1 | none |
| pgot_barriered | 18 | 281 | 1/1 | none |

Evidence implications:

- Scheduled direct/pgot start using more saved registers at `event=8` and
  `event=10`.
- Scheduled direct/pgot start allocating explicit stack frames from `event=12`.
- Stack frame size grows with event count from `event=12` to `event=18`.
- Barriered bodies avoid this high-event stack-frame pattern; even at
  `event=16/18`, they keep only one `push/pop` pair and no explicit stack frame.

This explains why scheduled high-event results are not a clean monotonic
primitive-cost curve. They include compiler register allocation and generated
code shape, not only the pgot data-table slot load.

## Data Quality Notes

- Each `(variant, event)` has `3100` raw samples before filtering.
- The raw mean delta and kept median delta agree closely for all scheduled
  events, so the conclusions are not created by outlier filtering.
- The drop rate is high for low-event cases because the measured delta is very
  small and quantized. For example, scheduled `event=1` has median delta
  `0.100 cycles/event` with IQR `0.000`; the IQR rule is therefore very strict.
- For the main stable region (`event=4..10`), drop rate is low, around
  `2.0%..3.0%`.

## Conclusion

The most defensible statement for the paper is:

```text
For independent statement-level data access in this kernel-mode microbenchmark,
data-pgot adds about 0.50 cycles/event in the normal scheduled sequence for
event=4..10. We use this range as the primary stable region: lower event counts
are affected by fixed loop overhead and short-sequence pipeline-fill effects,
while higher event counts include generated-code changes such as increased
register pressure and explicit stack-frame allocation. The empty-loop-adjusted
view explains low-event amortization, and the barriered diagnostic confirms
that compiler scheduling and live-range shape significantly affect non-monotonic
behavior. This kernel-mode result confirms that the data-pgot slot-load overhead
remains small in the normal scheduled sequence.
```

Do not describe this result as a pure architectural load-latency measurement.
It is a statement-sequence visible-overhead measurement with static assembly
evidence for the generated-code effects.
