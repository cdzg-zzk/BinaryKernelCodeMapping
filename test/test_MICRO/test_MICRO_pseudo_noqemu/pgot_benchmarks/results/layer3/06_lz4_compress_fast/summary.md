# Layer3 LZ4_compress_fast Copied-Closure PGOT Experiment

## Goal

This benchmark copies the kernel LZ4_compress_fast implementation closure into the LKM. The origin version keeps the copied implementation unchanged. The PGOT variants rewrite only closure-internal data references and mem* helper callsites that are visible in the copied closure.

| variant | transformation |
|---|---|
| origin | copied LZ4_compress_fast closure, direct internal data and mem helpers |
| data_pgot | copied closure with LZ4_minLength/LZ4_64Klimit loaded through data slots |
| func_pgot | copied closure with real memcpy/memset/memmove helper calls routed through function slots |
| all_pgot | data_pgot + func_pgot |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | data_pgot | 512 | 93 | 1774.330 | 1770.394 | -3.296 | 7.837 | 2.38 | -0.19 |
| no_retpoline | data_pgot | 1024 | 93 | 1778.626 | 1770.242 | -8.509 | 60.748 | 7.14 | -0.48 |
| no_retpoline | data_pgot | 2048 | 93 | 1776.087 | 1773.098 | -4.835 | 11.224 | 2.32 | -0.27 |
| no_retpoline | func_pgot | 512 | 93 | 1774.411 | 1769.614 | -3.763 | 7.390 | 1.96 | -0.21 |
| no_retpoline | func_pgot | 1024 | 93 | 1777.167 | 1802.508 | 25.048 | 120.691 | 4.82 | 1.41 |
| no_retpoline | func_pgot | 2048 | 93 | 1777.857 | 1773.151 | -0.726 | 26.547 | 36.57 | -0.04 |
| no_retpoline | all_pgot | 512 | 93 | 1773.090 | 1770.303 | -3.441 | 8.304 | 2.41 | -0.19 |
| no_retpoline | all_pgot | 1024 | 93 | 1778.094 | 1772.813 | -4.700 | 110.609 | 23.53 | -0.26 |
| no_retpoline | all_pgot | 2048 | 93 | 1777.002 | 1777.455 | 1.770 | 59.922 | 33.85 | 0.10 |
| retpoline | data_pgot | 512 | 93 | 1774.715 | 1770.193 | -5.996 | 9.542 | 1.59 | -0.34 |
| retpoline | data_pgot | 1024 | 93 | 1778.192 | 1772.281 | -6.012 | 8.323 | 1.38 | -0.34 |
| retpoline | data_pgot | 2048 | 93 | 1830.300 | 1771.664 | -58.639 | 56.467 | 0.96 | -3.20 |
| retpoline | func_pgot | 512 | 93 | 1772.820 | 1826.706 | 52.201 | 29.026 | 0.56 | 2.94 |
| retpoline | func_pgot | 1024 | 93 | 1777.414 | 1823.607 | 43.977 | 54.025 | 1.23 | 2.47 |
| retpoline | func_pgot | 2048 | 93 | 1830.125 | 1831.274 | 22.881 | 50.256 | 2.20 | 1.25 |
| retpoline | all_pgot | 512 | 93 | 1775.951 | 1823.373 | 51.342 | 52.574 | 1.02 | 2.89 |
| retpoline | all_pgot | 1024 | 93 | 1778.914 | 1823.111 | 42.450 | 54.957 | 1.29 | 2.39 |
| retpoline | all_pgot | 2048 | 93 | 1827.917 | 1824.238 | -1.936 | 52.373 | 27.05 | -0.11 |

## Static Validation

| check | expected evidence |
|---|---|
| data_pgot slot | objdump/nm references pgot_LZ4_minLength_* and pgot_LZ4_64Klimit_* in data/all variants |
| func_pgot slot | objdump/nm references pgot_memcpy_table_* / pgot_memmove_table_* in func/all variants when mem helpers remain calls |
| retpoline | retpoline objdump contains inline thunk markers around indirect mem-helper calls when present |

See static/objdump_*.txt and static/nm_*.txt for disassembly evidence.
