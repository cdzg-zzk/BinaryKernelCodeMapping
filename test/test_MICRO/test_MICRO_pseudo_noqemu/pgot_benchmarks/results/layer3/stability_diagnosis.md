# Layer3 Stability Diagnosis

This report is generated from each experiment's `paper_table.csv`.
The key stability metric is `IQR/|Δ|`: lower is better. Rows where `|Δ| < IQR` are not used as strong quantitative evidence.

Stability labels:

| label | meaning |
|---|---|
| strong | `IQR/|Δ| <= 0.25`; good paper result |
| usable | `IQR/|Δ| <= 0.50`; acceptable with IQR reported |
| weak | `IQR/|Δ| <= 1.00`; only cautious interpretation |
| near_zero | tiny delta and tiny IQR; report as no visible overhead |
| indistinguishable | `|Δ| < IQR`; signal is smaller than noise |
| unstable | large spread; not suitable as a main quantitative result |

## 01_sha256_transform / no_retpoline / data_pgot

Selected row: iterations=16384, Δ=0.526, IQR=3.815, label=near_zero.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 4096 | 93 | 1314.993 | 1315.372 | 0.380 | 5.501 | 14.48 | 0.03 | indistinguishable |
| 8192 | 93 | 1314.987 | 1315.732 | 1.027 | 4.459 | 4.34 | 0.08 | indistinguishable |
| 16384 | 93 | 1314.389 | 1314.855 | 0.526 | 3.815 | 7.25 | 0.04 | near_zero |

## 01_sha256_transform / retpoline / data_pgot

Selected row: iterations=16384, Δ=-0.978, IQR=4.451, label=near_zero.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 4096 | 93 | 1315.825 | 1313.057 | -1.404 | 5.612 | 4.00 | -0.11 | indistinguishable |
| 8192 | 93 | 1315.265 | 1315.035 | -0.089 | 5.314 | 59.71 | -0.01 | indistinguishable |
| 16384 | 93 | 1314.575 | 1313.522 | -0.978 | 4.451 | 4.55 | -0.07 | near_zero |

## 02_bch_encode / no_retpoline / data_pgot

Selected row: iterations=128, Δ=26.360, IQR=14.125, label=weak.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5488.023 | 5518.413 | 27.297 | 229.710 | 8.42 | 0.50 | indistinguishable |
| 128 | 93 | 5496.429 | 5519.374 | 26.360 | 14.125 | 0.54 | 0.48 | weak |
| 256 | 93 | 5492.663 | 5525.779 | 33.313 | 346.436 | 10.40 | 0.61 | indistinguishable |

## 02_bch_encode / no_retpoline / func_pgot

Selected row: iterations=64, Δ=75.062, IQR=20.961, label=usable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5488.413 | 5561.663 | 75.062 | 20.961 | 0.28 | 1.37 | usable |
| 128 | 93 | 5499.726 | 5563.390 | 70.941 | 37.633 | 0.53 | 1.29 | weak |
| 256 | 93 | 5492.861 | 5563.325 | 69.369 | 297.924 | 4.29 | 1.26 | indistinguishable |

## 02_bch_encode / no_retpoline / all_pgot

Selected row: iterations=128, Δ=108.746, IQR=33.086, label=usable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5490.796 | 5601.827 | 109.571 | 362.524 | 3.31 | 2.00 | indistinguishable |
| 128 | 93 | 5502.159 | 5604.730 | 108.746 | 33.086 | 0.30 | 1.98 | usable |
| 256 | 93 | 5495.623 | 5611.111 | 116.372 | 365.324 | 3.14 | 2.12 | indistinguishable |

## 02_bch_encode / retpoline / data_pgot

Selected row: iterations=64, Δ=32.523, IQR=67.164, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5491.046 | 5519.116 | 32.523 | 67.164 | 2.07 | 0.59 | indistinguishable |
| 128 | 93 | 5491.292 | 5542.976 | 50.906 | 819.304 | 16.09 | 0.93 | indistinguishable |
| 256 | 93 | 5495.067 | 5768.681 | 23.469 | 160.666 | 6.85 | 0.43 | indistinguishable |

## 02_bch_encode / retpoline / func_pgot

