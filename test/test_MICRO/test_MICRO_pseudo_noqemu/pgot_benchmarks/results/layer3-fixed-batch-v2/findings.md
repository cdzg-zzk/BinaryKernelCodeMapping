# Fixed-workload interpretation

Values below summarize module-load medians. Ranges span outer runs.

## 01_sha256_transform / no_retpoline
- data_pgot: +0.001% [-0.020, +0.018], paired delta +0.012 TSC ticks/op.

## 01_sha256_transform / retpoline
- data_pgot: +0.050% [-0.124, +0.141], paired delta +0.656 TSC ticks/op.

## 02_bch_encode / no_retpoline
- data_pgot: +4.309% [+0.642, +7.006], paired delta +236.649 TSC ticks/op.
- func_pgot: +1.353% [+1.330, +1.531], paired delta +74.297 TSC ticks/op.
- all_pgot: +6.329% [+5.187, +8.414], paired delta +347.828 TSC ticks/op.
Func-only versus All: +74.297 versus +347.828 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 02_bch_encode / retpoline
- data_pgot: +7.152% [+0.466, +7.719], paired delta +392.343 TSC ticks/op.
- func_pgot: +2.835% [+2.813, +2.862], paired delta +155.860 TSC ticks/op.
- all_pgot: +9.648% [+3.060, +10.382], paired delta +529.891 TSC ticks/op.
Func-only versus All: +155.860 versus +529.891 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 03_zlib_deflate / no_retpoline
- data_pgot: -0.315% [-1.454, -0.312], paired delta -87.000 TSC ticks/op.
- func_pgot: -0.575% [-1.455, +0.911], paired delta -158.844 TSC ticks/op.
- all_pgot: +0.962% [-0.484, +1.481], paired delta +265.781 TSC ticks/op.
Func-only versus All: -158.844 versus +265.781 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 03_zlib_deflate / retpoline
- data_pgot: +1.730% [+1.279, +1.791], paired delta +474.406 TSC ticks/op.
- func_pgot: -0.362% [-0.597, -0.077], paired delta -99.375 TSC ticks/op.
- all_pgot: -0.579% [-1.149, -0.399], paired delta -158.656 TSC ticks/op.
Func-only versus All: -99.375 versus -158.656 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 04_zstd_decompress / no_retpoline
- data_pgot: -0.411% [-0.470, -0.287], paired delta -26.000 TSC ticks/op.
- func_pgot: +0.225% [-0.015, +0.379], paired delta +14.188 TSC ticks/op.
- all_pgot: +1.250% [+1.217, +1.441], paired delta +78.781 TSC ticks/op.
Func-only versus All: +14.188 versus +78.781 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 04_zstd_decompress / retpoline
- data_pgot: -0.190% [-0.223, -0.035], paired delta -12.000 TSC ticks/op.
- func_pgot: +7.789% [+7.391, +7.834], paired delta +490.999 TSC ticks/op.
- all_pgot: +6.624% [+6.592, +6.642], paired delta +417.563 TSC ticks/op.
Func-only versus All: +490.999 versus +417.563 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

Small negative results are not attributed to a PGOT optimization. The fixed-input builds can differ in code generation and layout. There is no causal cross-build retpoline subtraction.
