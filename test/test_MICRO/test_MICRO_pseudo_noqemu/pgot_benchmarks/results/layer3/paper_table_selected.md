# Layer3 Stable Paper Rows

Selection rule: group by experiment/build/variant, prefer rows with smaller `IQR/|Δ|`; keep the stability label so weak or unstable cases are not overclaimed.

| experiment | build | variant | iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | stability |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 01_sha256_transform | no_retpoline | data_pgot | 16384 | 93 | 1314.389 | 1314.855 | 0.526 | 3.815 | 7.25 | 0.04 | near_zero |
| 01_sha256_transform | retpoline | data_pgot | 16384 | 93 | 1314.575 | 1313.522 | -0.978 | 4.451 | 4.55 | -0.07 | near_zero |
| 02_bch_encode | no_retpoline | data_pgot | 128 | 93 | 5496.429 | 5519.374 | 26.360 | 14.125 | 0.54 | 0.48 | weak |
| 02_bch_encode | no_retpoline | func_pgot | 64 | 93 | 5488.413 | 5561.663 | 75.062 | 20.961 | 0.28 | 1.37 | usable |
| 02_bch_encode | no_retpoline | all_pgot | 128 | 93 | 5502.159 | 5604.730 | 108.746 | 33.086 | 0.30 | 1.98 | usable |
| 02_bch_encode | retpoline | data_pgot | 64 | 93 | 5491.046 | 5519.116 | 32.523 | 67.164 | 2.07 | 0.59 | indistinguishable |
| 02_bch_encode | retpoline | func_pgot | 64 | 93 | 5490.593 | 5643.695 | 150.789 | 10.617 | 0.07 | 2.75 | strong |
| 02_bch_encode | retpoline | all_pgot | 64 | 93 | 5492.913 | 5660.585 | 178.609 | 47.134 | 0.26 | 3.25 | usable |
| 03_zlib_deflate | no_retpoline | data_pgot | 32 | 93 | 27513.375 | 27624.655 | 128.282 | 222.858 | 1.74 | 0.47 | indistinguishable |
| 03_zlib_deflate | no_retpoline | func_pgot | 32 | 93 | 27540.812 | 27483.734 | -45.219 | 256.281 | 5.67 | -0.16 | indistinguishable |
| 03_zlib_deflate | no_retpoline | all_pgot | 16 | 93 | 27599.375 | 27988.312 | 375.094 | 166.376 | 0.44 | 1.36 | usable |
| 03_zlib_deflate | retpoline | data_pgot | 32 | 93 | 27405.577 | 27859.593 | 469.578 | 237.421 | 0.51 | 1.71 | weak |
| 03_zlib_deflate | retpoline | func_pgot | 16 | 93 | 27480.812 | 27494.500 | -17.750 | 565.876 | 31.88 | -0.06 | indistinguishable |
| 03_zlib_deflate | retpoline | all_pgot | 32 | 93 | 27405.921 | 27248.218 | -180.234 | 192.156 | 1.07 | -0.66 | indistinguishable |
| 04_zstd_decompress | no_retpoline | data_pgot | 256 | 93 | 6276.015 | 6258.249 | -17.416 | 21.513 | 1.24 | -0.28 | indistinguishable |
| 04_zstd_decompress | no_retpoline | func_pgot | 128 | 93 | 6273.324 | 6295.484 | 20.633 | 26.664 | 1.29 | 0.33 | indistinguishable |
| 04_zstd_decompress | no_retpoline | all_pgot | 32 | 93 | 6296.984 | 6379.843 | 87.109 | 39.844 | 0.46 | 1.38 | usable |
| 04_zstd_decompress | retpoline | data_pgot | 128 | 93 | 6280.273 | 6259.195 | -19.644 | 29.968 | 1.53 | -0.31 | indistinguishable |
| 04_zstd_decompress | retpoline | func_pgot | 128 | 93 | 6278.601 | 6733.663 | 455.261 | 21.402 | 0.05 | 7.25 | strong |
| 04_zstd_decompress | retpoline | all_pgot | 128 | 93 | 6276.851 | 6666.569 | 391.059 | 24.304 | 0.06 | 6.23 | strong |