Selected row: iterations=64, Δ=150.789, IQR=10.617, label=strong.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5490.593 | 5643.695 | 150.789 | 10.617 | 0.07 | 2.75 | strong |
| 128 | 93 | 5489.495 | 5656.241 | 165.464 | 32.801 | 0.20 | 3.01 | strong |
| 256 | 93 | 5495.101 | 5829.021 | 163.178 | 130.853 | 0.80 | 2.97 | weak |

## 02_bch_encode / retpoline / all_pgot

Selected row: iterations=64, Δ=178.609, IQR=47.134, label=usable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 64 | 93 | 5492.913 | 5660.585 | 178.609 | 47.134 | 0.26 | 3.25 | usable |
| 128 | 93 | 5491.675 | 5682.218 | 190.007 | 822.595 | 4.33 | 3.46 | indistinguishable |
| 256 | 93 | 5495.423 | 5890.306 | 169.521 | 136.731 | 0.81 | 3.08 | weak |

## 03_zlib_deflate / no_retpoline / data_pgot

Selected row: iterations=32, Δ=128.282, IQR=222.858, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27610.093 | 27615.031 | 48.406 | 316.282 | 6.53 | 0.18 | indistinguishable |
| 32 | 93 | 27513.375 | 27624.655 | 128.282 | 222.858 | 1.74 | 0.47 | indistinguishable |
| 64 | 93 | 27623.765 | 27506.148 | -111.633 | 451.859 | 4.05 | -0.40 | indistinguishable |

## 03_zlib_deflate / no_retpoline / func_pgot

Selected row: iterations=32, Δ=-45.219, IQR=256.281, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27629.062 | 27647.312 | 55.782 | 357.313 | 6.41 | 0.20 | indistinguishable |
| 32 | 93 | 27540.812 | 27483.734 | -45.219 | 256.281 | 5.67 | -0.16 | indistinguishable |
| 64 | 93 | 27698.054 | 27629.835 | -0.954 | 541.945 | 568.08 | -0.00 | indistinguishable |

## 03_zlib_deflate / no_retpoline / all_pgot

Selected row: iterations=16, Δ=375.094, IQR=166.376, label=usable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27599.375 | 27988.312 | 375.094 | 166.376 | 0.44 | 1.36 | usable |
| 32 | 93 | 27547.765 | 27745.531 | 213.391 | 255.110 | 1.20 | 0.77 | indistinguishable |
| 64 | 93 | 27649.249 | 27871.249 | 231.141 | 383.477 | 1.66 | 0.84 | indistinguishable |

## 03_zlib_deflate / retpoline / data_pgot

Selected row: iterations=32, Δ=469.578, IQR=237.421, label=weak.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27453.625 | 27931.999 | 463.594 | 342.438 | 0.74 | 1.69 | weak |
| 32 | 93 | 27405.577 | 27859.593 | 469.578 | 237.421 | 0.51 | 1.71 | weak |
| 64 | 93 | 27419.304 | 27826.414 | 408.960 | 457.883 | 1.12 | 1.49 | indistinguishable |

## 03_zlib_deflate / retpoline / func_pgot

Selected row: iterations=16, Δ=-17.750, IQR=565.876, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27480.812 | 27494.500 | -17.750 | 565.876 | 31.88 | -0.06 | indistinguishable |
| 32 | 93 | 27397.609 | 27406.265 | -5.531 | 195.484 | 35.34 | -0.02 | indistinguishable |
| 64 | 93 | 27394.023 | 27426.039 | 9.430 | 446.344 | 47.33 | 0.03 | indistinguishable |

## 03_zlib_deflate / retpoline / all_pgot

Selected row: iterations=32, Δ=-180.234, IQR=192.156, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 27478.999 | 27266.281 | -194.969 | 281.250 | 1.44 | -0.71 | indistinguishable |
| 32 | 93 | 27405.921 | 27248.218 | -180.234 | 192.156 | 1.07 | -0.66 | indistinguishable |
| 64 | 93 | 27382.687 | 27145.117 | -265.110 | 459.875 | 1.73 | -0.97 | indistinguishable |

## 04_zstd_decompress / no_retpoline / data_pgot

