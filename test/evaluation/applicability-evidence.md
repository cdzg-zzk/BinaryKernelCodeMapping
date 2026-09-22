# Prospective applicability: actual built-in exports

Observed 2026-09-12. This extends group D's frozen eight-case cohort with
actual construction, registration and functional evidence for its two checker
passes. The complete unmodified `xxh32` and `sort` APIs execute from the running
Ubuntu `5.15.0-119-generic` kernel. No algorithm owner module is introduced.
The private KVM guest uses package version `5.15.0-119.129` and debug-image
build ID `822098bf89027e54e3aa301e90cc5b8e5c80f479`.

Current registration update: the same two roots pass [the identity-checked v3 run](results/applicability-identity-qemu-20260912-attempt01/result.json)
and [independent replay](results/applicability-identity-qemu-20260912-attempt01/independent-audit.json).
The no-owner manager path verifies vmlinux's GNU build ID before STAGE.
The full 247/1,152 cases, two shared pages per root, callback counts and fresh
mapping restoration are unchanged. The detailed earlier runtime archives
below retain their original manager identity; this is not a new static cohort
or a performance trial.

The [cross-case ledger](applicability-ledger-evidence.md) now joins all six deployed cases with the unchanged fixed cohort. It reconstructs declared closure functions, source/generated pages, helper slots, final Clocktime source scope and current algorithm support. Current-owner full kernel workloads remain open where shown in that ledger; loading an owner is not classified as kernel-domain functional success.

## Fixed cohort and observed stages

The revised static batch completed all eight prospective cases with the
patched checker. It records two PASS and six FAIL outcomes. The earlier
interrupted capture remains preserved as historical evidence; it is not mixed
with this complete batch. Source ownership classifications are independent of
checker execution state.

| Root | Checker | Visited functions | Dependency/build observation | Carrier and functional outcome |
| --- | --- | ---: | --- | --- |
| `xxh32` | PASS | 1 | Explicit input and seed; return thunk retained in final carrier | 247 kernel and 247 user observations agree with independent XXH32 oracle |
| `crc32_le` | FAIL | 2 | One absolute-address lookup-table reference | Not constructed |
| `sha256` | FAIL | 5 | 18 absolute-address findings; 14 instrumentation sites | Not constructed |
| `hex_dump_to_buffer` | FAIL | 1,834 | 6,405 static references, 408 indirect sites, 2,230 instrumentation sites, 3,542 hard failures and 716 unresolved records across 347 functions | Not constructed |
| `string_escape_mem` | FAIL | 2 | Four absolute-address table references | Not constructed |
| `sort` | PASS | 3 | Five indirect sites; caller-owned array and callbacks | 1,152 kernel and 1,152 user observations agree with independent sorted-byte reference |
| `rhashtable_insert_slow` | FAIL | 1,844 | 6,398 static references, 411 indirect sites, 2,232 instrumentation sites, 3,530 hard failures and 721 unresolved records; kernel container, allocation, RCU and locking | Not constructed; environment semantics require state/synchronization redesign |
| `get_random_bytes` | FAIL | 28 | 94 static references, 36 instrumentation sites, 36 hard failures and four unresolved records; kernel-private evolving RNG state | Not constructed; state ownership remains outside the code-page contract |

The revised static results are archived with their commands and source snapshot
in the [complete batch record](results/applicability-revised-20260912/README.md);
the earlier six-result capture remains in the [historical terminal audit](results/applicability-terminal-20260912/README.md).
Both guest exports rerun the normal checker successfully before construction.
Visited functions count the checker traversal, not the final symbol/page
closure. In particular, the checker does not count the retained XXH32 return
thunk as a visited function. Static rejection describes this executable build
and current tooling; it does not establish semantic impossibility.
The separate retrospective LZ4/BCH/XZ/Clocktime cohort retains its existing
deployment and adaptation evidence and is not added to a success denominator.

## Complete typed functional protocol

The same test driver engine calls the actual public kernel imports in a
separate GPL observation module and the exported user API through `dlsym`.
Assignments are type-checked against installed exact119 public kernel headers;
the guest additionally compiles assertions against each actual generated
`vkso_types.h`. The swap callback's size parameter is `int`, while the API
element count and width are `size_t`. All checks are outside performance
measurement.

**XXH32:** seven known-answer strings and 240 boundary cases cover lengths
0–33 around 4/16-byte algorithm boundaries and 4,095/4,096/4,097 bytes, four
seeds, and offsets 0/1/3 from aligned allocation. Each result includes the
complete input bytes, digest, input-preservation and guard checks. A portable
driver reference performs byte loads; offline replay independently computes
every result using installed libxxhash 0.8.1. No copied kernel implementation
is used as the resident-export backend.

**Sort:** 6 element counts (0/1/2/3/17/64), 6 widths (1/3/4/8/12/16 bytes),
2 alignments, 4 input patterns, 2 comparison directions, and default/custom
swap produce 1,152 cases per domain. Patterns are ascending, descending,
duplicates and a seeded permutation. The comparator orders complete element
bytes, so equal keys are byte-identical and stability does not affect the
reference. Every case records full input/expected/actual bytes, permutation,
ordering, guards, callback arguments and callback counts. The driver uses
insertion sort as its reference; the offline auditor independently regenerates
inputs and uses Python byte ordering. Each domain observes 95,384 comparator
calls and 35,252 custom-swap calls, with identical per-case results and counts.
User callbacks are local C functions compiled with explicit stack realignment;
this is the callback configuration tested, not a claim about arbitrary callback
ABIs.

