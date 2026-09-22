# Fixed applicability cases

The [candidate manifest](applicability-candidates.json) fixes this evaluation
batch before its new export attempts. It contains eight prospective API cases
and four explicitly retrospective integrations. “Prospective” means selected
before this batch, not that the project has never previously explored the API:
xxHash appears in repository examples, and several library algorithms already
appear in copied-closure experiments. Those histories are not counted as
successful resident exports without the corresponding deployment evidence.

This is a stratified case study selected by dependency and state shape, not a
random sample of Linux. Keep the two cohorts separate. Do not report their
combined success rate as the fraction of Linux functionality that is reusable.
The eight prospective entries remain in the table even if checks fail, a
carrier cannot be constructed, or their semantics require a different design.

| Prospective root | Selection dimension | Initial scope of attempt |
| --- | --- | --- |
| `xxh32` | Explicit buffer and scalar seed | Static inspection, then carrier construction if accepted |
| `crc32_le` | Buffer computation with read-only lookup table | Same |
| `sha256` | Complete digest with internal transform and temporary state | Same |
| `hex_dump_to_buffer` | Formatting into a caller-owned buffer | Same |
| `string_escape_mem` | Variable output and character classification | Same |
| `sort` | Caller-provided indirect comparator and optional swap callback | Inspect unresolved/bound control flow separately; construction alone is insufficient |
| `rhashtable_insert_slow` | Shared mutable container, allocation, RCU/synchronization | Static inspection first; no carrier attempt before environment semantics are resolved |
| `get_random_bytes` | Kernel-private evolving RNG state | Static inspection as a semantic boundary case; no carrier attempt before state ownership is resolved |

The intended final image is `/usr/lib/debug/boot/vmlinux-5.15.0-119-generic`.
The installed matching configuration has `CONFIG_XXHASH=y`, `CONFIG_CRC32=y`,
and `CONFIG_CRYPTO_LIB_SHA256=y`. Source reading uses the installed Linux 5.15
source tree, whose updates need not exactly match that old binary. Final-image
inspection determines executable closure/build results; source reading alone
does not certify byte identity or establish source-diff counts against that
image. The source path and this distinction are recorded in the manifest.

The four retrospective integrations are LZ4, BCH, XZ, and Clocktime. Import
their exact deployed entrypoints, archived closure records, carrier page maps,
correctness records, and adaptations. Their source/binding changes are
interventions that enabled the demonstrated configurations; success after
adaptation must remain distinct from the prospective default-build results.
Clocktime is an integrated subsystem replacement, while the three algorithms
use additional owner modules. See [algorithm evidence](algorithm-evidence.md).

## Separate the evidence stages

`applicability.py` records the actual static checker exit status and manifest
counts for every prospective root. The current checker can return PASS while
reporting instrumentation or indirect-control-flow sites. This follows its
`generate_report()` implementation: hard failures produce exit 1,
missing/unanalyzable dependencies produce exit 2, and otherwise it returns 0.
Therefore PASS is recorded as `checker_pass`, with those counts preserved;
it is not translated into “safe complete export” or “runtime success.”

With `--build-carriers`, the six computational/callback cases can proceed
through the existing `vkso build` pipeline after a checker pass. The command
does not skip its normal checks and never registers pages or executes the
generated functions. A successfully constructed carrier is labeled
`constructed_semantics_unverified`. The two kernel-environment boundary cases
remain static-only until their semantics have been addressed. No failure
automatically authorizes changes to the exporter or kernel mechanisms.

Use the explicit same-boot, same-final-image KRG cache after its first complete
construction rather than regenerating the entire kernel graph for each API.
Save every check/build log and result separately. Tool execution errors without
a complete manifest stop the batch; checker rejection/incompleteness remain
case results and do not remove the candidate from the denominator.

Print the plan now; execute after Clocktime and the algorithm measurements:

```sh
python3 test/evaluation/applicability.py \
  --output test/evaluation/results/applicability-default-20260911 --build-carriers
```

Append `--execute` on the original kernel to perform the inspection. Like the
algorithm runner, it refuses work while the Clocktime service is active or
on another kernel. Its result file keeps static checks, carrier construction,
and runtime status separate. The observed source/protocol limitation remains
a group B concern and is not resolved by building a DSO.

## Remaining applicability deliverable

For every case, the final ledger needs the source/build identity, semantic
classification, checker-visited closure size, declared text/RO pages, PGOT
slots and helper classes, adaptation type and measured source changes,
carrier outcome, and actual kernel/user functional evidence where applicable.
Use separate reasons for kernel-private state, required state/interface
restructuring, unsupported instructions/build conditions, and incomplete
analysis. A tool limitation is not proof of semantic impossibility.

For constructed eligible carriers, implement the complete typed functional
driver using the generated API and compare against the actual kernel API and
a correct reference. For callback cases, record the callback binding itself.
Do not substitute a copied user implementation for resident export. Manual
adaptation counts must come from actual source diffs, not inferred effort.
Already tested correctness cases are imported instead of repeated merely to
enlarge a table.

Current status (2026-09-12): the revised static batch has terminal results for
all eight fixed cases, with two PASS and six FAIL. The earlier interrupted
capture is retained separately and is not mixed into the revised denominator.
Both passing roots, `xxh32` and `sort`, now have actual carrier, registered PFN
and full typed functional evidence from a private exact119 guest: 247 and
1,152 cases respectively, checked in each domain against independent
references. Sort uses an additional generated thunk page, separately counted
from its two shared kernel pages. See the
[consolidated evidence and reproduction commands](applicability-evidence.md).
The retrospective adaptation ledger remains outstanding, and the six static
failures have no carrier/runtime evidence. This selected cohort does not
establish a Linux-wide success rate.
