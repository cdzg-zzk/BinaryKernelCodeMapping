# Final Layer3 Summary

## Main Results

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

## Interpretation

- `aes_encrypt`: no-ret Δ=41.559 cycles (strong), retpoline Δ=41.265 cycles (strong); retpoline shows a measurable positive all-pgot overhead, but the no-ret row prevents a clean amplification claim.
- `bch_encode`: no-ret Δ=347.828 cycles (weak), retpoline Δ=528.243 cycles (weak); this row should not be used as a strong retpoline amplification claim.
- `crc32_le`: no-ret Δ=-11.197 cycles (strong), retpoline Δ=-11.291 cycles (strong); this row should not be used as a strong retpoline amplification claim.
- `hex_dump_to_buffer`: no-ret Δ=10.365 cycles (usable), retpoline Δ=14.870 cycles (usable); retpoline amplifies the visible all-pgot overhead.
- `lz4_compress_fast`: no-ret Δ=-3.441 cycles (indistinguishable), retpoline Δ=51.342 cycles (indistinguishable); this row should not be used as a strong retpoline amplification claim.
- `lz4_decompress_safe`: no-ret Δ=5044.443 cycles (strong), retpoline Δ=7757.585 cycles (strong); retpoline amplifies the visible all-pgot overhead.
- `sha256_transform`: no-ret Δ=1.130 cycles (indistinguishable), retpoline Δ=-1.335 cycles (indistinguishable); this row should not be used as a strong retpoline amplification claim.
- `string_escape_mem`: no-ret Δ=-28.152 cycles (indistinguishable), retpoline Δ=-27.370 cycles (indistinguishable); this row should not be used as a strong retpoline amplification claim.
- `zlib_deflate`: no-ret Δ=274.796 cycles (weak), retpoline Δ=-199.094 cycles (indistinguishable); this row should not be used as a strong retpoline amplification claim.
- `zstd_decompress`: no-ret Δ=75.949 cycles (usable), retpoline Δ=402.813 cycles (strong); retpoline amplifies the visible all-pgot overhead.

## Required Notes

- `sha256_transform`: all-pgot is effectively data-pgot only; near-zero or negative deltas should be treated as indistinguishable/code-layout dominated, not as a speedup claim.
- `bch_encode`: expected to show a small copied-closure overhead when stability is usable or better; weak rows should not be over-interpreted.
- `zlib_deflate`: if rows are weak or indistinguishable, treat this function as noise/code-layout sensitive rather than a clean overhead estimate.
- `zstd_decompress`: retpoline func/all rows are the key evidence for significant helper-call overhead when the stability label is strong or usable.
- `aes_encrypt`: data/all rows measure AES S-box table indirection; func-pgot is intentionally a no-op for the timed encrypt path because no memcpy/memset/memmove callsite exists.
- `lz4_decompress_safe`: data-pgot covers decode tables; func/all rows include many internal LZ4_memcpy/LZ4_memmove callsites and therefore represent a helper-call-heavy case.
- `hex_dump_to_buffer`: data/all rows measure `hex_asc` table indirection in the groupsize=1 path; func-pgot is intentionally a no-op because no mem* callsite exists.
- `string_escape_mem`: data/all rows measure the `hex_asc` table used by `escape_hex`; func-pgot is intentionally a no-op because no mem* callsite exists.
- Rows labelled `indistinguishable`, `weak`, or `unstable` should not be used as strong quantitative claims.

## Ablation Rows

