# BCH live-allocation observer protocol

`bch_heap_probe.c` observes one existing same-source native DSO or one registered
BCH carrier per loader process. It includes the unchanged original
`test/test_BCH/src/bch_bench.c`, renaming only `main`, and directly reuses
`load_backend`, `new_control`, `prng_next`, `generate_error_vector`,
`prepare_decode_context`, `verify_decode`, and `free_decode_context`.
No algorithm implementation is copied into the observer.

Build from the repository root:

```sh
gcc -O2 -g -std=gnu11 -Wall -Wextra -shared -fPIC \
  test/evaluation/bch_heap_probe.c -ldl -o /tmp/libbch-heap-probe.so
```

The launcher may additionally define string-literal macros
`PROBE_BENCH_SHA256`, `PROBE_ADAPTED_SHA256`, `PROBE_HEADER_SHA256`, and
`PROBE_SHIM_SHA256` from its actually consumed files. Omitted identities are
reported as `unrecorded`, never guessed. Archive the helper and consumed source
files or their verified identities alongside observations. The helper's
header is the actual vendor Linux 5.15 `include/linux/bch.h`; the two small
private polynomial layouts are copied exactly from `adapted/bch.c:123–136`
solely to compute allocation sizes.

## API and snapshots

The five transition functions return `0` on success and negative errno for
observer contract or allocator-verification failures. Original benchmark
helpers retain their original behavior: failed allocation, symbol lookup, API
initialization, or correctness checks terminate the loader with a nonzero exit.
Such termination is a failed observation and must be retained by the launcher.
After every successful transition, require JSON `report_ok == true` and
`last_errno == 0`; inventory errors can first be detected while reporting.

| Function | State after successful call |
|---|---|
| `int probe_load(const char *path, int carrier)` | `loaded`; load native when `carrier=0`, registered carrier when `1`; no BCH controls yet |
| `int probe_initialize(void)` | `initialized`; one real m13/t4 control and one m13/t8 control, plus their two codewords |
| `int probe_activate(int case_index)` | `active`; index 0=t4 or 1=t8; one original full-decode context stays allocated after successful verification |
| `int probe_deactivate(void)` | `deactivated`; free only that active context |
| `int probe_release(void)` | `released`; free any active context, both codewords and both controls; leave the DSO loaded |
| `const char *probe_report(void)` | Return current inventory in a fixed 32 KiB static JSON buffer |

The usual sequence is before/load/initialize/activate(0)/deactivate/
activate(1)/deactivate/release. An outer wrapper may add more process or mapping
snapshots. Load the observation helper before the process baseline, and keep
its memory separate from the BCH allocation ledger. The interface is intended
for serial, single-threaded observation in one loader. Calls do not perform
performance timing, registration, module loading, or unloading.

Both codewords use the original payload seed `0xb4c00000 + case_index`, 512
payload bytes, and 7/13 ECC bytes. Activation uses the original correctness
seed `0x63c5a17e9b ^ (case_index << 48) ^ errors`, with trial 0 and errors=t.
It calls the original full decode, checks the exact returned error-location
set, flips the returned locations, compares the entire payload+ECC codeword,
then flips back just as the original verifier does. The live context therefore
holds the corrupted input after verification. Each successful activation adds
one actual `verification_checks`; this focused observer does not replace the
separate full 128-vector, all-error-count, three-backend correctness run.

## JSON and allocation interpretation

Top-level fields are `schema_version` (1), `stage`, `backend`, `active_case`
(-1 when inactive), `allocator_verified`, `dso_path`, `api_symbols`,
`api_addresses`, `allocator`, `source_identity`, `abi`, `geometry_checks`,
`verification_checks`, `cases`, `active_vector`, `allocations`,
`live_allocation_count`, `live_requested_bytes`, `live_usable_bytes`,
`last_errno`, and `report_ok`.

Each allocation contains integer `case_index`, `t`, `address`,
`requested_bytes`, `usable_bytes`, and string `category`, `name`.
The 14 control entries per case are `bch_control`, `a_pow_tab`, `a_log_tab`,
`mod8_tab`, `ecc_buf`, `ecc_buf2`, `xi_tab`, `syn`, `cache`, `elp`, and
`poly_2t[0]` through `poly_2t[3]`. Workload entries are `codeword`, plus
`work`, `difference`, and `errloc` for the single active case. Difference is
allocated even in full-decode mode because the original preparation helper
allocates it unconditionally. No Python buffers are counted as BCH memory.

Allocation formulas are those of `adapted/bch.c:1411–1432`:

