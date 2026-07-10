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
| 2 | 22.145 | 0.003 |
| 3 | 33.118 | 0.070 |
| 4 | 44.163 | 0.136 |
| 5 | 55.214 | 0.138 |
| 6 | 66.445 | 0.139 |
| 8 | 88.397 | 0.070 |
| 16 | 176.732 | 0.073 |
| 32 | 353.435 | 0.076 |
| 64 | 706.806 | 0.086 |

The retpoline call-only baseline is:

```text
none/workload=0 delta = 39.136 cycles/iteration
```

The first workload where all three retpoline placements have |delta| <= 1 cycle
in this run is:

```text
workload = 6
```

### 4.2 no-retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 4.014 | 1.003 | 0.002 | 33.31 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.002 | 0.00 |
| work_only | 2 | 22.144 | 22.144 | 0.000 | 0.068 | 0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.129 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.000 | 0.134 | 0.00 |
| work_only | 5 | 55.216 | 55.270 | 0.059 | 0.137 | 0.11 |
| work_only | 6 | 66.430 | 66.448 | 0.026 | 0.135 | 0.04 |
| work_only | 8 | 88.387 | 88.394 | 0.025 | 0.087 | 0.03 |
| work_only | 16 | 176.731 | 176.736 | 0.001 | 0.097 | 0.00 |
| work_only | 32 | 353.432 | 353.437 | 0.016 | 0.086 | 0.00 |
| work_only | 64 | 706.796 | 706.803 | 0.001 | 0.082 | 0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.106 | 12.102 | 0.004 | 0.042 | 0.03 |
| before | 2 | 23.291 | 23.169 | -0.129 | 0.189 | -0.55 |
| before | 3 | 34.231 | 34.303 | 0.072 | 0.132 | 0.21 |
| before | 4 | 45.372 | 45.308 | -0.062 | 0.141 | -0.14 |
| before | 5 | 56.447 | 56.554 | 0.111 | 0.144 | 0.20 |
| before | 6 | 67.465 | 67.546 | 0.019 | 0.279 | 0.03 |
| before | 8 | 89.513 | 89.522 | 0.007 | 0.107 | 0.01 |
| before | 16 | 177.949 | 177.881 | -0.093 | 0.244 | -0.05 |
| before | 32 | 354.661 | 354.634 | -0.021 | 0.165 | -0.01 |
| before | 64 | 707.947 | 708.023 | 0.096 | 0.067 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.002 | 33.31 |
| inside | 1 | 12.069 | 12.057 | -0.013 | 0.001 | -0.11 |
| inside | 2 | 23.130 | 23.137 | 0.008 | 0.065 | 0.03 |
| inside | 3 | 34.222 | 34.178 | -0.044 | 0.070 | -0.13 |
| inside | 4 | 45.283 | 45.264 | -0.007 | 0.163 | -0.02 |
| inside | 5 | 56.372 | 56.360 | -0.015 | 0.110 | -0.03 |
| inside | 6 | 67.417 | 67.356 | -0.082 | 0.134 | -0.12 |
| inside | 8 | 89.445 | 89.523 | 0.072 | 0.098 | 0.08 |
| inside | 16 | 177.756 | 177.822 | 0.069 | 0.106 | 0.04 |
| inside | 32 | 354.462 | 354.502 | 0.046 | 0.068 | 0.01 |
| inside | 64 | 707.840 | 707.882 | 0.037 | 0.108 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| after | 1 | 12.123 | 12.101 | -0.022 | 0.074 | -0.18 |
| after | 2 | 24.083 | 24.108 | 0.025 | 0.023 | 0.10 |
| after | 3 | 34.231 | 34.233 | 0.002 | 0.132 | 0.01 |
| after | 4 | 46.310 | 46.251 | -0.060 | 0.135 | -0.13 |
| after | 5 | 56.417 | 56.314 | -0.105 | 0.139 | -0.19 |
| after | 6 | 68.500 | 68.368 | -0.138 | 0.135 | -0.20 |
| after | 8 | 90.428 | 90.458 | 0.030 | 0.122 | 0.03 |
| after | 16 | 178.889 | 178.762 | -0.130 | 0.067 | -0.07 |
| after | 32 | 355.672 | 355.485 | -0.180 | 0.103 | -0.05 |
| after | 64 | 708.962 | 708.887 | -0.076 | 0.073 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 42.146 | 39.136 | 0.069 | 1299.77 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.003 | 0.00 |
| work_only | 2 | 22.145 | 22.144 | 0.000 | 0.003 | 0.00 |
| work_only | 3 | 33.118 | 33.119 | 0.000 | 0.070 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.001 | 0.136 | 0.00 |
| work_only | 5 | 55.214 | 55.214 | 0.000 | 0.138 | 0.00 |
| work_only | 6 | 66.445 | 66.427 | -0.020 | 0.139 | -0.03 |
| work_only | 8 | 88.397 | 88.386 | -0.014 | 0.070 | -0.02 |
| work_only | 16 | 176.732 | 176.735 | 0.000 | 0.073 | 0.00 |
| work_only | 32 | 353.435 | 353.429 | -0.016 | 0.076 | -0.00 |
| work_only | 64 | 706.806 | 706.801 | -0.006 | 0.086 | -0.00 |
| before | 0 | 3.011 | 42.146 | 39.135 | 0.072 | 1299.73 |
| before | 1 | 12.094 | 42.953 | 30.859 | 1.437 | 255.16 |
| before | 2 | 23.291 | 43.174 | 19.884 | 0.075 | 85.37 |
| before | 3 | 34.232 | 52.246 | 18.015 | 1.009 | 52.63 |
| before | 4 | 45.371 | 46.079 | 0.710 | 0.360 | 1.56 |
| before | 5 | 56.512 | 58.272 | 1.827 | 1.004 | 3.23 |
| before | 6 | 67.509 | 67.296 | -0.277 | 0.312 | -0.41 |
| before | 8 | 89.503 | 89.469 | -0.017 | 0.088 | -0.02 |
| before | 16 | 177.948 | 178.230 | 0.259 | 0.178 | 0.15 |
| before | 32 | 354.663 | 354.793 | 0.121 | 0.073 | 0.03 |
| before | 64 | 707.944 | 708.025 | 0.080 | 0.099 | 0.01 |
| inside | 0 | 3.011 | 42.146 | 39.135 | 0.062 | 1299.73 |
| inside | 1 | 12.069 | 45.156 | 33.020 | 5.065 | 273.59 |
| inside | 2 | 23.130 | 45.217 | 22.086 | 0.739 | 95.49 |
| inside | 3 | 34.223 | 45.345 | 11.122 | 2.549 | 32.50 |
| inside | 4 | 45.259 | 48.397 | 3.205 | 0.613 | 7.08 |
| inside | 5 | 56.377 | 56.267 | -0.079 | 0.159 | -0.14 |
| inside | 6 | 67.411 | 67.357 | -0.044 | 0.139 | -0.07 |
| inside | 8 | 89.455 | 89.464 | 0.018 | 0.100 | 0.02 |
| inside | 16 | 177.756 | 177.871 | 0.118 | 0.053 | 0.07 |
| inside | 32 | 354.462 | 354.632 | 0.164 | 0.108 | 0.05 |
| inside | 64 | 707.853 | 707.978 | 0.131 | 0.106 | 0.02 |
| after | 0 | 3.011 | 42.146 | 39.135 | 0.068 | 1299.73 |
| after | 1 | 12.124 | 48.515 | 36.457 | 0.078 | 300.70 |
| after | 2 | 24.083 | 49.172 | 25.087 | 0.092 | 104.17 |
| after | 3 | 34.231 | 50.502 | 16.271 | 0.752 | 47.53 |
| after | 4 | 46.310 | 50.819 | 4.493 | 0.769 | 9.70 |
| after | 5 | 56.355 | 56.282 | -0.072 | 0.150 | -0.13 |
| after | 6 | 68.496 | 68.280 | -0.223 | 0.139 | -0.33 |
| after | 8 | 90.430 | 90.401 | -0.030 | 0.086 | -0.03 |
| after | 16 | 178.889 | 178.850 | -0.042 | 0.112 | -0.02 |
| after | 32 | 355.717 | 355.676 | 0.013 | 0.204 | 0.00 |
| after | 64 | 708.972 | 708.987 | -0.015 | 0.203 | -0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.135 | 39.135 | 39.135 | before > inside > after |
| 1 | 11.115 | 30.859 | 33.020 | 36.457 | after > inside > before |
| 2 | 22.145 | 19.884 | 22.086 | 25.087 | after > inside > before |
| 3 | 33.118 | 18.015 | 11.122 | 16.271 | before > after > inside |
| 4 | 44.163 | 0.710 | 3.205 | 4.493 | after > inside > before |
| 5 | 55.214 | 1.827 | -0.079 | -0.072 | before > after > inside |
| 6 | 66.445 | -0.277 | -0.044 | -0.223 | inside > after > before |
| 8 | 88.397 | -0.017 | 0.018 | -0.030 | inside > before > after |
| 16 | 176.732 | 0.259 | 0.118 | -0.042 | before > inside > after |
| 32 | 353.435 | 0.121 | 0.164 | 0.013 | inside > before > after |
| 64 | 706.806 | 0.080 | 0.131 | -0.015 | inside > before > after |

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
