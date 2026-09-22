# xxh32 LKM and DSO Build

This directory builds the two DSO inputs used by
`test/test_first_call/matrix_bench`:

- `libclone_xxh32.so`: normal native userspace DSO.
- `zzk_xxh32_lkm.so`: stub DSO whose exported symbol metadata points at the
  LKM-backed code page used by the page-cache grafting mechanism.

Both use handwritten assembly so the benchmark compares the mapping mechanism,
not compiler-generated code differences.

## Current cooperative owner and API declaration

The owner now uses the shared VKSO descriptor/pin contract through
`vkso_owner.h`. Initialization publishes the permitted core ranges. The
`zzk_xxh32_kernel.S` and native assembly bodies are unchanged; `check-asm`
requires the full 338-byte function to match, permitting only trailing kernel
int3 padding after the return.

This assembly entry has no BTF FUNC prototype. `api.h` supplies its existing
SysV x86-64 declaration explicitly for the current `vkso --api-header` route.
The exporter still runs the closure checker and normal carrier construction;
the manager still checks owner/kernel identities and the complete page plan.
Header compilation checks syntax and named declarations, not semantic ABI
equivalence. Runtime byte comparison and independent XXH32 vectors validate
this supplied declaration and entry in the first-touch guest.

The older `stub-dso` target below uses the historical builder. Current guarded
registration is exercised by `test/evaluation/first_touch_qemu.py`, whose
source/build evidence is kept separately from the historical performance table.

## Build Order

The intended sequence is:

1. Build the LKM and the native DSO.
2. Verify that their exported function bodies are byte-identical.
3. Export the LKM-backed code layout into the stub DSO.
4. Copy the native and stub DSOs into `../matrix_bench`.

## Build LKM and Native DSO

```sh
make all
make check-asm
```

`make check-asm` rebuilds both `zzk_xxh32_lkm.ko` and
`libclone_xxh32.so` before comparing function bytes.

The `module` target also patches the LKM with BTF after Kbuild finishes:

```sh
pahole -J --btf_base=/sys/kernel/btf/vmlinux --skip_encoding_btf_enum64 zzk_xxh32_lkm.ko
```

This is needed because this environment's external-module build can print
`Skipping BTF generation ... due to unavailability of vmlinux` even though the
running kernel exposes base BTF at `/sys/kernel/btf/vmlinux`. Check the result
with:

```sh
readelf -S zzk_xxh32_lkm.ko | grep BTF
```

## Build All DSO Inputs

```sh
make dsos
```

This builds:

- `zzk_xxh32_lkm.ko`
- `libclone_xxh32.so`
- `libzzk_xxh32_lkm.so`
- `zzk_xxh32_lkm.so`

Install the two DSOs into the benchmark directory:

```sh
make install-to-bench
```

## Assembly Equivalence

Check that the native DSO function body matches the LKM function body:

```sh
make check-asm
```

The check compares the bytes of `clone_xxh32` in `libclone_xxh32.so` against
`zzk_xxh32` in `zzk_xxh32_lkm.ko`. The native assembly intentionally includes
the same unreachable `int3` byte after `ret`, so branch displacements and
function bytes remain identical.

## Notes

`stub-dso` uses the existing sparse LKM DSO builder:

```sh
make_dll/build_LKM_so.py
```

The builder names its direct output `libzzk_xxh32_lkm.so`; the Makefile copies
that file to `zzk_xxh32_lkm.so`, which is the name expected by the benchmark.
