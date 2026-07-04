# Layer1 Func-PGOT Stable Kmod Summary

## Reported Result

This experiment measures stable-target `func-pgot` in kernel mode.

Main source-level comparison:

```text
direct: call target_0(x)
pgot:   f = pgot_func_table[0]; call *f
```

The primary paper result is the real C-generated `direct vs pgot` visible
overhead. The diagnostic results explain why the no-retpoline result is not a
stable additive primitive cost.

### Paper Table: no-retpoline

Use this table when reporting the no-retpoline stable-target result. Values are
`cycles/event`, computed from paired samples after IQR outlier filtering.

| event | raw direct | raw pgot | raw delta | delta IQR | adjusted direct | adjusted pgot | drop rate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3.010 | 4.013 | 1.003 | 0.000 | 2.007 | 3.010 | 40.0% |
| 2 | 4.016 | 4.517 | 0.501 | 0.004 | 3.514 | 4.016 | 17.1% |
| 4 | 4.768 | 3.764 | -1.004 | 0.002 | 4.518 | 3.513 | 1.9% |
| 8 | 4.161 | 4.201 | 0.018 | 0.190 | 4.036 | 4.075 | 4.2% |
| 16 | 4.236 | 4.141 | -0.078 | 0.509 | 4.173 | 4.077 | 7.4% |

Conclusion:

```text
Without retpoline, stable-target func-pgot does not expose a robust additive
per-event primitive cost. The pgot slot load is present, but its visible cost is
mostly hidden or reshaped by the stable indirect-call stream and generated-code
shape.
```

The main no-retpoline result should be reported as an end-to-end visible
overhead table, not as a single fixed cycles/event number.

### Paper Table: retpoline

Use this table when reporting the retpoline result.

| event | raw direct | raw pgot | raw delta | delta IQR | adjusted direct | adjusted pgot | drop rate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3.010 | 42.160 | 39.150 | 0.003 | 2.007 | 41.157 | 19.7% |
| 2 | 4.016 | 42.496 | 38.480 | 0.995 | 3.514 | 41.995 | 1.0% |
| 4 | 4.768 | 43.550 | 38.782 | 0.172 | 4.518 | 43.299 | 1.9% |
| 8 | 4.250 | 45.005 | 40.788 | 0.156 | 4.124 | 44.879 | 0.0% |
| 16 | 4.231 | 45.282 | 41.059 | 0.243 | 4.168 | 45.220 | 0.3% |

Conclusion:

```text
With retpoline enabled, stable-target func-pgot adds about 39-41 cycles/event.
This cost is dominated by the retpoline-protected indirect call, not by the pgot
slot load itself.
```

The retpoline result is the clean positive result for `func-pgot`: replacing a
direct call with a pgot indirect call is expensive when Spectre-v2 retpoline
mitigation is enabled.

## Experiment

This is the kernel-mode Layer1 `func-pgot stable target` experiment.

Measured C semantics:

```c
// direct event
x = target_0(x);

// pgot event
bench_fn_t volatile *slot = pgot_func_table;
bench_fn_t f = slot[0];
x = f(x);
```

The target is stable: every pgot event calls `target_0`. The measured loop runs
inside the kernel module. Module loading, unloading, `dmesg` collection, and CSV
processing are outside the timed loop.

Formal main-run configuration:

```text
iterations=1000000
repeats=31
outer_runs=10
events=1,2,4,8,16
builds=no_retpoline,retpoline
target_pattern=stable
cpu=2
sample_order=interleave
raw_delta=pgot_cycles-direct_cycles
derived_view=empty_adjusted
outlier_filter=per-build,event IQR rule: [Q1-1.5*IQR, Q3+1.5*IQR]
```

Raw sample count:

```text
2 builds * 5 event counts * 31 repeats * 10 outer runs
= 3100 paired samples
```

Result files:

```text
raw.csv               raw empty/direct/cached/slot_direct/pgot paired samples
processed.csv         full processed statistics
paper_main.csv        primary direct-vs-pgot paper table
paper_diagnostics.csv C mechanism-split diagnostic table
metadata.txt          environment and run configuration
```

All reported values in this summary are `cycles/event`.

## Metric Interpretation

