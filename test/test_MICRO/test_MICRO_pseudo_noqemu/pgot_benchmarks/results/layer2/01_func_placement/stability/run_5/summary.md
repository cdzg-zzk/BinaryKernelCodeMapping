# Layer2 Func-PGOT Unfenced Placement/Workload Experiment

## 1. Experiment Goal

This kernel-module experiment measures the visible overhead of stable-target
`func-pgot` in an unfenced practical instruction stream.

It compares:

```c
// direct
x = target_work_N(x);

// pgot
bench_fn_t volatile *slot = pgot_func_table;
bench_fn_t f = slot[idx];
x = f(x);
```

The experiment now includes four workload contexts:

| placement | measured body |
|---|---|
| `work_only` | `WORK_N` only, no target call |
| `before` | `WORK_N; CALL(target_work_0)` |
| `inside` | `CALL(target_work_N)` |
| `after` | `CALL(target_work_0); WORK_N` |

`none/workload=0` is kept as the call-only baseline.

## 2. Experimental Setup

| item | value |
|---|---|
| execution mode | kernel module |
| function events | 1 call event / iteration |
| target pattern | stable target |
| fence mode | unfenced |
| builds | no-retpoline, retpoline |
| sample order | paired/interleave |
| iterations | 100000 |
| repeats | 15 |
| outer runs | 3 |
| raw samples / case | 45 |
| workload grid | 0,1,2,3,4,5,6,8,16,32,64 |
| placements | none,work_only,before,inside,after |
| CPU | pinned CPU 2 |

The reported delta is paired:

```text
delta[r] = pgot_cycles[r] - direct_cycles[r]
reported_delta = median(delta[r])
```

For `work_only`, both measured sides run the same no-call body. Its `direct`
cycle column is used as the workload-only baseline; its delta should stay near
measurement noise.

## 3. Key Code

```c
#define CALL_DIRECT(work) do { \
    x = target_work_##work(x); \
} while (0)

#define CALL_PGOT(idx) do { \
    bench_fn_t volatile *slot__ = pgot_func_table; \
    bench_fn_t f__ = slot__[idx]; \
    x = f__(x); \
} while (0)
```

`slot__ = pgot_func_table` only forms the table base. The actual pgot memory
operation is the slot load `f__ = slot__[idx]`.

## 4. Dynamic Results

### 4.1 Work-Only Baseline

The retpoline build's `work_only` body has no target call and no pgot call. It
shows how large the ordinary work stream is at each workload.

| workload | work_only cycles | IQR(delta same-body) |
|---:|---:|---:|
| 0 | 1.004 | 0.000 |
| 1 | 11.115 | 0.002 |
| 2 | 22.144 | 0.003 |
| 3 | 33.119 | 0.117 |
| 4 | 44.163 | 0.133 |
| 5 | 55.213 | 0.139 |
| 6 | 66.441 | 0.134 |
| 8 | 88.399 | 0.081 |
| 16 | 176.738 | 0.095 |
| 32 | 353.422 | 0.046 |
| 64 | 706.798 | 0.067 |

The retpoline call-only baseline is:

```text
none/workload=0 delta = 39.135 cycles/iteration
```

The first workload where all three retpoline placements have |delta| <= 1 cycle
in this run is:

```text
workload = 6
```

