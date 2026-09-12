# Algorithm owner residency and memory-accounting scope

The current algorithm runners load dedicated, adapted `vkso_*` owners. They
do not replace the original kernel algorithms or redirect their kernel
callers. This source/build distinction is separate from active PFN equality
between an owner and its user carrier.

## Exact 5.15.0-119-generic evidence

| Algorithm component | Original implementation in this kernel | Dedicated owner | Accounting consequence |
| --- | --- | --- | --- |
| LZ4 decompression | `CONFIG_LZ4_DECOMPRESS=y`; original decompress entry points remain in non-init `.text`; `lz4_uncompress` calls the original `LZ4_decompress_safe` | `vkso_lz4.ko` contains renamed `vkso_LZ4_*` code | Original built-in decoder remains resident when the dedicated decoder is loaded |
| LZ4 compression | `CONFIG_LZ4_COMPRESS=m`; `lib/lz4/lz4_compress.ko` supplies original API; crypto LZ4 references that API | Same dedicated LZ4 owner | Configuration alone does not establish that the original compression module is loaded |
| BCH | `CONFIG_BCH=m`; `lib/bch.ko` supplies original API; NAND core references `bch_*` | `vkso_bch.ko` supplies renamed API and private helper bindings | Original BCH residency depends on module load state; the dedicated owner is an additional allocation |
| XZ | `CONFIG_XZ_DEC=y`; original decoder entry points remain in non-init `.text`; SquashFS still calls `xz_dec_reset/run` | `vkso_xz.ko` supplies renamed API, single-stream configuration and private helper bindings | Original built-in decoder remains resident when the dedicated owner is loaded |

The [captured configuration, symbol/caller and build evidence](results/owner-residency-20260912/)
records the exact source paths and commands. The owner Makefiles use distinct
API names, and the runners only load/unload their own `vkso_*` modules. The
ordinary host snapshot during this audit had none of `bch`, `lz4_compress` or
the three dedicated owners loaded. That snapshot is not a reconstruction of
the historical benchmark sessions.

## Required B scenarios

For the newly loaded owner scenario, count the complete dedicated module
allocation, carrier, private support pages, page tables and registration
infrastructure. Original built-in LZ4 decompression and XZ stay on both sides
of that comparison. Matching a user PFN to a dedicated owner proves physical
sharing with that owner; it does not show that the original kernel copy has
been removed, nor does it determine the net memory difference by itself.

For an already resident target, report the marginal cost conditional on that
specific adapted owner already being present. Artificially preloading it is
an explicit experimental condition, not evidence that existing kernel
consumers needed it. A claim about eliminating existing kernel/user
duplication additionally requires reuse or replacement of the implementation
the original kernel consumers actually call, with those consumers validated.
The Clocktime replacement case supplies a separate kind of evidence and must
not be inferred from the dedicated algorithm owners.

These findings determine the ownership and baseline rows of the B memory
ledger. They supply no measured page totals or net-memory saving. Actual
same-session accounting and the kernel-side adaptation-cost measurements
remain required.
