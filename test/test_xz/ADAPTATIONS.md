# XZ Embedded adaptation boundary

The decoder sources are the Linux 5.15 XZ Embedded implementation. The same
four C files are compiled into the owner LKM and the ordinary user-space DSO.
The format parser, LZMA2 range decoder, dictionary logic, x86 BCJ filter, CRC32
algorithm, return codes, and state transitions are shared.

The test-local environment adaptations are:

- namespace externally visible LKM symbols with `vkso_xz_`;
- expose the five selected APIs through GPL module exports in `module_meta.c`,
  allowing ordinary kernel consumers and the evaluation observer to import
  the same resident owner used for user-space export;
- select the documented `XZ_DEC_SINGLE` build mode, x86 BCJ, and internal
  CRC32 implementation;
- remove fentry, sanitizers, stack-protector calls, retpoline/return thunks,
  and SIMD/FPU code from the reusable owner-module closure;
- materialize the base of the two x86 BCJ tables and CRC32 table with a
  RIP-relative `lea` before indexed access, avoiding absolute kernel addresses;
- route `__kmalloc`, `kfree`, `memcpy`, and `memmove` through four
  owner-private writable function slots. The loaded module slots point to
  kernel helpers, while user relocations select domain-local helpers; the memcpy slot
  explicitly targets `vkso_abi_memcpy`, whose alignment bridge calls default libc memcpy;
- provide user-space types, unaligned accessors, allocation macros, and memory
  helpers in `userspace/xz_config.h`.

The shared `dict_repeat` source caches its buffer pointer, position and end,
then writes back the final position. It retains forward overlapping-match
expansion and dictionary wrap. User and owner builds use this rewrite; the
kernel Matched control retains the original Ubuntu loop, kernel CRC32 and
feature configuration under owner code-generation options. See the
[kernel protocol](../evaluation/xz-kernel-methods.md). The [source ledger](../evaluation/results/section63/source-ledger/README.md)
records the complete diff. No decoder branch or input is specialized for the benchmark.
Initialization is outside the timed region; each timed stream includes the
documented `xz_dec_reset()` followed by `xz_dec_run()`.
