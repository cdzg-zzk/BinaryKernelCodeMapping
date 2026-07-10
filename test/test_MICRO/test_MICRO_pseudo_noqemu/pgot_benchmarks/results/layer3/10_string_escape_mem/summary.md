# Layer3 string_escape_mem Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel string_escape_mem closure into the LKM and exercises the ESCAPE_HEX path, which uses hex_asc through escape_hex. The outer benchmark call remains a direct call to the copied closure.

## Transformations

| variant | transformation |
|---|---|
| origin | copied string_escape_mem closure with direct hex_asc table references |
| data_pgot | escape_hex reaches hex_asc through a data slot |
| func_pgot | no memcpy/memset/memmove callsite exists in this closure, so this is intentionally identical to origin |
| all_pgot | same data-slot rewrite as data_pgot |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 512 | 93 | 700.599 | 659.561 | -41.133 | 29.182 | 0.71 | -5.87 |
| no_retpoline | data_pgot | 1024 | 93 | 700.489 | 659.446 | -42.010 | 26.510 | 0.63 | -6.00 |
| no_retpoline | data_pgot | 2048 | 93 | 700.470 | 681.673 | -24.020 | 61.595 | 2.56 | -3.43 |
| no_retpoline | func_pgot | 512 | 93 | 701.031 | 657.386 | -45.169 | 3.985 | 0.09 | -6.44 |
| no_retpoline | func_pgot | 1024 | 93 | 700.485 | 668.351 | -39.085 | 59.678 | 1.53 | -5.58 |
| no_retpoline | func_pgot | 2048 | 93 | 701.785 | 662.347 | -45.126 | 35.444 | 0.79 | -6.43 |
| no_retpoline | all_pgot | 512 | 93 | 700.543 | 701.530 | -17.662 | 64.093 | 3.63 | -2.52 |
| no_retpoline | all_pgot | 1024 | 93 | 700.503 | 697.274 | -28.152 | 64.563 | 2.29 | -4.02 |
| no_retpoline | all_pgot | 2048 | 93 | 701.217 | 701.437 | -23.085 | 57.195 | 2.48 | -3.29 |
| retpoline | data_pgot | 512 | 93 | 700.617 | 672.507 | -28.091 | 8.076 | 0.29 | -4.01 |
| retpoline | data_pgot | 1024 | 93 | 700.517 | 674.456 | -26.084 | 9.655 | 0.37 | -3.72 |
| retpoline | data_pgot | 2048 | 93 | 701.450 | 679.427 | -27.096 | 56.306 | 2.08 | -3.86 |
| retpoline | func_pgot | 512 | 93 | 701.062 | 660.501 | -40.201 | 46.765 | 1.16 | -5.73 |
| retpoline | func_pgot | 1024 | 93 | 700.684 | 654.639 | -45.171 | 26.307 | 0.58 | -6.45 |
| retpoline | func_pgot | 2048 | 93 | 701.491 | 660.383 | -45.138 | 32.239 | 0.71 | -6.43 |
| retpoline | all_pgot | 512 | 93 | 700.603 | 701.582 | 0.007 | 30.007 | 4286.71 | 0.00 |
| retpoline | all_pgot | 1024 | 93 | 700.508 | 673.438 | -27.370 | 62.934 | 2.30 | -3.91 |
| retpoline | all_pgot | 2048 | 93 | 700.527 | 701.494 | -12.966 | 39.209 | 3.02 | -1.85 |

## Static Validation

Expected evidence: data/all variants reference pgot_hex_asc_table_* in objdump/nm; func_pgot has no mem* table because this closure has no memcpy/memset/memmove callsite.