The main table reports both raw and empty-loop-adjusted values.

Empty adjustment is:

```text
direct_adjusted = direct - empty
pgot_adjusted   = pgot   - empty
```

The delta is unchanged by empty adjustment:

```text
adjusted_delta = (pgot - empty) - (direct - empty)
               = pgot - direct
```

Therefore, the adjusted columns are used to show absolute direct/pgot costs
after removing the empty-loop baseline. They do not change the reported
direct-vs-pgot delta.

## Main Observations

### no-retpoline

The no-retpoline direct-vs-pgot deltas are:

```text
event=1:  +1.003 cycles/event
event=2:  +0.501 cycles/event
event=4:  -1.004 cycles/event
event=8:  +0.018 cycles/event
event=16: -0.078 cycles/event
```

This is not a monotonic cost curve. It should not be summarized as a fixed
primitive cost such as "func-pgot costs X cycles/event" in the no-retpoline
case.

The key point is not that the measurement is simply noisy. Some groups are very
stable internally, but different event counts produce different generated-code
shapes and different direct-call vs stable-indirect-call behavior. This means
the result is not described by a simple additive model:

```text
direct call + fixed pgot slot-load cost
```

### retpoline

The retpoline deltas are:

```text
event=1:  39.150 cycles/event
event=2:  38.480 cycles/event
event=4:  38.782 cycles/event
event=8:  40.788 cycles/event
event=16: 41.059 cycles/event
```

This is the robust positive result. Retpoline turns the indirect call into a
thunk sequence, and that thunk dominates the cost.

## C Mechanism-Split Diagnostic

The C benchmark also records mechanism-split paths:

```text
direct          direct call target_0
cached_indirect load function pointer once before the loop, then call *f
slot_direct     per-event pgot slot load, then direct call target_0
pgot            per-event pgot slot load, then call *f
```

no-retpoline C diagnostic result:

| event | direct | cached indirect | slot direct | pgot | cached-direct | slot-direct | pgot-cached | pgot-direct |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3.010 | 4.019 | 3.010 | 4.013 | 1.009 | 0.000 | -0.006 | 1.003 |
| 2 | 4.016 | 4.517 | 4.542 | 4.517 | 0.500 | 0.527 | 0.001 | 0.501 |
| 4 | 4.768 | 4.768 | 3.639 | 3.764 | -0.000 | -1.129 | -1.004 | -1.004 |
| 8 | 4.161 | 4.087 | 4.192 | 4.201 | -0.100 | 0.000 | 0.125 | 0.018 |
| 16 | 4.236 | 5.985 | 4.344 | 4.141 | 1.735 | 0.129 | -1.421 | -0.078 |

Evidence from this table:

- At `event=1/2`, `pgot-direct` is almost entirely explained by
  `cached-direct`. That means the visible difference is mostly the direct-call
  vs stable-indirect-call path, not the pgot slot load.
- At `event=4`, `slot-direct` is also much faster than direct
  (`-1.129 cycles/event`). Since `slot-direct` still uses direct calls, the
  `event=4` negative result cannot be explained as "indirect call is faster".
  It is a generated-code/layout artifact in this C loop shape.
- The C mechanism split is useful diagnostic evidence, but it is still affected
  by compiler scheduling and layout. The asm matched diagnostic below is the
  stronger evidence for isolating the pgot slot load.

## Static C Code-Generation Evidence

The no-retpoline C code was validated with `objdump`. The pgot body contains
one slot load and one indirect call per event.

Example `body_pgot_4` structure:

```asm
mov pgot_func_table(%rip), %rax
call *%rax
mov %rax, %rdi
mov pgot_func_table(%rip), %rax
call *%rax
mov %rax, %rdi
...
```

The generated hot-loop structure is not layout-equivalent between direct and
pgot:

| kind | event | loop bytes | 64B blocks | insns | slot loads | direct calls | indirect calls | loop start mod64 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 1 | 17 | 1 | 5 | 0 | 1 | 0 | 27 |
| pgot | 1 | 21 | 1 | 6 | 1 | 0 | 1 | 27 |
| direct | 2 | 25 | 1 | 7 | 0 | 2 | 0 | 28 |
| pgot | 2 | 33 | 1 | 9 | 2 | 0 | 2 | 28 |
| direct | 4 | 41 | 2 | 11 | 0 | 4 | 0 | 28 |
| pgot | 4 | 57 | 2 | 15 | 4 | 0 | 4 | 28 |
| direct | 8 | 73 | 2 | 19 | 0 | 8 | 0 | 28 |
| pgot | 8 | 105 | 3 | 27 | 8 | 0 | 8 | 28 |
| direct | 16 | 141 | 3 | 35 | 0 | 16 | 0 | 32 |
| pgot | 16 | 205 | 4 | 51 | 16 | 0 | 16 | 32 |

Interpretation:

- The pgot slot load is present for every event.
- The direct and pgot loops differ in byte length, instruction count, call type,
  and number of 64B fetch blocks.
- Therefore the C main result is a real visible end-to-end overhead
  measurement, but it is not a pure isolated slot-load latency measurement.

## Layout-Order Diagnostic

We also changed the function definition order with `BENCH_PGOT_FIRST=1`. This
changes the placement of direct/pgot functions in `.text` without changing the
event bodies.

| event | baseline delta | pgot-first delta |
|---:|---:|---:|
| 1 | 1.003 | 1.003 |
| 2 | 0.501 | 0.501 |
| 4 | -1.004 | -1.004 |
| 8 | 0.018 | 0.001 |
| 16 | -0.078 | -0.125 |

This shows that the `event=4` negative result is not caused merely by whether
the pgot functions appear before or after the direct functions. The more
important factor is the internal hot-loop shape of the generated event body.

## LFENCE Diagnostic

The `lfence_split` diagnostic inserts fences around events. It is not the main
paper result because it changes the execution semantics, but it helps show that
the slot/call sequence can be made visible when scheduling and overlap are
blocked.

| event | direct | pgot | delta | delta IQR |
|---:|---:|---:|---:|---:|
| 1 | 38.142 | 40.301 | 2.253 | 0.580 |
| 2 | 33.033 | 38.875 | 5.841 | 0.052 |
| 4 | 31.081 | 38.998 | 7.911 | 0.088 |
| 8 | 29.815 | 38.742 | 8.928 | 0.033 |
| 16 | 29.174 | 38.610 | 9.441 | 0.066 |

Interpretation:

With fences, the normal overlap and scheduling opportunities are intentionally
removed. The visible pgot-vs-direct delta becomes much larger. This supports the
claim that, in the normal no-retpoline scheduled code, much of the pgot slot
load and stable indirect-call work is hidden or reshaped by the surrounding
instruction stream.

## Matched-Layout ASM Diagnostic

The strongest diagnostic control is the matched-layout hand-written asm
experiment:

```text
direct: call target_0; 5-byte nop; mov %rax,%rdi
cached: 7-byte nop; call *%r13; mov %rax,%rdi
pgot:   mov pgot_func_table(%rip),%r11; call *%r11; mov %rax,%rdi
```

The goal is to control layout. This diagnostic is no-retpoline only: handwritten
`call *%reg` is not transformed by GCC into a retpoline thunk.

Matched-layout validation from `objdump_summary.csv`:

Diagnostic result files:

```text
../kmod_diag_asm_matched/raw.csv
../kmod_diag_asm_matched/paper_main.csv
../kmod_diag_asm_matched/objdump_summary.csv
../kmod_diag_asm_matched/objdump.txt
```

