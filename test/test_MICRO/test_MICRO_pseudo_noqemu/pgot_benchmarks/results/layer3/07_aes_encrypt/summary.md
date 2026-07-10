# Layer3 aes_encrypt Copied-Closure PGOT Experiment

## Goal

This benchmark copies the generic kernel AES implementation closure into the LKM. Key expansion is performed before timing; the timed body directly calls the copied aes_encrypt closure.

## Transformations

| variant | transformation |
|---|---|
| origin | copied aes_encrypt/aes_expandkey closure with direct AES S-box references |
| data_pgot | aes_sbox/aes_inv_sbox table references are reached through data slots |
| func_pgot | no memcpy/memset/memmove callsite exists in aes_encrypt, so this is intentionally identical to origin for timed work |
| all_pgot | same data-slot rewrite as data_pgot |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 512 | 93 | 403.892 | 445.200 | 41.197 | 3.786 | 0.09 | 10.20 |
| no_retpoline | data_pgot | 1024 | 93 | 403.834 | 447.692 | 43.892 | 1.538 | 0.04 | 10.87 |
| no_retpoline | data_pgot | 2048 | 93 | 404.344 | 448.122 | 43.548 | 1.942 | 0.04 | 10.77 |
| no_retpoline | func_pgot | 512 | 93 | 403.948 | 404.197 | 0.187 | 1.286 | 6.88 | 0.05 |
| no_retpoline | func_pgot | 1024 | 93 | 403.637 | 404.454 | 0.832 | 0.702 | 0.84 | 0.21 |
| no_retpoline | func_pgot | 2048 | 93 | 404.206 | 404.301 | 0.415 | 1.645 | 3.96 | 0.10 |
| no_retpoline | all_pgot | 512 | 93 | 403.897 | 446.236 | 42.365 | 2.975 | 0.07 | 10.49 |
| no_retpoline | all_pgot | 1024 | 93 | 404.084 | 445.375 | 41.559 | 1.218 | 0.03 | 10.28 |
| no_retpoline | all_pgot | 2048 | 93 | 404.204 | 445.760 | 41.472 | 2.272 | 0.05 | 10.26 |
| retpoline | data_pgot | 512 | 93 | 404.147 | 448.784 | 44.410 | 1.335 | 0.03 | 10.99 |
| retpoline | data_pgot | 1024 | 93 | 404.200 | 448.537 | 44.359 | 1.723 | 0.04 | 10.97 |
| retpoline | data_pgot | 2048 | 93 | 404.131 | 448.689 | 44.427 | 3.869 | 0.09 | 10.99 |
| retpoline | func_pgot | 512 | 93 | 404.173 | 404.697 | 0.528 | 0.842 | 1.59 | 0.13 |
| retpoline | func_pgot | 1024 | 93 | 404.149 | 404.544 | 0.574 | 0.886 | 1.54 | 0.14 |
| retpoline | func_pgot | 2048 | 93 | 404.146 | 404.320 | 0.344 | 1.975 | 5.74 | 0.09 |
| retpoline | all_pgot | 512 | 93 | 404.399 | 444.668 | 40.797 | 2.249 | 0.06 | 10.09 |
| retpoline | all_pgot | 1024 | 93 | 404.310 | 445.951 | 41.493 | 1.668 | 0.04 | 10.26 |
| retpoline | all_pgot | 2048 | 93 | 404.274 | 445.709 | 41.265 | 1.610 | 0.04 | 10.21 |

## Static Validation

Expected evidence: data/all variants reference pgot_aes_sbox_table_* and pgot_aes_inv_sbox_table_* in objdump/nm; func_pgot has no mem* table because aes_encrypt has no memcpy/memset/memmove callsite.
