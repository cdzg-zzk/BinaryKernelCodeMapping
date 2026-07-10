# Layer3 ZSTD Decompress Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel zstd decompression closure into the LKM: decompress.c, huf_decompress.c, fse_decompress.c, entropy_common.c, and zstd_common.c.

| variant | transformation |
|---|---|
| origin | copied decompression closure, direct static tables, direct memcpy/memset/memmove |
| all_pgot | data_pgot + func_pgot |

Internal ZSTD/HUF/FSE helpers copied into the closure remain direct calls. The module validates origin/data/func/all by decompressing the same frame and comparing return code, output length, and output bytes before timing.

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 16 | 93 | 6314.687 | 6297.031 | -22.000 | 52.406 | 2.38 | -0.35 |
| no_retpoline | data_pgot | 32 | 93 | 6294.109 | 6280.250 | -13.453 | 35.671 | 2.65 | -0.21 |
| no_retpoline | data_pgot | 64 | 93 | 6290.398 | 6269.367 | -21.000 | 58.985 | 2.81 | -0.33 |
| no_retpoline | data_pgot | 128 | 93 | 6275.452 | 6262.999 | -11.520 | 21.792 | 1.89 | -0.18 |
| no_retpoline | data_pgot | 256 | 93 | 6275.122 | 6261.974 | -13.201 | 32.916 | 2.49 | -0.21 |
| no_retpoline | func_pgot | 16 | 93 | 6309.562 | 6324.968 | 14.656 | 39.969 | 2.73 | 0.23 |
| no_retpoline | func_pgot | 32 | 93 | 6293.062 | 6326.124 | 36.032 | 50.079 | 1.39 | 0.57 |
| no_retpoline | func_pgot | 64 | 93 | 6291.992 | 6303.546 | 14.195 | 60.211 | 4.24 | 0.23 |
| no_retpoline | func_pgot | 128 | 93 | 6275.101 | 6296.331 | 21.511 | 27.668 | 1.29 | 0.34 |
| no_retpoline | func_pgot | 256 | 93 | 6275.911 | 6298.579 | 22.851 | 41.392 | 1.81 | 0.36 |
| no_retpoline | all_pgot | 16 | 93 | 6302.781 | 6384.656 | 81.313 | 39.220 | 0.48 | 1.29 |
| no_retpoline | all_pgot | 32 | 93 | 6290.796 | 6365.781 | 72.015 | 41.297 | 0.57 | 1.14 |
| no_retpoline | all_pgot | 64 | 93 | 6289.968 | 6353.414 | 69.633 | 66.257 | 0.95 | 1.11 |
| no_retpoline | all_pgot | 128 | 93 | 6273.136 | 6350.159 | 75.949 | 34.075 | 0.45 | 1.21 |
| no_retpoline | all_pgot | 256 | 93 | 6273.519 | 6348.507 | 76.930 | 50.864 | 0.66 | 1.23 |
| retpoline | data_pgot | 16 | 93 | 6302.437 | 6293.406 | -5.812 | 51.376 | 8.84 | -0.09 |
| retpoline | data_pgot | 32 | 93 | 6290.453 | 6269.828 | -19.250 | 36.938 | 1.92 | -0.31 |
| retpoline | data_pgot | 64 | 93 | 6279.069 | 6262.077 | -14.820 | 35.336 | 2.38 | -0.24 |
| retpoline | data_pgot | 128 | 93 | 6289.019 | 6255.855 | -29.160 | 56.864 | 1.95 | -0.46 |
| retpoline | data_pgot | 256 | 93 | 6273.587 | 6272.970 | -5.932 | 59.480 | 10.03 | -0.09 |
| retpoline | func_pgot | 16 | 93 | 6308.468 | 6794.156 | 483.250 | 46.875 | 0.10 | 7.66 |
| retpoline | func_pgot | 32 | 93 | 6290.281 | 6764.499 | 475.422 | 33.266 | 0.07 | 7.56 |
| retpoline | func_pgot | 64 | 93 | 6282.632 | 6763.616 | 483.016 | 74.235 | 0.15 | 7.69 |
| retpoline | func_pgot | 128 | 93 | 6289.343 | 6809.874 | 495.726 | 78.930 | 0.16 | 7.88 |
| retpoline | func_pgot | 256 | 93 | 6278.832 | 6757.447 | 480.920 | 44.299 | 0.09 | 7.66 |
| retpoline | all_pgot | 16 | 93 | 6297.843 | 6709.312 | 416.031 | 48.531 | 0.12 | 6.61 |
| retpoline | all_pgot | 32 | 93 | 6286.437 | 6706.499 | 420.453 | 66.016 | 0.16 | 6.69 |
| retpoline | all_pgot | 64 | 93 | 6279.140 | 6677.976 | 402.813 | 31.805 | 0.08 | 6.42 |
| retpoline | all_pgot | 128 | 93 | 6283.105 | 6675.253 | 391.394 | 60.152 | 0.15 | 6.23 |
| retpoline | all_pgot | 256 | 93 | 6273.373 | 6672.829 | 403.488 | 41.506 | 0.10 | 6.43 |

## Static Validation

| check | expected evidence |
|---|---|
| all_pgot | both data-table slots and memory-helper slots are referenced |
| retpoline | retpoline objdump contains inline thunk markers for func/all indirect memory-helper calls |

See static/objdump_*.txt and static/nm_*.txt for the complete disassembly evidence.
