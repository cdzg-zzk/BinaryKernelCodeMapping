# Cross-case applicability and adaptation ledger

Updated 2026-09-12. This joins the frozen eight prospective cases with the
four retrospective integrations, without changing the denominator or running
new physical performance trials. The [ledger](results/applicability-ledger-20260912-attempt06/ledger.json)
and [replay](results/applicability-ledger-20260912-attempt06/independent-audit.json)
retain actual carrier metadata/ELFs, PFN records, source snapshots, complete
patches and the manually specified interpretation of each case.

## Declared closure and bindings

| Case | Declared code functions | Resident thunk bodies | Source text / RO / shared-state pages | Generated carrier text pages | External helper function slots | Other explicit bindings |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| xxh32 | 1 | 1 | 2 / 0 / 0 | 0 | 0 | Input pointer and seed |
| sort | 3 | 0 | 2 / 0 / 0 | 1 | 0 | Comparator and optional swap parameters |
| LZ4 | 3 | 0 | 4 / 1 / 0 | 0 | 3 | Caller-owned input, output and work memory |
| BCH | 11 | 0 | 3 / 1 / 0 | 0 | 4 | Caller-domain control, tables and codewords |
| XZ | 20 | 0 | 3 / 1 / 0 | 0 | 4 | Caller-domain decoder and private CRC table |
| Clocktime | 9 | 4 | 2 / 0 / 1 | 1 | 0 | Two failure callbacks and three data addresses in 40-byte context |

Code functions count positive-extent resolved `STT_FUNC` starts on declared
source text pages, deduplicated by address. Thunks are separate; Clocktime's
`__x86_indirect_thunk_array` and `__x86_indirect_thunk_rax` alias one body.
Generated code and incidental functions sharing a physical page are excluded
from the function count. This describes the exported closure, not the entire
owner API or all reader code in the paper's separate byte ledger. For example,
Clocktime's kernel-only call to `vkso_time_apply_offset` belongs to the broader
reader ledger but is absent from the user export's dependency roots.

KRG extents may include padding and are not summed as ELF function-body bytes.
The declared source pages total 20 across the six case artifacts; each matches
its recorded kernel PFN. They are observations in separate deployments, not a
simultaneous 20-page allocation or a net-memory saving. Generated text counts
cover the carrier itself; external Shim code, private data, page tables and
registration support remain outside this column.

The eleven algorithm slots are eight-byte private objects. Actual owner ELF
relocations initialize them to kernel helpers; carrier relocations bind their
user targets. LZ4 uses the three unique alignment bridges to libc memory
helpers. BCH binds allocation, free, copy and fill; XZ binds allocation, free,
copy and move; the current XZ memcpy slot uses the explicit libc ABI bridge. The auditor reconstructs both target lists from ELF relocations.
Unused undefined declarations and module metadata pointers are not counted
as callable helper slots. Sort's callbacks are API arguments, not stored PGOT
entries. Clocktime has no dynamic helper relocation: disassembly of the real
private binder confirms five writes into its 40-byte data area, whose source
declarations distinguish two function and three data pointers.

## Source adaptation

The [current algorithm source ledger](../section63/results/source-ledger/adaptation/README.md)
includes the shared BCH syndrome and XZ dictionary-loop rewrites. The fixed
candidate cohort and historical PFN observations retain their original scope.
Current performance, source identity and helper checks belong to section 6.3.

| Algorithm | Compared C/header files | Added / deleted code lines | Added / deleted physical lines | Owner support SLOC | Kbuild noncomment lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| LZ4 | 3 | 45 / 7 | 59 / 9 | 18 | 25 |
| BCH | 1 | 41 / 11 | 60 / 14 | 19 | 17 |
| XZ | 8 | 64 / 19 | 75 / 21 | 27 | 26 |

Owner support is each `module_meta.c`; it includes the private slot declarations
and cooperative descriptor/init calls. The common `owner.h` implementation is
archived once, rather than attributed independently to each algorithm. Generic
exporter, Shim, user-baseline compatibility and benchmark code are separate
infrastructure. LZ4 and XZ binding JSON files are retained as configuration, not C SLOC.
The source baseline is the retained Ubuntu 5.15.0-119.129 source package, matching
the distribution release used by the new Matched controls.
The owner-support files retain 18/19/27 SLOC for LZ4/BCH/XZ. The current
algorithm build records and source snapshots are retained with section 6.3.
The older cross-case binary ledger describes its recorded deployments; it is
not a claim that subsequent source rewrites preserve every machine-code byte.

