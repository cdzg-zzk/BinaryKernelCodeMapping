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
