# Cooperative owner lifetime and management-page exclusion

Historical protocol v2 evidence. The subsequent [v3 transaction results](registration-transaction-evidence.md) cover dynamic plans, rollback, query and retry.

Observed on 2026-09-12 in private Linux `5.15.0-119-generic` guests using the
full modified manager, page module and LZ4 owner. Group B now has evidence of
module references during active registration, refusal of active unload, and
release after backing removal. At this v2 checkpoint, dynamic transactions and cross-batch recovery were
unimplemented. Full file-operation boundaries and formal setup/resource results
remain unfinished after the later v3 work.

## Implementation exercised

[owner.h](../../page_cache_replace/owner.h) defines a page-aligned, full-page
`.vkso_owner` descriptor with a GPL-exported symbol, ABI, module pointer, source
version and complete core text/RO ranges. LZ4, BCH and XZ metadata instantiate
it and initialize ranges from the loaded module layout. All three owners
compile with exact119 headers. Only LZ4's new owner has completed runtime
validation in this update; earlier BCH/XZ results retain their old build.

Protocol version 2 carries descriptor symbol names and module `srcversion`.
The builder derives these from the actual owner ELF, writes
`owner_descriptors.txt`, and `vkso` installs it beside the page plan. The
manager transmits the manifest before source processing. The page module
acquires each symbol with `__symbol_get` before resolving source pages,
compares source versions and module ranges, and keeps each acquired owner
until the registry is empty. It holds the carrier file and a reference to
itself for that interval. Built-in pages have no unloadable module; their
existing explicit manifest remains the selection boundary.

`srcversion` identifies source inputs; it does **not** independently prove
compiler flags, complete ELF identity or all runtime rewriting. The full
build-identity contract remains part of the transaction work. The current
registry also permits only one active carrier mapping and retains its
256-entry capacity. This is an intermediate implementation of lifetime within
the batch protocol, not the final multi-transaction design.

The builder preserves module data offsets but zeroes the descriptor's entire
window in the private image and omits its relocations. It rejects direct
export of a management object. This prevents copying `THIS_MODULE` into the
carrier, without presenting the zero-filled window as a memory saving.
In the successful LZ4 carrier, that window is 4,096 bytes at offset 4,096
within a 12,288-byte private `.data` section; it contains only zero bytes,
and neither the descriptor nor `__this_module` is a dynamic symbol.

Each applied backup now records the actual source page, original mapping/index
and original uptodate state. Release checks source identity, holds the page
lock across cache-entry removal and user unmapping, restores the saved fields,
and drops the insertion reference before releasing owners. The file-fault and
fault-around paths in [Linux filemap.c](https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/filemap.c)
check page mapping under the page lock before installing mappings. The guest
observations below exercise persistent mappings and private COW; a sustained
concurrent-fault matrix remains part of B's transaction validation.

## Actual outcomes

The [owner fixture archive](results/registration-owner-qemu-20260912-attempt03/result.json)
uses boot ID `959acc5d-dbe9-4eda-ad52-b896a237b231`. Its saved source inputs,
module binaries, request results, manager logs and source PFN observations
retain the execution identity.

| Check | Result |
| --- | --- |
| Missing descriptor for a module source | EACCES, zero completed pages, both module references return to zero |
| Mismatched source version | ESTALE, zero completed pages, references return to zero |
| Attempt to share the management page | EACCES, zero completed pages, original file content retained |
| Active registration | LZ4 owner refcount 1; page-module refcount 1; user PFN matches source |
| Unload owner or page module while active | Both return nonzero; both modules remain loaded |
| Register a second carrier inode | EBUSY; second file remains original, references unchanged |
| Restore using the wrong mapping | EXDEV; active owner and page references retained |
| Private COW | Source bytes unchanged |
| Correct release with a persistent read mapping and a private COW mapping | Manager exits 0; read mapping sees original file bytes; private COW retains its modified byte; both module reference counts return to zero |
| Unload after release | Owner, observer and page module all unload successfully |

The separate [full LZ4 application archive](results/lz4-owner-qemu-20260912-attempt03/result.json)
uses boot ID `a0830dc8-c5d0-4515-b97b-a5d2cd2568e4`. All 24 Silesia input/block
pairs pass complete compression/decompression and stock cross-decoding checks.
The 48 operation traces match recorded carrier calls and the three libshim/
libc helper bindings. Four text pages and one RO page match source PFNs;
fresh post-release mappings no longer use those PFNs. The owner reference
count during registered CLI execution is 1, and all test modules unload.
Both final guests report no kernel panic, BUG or WARNING. No timing samples
from these functional runs enter the paper's performance tables.

## Preparation failures and validation

Owner attempt 01 fails module BTF validation before registration. With the
expanded owner metadata, pahole 1.25 emits enum information rejected by the
exact119 BTF validator unless `--skip_encoding_btf_enum64` is used. The three
algorithm runners now use that option, consistent with the
[Ubuntu kernel-team build correction](https://lists.ubuntu.com/archives/kernel-team/2024-January/148453.html).
It changes type metadata generation, not algorithm compiler flags.

Owner attempt 02 completes active pinning, conflict rejection, mapping recovery
and reference release, but final LZ4 unload fails because the newly added init
had no corresponding exit entry. Adding the module exit entry allows attempt
03 to finish. LZ4 application attempt 02 additionally exposed a manifest bug:
KRG names include `.ko`, so constructing a descriptor name by appending
`_owner` was incorrect. The builder now selects the unique global full-page
object in `.vkso_owner`, and `vkso` installs its manifest. All failed archives
remain distinct from the final passes.

The builder's 18 regression tests pass, including a management object carrying
an explicit module-pointer relocation: its private-image window becomes zero,
its management relocation disappears, and ordinary helper relocations remain.
Five shell cleanup tests also pass. These tests supplement the actual guest
results and do not stand in for transaction rollback or broader applicability.
