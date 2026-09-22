# Mechanism evidence

Formal timings have no diagnostic counters. A separately compiled BCH module uses `PGOT_DIAGNOSTIC=1` and returns after its checks, emitting no raw timing records. Static evidence was generated from the actual formal objects; complete linked-module objdump output is saved in every routine/build directory.

## SHA-256

Origin and Data each have an 872-byte transform with 214 static instructions in both builds. Data contains the `pgot_k_table` slot reference; Origin references the constant table directly. Both contain zero indirect transfers and zero retpoline loops in the transform. Thus the small signed timing changes do not involve a new helper-call path.

## BCH

| Diagnostic site | Source operation | Executions per fixed encode |
|---|---|---:|
| 0 | `load_ecc8`: copy remaining ECC bytes to pad | 1 |
| 1 | `bch_encode`: copy ECC words into local r | 1 |
| 2 | `bch_encode`: copy local r back into ECC words | 1 |
| 3 | `store_ecc8`: copy remaining pad bytes to output | 1 |

`diagnostics/bch-helper-counts.csv` records these counts for Origin, Data, Func and All in both builds (32 records). Origin/Data contain four direct memcpy sites. Func/All contain four helper-slot references and either four ordinary indirect transfers (no retpoline) or four inline-retpoline loops. The additional direct memory call in the algorithm is memset in the no-ECC branch, not a rewritten memcpy site. Internal algorithm helpers remain direct.

For example, in `static-evidence/02_bch_encode-retpoline-bench_kmod.txt`, `load_ecc8_func_pgot` loads `pgot_memcpy_table` at relocation 0x489, then uses the call/pause/lfence loop at 0x4ab–0x4b5 and stores the target at (%rsp) before ret. The instruction context and all other sites are indexed in `binding-sites.csv` and `binding-contexts.md`. These are formal uninstrumented objects.

## zlib

Four rewritten source locations are enumerated in `helper-source-sites.csv`: CLEAR_HASH memset, read_buf memcpy, fill_window sliding-window memcpy, and copy_block pending-buffer memcpy. Macro expansion/inlining produces five helper-slot references in each Func/All object. Other direct memory-helper operations introduced through included code or compilation remain direct; Func-PGOT here means the existing selected source transformations, not replacement of every possible memory operation.

Origin already dispatches through its compression configuration table, so its retpoline object already has one protected indirect path. Data retains that one; Func/All have six. Data also changes code generation beyond a single address-load instruction. In the retpoline build, `zlib_tr_init` sizes are 2300/1123/2300/1123 bytes for Origin/Data/Func/All, and `zlib_deflateReset` sizes are 475/325/502/352 bytes. `function-sizes.csv` and the six `zlib-*.diff` files show the full comparison. These are static code sizes, not counts of dynamically retired instructions. They demonstrate nonlocal compiler effects but do not by themselves prove which change caused the small negative All timing.

## Zstd

Data redirects LL_defaultDTable, ML_defaultDTable, OF_defaultDTable and algoTime. Func redirects the existing memcpy/memset/memmove source locations across the five copied compilation units. Every rewritten source statement has its generated-file line and context in `helper-source-sites.csv`. The final objects contain 102 helper slot references and 109 protected indirect paths in each Func/All retpoline variant. Slot-reference and transfer counts need not coincide because a loaded target can feed multiple branches; neither number is a dynamic call count for the fixed input. Origin/Data already contain two protected indirect paths.

`closure_func_pgot_decompress.o` provides concrete examples: `pgot_ZSTD_execSequenceLast7_func_pgot.isra.0` references `pgot_memmove_table_func_pgot` at 0x5d3 and has its protected call at 0x5f7–0x609; `pgot_ZSTD_decompressBegin_func_pgot` references the memcpy slot at 0xb69. Checking only decompressDCtx would miss these lower-level sites. Static evidence and the Data/Func/All timing interventions together support the mechanism interpretation; they do not assign the full percentage solely to thunk instructions.

