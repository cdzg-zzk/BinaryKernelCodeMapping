# Layer3 SHA-256 Transform PGOT Experiment

## 1. Goal

This Layer3 kernel-module benchmark moves from synthetic primitives to a copied
real-function closure: a SHA-256 64-byte block transform. It compares the
original closure against PGOT-style data and function transformations.

| variant | transformation |
|---|---|
| `origin` | direct K-table access and direct helper calls |
| `all_pgot` | K table address is loaded from a pgot data slot |
| `func_pgot` | not reported for SHA-256: no closure-external helper |

The benchmark does not call the system crypto API. It copies the SHA-256
compression closure into the test module so the origin and PGOT versions can be
compiled side by side and measured with identical inputs.

## 2. Setup

| item | value |
|---|---|
| execution mode | kernel module |
| function under test | SHA-256 block transform, one 64-byte block per call |
| comparison | variant cycles - origin cycles |
| builds | no-retpoline, retpoline |
| sample order | paired/interleave |
| iterations | 4096 8192 16384 |
| repeats | 31 |
| outer runs | 3 |
| variants | all_pgot |
| CPU | pinned CPU 2 |

The reported delta is paired:

```text
delta[r] = variant_cycles[r] - origin_cycles[r]
reported_delta = median(delta[r])
```

## 3. Dynamic Results

| build | variant | iterations | n | origin cycles | variant cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_retpoline | all_pgot | 4096 | 93 | 1317.605 | 1317.225 | 0.012 | 5.714 | 476.17 | 0.00 |
| no_retpoline | all_pgot | 8192 | 93 | 1319.994 | 1320.220 | 0.408 | 5.398 | 13.23 | 0.03 |
| no_retpoline | all_pgot | 16384 | 93 | 1320.522 | 1321.866 | 1.130 | 4.804 | 4.25 | 0.09 |
| retpoline | all_pgot | 4096 | 93 | 1318.062 | 1318.609 | 0.596 | 6.307 | 10.58 | 0.05 |
| retpoline | all_pgot | 8192 | 93 | 1320.010 | 1320.788 | 0.415 | 4.545 | 10.95 | 0.03 |
| retpoline | all_pgot | 16384 | 93 | 1321.756 | 1319.861 | -1.335 | 4.625 | 3.46 | -0.10 |

## 4. Key Observations

1. `all_pgot` does not expose a positive visible overhead in this copied
   SHA-256 closure. The measured deltas are 0.012
   cycles in no-retpoline and 0.596 cycles in
   retpoline. This must not be interpreted as "PGOT makes SHA-256 faster":
   the generated data-table transform is 0 bytes different
   from `origin`, so code layout/register allocation dominate a single K-table
   slot load.
2. SHA-256 transform has no honest closure-external helper in this benchmark.
   Endian word loading, message schedule, and round logic are part of the
   copied closure, so they remain direct/internal code instead of being forced
   through function PGOT.
3. Therefore this SHA-256 Layer3 case reports `all_pgot`, but its applicable
   transformation is data-PGOT only. Function-PGOT is evaluated by later
   Layer3 functions that naturally call helpers across the copied-closure
   boundary.


## 5. Static Validation

| validation | result |
|---|---|
| data_pgot data slot relocation | True |
| data_pgot has no indirect call | True |
| retpoline data_pgot has no retpoline thunk | True |

Symbol sizes:

| symbol | no-ret size | retpoline size |
|---|---:|---:|
| `sha256_transform_origin` | 872 | 872 |
| `sha256_transform_data_pgot` | 872 | 872 |
| `body_origin` | 174 | 174 |
| `body_data_pgot` | 174 | 174 |

Static interpretation:

1. `data_pgot` contains a relocation/reference to `pgot_k_table`, so the
   K-table base is actually obtained through a data slot.
2. The SHA-256 transform variant contains no function-PGOT path: no indirect
   call is present in no-retpoline, and no retpoline thunk is present in the
   retpoline build.

## 6. Interpretation

This experiment is closer to the real kernel setting than Layer1/Layer2:

1. `data_pgot` estimates the cost of moving a real constant table reference
   through a pgot data slot inside a nontrivial transform.
2. Function-PGOT is intentionally not reported for this function because the
   transform has no honest closure-external helper call.

The result should be interpreted as whole-function visible overhead per
SHA-256 block transform, not as a primitive load or primitive call latency.

## 7. Files

| file | description |
|---|---|
| `raw.csv` | paired raw origin/variant samples |
| `processed.csv` | mean/median/IQR/stddev/min/max per case |
| `paper_table.csv` | compact paper table |
| `metadata.txt` | environment and build metadata |
| `static/nm_*.txt` | symbol sizes |
| `static/objdump_*.txt` | disassembly with relocations |