| Function | Build | Variant | Origin cycles | PGOT cycles | Δcycles | Overhead% | IQR(Δ) | IQR/|Δ| | Stability |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| aes_encrypt | no_retpoline | data_pgot | 403.834 | 447.692 | 43.892 | 10.869 | 1.538 | 0.04 | strong |
| aes_encrypt | no_retpoline | func_pgot | 403.637 | 404.454 | 0.832 | 0.206 | 0.702 | 0.84 | weak |
| aes_encrypt | no_retpoline | all_pgot | 404.084 | 445.375 | 41.559 | 10.285 | 1.218 | 0.03 | strong |
| aes_encrypt | retpoline | data_pgot | 404.147 | 448.784 | 44.410 | 10.989 | 1.335 | 0.03 | strong |
| aes_encrypt | retpoline | func_pgot | 404.149 | 404.544 | 0.574 | 0.142 | 0.886 | 1.54 | indistinguishable |
| aes_encrypt | retpoline | all_pgot | 404.274 | 445.709 | 41.265 | 10.207 | 1.610 | 0.04 | strong |
| bch_encode | no_retpoline | data_pgot | 5493.382 | 5731.960 | 234.961 | 4.277 | 342.969 | 1.46 | indistinguishable |
| bch_encode | no_retpoline | func_pgot | 5486.460 | 5565.874 | 81.304 | 1.482 | 18.080 | 0.22 | strong |
| bch_encode | no_retpoline | all_pgot | 5492.726 | 5850.483 | 347.828 | 6.333 | 176.351 | 0.51 | weak |
| bch_encode | retpoline | data_pgot | 5490.640 | 5878.820 | 392.680 | 7.152 | 395.070 | 1.01 | indistinguishable |
| bch_encode | retpoline | func_pgot | 5491.663 | 5647.632 | 156.305 | 2.846 | 9.719 | 0.06 | strong |
| bch_encode | retpoline | all_pgot | 5492.030 | 6022.608 | 528.243 | 9.618 | 397.092 | 0.75 | weak |
| crc32_le | no_retpoline | all_pgot | 4196.651 | 4185.473 | -11.197 | -0.267 | 0.528 | 0.05 | strong |
| crc32_le | retpoline | all_pgot | 4196.733 | 4185.479 | -11.291 | -0.269 | 0.231 | 0.02 | strong |
| hex_dump_to_buffer | no_retpoline | data_pgot | 366.088 | 377.511 | 10.608 | 2.898 | 5.616 | 0.53 | weak |
| hex_dump_to_buffer | no_retpoline | func_pgot | 366.706 | 361.714 | -2.760 | -0.753 | 7.529 | 2.73 | indistinguishable |
| hex_dump_to_buffer | no_retpoline | all_pgot | 366.391 | 375.380 | 10.365 | 2.829 | 4.687 | 0.45 | usable |
| hex_dump_to_buffer | retpoline | data_pgot | 365.842 | 382.413 | 17.273 | 4.721 | 11.476 | 0.66 | weak |
| hex_dump_to_buffer | retpoline | func_pgot | 365.985 | 362.560 | -2.882 | -0.787 | 5.485 | 1.90 | indistinguishable |
| hex_dump_to_buffer | retpoline | all_pgot | 363.470 | 376.356 | 14.870 | 4.091 | 6.931 | 0.47 | usable |
| lz4_compress_fast | no_retpoline | data_pgot | 1776.087 | 1773.098 | -4.835 | -0.272 | 11.224 | 2.32 | indistinguishable |
| lz4_compress_fast | no_retpoline | func_pgot | 1774.411 | 1769.614 | -3.763 | -0.212 | 7.390 | 1.96 | indistinguishable |
| lz4_compress_fast | no_retpoline | all_pgot | 1773.090 | 1770.303 | -3.441 | -0.194 | 8.304 | 2.41 | indistinguishable |
| lz4_compress_fast | retpoline | data_pgot | 1830.300 | 1771.664 | -58.639 | -3.204 | 56.467 | 0.96 | weak |
| lz4_compress_fast | retpoline | func_pgot | 1772.820 | 1826.706 | 52.201 | 2.945 | 29.026 | 0.56 | weak |
| lz4_compress_fast | retpoline | all_pgot | 1775.951 | 1823.373 | 51.342 | 2.891 | 52.574 | 1.02 | indistinguishable |
| lz4_decompress_safe | no_retpoline | data_pgot | 557.791 | 567.516 | 9.440 | 1.692 | 9.608 | 1.02 | indistinguishable |
| lz4_decompress_safe | no_retpoline | func_pgot | 559.223 | 5622.121 | 5056.627 | 904.224 | 52.025 | 0.01 | strong |
| lz4_decompress_safe | no_retpoline | all_pgot | 559.865 | 5613.569 | 5044.443 | 901.011 | 64.769 | 0.01 | strong |
| lz4_decompress_safe | retpoline | data_pgot | 557.077 | 569.366 | 11.708 | 2.102 | 5.385 | 0.46 | usable |
| lz4_decompress_safe | retpoline | func_pgot | 560.476 | 8306.014 | 7744.434 | 1381.760 | 33.949 | 0.00 | strong |
| lz4_decompress_safe | retpoline | all_pgot | 558.002 | 8316.499 | 7757.585 | 1390.243 | 16.522 | 0.00 | strong |
| sha256_transform | no_retpoline | all_pgot | 1320.522 | 1321.866 | 1.130 | 0.086 | 4.804 | 4.25 | indistinguishable |
| sha256_transform | retpoline | all_pgot | 1321.756 | 1319.861 | -1.335 | -0.101 | 4.625 | 3.46 | indistinguishable |
| string_escape_mem | no_retpoline | data_pgot | 700.489 | 659.446 | -42.010 | -5.997 | 26.510 | 0.63 | weak |
| string_escape_mem | no_retpoline | func_pgot | 701.031 | 657.386 | -45.169 | -6.443 | 3.985 | 0.09 | strong |
| string_escape_mem | no_retpoline | all_pgot | 700.503 | 697.274 | -28.152 | -4.019 | 64.563 | 2.29 | indistinguishable |
| string_escape_mem | retpoline | data_pgot | 700.617 | 672.507 | -28.091 | -4.009 | 8.076 | 0.29 | usable |
| string_escape_mem | retpoline | func_pgot | 700.684 | 654.639 | -45.171 | -6.447 | 26.307 | 0.58 | weak |
| string_escape_mem | retpoline | all_pgot | 700.508 | 673.438 | -27.370 | -3.907 | 62.934 | 2.30 | indistinguishable |
| zlib_deflate | no_retpoline | data_pgot | 27629.359 | 27498.234 | -123.251 | -0.446 | 203.235 | 1.65 | indistinguishable |
| zlib_deflate | no_retpoline | func_pgot | 27602.562 | 27429.577 | -269.860 | -0.978 | 704.859 | 2.61 | indistinguishable |
| zlib_deflate | no_retpoline | all_pgot | 27592.250 | 27902.515 | 274.796 | 0.996 | 191.781 | 0.70 | weak |
| zlib_deflate | retpoline | data_pgot | 27488.249 | 27920.437 | 444.187 | 1.616 | 179.906 | 0.41 | usable |
| zlib_deflate | retpoline | func_pgot | 27483.687 | 27408.906 | -99.375 | -0.362 | 190.938 | 1.92 | indistinguishable |
| zlib_deflate | retpoline | all_pgot | 27486.906 | 27270.750 | -199.094 | -0.724 | 204.595 | 1.03 | indistinguishable |
| zstd_decompress | no_retpoline | data_pgot | 6275.452 | 6262.999 | -11.520 | -0.184 | 21.792 | 1.89 | indistinguishable |
| zstd_decompress | no_retpoline | func_pgot | 6275.101 | 6296.331 | 21.511 | 0.343 | 27.668 | 1.29 | indistinguishable |
| zstd_decompress | no_retpoline | all_pgot | 6273.136 | 6350.159 | 75.949 | 1.211 | 34.075 | 0.45 | usable |
| zstd_decompress | retpoline | data_pgot | 6290.453 | 6269.828 | -19.250 | -0.306 | 36.938 | 1.92 | indistinguishable |
| zstd_decompress | retpoline | func_pgot | 6290.281 | 6764.499 | 475.422 | 7.558 | 33.266 | 0.07 | strong |
| zstd_decompress | retpoline | all_pgot | 6279.140 | 6677.976 | 402.813 | 6.415 | 31.805 | 0.08 | strong |
