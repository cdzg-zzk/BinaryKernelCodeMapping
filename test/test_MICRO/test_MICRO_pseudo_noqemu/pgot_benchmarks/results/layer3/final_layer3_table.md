| Function | Build | Variant | Origin cycles | PGOT cycles | Δcycles | Overhead% | IQR(Δ) | IQR/|Δ| | Stability |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| aes_encrypt | no_retpoline | all_pgot | 404.084 | 445.375 | 41.559 | 10.285 | 1.218 | 0.03 | strong |
| aes_encrypt | retpoline | all_pgot | 404.274 | 445.709 | 41.265 | 10.207 | 1.610 | 0.04 | strong |
| bch_encode | no_retpoline | all_pgot | 5492.726 | 5850.483 | 347.828 | 6.333 | 176.351 | 0.51 | weak |
| bch_encode | retpoline | all_pgot | 5492.030 | 6022.608 | 528.243 | 9.618 | 397.092 | 0.75 | weak |
| crc32_le | no_retpoline | all_pgot | 4196.651 | 4185.473 | -11.197 | -0.267 | 0.528 | 0.05 | strong |
| crc32_le | retpoline | all_pgot | 4196.733 | 4185.479 | -11.291 | -0.269 | 0.231 | 0.02 | strong |
| hex_dump_to_buffer | no_retpoline | all_pgot | 366.391 | 375.380 | 10.365 | 2.829 | 4.687 | 0.45 | usable |
| hex_dump_to_buffer | retpoline | all_pgot | 363.470 | 376.356 | 14.870 | 4.091 | 6.931 | 0.47 | usable |
| lz4_compress_fast | no_retpoline | all_pgot | 1773.090 | 1770.303 | -3.441 | -0.194 | 8.304 | 2.41 | indistinguishable |
| lz4_compress_fast | retpoline | all_pgot | 1775.951 | 1823.373 | 51.342 | 2.891 | 52.574 | 1.02 | indistinguishable |
| lz4_decompress_safe | no_retpoline | all_pgot | 559.865 | 5613.569 | 5044.443 | 901.011 | 64.769 | 0.01 | strong |
| lz4_decompress_safe | retpoline | all_pgot | 558.002 | 8316.499 | 7757.585 | 1390.243 | 16.522 | 0.00 | strong |
| sha256_transform | no_retpoline | all_pgot | 1320.522 | 1321.866 | 1.130 | 0.086 | 4.804 | 4.25 | indistinguishable |
| sha256_transform | retpoline | all_pgot | 1321.756 | 1319.861 | -1.335 | -0.101 | 4.625 | 3.46 | indistinguishable |
| string_escape_mem | no_retpoline | all_pgot | 700.503 | 697.274 | -28.152 | -4.019 | 64.563 | 2.29 | indistinguishable |
| string_escape_mem | retpoline | all_pgot | 700.508 | 673.438 | -27.370 | -3.907 | 62.934 | 2.30 | indistinguishable |
| zlib_deflate | no_retpoline | all_pgot | 27592.250 | 27902.515 | 274.796 | 0.996 | 191.781 | 0.70 | weak |
| zlib_deflate | retpoline | all_pgot | 27486.906 | 27270.750 | -199.094 | -0.724 | 204.595 | 1.03 | indistinguishable |
| zstd_decompress | no_retpoline | all_pgot | 6273.136 | 6350.159 | 75.949 | 1.211 | 34.075 | 0.45 | usable |
| zstd_decompress | retpoline | all_pgot | 6279.140 | 6677.976 | 402.813 | 6.415 | 31.805 | 0.08 | strong |