### 4.2 no-retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.002 | 0.00 |
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.005 | 0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.128 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | -0.001 | 0.135 | -0.00 |
| work_only | 5 | 55.273 | 55.215 | -0.062 | 0.138 | -0.11 |
| work_only | 6 | 66.422 | 66.442 | 0.034 | 0.135 | 0.05 |
| work_only | 8 | 88.401 | 88.398 | -0.009 | 0.064 | -0.01 |
| work_only | 16 | 176.739 | 176.729 | -0.008 | 0.089 | -0.00 |
| work_only | 32 | 353.439 | 353.437 | -0.006 | 0.067 | -0.00 |
| work_only | 64 | 706.804 | 706.810 | 0.005 | 0.070 | 0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.094 | 12.102 | 0.033 | 0.041 | 0.27 |
| before | 2 | 23.290 | 23.170 | -0.122 | 0.159 | -0.52 |
| before | 3 | 34.231 | 34.302 | 0.071 | 0.134 | 0.21 |
| before | 4 | 45.371 | 45.309 | -0.061 | 0.137 | -0.13 |
| before | 5 | 56.447 | 56.567 | 0.123 | 0.141 | 0.22 |
| before | 6 | 67.461 | 67.521 | 0.041 | 0.247 | 0.06 |
| before | 8 | 89.511 | 89.529 | 0.007 | 0.073 | 0.01 |
| before | 16 | 177.939 | 177.887 | -0.068 | 0.267 | -0.04 |
| before | 32 | 354.663 | 354.661 | -0.026 | 0.186 | -0.01 |
| before | 64 | 707.942 | 708.025 | 0.088 | 0.072 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| inside | 1 | 12.069 | 12.057 | -0.013 | 0.002 | -0.11 |
| inside | 2 | 23.130 | 23.137 | 0.007 | 0.005 | 0.03 |
| inside | 3 | 34.223 | 34.178 | -0.045 | 0.130 | -0.13 |
| inside | 4 | 45.295 | 45.264 | -0.033 | 0.156 | -0.07 |
| inside | 5 | 56.318 | 56.361 | -0.018 | 0.066 | -0.03 |
| inside | 6 | 67.404 | 67.360 | -0.040 | 0.137 | -0.06 |
| inside | 8 | 89.449 | 89.536 | 0.074 | 0.092 | 0.08 |
| inside | 16 | 177.753 | 177.820 | 0.069 | 0.101 | 0.04 |
| inside | 32 | 354.463 | 354.497 | 0.040 | 0.076 | 0.01 |
| inside | 64 | 707.848 | 707.891 | 0.039 | 0.058 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| after | 1 | 12.121 | 12.101 | -0.017 | 0.082 | -0.14 |
| after | 2 | 24.083 | 24.108 | 0.025 | 0.007 | 0.10 |
| after | 3 | 34.231 | 34.232 | 0.001 | 0.136 | 0.00 |
| after | 4 | 46.309 | 46.251 | -0.058 | 0.137 | -0.13 |
| after | 5 | 56.385 | 56.370 | -0.010 | 0.142 | -0.02 |
| after | 6 | 68.481 | 68.389 | -0.085 | 0.133 | -0.12 |
| after | 8 | 90.433 | 90.478 | 0.063 | 0.112 | 0.07 |
| after | 16 | 178.889 | 178.762 | -0.133 | 0.058 | -0.07 |
| after | 32 | 355.699 | 355.486 | -0.203 | 0.082 | -0.06 |
| after | 64 | 708.966 | 708.883 | -0.070 | 0.063 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 42.146 | 39.135 | 0.070 | 1299.73 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.002 | 0.00 |
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.003 | 0.00 |
| work_only | 3 | 33.119 | 33.119 | 0.000 | 0.117 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.001 | 0.133 | 0.00 |
| work_only | 5 | 55.213 | 55.212 | 0.000 | 0.139 | 0.00 |
| work_only | 6 | 66.441 | 66.432 | -0.023 | 0.134 | -0.03 |
| work_only | 8 | 88.399 | 88.393 | -0.011 | 0.081 | -0.01 |
| work_only | 16 | 176.738 | 176.734 | -0.009 | 0.095 | -0.01 |
| work_only | 32 | 353.422 | 353.426 | 0.005 | 0.046 | 0.00 |
| work_only | 64 | 706.798 | 706.800 | 0.006 | 0.067 | 0.00 |
| before | 0 | 3.011 | 42.146 | 39.135 | 0.070 | 1299.73 |
| before | 1 | 12.069 | 43.124 | 31.063 | 1.567 | 257.38 |
| before | 2 | 23.291 | 43.242 | 19.949 | 0.077 | 85.65 |
| before | 3 | 34.231 | 47.648 | 13.416 | 0.098 | 39.19 |
| before | 4 | 45.371 | 46.085 | 0.715 | 0.372 | 1.58 |
| before | 5 | 56.483 | 58.201 | 1.686 | 1.916 | 2.98 |
| before | 6 | 67.514 | 67.296 | -0.258 | 0.308 | -0.38 |
| before | 8 | 89.517 | 89.458 | -0.059 | 0.097 | -0.07 |
| before | 16 | 177.979 | 178.228 | 0.270 | 0.215 | 0.15 |
| before | 32 | 354.664 | 354.775 | 0.112 | 0.061 | 0.03 |
| before | 64 | 707.945 | 708.062 | 0.101 | 0.086 | 0.01 |
| inside | 0 | 3.011 | 42.148 | 39.137 | 0.070 | 1299.80 |
| inside | 1 | 12.069 | 43.090 | 31.021 | 0.116 | 257.03 |
| inside | 2 | 23.130 | 45.227 | 22.098 | 1.051 | 95.54 |
| inside | 3 | 34.223 | 46.166 | 11.943 | 3.830 | 34.90 |
| inside | 4 | 45.272 | 48.324 | 3.059 | 0.241 | 6.76 |
| inside | 5 | 56.318 | 56.270 | -0.047 | 0.158 | -0.08 |
| inside | 6 | 67.417 | 67.319 | -0.066 | 0.154 | -0.10 |
| inside | 8 | 89.447 | 89.464 | 0.040 | 0.096 | 0.04 |
| inside | 16 | 177.755 | 177.889 | 0.125 | 0.112 | 0.07 |
| inside | 32 | 354.462 | 354.608 | 0.148 | 0.052 | 0.04 |
| inside | 64 | 707.860 | 707.964 | 0.091 | 0.090 | 0.01 |
| after | 0 | 3.011 | 42.146 | 39.135 | 0.061 | 1299.73 |
| after | 1 | 12.124 | 48.515 | 36.392 | 0.074 | 300.16 |
| after | 2 | 24.083 | 49.236 | 25.153 | 0.073 | 104.44 |
| after | 3 | 34.231 | 50.522 | 16.292 | 0.658 | 47.59 |
| after | 4 | 46.309 | 50.362 | 4.054 | 0.141 | 8.75 |
| after | 5 | 56.418 | 56.308 | -0.109 | 0.121 | -0.19 |
| after | 6 | 68.499 | 68.277 | -0.229 | 0.140 | -0.33 |
| after | 8 | 90.432 | 90.386 | -0.028 | 0.089 | -0.03 |
| after | 16 | 178.888 | 178.865 | -0.013 | 0.081 | -0.01 |
| after | 32 | 355.662 | 355.591 | -0.075 | 0.097 | -0.02 |
| after | 64 | 708.970 | 708.951 | -0.019 | 0.221 | -0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.135 | 39.137 | 39.135 | inside > before > after |
| 1 | 11.115 | 31.063 | 31.021 | 36.392 | after > before > inside |
| 2 | 22.144 | 19.949 | 22.098 | 25.153 | after > inside > before |
| 3 | 33.119 | 13.416 | 11.943 | 16.292 | after > before > inside |
| 4 | 44.163 | 0.715 | 3.059 | 4.054 | after > inside > before |
| 5 | 55.213 | 1.686 | -0.047 | -0.109 | before > inside > after |
| 6 | 66.441 | -0.258 | -0.066 | -0.229 | inside > after > before |
| 8 | 88.399 | -0.059 | 0.040 | -0.028 | inside > after > before |
| 16 | 176.738 | 0.270 | 0.125 | -0.013 | before > inside > after |
| 32 | 353.422 | 0.112 | 0.148 | -0.075 | inside > before > after |
| 64 | 706.798 | 0.101 | 0.091 | -0.019 | before > inside > after |

