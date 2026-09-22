# Layer-3 fixed-batch final assessment

All four routines, both builds and all applicable ablations have completed formal timing: 64 module loads, 2,400 paired inner records and 160 outer-run comparison estimates. No formal measurements are pending. Each configuration uses eight module loads and 15 paired ABBA/BAAB rounds per comparison. Reported costs are TSC ticks per operation.

## Historical reconstruction and new confirmation

The historical selected report does not match the available raw archive in any of its 20 rows. Its percentages are retained as reported values; the available raw data are the source for the fixed-batch reconstruction. Changes between these columns cannot all be attributed to batch selection. `../layer3-fixed-batch-v2/historical-vs-fixed.csv` also applies the old batch choices to the available raw data, separating selection changes from provenance differences.

| Routine | Build | Variant | Historical report (%) | Fixed-batch archive (%) | Confirmatory (%) | 95% CI | Outer-run range (%) |
|---|---|---|---:|---:|---:|---|---|
| sha256_transform | no_retpoline | data_pgot | +0.040 | +0.001 | -0.029 | [-0.179, +0.022] | [-0.220, +0.183] |
| sha256_transform | retpoline | data_pgot | -0.074 | +0.050 | -0.048 | [-0.074, +0.058] | [-0.125, +0.221] |
| bch_encode | no_retpoline | data_pgot | +0.480 | +4.309 | +0.513 | [+0.471, +0.990] | [+0.428, +16.593] |
| bch_encode | no_retpoline | func_pgot | +1.368 | +1.353 | +1.312 | [+1.267, +1.364] | [+1.248, +1.396] |
| bch_encode | no_retpoline | all_pgot | +1.976 | +6.329 | +1.945 | [+1.859, +2.359] | [+1.842, +17.000] |
| bch_encode | retpoline | data_pgot | +0.592 | +7.152 | +0.514 | [+0.425, +0.737] | [+0.410, +0.751] |
| bch_encode | retpoline | func_pgot | +2.746 | +2.835 | +2.944 | [+2.677, +3.032] | [+2.589, +3.096] |
| bch_encode | retpoline | all_pgot | +3.252 | +9.648 | +3.408 | [+3.266, +3.567] | [+3.229, +3.647] |
| zlib_deflate | no_retpoline | data_pgot | +0.466 | -0.315 | -0.418 | [-1.163, +0.126] | [-1.311, +0.519] |
| zlib_deflate | no_retpoline | func_pgot | -0.164 | -0.575 | +0.010 | [-0.856, +0.905] | [-1.494, +1.446] |
| zlib_deflate | no_retpoline | all_pgot | +1.359 | +0.962 | +0.763 | [+0.394, +1.585] | [-1.090, +1.851] |
| zlib_deflate | retpoline | data_pgot | +1.713 | +1.730 | +2.023 | [+0.742, +2.705] | [+0.129, +3.208] |
| zlib_deflate | retpoline | func_pgot | -0.065 | -0.362 | +0.044 | [-0.686, +0.781] | [-1.674, +1.261] |
| zlib_deflate | retpoline | all_pgot | -0.658 | -0.579 | -0.750 | [-0.863, -0.628] | [-2.012, -0.460] |
| zstd_decompress | no_retpoline | data_pgot | -0.278 | -0.411 | -0.266 | [-0.378, -0.186] | [-0.450, +0.232] |
| zstd_decompress | no_retpoline | func_pgot | +0.329 | +0.225 | +0.336 | [+0.253, +0.515] | [+0.220, +0.646] |
| zstd_decompress | no_retpoline | all_pgot | +1.383 | +1.250 | +1.536 | [+1.301, +1.610] | [+1.264, +1.964] |
| zstd_decompress | retpoline | data_pgot | -0.313 | -0.190 | -0.158 | [-0.316, -0.076] | [-0.480, -0.064] |
| zstd_decompress | retpoline | func_pgot | +7.251 | +7.789 | +7.560 | [+7.452, +7.603] | [+7.203, +7.728] |
| zstd_decompress | retpoline | all_pgot | +6.230 | +6.624 | +6.551 | [+6.446, +7.058] | [+6.304, +7.792] |

## Answers to the prespecified interpretation questions

1. **SHA-256 remains close to Origin.** The archive and confirmatory medians are below 0.1% in magnitude in both builds. Confirmatory outer-bootstrap intervals cross zero. The archived SHA benchmark had no explicit output check; the new run validates both transform states and the padded-block digest outside timing.

2. **BCH no-retpoline requires a variability qualification.** The fixed-batch archive gives 6.329% All-PGOT, rather than the historical reported 1.976%. The confirmation median is 1.945% with a 95% median CI of [1.859%, 2.359%], but one of eight loads reaches 17.000%. Data-PGOT rises to 16.593% in that same load (run_id=6), whereas Func-PGOT stays at 1.286% and paired Origin costs remain about 5,490 ticks. Every load is retained. A small median does not establish uniformly small per-load cost. The source of this load-specific data-path slowdown is not established by the collected diagnostics.

3. **BCH retpoline: the archive does not preserve Func dominance; the confirmation does.** Archive Data/Func/All medians are 7.152/2.835/9.648%. In the confirmation they are 0.514/2.944/3.408%; the helper-only intervention reproduces most of the full-adaptation increase. Four rewritten memcpy sites each execute once per encode, and their formal objects contain the protected indirect sequences. This supports helper adaptation as the principal observed contribution in the new retpoline run; it is not a decomposition of the total into a fixed per-thunk price.

4. **Zstd Data-only stays small.** Confirmation Data medians are -0.266% and -0.158%. The no-retpoline Func median is 0.336%, so Data and Func are both small there. Under retpoline the Func and All medians are 7.560% and 6.551%; the corresponding archive values are 7.789% and 6.624%. The helper-only intervention reproduces the substantial retpoline-build increase. Its value exceeding All also shows why ablation deltas cannot be added as independent components.

5. **zlib remains near Origin at the complete-adaptation level, without an optimization claim.** Confirmatory All medians are +0.763% and -0.750%. The retpoline All interval lies below zero in this particular campaign; the sign is reported as observed, not called noise by fiat. Data-only is +2.023% in that build and Func-only +0.044%. This non-additive pattern, together with the machine-code differences documented below, means the negative aggregate result does not establish an intrinsic PGOT speedup. The specific instruction/layout cause of that small change has not been isolated.

6. **The original qualitative story is only partly preserved by reanalysis.** SHA, zlib and retpoline Zstd broadly retain it. BCH in the available archive changes materially; the new campaign recovers small typical BCH costs but also exposes a large no-retpoline load-specific increase. The archived and new results are presented separately.

The confirmatory figure shows all outer-run points alongside the medians and CIs; the large BCH observation is visible. No batch was selected using an adapted cost or delta. Neither cross-build subtraction nor division by helper count is used for causal retpoline attribution. The workloads remain the four fixed inputs specified in the task.

## Evidence locations

- `ablation.csv`: all 20 comparisons with paired Origin/adapted costs, deltas, percentages, ranges and CIs.
- `origin-and-variants.csv`: explicit backend rows, with Origin retained per comparison.
- `outer-runs.csv`, per-routine `raw.csv`, logs and `sessions.json`: all repetition levels.
- `figures/ablation.pdf` and `.png`: two-panel grayscale ablation figure.
- `MECHANISM-EVIDENCE.md`, `static-evidence/` and `diagnostics/`: source/object and non-timed execution evidence.
- `../layer3-fixed-batch-v2/README.md`: reproduction and artifact map.

Historical data are preserved and paper prose has not been edited in this revision.
