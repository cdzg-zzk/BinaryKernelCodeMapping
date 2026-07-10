# Layer3 Copied-Closure PGOT Summary

Layer3 copies complete kernel-function closures into LKM benchmarks and compares copied `origin` implementations against `data_pgot`, `func_pgot`, and `all_pgot` variants where applicable.

Correctness is checked inside each module before timing. Each PGOT variant runs on the same input as `origin`; output status, output length, and output bytes must match before raw timing data is emitted.

## Experiments

| experiment | copied closure | variants |
|---|---|---|
| 01_sha256_transform | SHA-256 transform closure | data_pgot |
| 02_bch_encode | BCH encode closure | data_pgot, func_pgot, all_pgot |
| 03_zlib_deflate | zlib deflate.c + deftree.c closure | data_pgot, func_pgot, all_pgot |
| 04_zstd_decompress | zstd decompress + HUF/FSE/common closure | data_pgot, func_pgot, all_pgot |

## Results

| experiment | build | variant | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | overhead% |
|---|---|---|---:|---:|---:|---:|---:|---:|
| sha256 | no_retpoline | data_pgot | 93 | 1315.332 | 1313.483 | -2.514 | 7.397 | -0.19 |
| sha256 | retpoline | data_pgot | 93 | 1315.997 | 1314.122 | -2.333 | 7.166 | -0.18 |
| bch | no_retpoline | data_pgot | 93 | 5426.683 | 6187.374 | 116.563 | 964.839 | 2.15 |
| bch | no_retpoline | func_pgot | 93 | 5427.216 | 5507.794 | 78.679 | 5.924 | 1.45 |
| bch | no_retpoline | all_pgot | 93 | 5426.370 | 6668.159 | 573.627 | 1060.806 | 10.57 |
| bch | retpoline | data_pgot | 93 | 5425.954 | 5518.200 | 92.803 | 15.629 | 1.71 |
| bch | retpoline | func_pgot | 93 | 5425.958 | 5606.325 | 180.564 | 21.104 | 3.33 |
| bch | retpoline | all_pgot | 93 | 5426.080 | 5668.877 | 240.895 | 41.344 | 4.44 |
| zlib | no_retpoline | data_pgot | 93 | 27444.659 | 27368.661 | -49.251 | 144.100 | -0.18 |
| zlib | no_retpoline | func_pgot | 93 | 27442.594 | 27429.529 | -7.835 | 191.732 | -0.03 |
| zlib | no_retpoline | all_pgot | 93 | 27437.180 | 27750.563 | 292.229 | 115.892 | 1.07 |
| zlib | retpoline | data_pgot | 93 | 27363.841 | 27797.630 | 484.636 | 105.131 | 1.77 |
| zlib | retpoline | func_pgot | 93 | 27356.332 | 27349.961 | 53.023 | 168.567 | 0.19 |
| zlib | retpoline | all_pgot | 93 | 27371.352 | 27190.740 | -192.360 | 329.655 | -0.70 |
| zstd | no_retpoline | data_pgot | 93 | 6272.590 | 6262.502 | -10.075 | 15.891 | -0.16 |
| zstd | no_retpoline | func_pgot | 93 | 6271.333 | 6294.841 | 23.799 | 23.355 | 0.38 |
| zstd | no_retpoline | all_pgot | 93 | 6271.029 | 6347.372 | 82.161 | 179.505 | 1.31 |
| zstd | retpoline | data_pgot | 93 | 6273.434 | 6253.531 | -18.084 | 15.498 | -0.29 |
| zstd | retpoline | func_pgot | 93 | 6272.658 | 6731.902 | 462.733 | 20.354 | 7.38 |
| zstd | retpoline | all_pgot | 93 | 6272.679 | 6672.283 | 403.692 | 52.038 | 6.44 |

## Interpretation

The copied-closure results separate real-function behavior from primitive microbenchmarks. Data-PGOT overhead is usually small relative to full-function cost and can be hidden or slightly negative because it changes code generation and scheduling, not only the number of loads. Func-PGOT is most visible when it introduces retpoline-protected indirect calls to closure-external helpers, as shown clearly in zstd retpoline `func_pgot` and `all_pgot`.

BCH no-retpoline `data_pgot` and `all_pgot` have high IQR and should be treated as noisy on this run. The corresponding retpoline rows are much tighter. Per-experiment `summary.md`, `paper_table.csv`, and `static/objdump_*.txt` should be used for detailed reporting.