## Static object inventory

Text bytes sum function-symbol sizes; alignment padding is excluded. Relocations count static references, and retpoline loops count static pause sites in inspected algorithm functions. Timed body wrappers are excluded.

| Routine/build/variant | Text bytes | Data slot refs | Helper slot refs | Direct memory calls | Indirect transfers | Inline-retpoline loops |
|---|---:|---:|---:|---:|---:|---:|
| 01_sha256_transform/no_retpoline/origin | 872 | 0 | 0 | 0 | 0 | 0 |
| 01_sha256_transform/no_retpoline/data_pgot | 872 | 1 | 0 | 0 | 0 | 0 |
| 01_sha256_transform/retpoline/origin | 872 | 0 | 0 | 0 | 0 | 0 |
| 01_sha256_transform/retpoline/data_pgot | 872 | 1 | 0 | 0 | 0 | 0 |
| 02_bch_encode/no_retpoline/origin | 2356 | 0 | 0 | 5 | 0 | 0 |
| 02_bch_encode/no_retpoline/data_pgot | 2356 | 1 | 0 | 5 | 0 | 0 |
| 02_bch_encode/no_retpoline/func_pgot | 2355 | 0 | 4 | 1 | 4 | 0 |
| 02_bch_encode/no_retpoline/all_pgot | 2355 | 1 | 4 | 1 | 4 | 0 |
| 02_bch_encode/retpoline/origin | 2356 | 0 | 0 | 5 | 0 | 0 |
| 02_bch_encode/retpoline/data_pgot | 2356 | 1 | 0 | 5 | 0 | 0 |
| 02_bch_encode/retpoline/func_pgot | 2447 | 0 | 4 | 1 | 0 | 4 |
| 02_bch_encode/retpoline/all_pgot | 2447 | 1 | 4 | 1 | 0 | 4 |
| 03_zlib_deflate/no_retpoline/all_pgot | 25624 | 37 | 5 | 11 | 6 | 0 |
| 03_zlib_deflate/no_retpoline/data_pgot | 25604 | 37 | 0 | 16 | 1 | 0 |
| 03_zlib_deflate/no_retpoline/func_pgot | 27552 | 0 | 5 | 11 | 6 | 0 |
| 03_zlib_deflate/no_retpoline/origin | 27532 | 0 | 0 | 16 | 1 | 0 |
| 03_zlib_deflate/retpoline/all_pgot | 25766 | 37 | 5 | 11 | 0 | 6 |
| 03_zlib_deflate/retpoline/data_pgot | 25627 | 37 | 0 | 16 | 0 | 1 |
| 03_zlib_deflate/retpoline/func_pgot | 27694 | 0 | 5 | 11 | 0 | 6 |
| 03_zlib_deflate/retpoline/origin | 27555 | 0 | 0 | 16 | 0 | 1 |
| 04_zstd_decompress/no_retpoline/all_pgot | 45541 | 7 | 102 | 1 | 109 | 0 |
| 04_zstd_decompress/no_retpoline/data_pgot | 42620 | 7 | 0 | 29 | 2 | 0 |
| 04_zstd_decompress/no_retpoline/func_pgot | 46507 | 0 | 102 | 1 | 109 | 0 |
| 04_zstd_decompress/no_retpoline/origin | 43702 | 0 | 0 | 29 | 2 | 0 |
| 04_zstd_decompress/retpoline/all_pgot | 48111 | 7 | 102 | 1 | 0 | 109 |
| 04_zstd_decompress/retpoline/data_pgot | 42666 | 7 | 0 | 29 | 0 | 2 |
| 04_zstd_decompress/retpoline/func_pgot | 49077 | 0 | 102 | 1 | 0 | 109 |
| 04_zstd_decompress/retpoline/origin | 43748 | 0 | 0 | 29 | 0 | 2 |
