# Fixed-workload interpretation

Values below summarize module-load medians. Ranges span outer runs.

## 01_sha256_transform / no_retpoline
- data_pgot: -0.029% [-0.220, +0.183], paired delta -0.379 TSC ticks/op.

## 01_sha256_transform / retpoline
- data_pgot: -0.048% [-0.125, +0.221], paired delta -0.635 TSC ticks/op.

## 02_bch_encode / no_retpoline
- data_pgot: +0.513% [+0.428, +16.593], paired delta +28.148 TSC ticks/op.
- func_pgot: +1.312% [+1.248, +1.396], paired delta +72.035 TSC ticks/op.
- all_pgot: +1.945% [+1.842, +17.000], paired delta +106.902 TSC ticks/op.
Func-only versus All: +72.035 versus +106.902 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 02_bch_encode / retpoline
- data_pgot: +0.514% [+0.410, +0.751], paired delta +28.250 TSC ticks/op.
- func_pgot: +2.944% [+2.589, +3.096], paired delta +161.410 TSC ticks/op.
- all_pgot: +3.408% [+3.229, +3.647], paired delta +186.938 TSC ticks/op.
Func-only versus All: +161.410 versus +186.938 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 03_zlib_deflate / no_retpoline
- data_pgot: -0.418% [-1.311, +0.519], paired delta -115.344 TSC ticks/op.
- func_pgot: +0.010% [-1.494, +1.446], paired delta +2.734 TSC ticks/op.
- all_pgot: +0.763% [-1.090, +1.851], paired delta +211.266 TSC ticks/op.
Func-only versus All: +2.734 versus +211.266 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 03_zlib_deflate / retpoline
- data_pgot: +2.023% [+0.129, +3.208], paired delta +557.109 TSC ticks/op.
- func_pgot: +0.044% [-1.674, +1.261], paired delta +12.187 TSC ticks/op.
- all_pgot: -0.750% [-2.012, -0.460], paired delta -206.109 TSC ticks/op.
Func-only versus All: +12.187 versus -206.109 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 04_zstd_decompress / no_retpoline
- data_pgot: -0.266% [-0.450, +0.232], paired delta -16.781 TSC ticks/op.
- func_pgot: +0.336% [+0.220, +0.646], paired delta +21.203 TSC ticks/op.
- all_pgot: +1.536% [+1.264, +1.964], paired delta +96.656 TSC ticks/op.
Func-only versus All: +21.203 versus +96.656 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

## 04_zstd_decompress / retpoline
- data_pgot: -0.158% [-0.480, -0.064], paired delta -9.922 TSC ticks/op.
- func_pgot: +7.560% [+7.203, +7.728], paired delta +476.875 TSC ticks/op.
- all_pgot: +6.551% [+6.304, +7.792], paired delta +412.765 TSC ticks/op.
Func-only versus All: +476.875 versus +412.765 ticks/op. These are separate interventions; do not add their deltas or interpret their ratio as an exact cost partition.

Small negative results are not attributed to a PGOT optimization. The fixed-input builds can differ in code generation and layout. There is no causal cross-build retpoline subtraction.
