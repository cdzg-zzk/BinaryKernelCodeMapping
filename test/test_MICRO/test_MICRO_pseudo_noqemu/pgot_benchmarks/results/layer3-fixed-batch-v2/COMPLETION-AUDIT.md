# Completion audit against the requested Layer-3 revision

This audit covers the pasted task's ten deliverables and its measurement,
interpretation and preservation constraints. Current evidence was inspected;
completion is not inferred from collector status alone.

| Requirement | Authoritative evidence inspected | Result |
|---|---|---|
| 1. Audit original sources, timed regions, generators, builds, selection and binaries before changes | `AUDIT.md`, `prechange/` benchmark/generator/run.sh snapshots and both archived-KO disassemblies; saved old selector | Complete. SHA missing validation, result-provenance mismatch and outcome-dependent selection are explicit. |
| 2. Full original batch scan and deterministic baseline-only selection | 72 rows in `complete-scan.csv`; 216 outer rows; every original 3-by-31 grid checked; 6,006 independent timestamp samples; `batch-selection-evidence.csv`, `fixed-batches.json` | Complete. SHA4096/BCH64/zlib16/Zstd16; both builds and all variants share each value. Three methodology tests pass, including treatment-value mutation and failure without a qualifying candidate. |
| 3. Reanalyze archive before confirmation and compare historical/fixed results | Frozen configuration predates confirmation; `historical-vs-fixed.csv` has 20 rows, historical reported values, available raw reaggregated at old choices, and fixed-batch values, costs, deltas and outer ranges | Complete. Missing outer provenance for the historical selected report is explicitly marked unavailable; no observations are invented. All six requested qualitative questions are answered in the final assessment. |
| 4. Outer-run repetition and balanced within-load pairing | Source ABBA/BAAB loops, `sessions.json`, 64 per-load logs/JSONs, 160 outer comparison estimates, collector build-order reversal | Complete. Eight module loads per routine/build, 15 pairs per applicable comparison; outer-run bootstrap, not pooled inner trials. |
| 5. Targeted confirmation and correctness | All 64 logs independently matched to raw CSV records and corresponding KO hashes, arguments, loaded/unloaded state and success messages; 2,400 inner pairs | Complete. Only frozen batches run. SHA state plus known-digest check and all original BCH/zlib/Zstd comparisons pass outside timing. |
| 6. Full ablation tables | 20 comparison rows in confirmatory `ablation.csv`, 40 paired backend rows in `origin-and-variants.csv`, both builds and all four routines | Complete. SHA has only the applicable Data comparison. Paired Origin cost is preserved separately for each intervention. |
| 7. Two-panel figure PDF, PNG and source | Both actual renders inspected; `figures/ablation.pdf`, `.png`, `plot_layer3_v2.py`, exact plot CSVs and manifest | Complete. Grayscale/hatching; signed axis and zero baseline; every outer point including the BCH outlier; confidence intervals use outer resampling. PDF embeds TrueType fonts. |
| 8. Mechanism evidence and separate diagnostics | `MECHANISM-EVIDENCE.md`, 28 variant/build object summaries, 878 binding references, helper source inventory, function-size comparison and zlib diffs; all inline pause/lfence/stack-target/ret sequences checked | Complete. SHA introduces no indirect path; BCH's four memcpy sites verified direct/indirect/protected; Zstd helper bindings and protected paths recorded; zlib existing dispatch and broader codegen differences documented. |
| BCH non-timed executed-site check | Separate `diagnostics/` KOs/logs, 32 counter rows (four sites x four variants x two builds), each count 1 | Complete. No timing records in diagnostic logs; no diagnostic symbols/flags in any formal object. |
| 9. Reproducibility and preservation | README one-command regeneration executed successfully; raw/source/config/object hashes checked; compiler/flags/kernel/boot/git/worktree metadata; final scripts in `analysis-source/` | Complete. All 323 historical files unchanged; source and built-object identities match; analysis/plot source supplied. |
| 10. Final interpretation and missing-measurement assessment | `../layer3-confirmatory-v2/FINAL-ASSESSMENT.md` and three-way comparison CSV | Complete. Archive BCH findings change materially; confirmation supports retpoline helper dominance for BCH/Zstd, with BCH no-retpoline variability retained. zlib's negative result is observed but not called an intrinsic optimization. No required formal measurement is pending. |
| Fixed workload, execution domain and timed-region preservation | Benchmark diff, captured source, actual build flags | Complete. No page grafting, export campaign, syscalls or carrier loading mixed into this experiment. Workload loops and existing resets remain unchanged. |
| No paper edits | Paper diff section compared byte-for-byte with pre-revision `worktree-before.patch` | Complete. Pre-existing manuscript modifications are preserved. |
| Runtime cleanup | `/sys/module/bench_kmod` and `/sys/module/pgot_timestamp` absent after runs | Complete. |

The no-retpoline BCH load-specific data-path slowdown and the exact cause of
zlib's small negative aggregate delta remain scientific interpretation limits,
not omitted required experiments. No extra sweep or result-driven retuning was
used to remove those observations. The completed evidence supports the
qualified conclusions stated in the final assessment.

Machine-readable verification: `verification.json`. Methodology test output:
`methodology-tests.txt`. Reproduction command: `python3 scripts/reproduce_layer3_v2.py`
from the benchmark directory (with the documented Python dependencies).
