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
| 2 | 22.145 | 0.003 |
| 3 | 33.118 | 0.066 |
| 4 | 44.163 | 0.136 |
| 5 | 55.214 | 0.139 |
| 6 | 66.427 | 0.135 |
| 8 | 88.397 | 0.078 |
| 16 | 176.730 | 0.052 |
| 32 | 353.429 | 0.068 |
| 64 | 706.808 | 0.059 |

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
| none | 0 | 3.011 | 4.014 | 1.003 | 0.000 | 33.31 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.002 | 0.00 |
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.004 | 0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.088 | 0.00 |
| work_only | 4 | 44.162 | 44.163 | 0.000 | 0.134 | 0.00 |
| work_only | 5 | 55.214 | 55.270 | 0.057 | 0.139 | 0.10 |
| work_only | 6 | 66.447 | 66.432 | -0.015 | 0.130 | -0.02 |
| work_only | 8 | 88.406 | 88.387 | -0.025 | 0.081 | -0.03 |
| work_only | 16 | 176.734 | 176.731 | -0.010 | 0.092 | -0.01 |
| work_only | 32 | 353.438 | 353.438 | -0.005 | 0.056 | -0.00 |
| work_only | 64 | 706.796 | 706.806 | 0.010 | 0.057 | 0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.068 | 12.102 | 0.034 | 0.042 | 0.28 |
| before | 2 | 23.290 | 23.171 | -0.119 | 0.124 | -0.51 |
| before | 3 | 34.231 | 34.302 | 0.071 | 0.133 | 0.21 |
| before | 4 | 45.372 | 45.310 | -0.060 | 0.138 | -0.13 |
| before | 5 | 56.449 | 56.548 | 0.104 | 0.142 | 0.18 |
| before | 6 | 67.455 | 67.540 | 0.036 | 0.251 | 0.05 |
| before | 8 | 89.511 | 89.523 | 0.006 | 0.067 | 0.01 |
| before | 16 | 177.972 | 177.879 | -0.104 | 0.228 | -0.06 |
| before | 32 | 354.657 | 354.673 | 0.017 | 0.165 | 0.00 |
| before | 64 | 707.942 | 708.021 | 0.073 | 0.044 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| inside | 1 | 12.069 | 12.056 | -0.013 | 0.002 | -0.11 |
| inside | 2 | 23.129 | 23.137 | 0.008 | 0.003 | 0.03 |
| inside | 3 | 34.223 | 34.178 | -0.044 | 0.134 | -0.13 |
| inside | 4 | 45.286 | 45.263 | -0.026 | 0.194 | -0.06 |
| inside | 5 | 56.381 | 56.363 | 0.014 | 0.118 | 0.02 |
| inside | 6 | 67.400 | 67.365 | -0.031 | 0.135 | -0.05 |
| inside | 8 | 89.447 | 89.523 | 0.071 | 0.075 | 0.08 |
| inside | 16 | 177.753 | 177.823 | 0.075 | 0.067 | 0.04 |
| inside | 32 | 354.465 | 354.503 | 0.032 | 0.052 | 0.01 |
| inside | 64 | 707.848 | 707.897 | 0.056 | 0.073 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| after | 1 | 12.124 | 12.101 | -0.023 | 0.057 | -0.19 |
| after | 2 | 24.083 | 24.109 | 0.025 | 0.021 | 0.10 |
| after | 3 | 34.231 | 34.233 | 0.002 | 0.132 | 0.01 |
| after | 4 | 46.310 | 46.250 | -0.058 | 0.137 | -0.13 |
| after | 5 | 56.416 | 56.315 | -0.103 | 0.139 | -0.18 |
| after | 6 | 68.487 | 68.389 | -0.089 | 0.136 | -0.13 |
| after | 8 | 90.429 | 90.459 | 0.047 | 0.162 | 0.05 |
| after | 16 | 178.892 | 178.762 | -0.126 | 0.096 | -0.07 |
| after | 32 | 355.681 | 355.484 | -0.193 | 0.092 | -0.05 |
| after | 64 | 708.968 | 708.885 | -0.079 | 0.057 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 42.146 | 39.135 | 0.071 | 1299.73 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.002 | 0.00 |
| work_only | 2 | 22.145 | 22.145 | 0.000 | 0.003 | 0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.066 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.001 | 0.136 | 0.00 |
| work_only | 5 | 55.214 | 55.273 | 0.061 | 0.139 | 0.11 |
| work_only | 6 | 66.427 | 66.448 | 0.033 | 0.135 | 0.05 |
| work_only | 8 | 88.397 | 88.399 | 0.013 | 0.078 | 0.01 |
| work_only | 16 | 176.730 | 176.734 | 0.006 | 0.052 | 0.00 |
| work_only | 32 | 353.429 | 353.431 | -0.001 | 0.068 | -0.00 |
| work_only | 64 | 706.808 | 706.801 | -0.015 | 0.059 | -0.00 |
| before | 0 | 3.011 | 42.217 | 39.205 | 4.013 | 1302.06 |
| before | 1 | 12.092 | 43.017 | 30.949 | 1.427 | 255.95 |
| before | 2 | 23.291 | 43.175 | 19.886 | 0.074 | 85.38 |
| before | 3 | 34.232 | 47.664 | 13.366 | 0.134 | 39.05 |
| before | 4 | 45.370 | 45.912 | 0.541 | 0.376 | 1.19 |
| before | 5 | 56.502 | 58.201 | 1.688 | 2.372 | 2.99 |
| before | 6 | 67.472 | 67.735 | 0.240 | 0.361 | 0.36 |
| before | 8 | 89.513 | 89.473 | -0.041 | 0.135 | -0.05 |
| before | 16 | 177.956 | 178.225 | 0.264 | 0.195 | 0.15 |
| before | 32 | 354.667 | 354.783 | 0.110 | 0.085 | 0.03 |
| before | 64 | 707.952 | 708.051 | 0.087 | 0.073 | 0.01 |
| inside | 0 | 3.011 | 42.216 | 39.205 | 4.013 | 1302.06 |
| inside | 1 | 12.069 | 43.091 | 31.021 | 0.073 | 257.03 |
| inside | 2 | 23.130 | 45.223 | 22.093 | 1.372 | 95.52 |
| inside | 3 | 34.223 | 46.010 | 11.788 | 2.153 | 34.44 |
| inside | 4 | 45.267 | 49.170 | 3.890 | 1.058 | 8.59 |
| inside | 5 | 56.376 | 56.266 | -0.063 | 0.130 | -0.11 |
| inside | 6 | 67.408 | 67.344 | -0.051 | 0.132 | -0.08 |
| inside | 8 | 89.450 | 89.458 | 0.014 | 0.079 | 0.02 |
| inside | 16 | 177.761 | 177.881 | 0.117 | 0.093 | 0.07 |
| inside | 32 | 354.467 | 354.611 | 0.155 | 0.081 | 0.04 |
| inside | 64 | 707.850 | 707.978 | 0.124 | 0.068 | 0.02 |
| after | 0 | 3.011 | 42.147 | 39.135 | 0.070 | 1299.73 |
| after | 1 | 12.124 | 48.515 | 36.458 | 0.083 | 300.71 |
| after | 2 | 24.083 | 49.170 | 25.087 | 0.151 | 104.17 |
| after | 3 | 34.231 | 50.798 | 16.568 | 0.748 | 48.40 |
| after | 4 | 46.309 | 50.361 | 3.981 | 0.239 | 8.60 |
| after | 5 | 56.354 | 56.284 | -0.068 | 0.144 | -0.12 |
| after | 6 | 68.500 | 68.279 | -0.223 | 0.138 | -0.33 |
| after | 8 | 90.419 | 90.402 | -0.016 | 0.055 | -0.02 |
| after | 16 | 178.891 | 178.860 | -0.018 | 0.085 | -0.01 |
| after | 32 | 355.676 | 355.645 | -0.018 | 0.130 | -0.01 |
| after | 64 | 708.977 | 708.935 | -0.027 | 0.130 | -0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.205 | 39.205 | 39.135 | before > inside > after |
| 1 | 11.115 | 30.949 | 31.021 | 36.458 | after > inside > before |
| 2 | 22.145 | 19.886 | 22.093 | 25.087 | after > inside > before |
| 3 | 33.118 | 13.366 | 11.788 | 16.568 | after > before > inside |
| 4 | 44.163 | 0.541 | 3.890 | 3.981 | after > inside > before |
| 5 | 55.214 | 1.688 | -0.063 | -0.068 | before > inside > after |
| 6 | 66.427 | 0.240 | -0.051 | -0.223 | before > inside > after |
| 8 | 88.397 | -0.041 | 0.014 | -0.016 | inside > after > before |
| 16 | 176.730 | 0.264 | 0.117 | -0.018 | before > inside > after |
| 32 | 353.429 | 0.110 | 0.155 | -0.018 | inside > before > after |
| 64 | 706.808 | 0.087 | 0.124 | -0.027 | inside > before > after |

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
