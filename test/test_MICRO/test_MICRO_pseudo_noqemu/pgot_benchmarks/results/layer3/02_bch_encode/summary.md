# Layer3 BCH Encode Copied-Closure PGOT Experiment

## Goal

This benchmark copies the BCH encode closure into the LKM and compares origin against all_pgot:

| variant | transformation |
|---|---|
| origin | copied encode closure, direct swap_bits_table, direct memcpy |
| all_pgot | data_pgot + func_pgot |

Internal helpers such as swap_bits, load_ecc8, store_ecc8, and bch_encode_unaligned are copied as part of the closure and remain direct calls.

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 64 | 93 | 5493.382 | 5731.960 | 234.961 | 342.969 | 1.46 | 4.28 |
| no_retpoline | data_pgot | 128 | 93 | 5491.398 | 5738.777 | 243.044 | 407.823 | 1.68 | 4.43 |
| no_retpoline | data_pgot | 256 | 93 | 5496.040 | 5519.062 | 23.994 | 326.059 | 13.59 | 0.44 |
| no_retpoline | func_pgot | 64 | 93 | 5486.460 | 5565.874 | 81.304 | 18.080 | 0.22 | 1.48 |
| no_retpoline | func_pgot | 128 | 93 | 5493.097 | 5563.448 | 70.094 | 17.380 | 0.25 | 1.28 |
| no_retpoline | func_pgot | 256 | 93 | 5495.068 | 5569.468 | 75.607 | 280.697 | 3.71 | 1.38 |
| no_retpoline | all_pgot | 64 | 93 | 5492.726 | 5850.483 | 347.828 | 176.351 | 0.51 | 6.33 |
| no_retpoline | all_pgot | 128 | 93 | 5494.667 | 5846.073 | 341.184 | 415.678 | 1.22 | 6.21 |
| no_retpoline | all_pgot | 256 | 93 | 5497.285 | 5795.452 | 121.682 | 677.479 | 5.57 | 2.21 |
| retpoline | data_pgot | 64 | 93 | 5490.640 | 5878.820 | 392.680 | 395.070 | 1.01 | 7.15 |
| retpoline | data_pgot | 128 | 93 | 5490.870 | 5522.066 | 36.223 | 811.414 | 22.40 | 0.66 |
| retpoline | data_pgot | 256 | 93 | 5493.896 | 5515.482 | 22.783 | 161.476 | 7.09 | 0.41 |
| retpoline | func_pgot | 64 | 93 | 5491.663 | 5647.632 | 156.305 | 9.719 | 0.06 | 2.85 |
| retpoline | func_pgot | 128 | 93 | 5491.882 | 5656.073 | 168.515 | 27.915 | 0.17 | 3.07 |
| retpoline | func_pgot | 256 | 93 | 5495.316 | 5650.905 | 153.180 | 388.251 | 2.53 | 2.79 |
| retpoline | all_pgot | 64 | 93 | 5492.030 | 6022.608 | 528.243 | 397.092 | 0.75 | 9.62 |
| retpoline | all_pgot | 128 | 93 | 5491.367 | 5689.964 | 205.191 | 822.254 | 4.01 | 3.74 |
| retpoline | all_pgot | 256 | 93 | 5492.781 | 5662.206 | 171.445 | 391.068 | 2.28 | 3.12 |

## Static Validation

| check | expected evidence |
|---|---|
| all_pgot | objdump for swap_bits_all_pgot references pgot_swap_bits_table and memcpy callsites reference pgot_memcpy_table |
| retpoline | retpoline objdump contains inline thunk markers for func/all indirect memcpy calls |

See static/objdump_*.txt and static/nm_*.txt for the complete disassembly evidence.
