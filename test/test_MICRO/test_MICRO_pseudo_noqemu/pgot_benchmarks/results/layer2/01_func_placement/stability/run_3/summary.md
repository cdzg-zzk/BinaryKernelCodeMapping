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
| 2 | 22.145 | 0.004 |
| 3 | 33.118 | 0.068 |
| 4 | 44.163 | 0.134 |
| 5 | 55.215 | 0.139 |
| 6 | 66.418 | 0.138 |
| 8 | 88.397 | 0.098 |
| 16 | 176.731 | 0.054 |
| 32 | 353.427 | 0.063 |
| 64 | 706.804 | 0.071 |

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
| work_only | 2 | 22.144 | 22.144 | -0.001 | 0.004 | -0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.068 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.001 | 0.136 | 0.00 |
| work_only | 5 | 55.213 | 55.276 | 0.065 | 0.140 | 0.12 |
| work_only | 6 | 66.440 | 66.427 | -0.025 | 0.132 | -0.04 |
| work_only | 8 | 88.397 | 88.398 | 0.019 | 0.072 | 0.02 |
| work_only | 16 | 176.735 | 176.732 | 0.004 | 0.067 | 0.00 |
| work_only | 32 | 353.437 | 353.444 | 0.005 | 0.076 | 0.00 |
| work_only | 64 | 706.806 | 706.804 | -0.007 | 0.067 | -0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.069 | 12.102 | 0.035 | 0.041 | 0.29 |
| before | 2 | 23.291 | 23.174 | -0.121 | 0.245 | -0.52 |
| before | 3 | 34.231 | 34.302 | 0.070 | 0.130 | 0.20 |
| before | 4 | 45.372 | 45.308 | -0.064 | 0.136 | -0.14 |
| before | 5 | 56.447 | 56.565 | 0.120 | 0.141 | 0.21 |
| before | 6 | 67.480 | 67.544 | 0.022 | 0.252 | 0.03 |
| before | 8 | 89.508 | 89.522 | -0.001 | 0.069 | -0.00 |
| before | 16 | 177.977 | 177.884 | -0.084 | 0.317 | -0.05 |
| before | 32 | 354.664 | 354.686 | 0.027 | 0.180 | 0.01 |
| before | 64 | 707.944 | 708.025 | 0.083 | 0.074 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| inside | 1 | 12.069 | 12.057 | -0.013 | 0.001 | -0.11 |
| inside | 2 | 23.130 | 23.137 | 0.008 | 0.005 | 0.03 |
| inside | 3 | 34.222 | 34.178 | -0.044 | 0.070 | -0.13 |
| inside | 4 | 45.286 | 45.264 | 0.004 | 0.205 | 0.01 |
| inside | 5 | 56.377 | 56.361 | -0.019 | 0.181 | -0.03 |
| inside | 6 | 67.422 | 67.336 | -0.090 | 0.136 | -0.13 |
| inside | 8 | 89.449 | 89.520 | 0.068 | 0.092 | 0.08 |
| inside | 16 | 177.757 | 177.816 | 0.055 | 0.092 | 0.03 |
| inside | 32 | 354.463 | 354.502 | 0.040 | 0.062 | 0.01 |
| inside | 64 | 707.855 | 707.896 | 0.036 | 0.082 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| after | 1 | 12.124 | 12.101 | -0.022 | 0.002 | -0.18 |
| after | 2 | 24.083 | 24.108 | 0.025 | 0.022 | 0.10 |
| after | 3 | 34.231 | 34.232 | 0.001 | 0.135 | 0.00 |
| after | 4 | 46.309 | 46.251 | -0.057 | 0.139 | -0.12 |
| after | 5 | 56.415 | 56.314 | -0.103 | 0.139 | -0.18 |
| after | 6 | 68.498 | 68.372 | -0.134 | 0.136 | -0.20 |
| after | 8 | 90.432 | 90.442 | 0.021 | 0.083 | 0.02 |
| after | 16 | 178.889 | 178.764 | -0.129 | 0.093 | -0.07 |
| after | 32 | 355.653 | 355.482 | -0.161 | 0.090 | -0.05 |
| after | 64 | 708.966 | 708.887 | -0.094 | 0.061 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 42.146 | 39.135 | 0.075 | 1299.73 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.001 | 0.003 | 0.01 |
| work_only | 2 | 22.145 | 22.144 | 0.000 | 0.004 | 0.00 |
| work_only | 3 | 33.118 | 33.119 | 0.000 | 0.068 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.000 | 0.134 | 0.00 |
| work_only | 5 | 55.215 | 55.270 | 0.059 | 0.139 | 0.11 |
| work_only | 6 | 66.418 | 66.449 | 0.034 | 0.138 | 0.05 |
| work_only | 8 | 88.397 | 88.391 | -0.019 | 0.098 | -0.02 |
| work_only | 16 | 176.731 | 176.737 | 0.009 | 0.054 | 0.01 |
| work_only | 32 | 353.427 | 353.431 | 0.003 | 0.063 | 0.00 |
| work_only | 64 | 706.804 | 706.807 | -0.007 | 0.071 | -0.00 |
| before | 0 | 3.011 | 42.146 | 39.135 | 0.067 | 1299.73 |
| before | 1 | 12.095 | 42.827 | 30.681 | 0.947 | 253.67 |
| before | 2 | 23.291 | 43.175 | 19.886 | 0.073 | 85.38 |
| before | 3 | 34.232 | 47.664 | 13.409 | 0.127 | 39.17 |
| before | 4 | 45.370 | 45.864 | 0.496 | 0.424 | 1.09 |
| before | 5 | 56.504 | 58.200 | 1.684 | 2.461 | 2.98 |
| before | 6 | 67.481 | 67.299 | -0.210 | 0.351 | -0.31 |
| before | 8 | 89.515 | 89.466 | -0.053 | 0.096 | -0.06 |
| before | 16 | 177.968 | 178.221 | 0.247 | 0.274 | 0.14 |
| before | 32 | 354.661 | 354.799 | 0.114 | 0.079 | 0.03 |
| before | 64 | 707.948 | 708.059 | 0.101 | 0.085 | 0.01 |
| inside | 0 | 3.011 | 42.146 | 39.135 | 0.058 | 1299.73 |
| inside | 1 | 12.070 | 43.024 | 30.955 | 2.057 | 256.46 |
| inside | 2 | 23.130 | 45.156 | 22.028 | 0.078 | 95.24 |
| inside | 3 | 34.223 | 46.195 | 11.972 | 2.979 | 34.98 |
| inside | 4 | 45.303 | 49.093 | 3.685 | 0.922 | 8.13 |
| inside | 5 | 56.374 | 56.244 | -0.138 | 0.151 | -0.24 |
| inside | 6 | 67.410 | 67.326 | -0.068 | 0.080 | -0.10 |
| inside | 8 | 89.445 | 89.457 | 0.021 | 0.094 | 0.02 |
| inside | 16 | 177.757 | 177.882 | 0.121 | 0.081 | 0.07 |
| inside | 32 | 354.469 | 354.613 | 0.148 | 0.093 | 0.04 |
| inside | 64 | 707.862 | 707.970 | 0.109 | 0.093 | 0.02 |
| after | 0 | 3.011 | 42.148 | 39.136 | 0.074 | 1299.77 |
| after | 1 | 12.124 | 48.581 | 36.460 | 0.074 | 300.73 |
| after | 2 | 24.083 | 49.170 | 25.087 | 0.071 | 104.17 |
| after | 3 | 34.231 | 50.425 | 16.195 | 0.581 | 47.31 |
| after | 4 | 46.310 | 50.362 | 4.050 | 0.310 | 8.75 |
| after | 5 | 56.416 | 56.232 | -0.186 | 0.143 | -0.33 |
| after | 6 | 68.494 | 68.301 | -0.161 | 0.135 | -0.24 |
| after | 8 | 90.431 | 90.388 | -0.033 | 0.082 | -0.04 |
| after | 16 | 178.893 | 178.873 | -0.025 | 0.111 | -0.01 |
| after | 32 | 355.690 | 355.658 | -0.023 | 0.189 | -0.01 |
| after | 64 | 708.966 | 708.985 | -0.001 | 0.198 | -0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.135 | 39.135 | 39.136 | after > before > inside |
| 1 | 11.115 | 30.681 | 30.955 | 36.460 | after > inside > before |
| 2 | 22.145 | 19.886 | 22.028 | 25.087 | after > inside > before |
| 3 | 33.118 | 13.409 | 11.972 | 16.195 | after > before > inside |
| 4 | 44.163 | 0.496 | 3.685 | 4.050 | after > inside > before |
| 5 | 55.215 | 1.684 | -0.138 | -0.186 | before > inside > after |
| 6 | 66.418 | -0.210 | -0.068 | -0.161 | inside > after > before |
| 8 | 88.397 | -0.053 | 0.021 | -0.033 | inside > after > before |
| 16 | 176.731 | 0.247 | 0.121 | -0.025 | before > inside > after |
| 32 | 353.427 | 0.114 | 0.148 | -0.023 | inside > before > after |
| 64 | 706.804 | 0.101 | 0.109 | -0.001 | inside > before > after |

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
