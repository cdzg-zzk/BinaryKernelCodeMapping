# Layer3 hex_dump_to_buffer Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel hex_dump_to_buffer implementation into the LKM and times direct calls to the copied closure. The benchmark uses groupsize=1/ascii=true so the normal hex_asc table path is exercised without snprintf callsites.

## Transformations

| variant | transformation |
|---|---|
| origin | copied hex_dump_to_buffer closure with direct hex_asc table references |
| data_pgot | hex_asc is reached through a data slot before hex_asc_hi/lo indexing |
| func_pgot | no mem* callsite exists here, so this is intentionally identical to origin |
| all_pgot | same data-slot rewrite as data_pgot |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 512 | 93 | 366.088 | 377.511 | 10.608 | 5.616 | 0.53 | 2.90 |
| no_retpoline | data_pgot | 1024 | 93 | 367.155 | 376.853 | 7.984 | 6.307 | 0.79 | 2.17 |
| no_retpoline | data_pgot | 2048 | 93 | 366.520 | 377.314 | 11.869 | 10.621 | 0.89 | 3.24 |
| no_retpoline | func_pgot | 512 | 93 | 366.706 | 361.714 | -2.760 | 7.529 | 2.73 | -0.75 |
| no_retpoline | func_pgot | 1024 | 93 | 365.895 | 363.198 | 0.445 | 9.945 | 22.35 | 0.12 |
| no_retpoline | func_pgot | 2048 | 93 | 366.507 | 363.162 | -0.689 | 6.827 | 9.91 | -0.19 |
| no_retpoline | all_pgot | 512 | 93 | 363.526 | 375.152 | 11.541 | 9.514 | 0.82 | 3.17 |
| no_retpoline | all_pgot | 1024 | 93 | 366.391 | 375.380 | 10.365 | 4.687 | 0.45 | 2.83 |
| no_retpoline | all_pgot | 2048 | 93 | 366.793 | 376.349 | 9.984 | 6.065 | 0.61 | 2.72 |
| retpoline | data_pgot | 512 | 93 | 367.675 | 377.164 | 9.040 | 8.758 | 0.97 | 2.46 |
| retpoline | data_pgot | 1024 | 93 | 367.581 | 377.474 | 10.635 | 10.870 | 1.02 | 2.89 |
| retpoline | data_pgot | 2048 | 93 | 365.842 | 382.413 | 17.273 | 11.476 | 0.66 | 4.72 |
| retpoline | func_pgot | 512 | 93 | 365.985 | 362.560 | -2.882 | 5.485 | 1.90 | -0.79 |
| retpoline | func_pgot | 1024 | 93 | 363.299 | 368.101 | 1.860 | 9.015 | 4.85 | 0.51 |
| retpoline | func_pgot | 2048 | 93 | 366.383 | 365.528 | -0.026 | 6.001 | 230.81 | -0.01 |
| retpoline | all_pgot | 512 | 93 | 363.976 | 376.342 | 15.019 | 7.087 | 0.47 | 4.13 |
| retpoline | all_pgot | 1024 | 93 | 367.537 | 375.867 | 7.859 | 6.051 | 0.77 | 2.14 |
| retpoline | all_pgot | 2048 | 93 | 363.470 | 376.356 | 14.870 | 6.931 | 0.47 | 4.09 |

## Static Validation

Expected evidence: data/all variants reference pgot_hex_asc_table_* in objdump/nm; func_pgot has no mem* table because hex_dump_to_buffer has no memcpy/memset/memmove callsite in this measured path.