This ordering table is computed mechanically from the current data. It should
be interpreted together with repeatability checks: low workload ordering is
usually stable, while transition workloads can be sensitive to front-end state.

## 5. Static Analysis Evidence

### 5.1 pgot call validation

retpoline build contains inline retpoline structure in `body_PGOT_inside_4`:

```text
pause/lfence/ret found = True
```

no-retpoline build contains a normal indirect call in `body_PGOT_inside_4`:

```text
call *%rax found = True
```

The important no-retpoline shape is:

```asm
mov    pgot_func_table[idx], %rax
call   *%rax
```

The important retpoline shape is:

```asm
mov    pgot_func_table[idx], %rax
call   <inline retpoline sequence>
pause
lfence
ret
```

Thus the pgot path is not optimized into a direct call.

### 5.2 Function and body sizes

Target function sizes:

| symbol | size bytes |
|---|---:|
| `target_work_0` | 5 |
| `target_work_1` | 63 |
| `target_work_2` | 93 |
| `target_work_3` | 123 |
| `target_work_4` | 153 |
| `target_work_5` | 183 |
| `target_work_6` | 213 |
| `target_work_8` | 273 |
| `target_work_16` | 512 |
| `target_work_32` | 992 |
| `target_work_64` | 1952 |

Retpoline body sizes:

| workload | work_only | DIRECT before | PGOT before | DIRECT inside | PGOT inside | DIRECT after | PGOT after |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 28 | 53 | 80 | 53 | 80 | 53 | 80 |
| 1 | 89 | 122 | 153 | 53 | 80 | 123 | 150 |
| 2 | 121 | 156 | 183 | 53 | 80 | 156 | 187 |
| 3 | 156 | 186 | 217 | 53 | 80 | 187 | 218 |
| 4 | 190 | 220 | 247 | 53 | 80 | 224 | 251 |
| 5 | 220 | 250 | 277 | 53 | 80 | 251 | 278 |
| 6 | 250 | 280 | 307 | 53 | 80 | 284 | 311 |
| 8 | 310 | 340 | 367 | 53 | 80 | 344 | 371 |
| 16 | 550 | 580 | 607 | 53 | 80 | 584 | 611 |
| 32 | 1030 | 1060 | 1087 | 53 | 80 | 1064 | 1091 |
| 64 | 1990 | 2020 | 2047 | 53 | 80 | 2024 | 2051 |

Static interpretation:

1. `work_only` contains only the expanded arithmetic work in the caller loop.
2. `inside` keeps the caller body almost fixed; workload moves into
   `target_work_N`.
3. `before` and `after` expand workload in the caller, so caller size and call
   position change with workload.
4. Therefore, before/inside/after are not just the same instructions shifted in
   time. They alter caller/callee boundary, loop layout, and retpoline context.

## 6. Interpretation

The experiment separates three questions:

1. How large is the ordinary work stream without any target call? This is
   answered by `work_only`.
2. How large is call-only retpoline func-pgot overhead? This is answered by
   `none/workload=0`.
3. How does the same workload affect visible overhead when placed before,
   inside, or after the call? This is answered by the placement table.

The correct interpretation is visible whole-loop overhead, not pure hardware
latency. The target or after-work cannot execute before retpoline completes
control transfer. The reduction in delta means the fixed retpoline disturbance
becomes less visible in the steady-state loop as ordinary work and code layout
change.

## 7. Conclusions

1. `func-pgot` adds one pgot function-slot load. Under no-retpoline this feeds
   a normal indirect call; under retpoline it feeds the inline retpoline
   sequence.
2. The `work_only` group provides the no-call workload scale and helps identify
   when ordinary work is large enough to make retpoline overhead less visible.
3. Same-workload before/inside/after can differ because the machine-code shape
   differs: caller-expanded work, callee-contained work, and post-call work
   create different front-end and loop contexts.
4. A fixed ordering should only be claimed if it survives repeatability checks.
   If a workload is in the transition region, report it as transition behavior
   rather than as a deterministic primitive cost.

## 8. Files

| file | description |
|---|---|
| `raw.csv` | paired raw direct/pgot samples |
| `processed.csv` | mean/median/IQR/stddev/min/max per case |
| `paper_table.csv` | compact table for paper figures |
| `metadata.txt` | environment and build parameters |
| `static/nm_*.txt` | symbol sizes |
| `static/objdump_*.txt` | disassembly validation |
