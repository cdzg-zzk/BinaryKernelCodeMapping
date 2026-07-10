# Layer3 lz4_decompress_safe Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel LZ4_decompress_safe implementation closure into the LKM. The compressed input is generated during module initialization and the timed region calls only the copied decompressor closure.

## Transformations

| variant | transformation |
|---|---|
| origin | copied LZ4_decompress_safe closure, direct local static decode tables and direct/inlined mem helpers |
| data_pgot | inc32table and dec64table are reached through data slots inside LZ4_decompress_generic |
| func_pgot | LZ4_memcpy/LZ4_memmove/raw memmove callsites in the copied closure are routed through function slots |
| all_pgot | data_pgot + func_pgot |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 512 | 93 | 558.412 | 572.970 | 14.561 | 19.446 | 1.34 | 2.61 |
| no_retpoline | data_pgot | 1024 | 93 | 557.791 | 567.516 | 9.440 | 9.608 | 1.02 | 1.69 |
| no_retpoline | data_pgot | 2048 | 93 | 558.534 | 571.493 | 14.735 | 17.441 | 1.18 | 2.64 |
| no_retpoline | func_pgot | 512 | 93 | 557.998 | 5581.474 | 5024.051 | 64.081 | 0.01 | 900.37 |
| no_retpoline | func_pgot | 1024 | 93 | 559.223 | 5622.121 | 5056.627 | 52.025 | 0.01 | 904.22 |
| no_retpoline | func_pgot | 2048 | 93 | 558.504 | 5686.486 | 5108.645 | 85.134 | 0.02 | 914.70 |
| no_retpoline | all_pgot | 512 | 93 | 558.519 | 5584.218 | 5020.655 | 77.862 | 0.02 | 898.92 |
| no_retpoline | all_pgot | 1024 | 93 | 559.865 | 5613.569 | 5044.443 | 64.769 | 0.01 | 901.01 |
| no_retpoline | all_pgot | 2048 | 93 | 560.038 | 5676.063 | 5099.092 | 77.459 | 0.02 | 910.49 |
| retpoline | data_pgot | 512 | 93 | 557.077 | 569.366 | 11.708 | 5.385 | 0.46 | 2.10 |
| retpoline | data_pgot | 1024 | 93 | 557.170 | 567.786 | 9.901 | 11.790 | 1.19 | 1.78 |
| retpoline | data_pgot | 2048 | 93 | 557.501 | 572.771 | 14.859 | 19.814 | 1.33 | 2.67 |
| retpoline | func_pgot | 512 | 93 | 557.202 | 8716.946 | 8156.372 | 436.816 | 0.05 | 1463.81 |
| retpoline | func_pgot | 1024 | 93 | 559.513 | 8292.029 | 7722.671 | 46.302 | 0.01 | 1380.25 |
| retpoline | func_pgot | 2048 | 93 | 560.476 | 8306.014 | 7744.434 | 33.949 | 0.00 | 1381.76 |
| retpoline | all_pgot | 512 | 93 | 558.002 | 8316.499 | 7757.585 | 16.522 | 0.00 | 1390.24 |
| retpoline | all_pgot | 1024 | 93 | 560.932 | 8324.971 | 7749.320 | 48.468 | 0.01 | 1381.51 |
| retpoline | all_pgot | 2048 | 93 | 559.107 | 8336.528 | 7763.235 | 44.122 | 0.01 | 1388.51 |

## Static Validation

Expected evidence: data/all variants reference pgot_lz4_inc32table_* and pgot_lz4_dec64table_*; func/all variants reference pgot_memcpy_table_* or pgot_memmove_table_*; retpoline objdump should show thunk code around indirect mem-helper calls when they remain calls.
