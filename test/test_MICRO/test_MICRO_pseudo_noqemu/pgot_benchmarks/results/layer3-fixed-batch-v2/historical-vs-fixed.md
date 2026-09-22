# Historical selection versus fixed batches

Historical reported values lack matching raw provenance. The middle column applies the historical batch choice to the available archive using outer-run aggregation. The last column uses the frozen batch and the same aggregation. Brackets are outer-run ranges.

| Routine/build/variant | Historical reported % (batch) | Available raw at old batch % [range] | Fixed % [range] (batch) |
|---|---:|---:|---:|
| 01_sha256_transform/no_retpoline/data_pgot | +0.040 (16384) | +0.022 [-0.006, +0.173] | +0.001 [-0.020, +0.018] (4096) |
| 01_sha256_transform/retpoline/data_pgot | -0.074 (16384) | -0.097 [-0.148, -0.084] | +0.050 [-0.124, +0.141] (4096) |
| 02_bch_encode/no_retpoline/data_pgot | +0.480 (128) | +4.420 [+0.507, +7.976] | +4.309 [+0.642, +7.006] (64) |
| 02_bch_encode/no_retpoline/func_pgot | +1.368 (64) | +1.353 [+1.330, +1.531] | +1.353 [+1.330, +1.531] (64) |
| 02_bch_encode/no_retpoline/all_pgot | +1.976 (128) | +6.272 [+1.906, +9.654] | +6.329 [+5.187, +8.414] (64) |
| 02_bch_encode/retpoline/data_pgot | +0.592 (64) | +7.152 [+0.466, +7.719] | +7.152 [+0.466, +7.719] (64) |
| 02_bch_encode/retpoline/func_pgot | +2.746 (64) | +2.835 [+2.813, +2.862] | +2.835 [+2.813, +2.862] (64) |
| 02_bch_encode/retpoline/all_pgot | +3.252 (64) | +9.648 [+3.060, +10.382] | +9.648 [+3.060, +10.382] (64) |
| 03_zlib_deflate/no_retpoline/data_pgot | +0.466 (32) | -0.448 [-0.480, -0.324] | -0.315 [-1.454, -0.312] (16) |
| 03_zlib_deflate/no_retpoline/func_pgot | -0.164 (32) | -1.117 [-1.574, +0.988] | -0.575 [-1.455, +0.911] (16) |
| 03_zlib_deflate/no_retpoline/all_pgot | +1.359 (16) | +0.962 [-0.484, +1.481] | +0.962 [-0.484, +1.481] (16) |
| 03_zlib_deflate/retpoline/data_pgot | +1.713 (32) | +2.271 [+1.711, +2.623] | +1.730 [+1.279, +1.791] (16) |
| 03_zlib_deflate/retpoline/func_pgot | -0.065 (16) | -0.362 [-0.597, -0.077] | -0.362 [-0.597, -0.077] (16) |
| 03_zlib_deflate/retpoline/all_pgot | -0.658 (32) | -0.390 [-0.396, -0.375] | -0.579 [-1.149, -0.399] (16) |
| 04_zstd_decompress/no_retpoline/data_pgot | -0.278 (256) | -0.195 [-0.287, -0.031] | -0.411 [-0.470, -0.287] (16) |
| 04_zstd_decompress/no_retpoline/func_pgot | +0.329 (128) | +0.331 [+0.308, +0.460] | +0.225 [-0.015, +0.379] (16) |
| 04_zstd_decompress/no_retpoline/all_pgot | +1.383 (32) | +1.130 [+1.078, +1.227] | +1.250 [+1.217, +1.441] (16) |
| 04_zstd_decompress/retpoline/data_pgot | -0.313 (128) | -0.352 [-0.982, -0.269] | -0.190 [-0.223, -0.035] (16) |
| 04_zstd_decompress/retpoline/func_pgot | +7.251 (128) | +7.693 [+7.563, +8.864] | +7.789 [+7.391, +7.834] (16) |
| 04_zstd_decompress/retpoline/all_pgot | +6.230 (128) | +6.397 [+5.552, +6.399] | +6.624 [+6.592, +6.642] (16) |