| Entry | Requested bytes, with w=ceil(m*t/32) |
|---|---|
| bch_control | sizeof public-header struct, 136 on this x86-64 build |
| a_pow_tab, a_log_tab | each (n+1)*2 |
| mod8_tab | w*1024*4 |
| ecc_buf, ecc_buf2 | each w*4 |
| xi_tab | m*4 |
| syn, cache | each 2*t*4 |
| elp | (t+1)*12 |
| each poly_2t | 4+(2*t+1)*4 |

The two control inventories request 41,448 and 49,896 bytes. Initialized
controls+codewords total 30 allocations and 92,388 requested bytes. Active t4
adds 542 bytes (total 92,930); active t8 adds 570 bytes (total 92,958), each
with 33 allocations. These requested totals follow actual source allocation
sizes; `malloc_usable_size` is measured independently and can vary with
allocator/process state. Released inventory is empty. Do not turn summed
object sizes into distinct physical-page counts: the outer observer must
union the pages touched by the recorded address ranges.

The helper verifies glibc versioned malloc/calloc/free/malloc_usable_size
resolution, and reads actual dynamic relocation slots before any usable-size
call. Native malloc/calloc/free import targets must match libc. Carrier
`__kmalloc`/`kfree` slots must match the loaded `libshim.so` helpers, whose
own malloc/free slots must match libc. Source inspection establishes that
the current native compatibility macros map allocations to malloc/calloc and
free (`vendor/parrot-bch/standalone/linux/kernel.h:9–11`), while the current
shim maps `__kmalloc` to malloc and `kfree` to free (`make_dll/shim.c:50–65`).
The launcher must preserve those actual source/build identities; checking
symbol binding alone does not prove arbitrary replacement code has those
semantics. Symbol lookup or import-binding differences cause explicit failure.

In `allocator`, addresses `malloc`, `calloc`, `free`, `malloc_usable_size`
refer to libc. The three-entry `native_import_targets` and
`shim_import_targets` arrays are ordered malloc/calloc/free (zero where that
role has no such import). The two-entry `carrier_helper_targets` and
`carrier_slot_addresses` arrays are ordered __kmalloc/kfree. The latter are
actual user-space slot addresses; matching contents are checked in C.
`link_map.l_addr` provides ELF load bias even for the sparse carrier with a
nonzero first PT_LOAD virtual address. Slots need not appear in `.dynsym` as
exported objects; their public dynamic relocations identify their locations.

`abi` reports field offsets and structure sizes. `active_vector` is null when
inactive and otherwise records mode, trial, errors, seed, actual injected
positions, and verified returned positions. `cases` retains geometry, payload
seed, and per-case actual verification counts even after release.

Scope is **live retained BCH controls and original workload allocations**.
It excludes transient generator-polynomial/roots allocations freed before
`bch_init` returns, allocator metadata and arenas, unrelated process/runtime
allocations, and the observation helper itself. Releasing objects does not
imply glibc returns their pages to the kernel; the outer mappings/PFN snapshots
must record that behavior separately. This API does not claim whole-system
net memory savings.

## Local collector validation

On 2026-09-12 07:13 UTC, an ordinary-user native-only helper check passed on
5.15.0-119-generic/glibc 2.35. The final helper compiled with the command above
plus `-Werror`, without diagnostics. It loaded the existing
`test/test_BCH/build/libbch-kernel-native.so` (SHA-256
`f0bfedf54cbb16daf3462a955d54d2c2ab4c26a6110f0ceb74ced92de6aedf6e`).
The helper source SHA-256 was
`f9d12c973053a17c97a8d124cfebdf0e4441ce4210762fa197c2ae37d1009cf6`.

The ctypes check parsed every report, asserted `report_ok`/errno, exact live
counts and requested totals, usable>=requested for each allocation, and equal
injected/returned location sets on each active case. Actual observations:

| Phase | Allocations | Requested bytes | Usable bytes | Completed decode checks |
|---|---:|---:|---:|---:|
| before | 0 | 0 | 0 | 0 |
| loaded | 0 | 0 | 0 | 0 |
| initialized | 30 | 92388 | 92560 | 0 |
| active t4 | 33 | 92930 | 93128 | 1 |
| t4 deactivated | 30 | 92388 | 92560 | 1 |
| active t8 | 33 | 92958 | 93176 | 2 |
| t8 deactivated | 30 | 92388 | 92560 | 2 |
| released | 0 | 0 | 0 | 2 |

An attempted activation after release returned `-EINVAL`. This validates the
native collector interface and cleanup only; it is not a guest result,
multi-process accounting result, registered-carrier execution result, or
performance measurement. The carrier-specific binding checks still require
the separately orchestrated registered guest run.