The kernel and user records total 2,798 API observations across 1,399 distinct
test cases. These are functional coverage counts, not independent performance
trials or an exhaustive proof over the input spaces.

## Actual backing and dependency bindings

The guest uses the existing `vkso init` / `vkso exec` workflow, including the
then-current checker, KRG generation, PIC exporter, manager and registration
module. Copied prepared workflow sources were byte-compared with the repository
at that session (`vkso`, three Python/text files in each of `make_dll` and
`kernel_cgd`, and the supplied manager source); they agreed at capture time. Later checker
and helper-binding revisions are separate source identities. The launcher
archives the actual payload files. The original two target algorithms are
neither rebuilt nor edited.

| Root | Source-backed executable pages | Generated executable support pages | External Shim DSO | Algorithm source changes |
| --- | ---: | ---: | --- | ---: |
| `xxh32` | 2 | 0 | None | 0 |
| `sort` | 2 | 1 | None | 0 |

XXH32's pages contain the algorithm and its original return thunk. Sort shares
the two pages containing `sort`, `sort_r` and `do_swap`; the existing exporter
generates a separate page containing four indirect-jump thunks and a return.
The replacement thunks retain relative target positions and transfer to the
domain-local callbacks. Their bytes and ELF locations were independently
checked. This third page is ordinary carrier-backed support, not a shared
kernel page. These counts do not include writable loader metadata, callback
code, page tables or registration support and are not a net-memory result.

During each active hold, a separate loader faults every declared source-backed
page and captures raw pagemap entries plus source PFNs. All four declared
pages across the two carriers match their kernel PFNs and have RX mappings.
The typed driver's `dladdr` identity and API address are checked against the
actual carrier ELF; the root's file offset maps to the corresponding built-in
kernel symbol. The PFN observer and functional driver are separate processes
using the same registered inode; no PFN observation of the typed driver's own
page tables is claimed.

After each `exec` restores the carrier, fresh mappings have PFNs different
from their former kernel sources. The experiment modules unload and the guest
powers off without panic, BUG or WARNING. The inherited `virtio_blk` module
remains until shutdown as the guest disk driver. Fresh-mapping restoration
does not measure old live mappings, original-byte recovery or transactional
failure handling.

## Artifacts and verification

- [Attempt 01](results/applicability-runtime-qemu-20260912-attempt01/result.json)
  stopped at observation-driver compilation because `linux/mm.h` was missing.
  No guest or API execution occurred. Adding that declaration include fixed
  the observer; this is not a candidate failure or algorithm change.
- [Attempt 02](results/applicability-runtime-qemu-20260912-attempt02/result.json)
  completed both exports and the entire functional protocol. The archive
  retains build commands, module and user binaries, guest payload/disk/console,
  generated headers/ELFs, per-case CSVs, import addresses, source/user PFNs and
  restoration records.
- [Independent replay](results/applicability-runtime-qemu-20260912-attempt02/functional-audit.json)
  passes input regeneration, complete matrices, independent references,
  kernel/user agreement, exact API ELF offsets, thunk bytes, declared-page
  coverage, PFN identity and fresh-mapping restoration.

Run a new complete experiment with ordinary KVM access:

```sh
python3 test/evaluation/applicability_runtime_qemu.py \
  --output test/evaluation/results/applicability-runtime-new
```

The launcher currently depends on the exact119 kernel package and the prepared
initramfs/payload documented by `--prepared`; it rejects an existing output
directory. It installs no host service and performs module operations solely
inside a private guest with no network or shared host filesystem.

Replay and validate the auditor using the completed real archive:

```sh
python3 test/evaluation/applicability_runtime_audit.py \
  test/evaluation/results/applicability-runtime-qemu-20260912-attempt02/evidence/validation
python3 test/evaluation/test_applicability_runtime_audit.py --evidence \
  test/evaluation/results/applicability-runtime-qemu-20260912-attempt02/evidence/validation
```

Eight auditor checks cover the real archive and meaningful corruptions:
duplicate IDs, an agreeing but wrong kernel/user digest, wrong sorted output,
callback binding, raw PFN identity, API location, and absent user evidence.
Missing evidence remains partial. These software checks do not add scientific
observations to the functional counts.

## Evaluation design consequence

[Orbit §5.3](https://www.usenix.org/system/files/osdi22-jing.pdf) demonstrates
generality through concrete tasks and their adaptations. This motivates making
VKSO's complete API, state ownership and callback configuration explicit.
[µFork §5](https://owl.eu.com/papers/ufork-sosp25.pdf) separates application
utility, memory and alternative mechanisms; accordingly the generated sort
thunk page is reported separately from kernel sharing, and these functional
cases do not substitute for the B resource ledger or E application workflow.
[Userspace Bypass §6](https://www.usenix.org/system/files/osdi23-zhou-zhe.pdf)
reports microbenchmarks and complete applications under different deployment
conditions. For VKSO, passing these APIs in KVM establishes functionality in
that environment and does not update the existing bare-metal performance
tables. The three original Evaluation sections were rechecked for this revision.

The eight-case static batch and cross-cohort source/structure ledger are now complete. Group D still needs the current-owner kernel workloads identified in that ledger, to be collected with group C. Existing B setup/net-memory gaps, C deployment repetitions and E's formal application measurements remain separate tasks.