| kind | event | loop bytes | 64B blocks | insns | slot loads | direct calls | indirect calls | loop start mod64 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| empty | 1 | 22 | 1 | 6 | 0 | 0 | 0 | 0 |
| direct | 1 | 22 | 1 | 6 | 0 | 1 | 0 | 0 |
| cached | 1 | 22 | 1 | 6 | 0 | 0 | 1 | 0 |
| pgot | 1 | 22 | 1 | 6 | 1 | 0 | 1 | 0 |
| empty | 2 | 35 | 1 | 9 | 0 | 0 | 0 | 0 |
| direct | 2 | 35 | 1 | 9 | 0 | 2 | 0 | 0 |
| cached | 2 | 35 | 1 | 9 | 0 | 0 | 2 | 0 |
| pgot | 2 | 35 | 1 | 9 | 2 | 0 | 2 | 0 |
| empty | 4 | 61 | 1 | 15 | 0 | 0 | 0 | 0 |
| direct | 4 | 61 | 1 | 15 | 0 | 4 | 0 | 0 |
| cached | 4 | 61 | 1 | 15 | 0 | 0 | 4 | 0 |
| pgot | 4 | 61 | 1 | 15 | 4 | 0 | 4 | 0 |
| empty | 8 | 113 | 2 | 27 | 0 | 0 | 0 | 0 |
| direct | 8 | 113 | 2 | 27 | 0 | 8 | 0 | 0 |
| cached | 8 | 113 | 2 | 27 | 0 | 0 | 8 | 0 |
| pgot | 8 | 113 | 2 | 27 | 8 | 0 | 8 | 0 |
| empty | 16 | 221 | 4 | 51 | 0 | 0 | 0 | 0 |
| direct | 16 | 221 | 4 | 51 | 0 | 16 | 0 | 0 |
| cached | 16 | 221 | 4 | 51 | 0 | 0 | 16 | 0 |
| pgot | 16 | 221 | 4 | 51 | 16 | 0 | 16 | 0 |

Matched-layout asm result:

| event | direct | cached indirect | pgot | cached-direct | pgot-cached | pgot-direct | IQR pgot-cached |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3.010 | 4.013 | 4.013 | 1.003 | 0.000 | 1.003 | 0.014 |
| 2 | 4.240 | 3.514 | 3.514 | -0.728 | -0.001 | -0.726 | 0.004 |
| 4 | 4.266 | 4.266 | 4.266 | 0.000 | -0.000 | -0.001 | 0.002 |
| 8 | 4.500 | 4.258 | 4.166 | -0.251 | -0.063 | -0.305 | 0.147 |
| 16 | 4.426 | 4.144 | 4.174 | -0.275 | 0.027 | -0.245 | 0.126 |

Evidence from the asm diagnostic:

- `pgot-cached` isolates the per-event slot load inside a stable indirect-call
  stream.
- `pgot-cached` is approximately zero for `event=1,2,4`, and remains small at
  `event=8,16` (`-0.063` and `+0.027 cycles/event`).
- Therefore the per-event pgot slot load is not the main visible cost in the
  no-retpoline stable-target function-call stream.
- The remaining non-monotonic behavior is already present in
  `cached-direct`, so it belongs to direct-call vs stable-indirect-call control
  flow behavior and short loop/front-end effects, not to the pgot slot load
  alone.

This diagnostic also explains the C `event=4` anomaly. In the C main result:

```text
event=4 pgot-direct = -1.004 cycles/event
```

In the matched-layout asm result:

```text
event=4 pgot-direct = -0.001 cycles/event
```

Thus the large negative C result at `event=4` is a generated-code/layout
artifact, not a real "pgot is faster" rule.

## Target-Empty Diagnostic

We also tested whether the target function body itself caused the no-retpoline
non-monotonic result. The diagnostic target keeps a real call/return boundary
but removes the arithmetic body:

```c
static noinline noipa u64 target_0(u64 x)
{
    asm volatile("" : "+r"(x) :: "memory");
    return x;
}
```

Static validation shows that the target is effectively empty but not optimized
away:

```asm
<target_0>:
  mov %rdi,%rax
  ret
```

The pgot path still contains one slot load and one indirect call per event:

```asm
mov pgot_func_table(%rip),%rax
call *%rax
```

Diagnostic result files:

```text
../kmod_diag_target_empty/raw.csv
../kmod_diag_target_empty/paper_main.csv
../kmod_diag_target_empty/paper_diagnostics.csv
../kmod_diag_target_empty/objdump_validation.txt
```

Target-empty main result:

| build | event | raw direct | raw pgot | raw delta | delta IQR | adjusted direct | adjusted pgot | drop rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | 1 | 3.010 | 4.013 | 1.003 | 0.000 | 2.007 | 3.010 | 35.5% |
| no_retpoline | 2 | 4.016 | 4.517 | 0.501 | 0.004 | 3.514 | 4.016 | 15.8% |
| no_retpoline | 4 | 4.768 | 3.764 | -1.004 | 0.002 | 4.518 | 3.513 | 4.5% |
| no_retpoline | 8 | 4.155 | 4.196 | 0.005 | 0.167 | 4.029 | 4.070 | 0.0% |
| no_retpoline | 16 | 4.232 | 4.142 | -0.042 | 0.559 | 4.169 | 4.079 | 6.1% |
| retpoline | 1 | 3.010 | 42.160 | 39.149 | 0.007 | 2.007 | 41.157 | 21.6% |
| retpoline | 2 | 4.016 | 42.501 | 38.486 | 0.892 | 3.514 | 41.999 | 1.3% |
| retpoline | 4 | 4.768 | 43.565 | 38.797 | 0.169 | 4.518 | 43.315 | 0.6% |
| retpoline | 8 | 4.255 | 45.001 | 40.781 | 0.134 | 4.129 | 44.875 | 0.3% |
| retpoline | 16 | 4.224 | 45.422 | 41.190 | 0.283 | 4.161 | 45.359 | 1.9% |

Comparison with the original target body:

| build | event | original delta | empty-target delta | difference |
|---|---:|---:|---:|---:|
| no_retpoline | 1 | 1.003 | 1.003 | 0.000 |
| no_retpoline | 2 | 0.501 | 0.501 | 0.000 |
| no_retpoline | 4 | -1.004 | -1.004 | 0.000 |
| no_retpoline | 8 | 0.018 | 0.005 | -0.013 |
| no_retpoline | 16 | -0.078 | -0.042 | 0.036 |
| retpoline | 1 | 39.150 | 39.149 | -0.001 |
| retpoline | 2 | 38.480 | 38.486 | 0.006 |
| retpoline | 4 | 38.782 | 38.797 | 0.016 |
| retpoline | 8 | 40.788 | 40.781 | -0.007 |
| retpoline | 16 | 41.059 | 41.190 | 0.132 |

The target-empty result is almost identical to the original result. Therefore,
the no-retpoline non-monotonicity is not caused by the arithmetic inside
`target_0`. It is caused by the call-stream/code-shape factors already isolated
above: direct call versus stable indirect call behavior, pgot slot-load
absorption, and generated hot-loop layout.

## Retpoline Static Evidence

The retpoline build uses:

```text
-mindirect-branch=thunk-inline
-mindirect-branch-register
-mfunction-return=keep
-fcf-protection=none
```

`objdump` of `body_pgot_1` shows the inline retpoline thunk:

```asm
mov    pgot_func_table(%rip),%rax
jmp    <thunk_entry>
call   <capture_return>
pause
lfence
jmp    <pause_loop>
mov    %rax,(%rsp)
ret
call   <thunk>
```

This validates that the retpoline result measures a retpoline-protected indirect
call path. The large `39-41 cycles/event` overhead is therefore expected and is
not caused by the pgot slot load alone.

## Final Interpretation

### What We Can Claim

1. In the real C-generated no-retpoline benchmark, stable-target func-pgot has
   low visible overhead but no stable additive per-event primitive cost.
2. The pgot slot load is present in the generated code.
3. Matched-layout asm shows that the per-event slot load over a cached stable
   indirect call is nearly zero in this benchmark shape.
4. The no-retpoline direct-vs-pgot non-monotonicity is primarily explained by
   generated-code shape and direct-call vs stable-indirect-call control-flow
   behavior.
5. With retpoline enabled, func-pgot has a robust `39-41 cycles/event` overhead,
   dominated by the retpoline indirect-call thunk.

### What We Should Not Claim

Do not claim:

```text
no-retpoline stable func-pgot has a fixed X cycles/event primitive cost
```

Do claim:

```text
For stable-target func-pgot without retpoline, the pgot slot load is present but
is not exposed as a robust additive primitive cost. Matched-layout diagnostics
show that the per-event slot load is mostly absorbed in the stable indirect-call
stream, while the remaining direct-vs-pgot variation is dominated by code shape
and direct-call vs stable-indirect-call control-flow behavior.
```

For retpoline, do claim:

```text
With retpoline, func-pgot adds about 39-41 cycles/event because the indirect call
is compiled into a retpoline thunk.
```
