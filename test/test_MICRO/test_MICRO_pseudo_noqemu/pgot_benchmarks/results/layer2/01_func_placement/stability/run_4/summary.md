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
| 1 | 11.115 | 0.003 |
| 2 | 22.144 | 0.004 |
| 3 | 33.119 | 0.122 |
| 4 | 44.163 | 0.133 |
| 5 | 55.213 | 0.134 |
| 6 | 66.436 | 0.134 |
| 8 | 88.407 | 0.076 |
| 16 | 176.735 | 0.090 |
| 32 | 353.428 | 0.073 |
| 64 | 706.796 | 0.080 |

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
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.004 | 0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.123 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.000 | 0.135 | 0.00 |
| work_only | 5 | 55.213 | 55.275 | 0.064 | 0.137 | 0.12 |
| work_only | 6 | 66.446 | 66.437 | -0.018 | 0.134 | -0.03 |
| work_only | 8 | 88.402 | 88.386 | -0.020 | 0.098 | -0.02 |
| work_only | 16 | 176.729 | 176.734 | 0.005 | 0.045 | 0.00 |
| work_only | 32 | 353.433 | 353.436 | 0.001 | 0.061 | 0.00 |
| work_only | 64 | 706.811 | 706.807 | -0.003 | 0.059 | -0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.096 | 12.102 | 0.008 | 0.043 | 0.07 |
| before | 2 | 23.290 | 23.172 | -0.120 | 0.163 | -0.52 |
| before | 3 | 34.231 | 34.302 | 0.071 | 0.134 | 0.21 |
| before | 4 | 45.371 | 45.309 | -0.060 | 0.139 | -0.13 |
| before | 5 | 56.446 | 56.564 | 0.117 | 0.143 | 0.21 |
| before | 6 | 67.437 | 67.519 | 0.071 | 0.151 | 0.11 |
| before | 8 | 89.515 | 89.531 | 0.006 | 0.076 | 0.01 |
| before | 16 | 177.972 | 177.880 | -0.099 | 0.175 | -0.06 |
| before | 32 | 354.662 | 354.656 | -0.028 | 0.157 | -0.01 |
| before | 64 | 707.942 | 708.021 | 0.081 | 0.071 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| inside | 1 | 12.069 | 12.057 | -0.013 | 0.002 | -0.11 |
| inside | 2 | 23.130 | 23.137 | 0.008 | 0.004 | 0.03 |
| inside | 3 | 34.222 | 34.178 | -0.044 | 0.133 | -0.13 |
| inside | 4 | 45.284 | 45.264 | -0.016 | 0.208 | -0.04 |
| inside | 5 | 56.378 | 56.357 | -0.021 | 0.138 | -0.04 |
| inside | 6 | 67.419 | 67.362 | -0.035 | 0.140 | -0.05 |
| inside | 8 | 89.451 | 89.520 | 0.063 | 0.099 | 0.07 |
| inside | 16 | 177.751 | 177.819 | 0.067 | 0.104 | 0.04 |
| inside | 32 | 354.462 | 354.502 | 0.041 | 0.047 | 0.01 |
| inside | 64 | 707.851 | 707.898 | 0.048 | 0.057 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.002 | 33.31 |
| after | 1 | 12.124 | 12.101 | -0.023 | 0.004 | -0.19 |
| after | 2 | 24.083 | 24.108 | 0.025 | 0.069 | 0.10 |
| after | 3 | 34.231 | 34.232 | 0.002 | 0.133 | 0.01 |
| after | 4 | 46.311 | 46.250 | -0.060 | 0.136 | -0.13 |
| after | 5 | 56.413 | 56.315 | -0.098 | 0.140 | -0.17 |
| after | 6 | 68.495 | 68.372 | -0.127 | 0.137 | -0.19 |
| after | 8 | 90.435 | 90.482 | 0.053 | 0.102 | 0.06 |
| after | 16 | 178.890 | 178.764 | -0.133 | 0.064 | -0.07 |
| after | 32 | 355.687 | 355.484 | -0.192 | 0.079 | -0.05 |
| after | 64 | 708.956 | 708.883 | -0.066 | 0.081 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 42.146 | 39.135 | 0.069 | 1299.73 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.003 | 0.00 |
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.004 | 0.00 |
| work_only | 3 | 33.119 | 33.118 | 0.000 | 0.122 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | -0.001 | 0.133 | -0.00 |
| work_only | 5 | 55.213 | 55.264 | 0.053 | 0.134 | 0.10 |
| work_only | 6 | 66.436 | 66.440 | -0.018 | 0.134 | -0.03 |
| work_only | 8 | 88.407 | 88.386 | -0.025 | 0.076 | -0.03 |
| work_only | 16 | 176.735 | 176.734 | -0.001 | 0.090 | -0.00 |
| work_only | 32 | 353.428 | 353.426 | 0.002 | 0.073 | 0.00 |
| work_only | 64 | 706.796 | 706.805 | 0.017 | 0.080 | 0.00 |
| before | 0 | 3.011 | 42.146 | 39.135 | 0.068 | 1299.73 |
| before | 1 | 12.093 | 42.881 | 30.790 | 1.541 | 254.61 |
| before | 2 | 23.290 | 43.175 | 19.886 | 0.071 | 85.38 |
| before | 3 | 34.232 | 47.663 | 13.416 | 0.134 | 39.19 |
| before | 4 | 45.370 | 45.869 | 0.499 | 0.400 | 1.10 |
| before | 5 | 56.448 | 58.201 | 1.687 | 1.600 | 2.99 |
| before | 6 | 67.456 | 67.682 | 0.134 | 0.474 | 0.20 |
| before | 8 | 89.513 | 89.470 | -0.051 | 0.088 | -0.06 |
| before | 16 | 177.970 | 178.225 | 0.235 | 0.303 | 0.13 |
| before | 32 | 354.664 | 354.805 | 0.136 | 0.070 | 0.04 |
| before | 64 | 707.951 | 708.041 | 0.080 | 0.089 | 0.01 |
| inside | 0 | 3.011 | 42.146 | 39.135 | 0.061 | 1299.73 |
| inside | 1 | 12.069 | 43.094 | 31.025 | 0.078 | 257.06 |
| inside | 2 | 23.130 | 45.232 | 22.103 | 3.011 | 95.56 |
| inside | 3 | 34.223 | 46.460 | 12.238 | 3.152 | 35.76 |
| inside | 4 | 45.267 | 48.369 | 3.122 | 0.226 | 6.90 |
| inside | 5 | 56.379 | 56.321 | -0.048 | 0.126 | -0.09 |
| inside | 6 | 67.421 | 67.356 | -0.043 | 0.120 | -0.06 |
| inside | 8 | 89.433 | 89.464 | 0.040 | 0.091 | 0.04 |
| inside | 16 | 177.752 | 177.883 | 0.130 | 0.085 | 0.07 |
| inside | 32 | 354.462 | 354.627 | 0.167 | 0.066 | 0.05 |
| inside | 64 | 707.852 | 707.960 | 0.103 | 0.098 | 0.01 |
| after | 0 | 3.011 | 42.147 | 39.135 | 0.071 | 1299.73 |
| after | 1 | 12.124 | 48.516 | 36.393 | 0.074 | 300.17 |
| after | 2 | 24.083 | 49.170 | 25.087 | 0.071 | 104.17 |
| after | 3 | 34.231 | 50.494 | 16.264 | 0.480 | 47.51 |
| after | 4 | 46.309 | 50.883 | 4.576 | 0.482 | 9.88 |
| after | 5 | 56.387 | 56.305 | -0.085 | 0.125 | -0.15 |
| after | 6 | 68.499 | 68.281 | -0.225 | 0.140 | -0.33 |
| after | 8 | 90.427 | 90.393 | -0.023 | 0.087 | -0.03 |
| after | 16 | 178.892 | 178.865 | -0.021 | 0.073 | -0.01 |
| after | 32 | 355.716 | 355.643 | -0.035 | 0.153 | -0.01 |
| after | 64 | 708.967 | 708.973 | 0.029 | 0.223 | 0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.135 | 39.135 | 39.135 | before > inside > after |
| 1 | 11.115 | 30.790 | 31.025 | 36.393 | after > inside > before |
| 2 | 22.144 | 19.886 | 22.103 | 25.087 | after > inside > before |
| 3 | 33.119 | 13.416 | 12.238 | 16.264 | after > before > inside |
| 4 | 44.163 | 0.499 | 3.122 | 4.576 | after > inside > before |
| 5 | 55.213 | 1.687 | -0.048 | -0.085 | before > inside > after |
| 6 | 66.436 | 0.134 | -0.043 | -0.225 | before > inside > after |
| 8 | 88.407 | -0.051 | 0.040 | -0.023 | inside > after > before |
| 16 | 176.735 | 0.235 | 0.130 | -0.021 | before > inside > after |
| 32 | 353.428 | 0.136 | 0.167 | -0.035 | inside > before > after |
| 64 | 706.796 | 0.080 | 0.103 | 0.029 | inside > before > after |

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
