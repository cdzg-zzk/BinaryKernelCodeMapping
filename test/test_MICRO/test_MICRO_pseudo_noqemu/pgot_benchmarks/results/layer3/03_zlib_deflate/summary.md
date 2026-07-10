# Layer3 zlib Deflate Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel zlib deflate closure from lib/zlib_deflate/deflate.c and deftree.c into the LKM and compares:

| variant | transformation |
|---|---|
| origin | copied deflate closure, direct static tables, direct memcpy/memset |
| all_pgot | data_pgot + func_pgot |

Internal zlib helpers copied into the closure remain direct calls. The function pointer entries inside configuration_table are treated as table contents; the PGOT transformation is the table-base load, not converting deflate_fast/slow into separate external func-PGOT callsites.

The module validates origin/data/func/all by compressing the same input once and comparing return code, output length, and compressed bytes before any timing data is emitted.

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 16 | 93 | 27658.312 | 27532.593 | -171.187 | 302.406 | 1.77 | -0.62 |
| no_retpoline | data_pgot | 32 | 93 | 27629.359 | 27498.234 | -123.251 | 203.235 | 1.65 | -0.45 |
| no_retpoline | data_pgot | 64 | 93 | 27853.327 | 27748.640 | -12.946 | 631.165 | 48.75 | -0.05 |
| no_retpoline | func_pgot | 16 | 93 | 27674.906 | 27603.687 | -158.562 | 590.469 | 3.72 | -0.57 |
| no_retpoline | func_pgot | 32 | 93 | 27602.562 | 27429.577 | -269.860 | 704.859 | 2.61 | -0.98 |
| no_retpoline | func_pgot | 64 | 93 | 27836.609 | 27432.351 | -200.593 | 590.750 | 2.95 | -0.72 |
| no_retpoline | all_pgot | 16 | 93 | 27671.249 | 27894.125 | 255.188 | 522.032 | 2.05 | 0.92 |
| no_retpoline | all_pgot | 32 | 93 | 27592.250 | 27902.515 | 274.796 | 191.781 | 0.70 | 1.00 |
| no_retpoline | all_pgot | 64 | 93 | 27726.366 | 27699.265 | 157.218 | 448.070 | 2.85 | 0.57 |
| retpoline | data_pgot | 16 | 93 | 27488.249 | 27920.437 | 444.187 | 179.906 | 0.41 | 1.62 |
| retpoline | data_pgot | 32 | 93 | 27409.359 | 28040.406 | 576.610 | 259.297 | 0.45 | 2.10 |
| retpoline | data_pgot | 64 | 93 | 27521.749 | 28182.577 | 541.047 | 485.156 | 0.90 | 1.97 |
| retpoline | func_pgot | 16 | 93 | 27483.687 | 27408.906 | -99.375 | 190.938 | 1.92 | -0.36 |
| retpoline | func_pgot | 32 | 93 | 27387.531 | 27362.687 | -39.328 | 257.079 | 6.54 | -0.14 |
| retpoline | func_pgot | 64 | 93 | 27464.398 | 27385.492 | -123.836 | 627.336 | 5.07 | -0.45 |
| retpoline | all_pgot | 16 | 93 | 27486.906 | 27270.750 | -199.094 | 204.595 | 1.03 | -0.72 |
| retpoline | all_pgot | 32 | 93 | 27396.281 | 27285.828 | -106.656 | 165.344 | 1.55 | -0.39 |
| retpoline | all_pgot | 64 | 93 | 27504.757 | 27252.538 | -201.047 | 541.157 | 2.69 | -0.73 |

## Static Validation

| check | expected evidence |
|---|---|
| all_pgot | both data-table slots and memcpy/memset slots are referenced |
| retpoline | retpoline objdump contains inline thunk markers for func/all indirect memcpy/memset calls |

See static/objdump_*.txt and static/nm_*.txt for the complete disassembly evidence.
