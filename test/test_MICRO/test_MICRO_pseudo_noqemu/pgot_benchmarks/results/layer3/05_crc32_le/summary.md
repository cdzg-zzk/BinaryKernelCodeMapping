# Layer3 CRC32_LE Copied-Closure All-PGOT Experiment

## Goal

This benchmark copies the kernel crc32_le computation into the LKM and compares origin with all_pgot. In this closure, the applicable PGOT transformation is data-pgot: the CRC table base is loaded through pgot_crc32table_le[0].

| variant | transformation |
|---|---|
| origin | copied crc32_le closure, direct crc32table_le reference |
| all_pgot | copied crc32_le closure, crc32table_le base loaded from pgot_crc32table_le[0] |

## Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | all_pgot | 512 | 93 | 4196.657 | 4185.432 | -11.203 | 6.072 | 0.54 | -0.27 |
| no_retpoline | all_pgot | 1024 | 93 | 4196.651 | 4185.473 | -11.197 | 0.528 | 0.05 | -0.27 |
| no_retpoline | all_pgot | 2048 | 93 | 4196.662 | 4185.465 | -11.205 | 5.792 | 0.52 | -0.27 |
| retpoline | all_pgot | 512 | 93 | 4196.869 | 4185.556 | -11.318 | 0.531 | 0.05 | -0.27 |
| retpoline | all_pgot | 1024 | 93 | 4196.775 | 4185.515 | -11.247 | 0.333 | 0.03 | -0.27 |
| retpoline | all_pgot | 2048 | 93 | 4196.733 | 4185.479 | -11.291 | 0.231 | 0.02 | -0.27 |

## Static Validation

| check | expected evidence |
|---|---|
| all_pgot data slot | objdump references pgot_crc32table_le in crc32_le_all_pgot_local |
| no function PGOT | this copied closure has no required helper call rewrite; all_pgot equals all applicable PGOT transformations |

See static/objdump_*.txt and static/nm_*.txt for disassembly evidence.