Selected row: iterations=256, Δ=-17.416, IQR=21.513, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6313.687 | 6297.624 | -14.093 | 54.970 | 3.90 | -0.22 | indistinguishable |
| 32 | 93 | 6300.327 | 6296.734 | -0.829 | 59.501 | 71.77 | -0.01 | indistinguishable |
| 64 | 93 | 6290.398 | 6267.421 | -24.547 | 53.140 | 2.16 | -0.39 | indistinguishable |
| 128 | 93 | 6274.609 | 6314.624 | 37.586 | 64.313 | 1.71 | 0.60 | indistinguishable |
| 256 | 93 | 6276.015 | 6258.249 | -17.416 | 21.513 | 1.24 | -0.28 | indistinguishable |

## 04_zstd_decompress / no_retpoline / func_pgot

Selected row: iterations=128, Δ=20.633, IQR=26.664, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6307.625 | 6322.812 | 20.750 | 52.656 | 2.54 | 0.33 | indistinguishable |
| 32 | 93 | 6296.062 | 6309.406 | 16.953 | 28.953 | 1.71 | 0.27 | indistinguishable |
| 64 | 93 | 6289.733 | 6298.656 | 9.969 | 54.195 | 5.44 | 0.16 | indistinguishable |
| 128 | 93 | 6273.324 | 6295.484 | 20.633 | 26.664 | 1.29 | 0.33 | indistinguishable |
| 256 | 93 | 6274.929 | 6294.290 | 19.418 | 47.281 | 2.43 | 0.31 | indistinguishable |

## 04_zstd_decompress / no_retpoline / all_pgot

Selected row: iterations=32, Δ=87.109, IQR=39.844, label=usable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6298.499 | 6387.906 | 87.250 | 49.032 | 0.56 | 1.39 | weak |
| 32 | 93 | 6296.984 | 6379.843 | 87.109 | 39.844 | 0.46 | 1.38 | usable |
| 64 | 93 | 6285.687 | 6351.983 | 66.243 | 49.336 | 0.74 | 1.05 | weak |
| 128 | 93 | 6277.281 | 6345.464 | 67.672 | 31.825 | 0.47 | 1.08 | usable |
| 256 | 93 | 6274.279 | 6343.525 | 69.395 | 41.221 | 0.59 | 1.11 | weak |

## 04_zstd_decompress / retpoline / data_pgot

Selected row: iterations=128, Δ=-19.644, IQR=29.968, label=indistinguishable.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6306.562 | 6302.281 | -9.469 | 48.782 | 5.15 | -0.15 | indistinguishable |
| 32 | 93 | 6291.687 | 6271.218 | -20.203 | 38.938 | 1.93 | -0.32 | indistinguishable |
| 64 | 93 | 6276.273 | 6273.241 | 1.805 | 35.601 | 19.72 | 0.03 | indistinguishable |
| 128 | 93 | 6280.273 | 6259.195 | -19.644 | 29.968 | 1.53 | -0.31 | indistinguishable |
| 256 | 93 | 6272.585 | 6254.843 | -17.594 | 28.197 | 1.60 | -0.28 | indistinguishable |

## 04_zstd_decompress / retpoline / func_pgot

Selected row: iterations=128, Δ=455.261, IQR=21.402, label=strong.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6308.656 | 6771.093 | 459.844 | 44.749 | 0.10 | 7.29 | strong |
| 32 | 93 | 6295.171 | 6750.843 | 455.875 | 35.016 | 0.08 | 7.24 | strong |
| 64 | 93 | 6279.874 | 6741.187 | 460.906 | 29.172 | 0.06 | 7.34 | strong |
| 128 | 93 | 6278.601 | 6733.663 | 455.261 | 21.402 | 0.05 | 7.25 | strong |
| 256 | 93 | 6275.283 | 6762.167 | 484.773 | 55.508 | 0.11 | 7.73 | strong |

## 04_zstd_decompress / retpoline / all_pgot

Selected row: iterations=128, Δ=391.059, IQR=24.304, label=strong.

| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 16 | 93 | 6295.968 | 6705.500 | 409.094 | 41.530 | 0.10 | 6.50 | strong |
| 32 | 93 | 6292.296 | 6687.687 | 397.156 | 41.796 | 0.11 | 6.31 | strong |
| 64 | 93 | 6281.835 | 6678.640 | 402.820 | 44.203 | 0.11 | 6.41 | strong |
| 128 | 93 | 6276.851 | 6666.569 | 391.059 | 24.304 | 0.06 | 6.23 | strong |
| 256 | 93 | 6275.970 | 6668.571 | 396.181 | 41.443 | 0.10 | 6.31 | strong |
