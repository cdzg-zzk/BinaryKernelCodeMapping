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
| 3 | 33.118 | 0.066 |
| 4 | 44.163 | 0.135 |
| 5 | 55.212 | 0.136 |
| 6 | 66.450 | 0.134 |
| 8 | 88.403 | 0.084 |
| 16 | 176.736 | 0.059 |
| 32 | 353.433 | 0.061 |
| 64 | 706.816 | 0.076 |

The retpoline call-only baseline is:

```text
none/workload=0 delta = 41.860 cycles/iteration
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
| work_only | 2 | 22.144 | 22.144 | -0.001 | 0.004 | -0.00 |
| work_only | 3 | 33.118 | 33.118 | 0.000 | 0.126 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.000 | 0.135 | 0.00 |
| work_only | 5 | 55.273 | 55.213 | -0.062 | 0.138 | -0.11 |
| work_only | 6 | 66.425 | 66.445 | 0.026 | 0.134 | 0.04 |
| work_only | 8 | 88.404 | 88.385 | -0.019 | 0.102 | -0.02 |
| work_only | 16 | 176.731 | 176.731 | 0.001 | 0.103 | 0.00 |
| work_only | 32 | 353.425 | 353.442 | 0.018 | 0.058 | 0.01 |
| work_only | 64 | 706.799 | 706.798 | -0.001 | 0.071 | -0.00 |
| before | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| before | 1 | 12.093 | 12.102 | 0.011 | 0.043 | 0.09 |
| before | 2 | 23.290 | 23.170 | -0.121 | 0.096 | -0.52 |
| before | 3 | 34.231 | 34.302 | 0.071 | 0.136 | 0.21 |
| before | 4 | 45.371 | 45.309 | -0.061 | 0.139 | -0.13 |
| before | 5 | 56.447 | 56.563 | 0.119 | 0.145 | 0.21 |
| before | 6 | 67.483 | 67.541 | 0.003 | 0.255 | 0.00 |
| before | 8 | 89.511 | 89.541 | 0.044 | 0.093 | 0.05 |
| before | 16 | 177.976 | 177.877 | -0.101 | 0.274 | -0.06 |
| before | 32 | 354.663 | 354.656 | -0.002 | 0.125 | -0.00 |
| before | 64 | 707.945 | 708.028 | 0.096 | 0.087 | 0.01 |
| inside | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| inside | 1 | 12.069 | 12.057 | -0.013 | 0.001 | -0.11 |
| inside | 2 | 23.130 | 23.137 | 0.008 | 0.065 | 0.03 |
| inside | 3 | 34.222 | 34.178 | -0.044 | 0.132 | -0.13 |
| inside | 4 | 45.271 | 45.264 | -0.007 | 0.199 | -0.02 |
| inside | 5 | 56.349 | 56.362 | -0.013 | 0.105 | -0.02 |
| inside | 6 | 67.404 | 67.361 | -0.033 | 0.137 | -0.05 |
| inside | 8 | 89.449 | 89.518 | 0.064 | 0.097 | 0.07 |
| inside | 16 | 177.755 | 177.820 | 0.065 | 0.102 | 0.04 |
| inside | 32 | 354.462 | 354.500 | 0.036 | 0.044 | 0.01 |
| inside | 64 | 707.856 | 707.895 | 0.049 | 0.085 | 0.01 |
| after | 0 | 3.011 | 4.014 | 1.003 | 0.001 | 33.31 |
| after | 1 | 12.124 | 12.101 | -0.022 | 0.005 | -0.18 |
| after | 2 | 24.083 | 24.108 | 0.025 | 0.023 | 0.10 |
| after | 3 | 34.231 | 34.233 | 0.002 | 0.071 | 0.01 |
| after | 4 | 46.310 | 46.250 | -0.060 | 0.144 | -0.13 |
| after | 5 | 56.409 | 56.315 | -0.096 | 0.146 | -0.17 |
| after | 6 | 68.496 | 68.375 | -0.127 | 0.134 | -0.19 |
| after | 8 | 90.429 | 90.476 | 0.055 | 0.102 | 0.06 |
| after | 16 | 178.886 | 178.761 | -0.123 | 0.070 | -0.07 |
| after | 32 | 355.698 | 355.485 | -0.202 | 0.108 | -0.06 |
| after | 64 | 708.968 | 708.883 | -0.082 | 0.065 | -0.01 |

### 4.3 retpoline

| placement | workload | direct | pgot | delta | IQR | overhead% |
|---|---:|---:|---:|---:|---:|---:|
| none | 0 | 3.011 | 44.871 | 41.860 | 4.013 | 1390.24 |
| work_only | 0 | 1.004 | 1.004 | 0.000 | 0.000 | 0.00 |
| work_only | 1 | 11.115 | 11.115 | 0.000 | 0.003 | 0.00 |
| work_only | 2 | 22.145 | 22.144 | 0.000 | 0.003 | 0.00 |
| work_only | 3 | 33.118 | 33.119 | 0.000 | 0.066 | 0.00 |
| work_only | 4 | 44.163 | 44.163 | 0.001 | 0.135 | 0.00 |
| work_only | 5 | 55.212 | 55.212 | 0.000 | 0.136 | 0.00 |
| work_only | 6 | 66.450 | 66.426 | -0.017 | 0.134 | -0.03 |
| work_only | 8 | 88.403 | 88.388 | -0.025 | 0.084 | -0.03 |
| work_only | 16 | 176.736 | 176.732 | -0.009 | 0.059 | -0.01 |
| work_only | 32 | 353.433 | 353.425 | -0.012 | 0.061 | -0.00 |
| work_only | 64 | 706.816 | 706.801 | -0.023 | 0.076 | -0.00 |
| before | 0 | 3.011 | 42.146 | 39.135 | 0.074 | 1299.73 |
| before | 1 | 12.096 | 42.858 | 30.770 | 1.458 | 254.38 |
| before | 2 | 23.291 | 43.241 | 19.951 | 0.197 | 85.66 |
| before | 3 | 34.231 | 52.180 | 17.948 | 0.144 | 52.43 |
| before | 4 | 45.371 | 54.257 | 8.887 | 0.227 | 19.59 |
| before | 5 | 56.507 | 58.201 | 1.682 | 1.877 | 2.98 |
| before | 6 | 67.535 | 67.273 | -0.249 | 0.297 | -0.37 |
| before | 8 | 89.511 | 89.472 | -0.015 | 0.108 | -0.02 |
| before | 16 | 177.960 | 178.227 | 0.249 | 0.255 | 0.14 |
| before | 32 | 354.666 | 354.796 | 0.127 | 0.081 | 0.04 |
| before | 64 | 707.961 | 708.061 | 0.091 | 0.088 | 0.01 |
| inside | 0 | 3.011 | 42.212 | 39.200 | 4.013 | 1301.89 |
| inside | 1 | 12.069 | 43.024 | 30.954 | 0.071 | 256.48 |
| inside | 2 | 23.130 | 45.219 | 22.089 | 0.430 | 95.50 |
| inside | 3 | 34.223 | 45.425 | 11.202 | 2.503 | 32.73 |
| inside | 4 | 45.262 | 48.466 | 3.272 | 1.465 | 7.23 |
| inside | 5 | 56.317 | 56.313 | -0.047 | 0.158 | -0.08 |
| inside | 6 | 67.420 | 67.334 | -0.053 | 0.136 | -0.08 |
| inside | 8 | 89.446 | 89.454 | 0.014 | 0.089 | 0.02 |
| inside | 16 | 177.756 | 177.885 | 0.137 | 0.094 | 0.08 |
| inside | 32 | 354.463 | 354.611 | 0.143 | 0.067 | 0.04 |
| inside | 64 | 707.851 | 707.974 | 0.118 | 0.096 | 0.02 |
| after | 0 | 3.011 | 42.146 | 39.135 | 0.072 | 1299.73 |
| after | 1 | 12.124 | 48.516 | 36.457 | 0.073 | 300.70 |
| after | 2 | 24.083 | 49.170 | 25.087 | 0.091 | 104.17 |
| after | 3 | 34.232 | 50.491 | 16.260 | 0.736 | 47.50 |
| after | 4 | 46.309 | 51.120 | 4.713 | 0.224 | 10.18 |
| after | 5 | 56.415 | 56.231 | -0.191 | 0.141 | -0.34 |
| after | 6 | 68.499 | 68.280 | -0.219 | 0.137 | -0.32 |
| after | 8 | 90.430 | 90.395 | -0.042 | 0.072 | -0.05 |
| after | 16 | 178.887 | 178.851 | -0.026 | 0.111 | -0.01 |
| after | 32 | 355.691 | 355.652 | -0.038 | 0.151 | -0.01 |
| after | 64 | 708.963 | 708.949 | -0.031 | 0.269 | -0.00 |

### 4.4 Placement Ordering Under Retpoline

| workload | work_only cycles | before delta | inside delta | after delta | ordering by visible overhead |
|---:|---:|---:|---:|---:|---|
| 0 | 1.004 | 39.135 | 39.200 | 39.135 | inside > before > after |
| 1 | 11.115 | 30.770 | 30.954 | 36.457 | after > inside > before |
| 2 | 22.145 | 19.951 | 22.089 | 25.087 | after > inside > before |
| 3 | 33.118 | 17.948 | 11.202 | 16.260 | before > after > inside |
| 4 | 44.163 | 8.887 | 3.272 | 4.713 | before > after > inside |
| 5 | 55.212 | 1.682 | -0.047 | -0.191 | before > inside > after |
| 6 | 66.450 | -0.249 | -0.053 | -0.219 | inside > after > before |
| 8 | 88.403 | -0.015 | 0.014 | -0.042 | inside > before > after |
| 16 | 176.736 | 0.249 | 0.137 | -0.026 | before > inside > after |
| 32 | 353.433 | 0.127 | 0.143 | -0.038 | inside > before > after |
| 64 | 706.816 | 0.091 | 0.118 | -0.031 | inside > before > after |

This ordering table is computed mechanically from the current data. It should
be interpreted together with repeatability checks. The stable claim is the
threshold behavior, not a universal before/inside/after ordering across every
workload.

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


## 9. Stability Check With Fine-Grained Workloads


This repeats the revised experiment with `work_only` and workload grid `0,1,2,3,4,5,6,8,16,32,64` for five independent campaigns. Each campaign uses `ITERATIONS=100000`, `REPEATS=15`, and `OUTER_RUNS=3`, so each case has 45 paired samples per campaign.

## Retpoline Stability Summary

| workload | work_only cycles | before median [min,max] | inside median [min,max] | after median [min,max] | ordering stable? | dominant ordering | all abs(delta)<=1 runs |
|---:|---:|---:|---:|---:|---|---|---:|
| 0 | 1.004 | 39.135 [39.135,39.205] | 39.135 [39.135,39.205] | 39.135 [39.135,39.136] | no | before>inside>after (3/5) | 0/5 |
| 1 | 11.115 | 30.859 [30.681,31.063] | 31.021 [30.955,33.020] | 36.457 [36.392,36.460] | no | after>inside>before (4/5) | 0/5 |
| 2 | 22.145 | 19.886 [19.884,19.949] | 22.093 [22.028,22.103] | 25.087 [25.087,25.153] | yes | after>inside>before (5/5) | 0/5 |
| 3 | 33.118 | 13.416 [13.366,18.015] | 11.943 [11.122,12.238] | 16.271 [16.195,16.568] | no | after>before>inside (4/5) | 0/5 |
| 4 | 44.163 | 0.541 [0.496,0.715] | 3.205 [3.059,3.890] | 4.054 [3.981,4.576] | yes | after>inside>before (5/5) | 0/5 |
| 5 | 55.214 | 1.687 [1.684,1.827] | -0.063 [-0.138,-0.047] | -0.085 [-0.186,-0.068] | no | before>inside>after (4/5) | 0/5 |
| 6 | 66.436 | -0.210 [-0.277,0.240] | -0.051 [-0.068,-0.043] | -0.223 [-0.229,-0.161] | no | inside>after>before (3/5) | 5/5 |
| 8 | 88.397 | -0.051 [-0.059,-0.017] | 0.021 [0.014,0.040] | -0.028 [-0.033,-0.016] | no | inside>after>before (4/5) | 5/5 |
| 16 | 176.732 | 0.259 [0.235,0.270] | 0.121 [0.117,0.130] | -0.021 [-0.042,-0.013] | yes | before>inside>after (5/5) | 5/5 |
| 32 | 353.428 | 0.114 [0.110,0.136] | 0.155 [0.148,0.167] | -0.023 [-0.075,0.013] | yes | inside>before>after (5/5) | 5/5 |
| 64 | 706.804 | 0.087 [0.080,0.101] | 0.109 [0.091,0.131] | -0.015 [-0.027,0.029] | no | inside>before>after (4/5) | 5/5 |

## Key Observations

1. The first workload where all five campaigns have all three placement deltas within +/-1 cycle is `6`.
2. Low workloads show stable large retpoline visible overhead, but the exact placement ordering is not globally constant across all workloads.
3. The refined grid shows the transition more clearly: workload 3/4/5 are the sensitive region where some placements have already become small while others can still expose overhead.
4. The stable paper claim should therefore be threshold-based, not a universal ordering such as before > inside > after for every workload.

Full CSV: `stability/stability_summary_retpoline_v2.csv`.

<!-- fence-diagnostics:start -->
## 10. Fence Diagnostics


This diagnostic keeps the same Layer2 func-placement benchmark, but rebuilds
the retpoline module with progressively stronger `lfence` boundaries.

| mode | compile-time fence |
|---|---|
| `unfenced` | none |
| `post_fenced` | `lfence` after each direct/pgot call event |
| `iter_fenced` | `lfence` at the end of each benchmark iteration |
| `pre_post_iter_fenced` | `lfence` before call, after call, and at iteration end |

Parameters: `iterations=100000`, `repeats=15`,
`outer_runs=3`, `sample_order=interleave`.

## Summary Table

| fence mode | call-only Δ | first workload with all |Δ|<=1 | before Δ@4 | inside Δ@4 | after Δ@4 | before Δ@6 | inside Δ@6 | after Δ@6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| unfenced | 39.135 | 6 | 0.515 | 3.752 | 4.740 | -0.123 | -0.057 | -0.174 |
| post_fenced | 26.693 | not reached | 4.496 | 34.201 | 3.363 | 2.822 | 31.055 | 1.480 |
| iter_fenced | 26.731 | not reached | 5.488 | 34.192 | 33.488 | 2.570 | 30.831 | 32.554 |
| pre_post_iter_fenced | 28.502 | not reached | 28.154 | 32.841 | 27.615 | 26.905 | 31.922 | 27.330 |

## Full Delta Tables

### unfenced

| workload | work-only cycles | before Δ | inside Δ | after Δ |
|---:|---:|---:|---:|---:|
| 0 | 1.004 | 39.135 | 39.135 | 39.135 |
| 1 | 11.115 | 30.497 | 31.172 | 36.392 |
| 2 | 22.145 | 19.885 | 20.512 | 25.087 |
| 3 | 33.119 | 17.949 | 11.999 | 16.274 |
| 4 | 44.163 | 0.515 | 3.752 | 4.740 |
| 5 | 55.274 | 1.693 | -0.046 | -0.071 |
| 6 | 66.429 | -0.123 | -0.057 | -0.174 |
| 8 | 88.404 | -0.053 | 0.022 | -0.024 |
| 16 | 176.736 | 0.257 | 0.136 | -0.037 |
| 32 | 353.429 | 0.111 | 0.167 | -0.039 |
| 64 | 706.808 | 0.091 | 0.113 | -0.014 |

### post_fenced

| workload | work-only cycles | before Δ | inside Δ | after Δ |
|---:|---:|---:|---:|---:|
| 0 | 1.004 | 26.693 | 26.693 | 26.708 |
| 1 | 11.115 | 26.927 | 32.803 | 26.853 |
| 2 | 22.144 | 19.567 | 32.354 | 20.696 |
| 3 | 33.118 | 18.106 | 34.371 | 14.104 |
| 4 | 44.163 | 4.496 | 34.201 | 3.363 |
| 5 | 55.270 | 6.595 | 33.037 | 5.055 |
| 6 | 66.449 | 2.822 | 31.055 | 1.480 |
| 8 | 88.397 | 1.742 | 32.347 | 3.001 |
| 16 | 176.735 | 4.796 | 32.217 | 3.113 |
| 32 | 353.434 | 4.950 | 32.383 | 2.870 |
| 64 | 706.805 | 5.052 | 30.594 | 3.068 |

### iter_fenced

| workload | work-only cycles | before Δ | inside Δ | after Δ |
|---:|---:|---:|---:|---:|
| 0 | 14.250 | 26.731 | 26.706 | 26.694 |
| 1 | 22.678 | 26.621 | 32.847 | 34.393 |
| 2 | 33.717 | 19.574 | 32.429 | 33.642 |
| 3 | 45.156 | 16.571 | 34.135 | 34.512 |
| 4 | 55.868 | 5.488 | 34.192 | 33.488 |
| 5 | 66.871 | 5.140 | 33.499 | 34.525 |
| 6 | 78.339 | 2.570 | 30.831 | 32.554 |
| 8 | 102.053 | 1.969 | 30.642 | 32.667 |
| 16 | 188.263 | 5.289 | 32.379 | 33.428 |
| 32 | 365.382 | 5.260 | 32.412 | 33.331 |
| 64 | 718.507 | 4.791 | 32.487 | 35.458 |

### pre_post_iter_fenced

| workload | work-only cycles | before Δ | inside Δ | after Δ |
|---:|---:|---:|---:|---:|
| 0 | 14.249 | 28.502 | 28.555 | 29.044 |
| 1 | 22.678 | 29.790 | 36.877 | 26.586 |
| 2 | 33.717 | 25.021 | 34.130 | 25.577 |
| 3 | 45.156 | 28.250 | 33.423 | 25.575 |
| 4 | 55.912 | 28.154 | 32.841 | 27.615 |
| 5 | 66.888 | 27.287 | 30.867 | 25.568 |
| 6 | 78.468 | 26.905 | 31.922 | 27.330 |
| 8 | 101.883 | 30.724 | 30.985 | 27.476 |
| 16 | 188.145 | 27.770 | 29.939 | 26.735 |
| 32 | 365.371 | 26.192 | 30.936 | 29.709 |
| 64 | 718.531 | 26.814 | 29.742 | 31.070 |

## Static Fence Validation

| mode | DIRECT after_4 lfence/call | PGOT after_4 lfence/call/pause | interpretation |
|---|---:|---:|---|
| unfenced | 0/1 | 1/2/1 | only the retpoline thunk contributes the PGOT-side lfence; PGOT has 1 extra lfence from retpoline thunk |
| post_fenced | 1/1 | 2/2/1 | adds one post-call lfence to both direct and PGOT; PGOT has 1 extra lfence from retpoline thunk |
| iter_fenced | 1/1 | 2/2/1 | adds one end-of-iteration lfence to both direct and PGOT; PGOT has 1 extra lfence from retpoline thunk |
| pre_post_iter_fenced | 3/1 | 4/2/1 | adds pre-call, post-call, and end-of-iteration lfences; PGOT has 1 extra lfence from retpoline thunk |

## Diagnostic Interpretation

The important comparison is within each fence mode, not the absolute call-only
number across modes, because adding `lfence` changes both the direct and PGOT
instruction streams.

1. In the unfenced practical stream, all placements reach `|Δ| <= 1` at
   workload 6.
2. In the strongest `pre_post_iter_fenced` mode, the threshold is not reached:
   before/inside/after remain around 26-32 cycles even at large workloads.
3. Therefore, workload does not make the retpoline thunk itself faster. The
   main-experiment collapse requires the unfenced whole-loop execution context.
4. The intermediate modes separate the context effects. `post_fenced` keeps
   inside high but lets before/after become small; `iter_fenced` keeps
   inside/after high but lets before become small. This shows that the visible
   delta depends on where the work sits relative to call boundaries and
   iteration boundaries, plus the resulting caller/callee code layout.
5. The defensible causal statement is: the decreasing retpoline `Δcycles` is a
   whole-loop visible-overhead effect caused by unfenced surrounding work,
   cross-iteration steady state, and code-layout/caller-callee shape. It is not
   evidence that target instructions execute before the retpoline transfer is
   complete.

Full diagnostic report: `diagnostics/fence_modes/summary.md`.
<!-- fence-diagnostics:end -->