Clocktime requires state and interface restructuring rather than a few helper
edits. The final semantic manifest is reconstructed from M11 (`adfe313`) plus
the final fallback-boundary ranges (`6656f97`). The original Linux 5.15.198
files were recovered from the [official source archive](https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.198.tar.xz),
and both Git endpoints and all compared sources are preserved. Every original
M11 row and final affected range is recounted with the existing lexical policy.

| Clocktime semantic scope | Raw SLOC | Final VKSO SLOC |
| --- | ---: | ---: |
| Runtime function | 857 | 885 |
| Runtime mechanism | 490 | 363 |
| Feature-specific build/link | 158 | 57 |
| Product total | 1,505 | 1,305 |

The total is implementation scope, not added-line churn. Common reusable-text
infrastructure (84 SLOC) and validation (366 SLOC) remain separate. All current
product ranges equal the final frozen source ranges; the current evaluation
work has not changed those ranges. The full-file supplementary comparison
covers 32 product-bearing files: +1,740/−482 physical lines and +1,393/−343
lexical code lines against upstream, with new project files compared to empty.
This wider diff also contains validation and configuration branches within
those files, so it is not presented as product-only adaptation SLOC. Complete
patch replay recreates all 32 files. No line count is converted to person-hours.

## Build and execution scope

| Case | Build/ABI restriction | User execution | Kernel execution evidence |
| --- | --- | --- | --- |
| xxh32 | Unmodified default exact119 binary and original return thunk | 247 independent-reference cases | Same 247 cases through actual public built-in import |
| sort | Default exact119 binary; generated thunk page; tested callbacks use stack realignment and original `int` swap width | 1,152 complete cases | Same 1,152 cases and callback counts |
| LZ4 | Full owner sources; ftrace removed from algorithm objects; native returns/indirect calls; two selected exported APIs | Complete component and CLI workflows | Same registered owner; all 12 full files, both block sizes and independent cross-decodes pass in 792 three-backend trials |
| BCH | Scalar exact119 Kbuild; no algorithm ftrace/stack-protector/sanitizer instrumentation or jump tables; runtime m/t retained | Original full matrix with current owner | Same registered owner; 10,752 correctness decode checks and 1,056 timing rows pass across three kernel backends |
| XZ | Full documented XZ_SINGLE/x86-BCJ/internal-CRC configuration; scalar build and omitted kernel-only instrumentation | Three complete input files and full matrix | Same registered owner; 99 three-backend full-file trials pass |
| Clocktime | Linux 5.15.198 Normal; shared-text instrumentation controls and retained thunk/ITS handling | A's completed campaign and ABI records | A's public kernel readers, writer and concurrent workloads |

LZ4/BCH/XZ export 2/4/5 requested APIs respectively. The three LZ4 closure
functions are the two requested APIs and `LZ4_compress_fast_extState`; retaining
the owner's complete API source does not mean all APIs were exported or tested.
[The kernel observers](kernel-cost-evidence.md) import public APIs and record
their actual addresses and providers. They run after the existing user
workflow and before the same registration is released. These full kernel
workloads close the previous C/D functional handoff; physical cost remains C work.

The fixed prospective cohort remains two checker passes and six rejections.
Absolute table addresses and unspecialized formatting dependencies are
binary/tool limitations; kernel container synchronization and evolving RNG
state introduce additional semantic requirements. Failed cases remain in the
ledger with construction/runtime marked unattempted. The retrospective four
cases and the first-touch assembly mechanism benchmark do not enlarge the
prospective success numerator.

## Reproduction and remaining work

```sh
python3 test/evaluation/applicability_ledger.py --linux-tarball /path/to/linux-5.15.198.tar.xz \
  --output test/evaluation/results/applicability-ledger-NEW
python3 test/evaluation/audit_applicability_ledger.py \
  test/evaluation/results/applicability-ledger-NEW
```

The collector selects the documented attempt04 algorithm source ledger and the
three current-owner kernel-cost archives. Optional `--algorithm-source` and
`--algorithm-archive NAME=PATH` select explicit inputs. Their contents are copied
into the joined archive. The earlier four negative checks reject an incorrect
PFN, a consistently misstated binding, an omitted candidate and an altered
patch output; the kernel-cost audit adds full matrix and provider checks.

Attempt 06 updates the complete joined ledger with current two-domain runtime
evidence. Attempt 05 retains its earlier owner/support identities. Earlier attempts preserve collector
integration failures/partial outputs: missing private object names in the ELF,
an unfiltered retrospective list and an assumed LZ4 Kbuild file. These are not
additional candidate failures or runtime experiments. The structure, source
adaptation and build/ABI ledger is now populated for all six deployed cases.
Together with the actual kernel workloads, D's fixed candidate, source,
binding, build and two-domain functional deliverables are complete. B resource
accounting and boundaries, C's physical performance and regression diagnosis,
and E's formal workflow collection remain outstanding work.
