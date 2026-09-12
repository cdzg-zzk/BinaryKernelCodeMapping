# Applicability: source semantics and static-result scope

Source review: 2026-09-12. The candidate list remains the eight entries frozen
on 2026-09-11; none was replaced after seeing a checker result. The four existing
integrations form a separate retrospective cohort. These are selected cases,
not a random sample of Linux or a basis for a whole-kernel success percentage.

The semantic reading uses
`/usr/src/linux-source-5.15.0/linux-source-5.15.0/`. This tree can contain newer
5.15 backports than the selected 5.15.0-119-generic image. It informs ownership
and interface requirements; actual static decisions use that image's final
`/usr/lib/debug/boot/vmlinux-5.15.0-119-generic`. No runtime result follows from
the source reading alone.

## Candidate semantics

| Entry | Source evidence | Ownership and environment requirements | Semantic assessment |
| --- | --- | --- | --- |
| `xxh32` | `lib/xxhash.c:102`, complete buffer/seed function | Caller provides buffer, length and scalar seed; working state is local and scalar constants are embedded | Explicit-input computation candidate. Static acceptance does not establish carrier construction or runtime compatibility. |
| `crc32_le` | `lib/crc32.c:195`, table-backed implementation | Caller supplies buffer, length and initial CRC; the selected build passes a lookup-table address to the calculation | Read-only dependency candidate. Address representation/binding must remain valid in both domains. |
| `sha256` | `lib/crypto/sha256.c:199`, plus update/final helpers | The complete API creates a local state, reads the caller's buffer and writes its digest; padding/constants and memory helpers are dependencies | Call-local state candidate. Actual image instrumentation and final code shape require separate inspection. |
| `hex_dump_to_buffer` | `lib/hexdump.c:127`, all group sizes and ASCII output | Caller owns input and bounded output; wider groups call `snprintf` with fixed integer/string formats; hex and character classification use tables | Formatting candidate with a real helper boundary. Do not silently reduce the API to its one-byte/no-ASCII branch to obtain a smaller closure. |
| `string_escape_mem` | `lib/string_helpers.c:519`, full flag/selector loop | Caller owns source, output, flags and optional selector string; helpers classify/escape characters and respect output capacity | Caller-owned transformation candidate with character tables and helper dependencies. Preserve the complete flag semantics. |
| `sort` | `lib/sort.c:266`, `sort_r`, `do_cmp`, `do_swap` | Array is caller-owned; comparator and optional swap function are explicit indirect dependencies | Requires domain-local callback provisioning. Unresolved indirect targets are a closure/binding issue, not evidence that sorting semantically requires kernel privilege. |
| `rhashtable_insert_slow` | `lib/rhashtable.c:629`, `rhashtable_try_insert` | Uses kernel RCU, mutable bucket tables, bucket locking and possible rehash/allocation paths | The existing kernel-owned container cannot be directly shared as caller-local computation. State/synchronization redesign would be a separate implementation, so no carrier attempt is authorized by this candidate check. |
| `get_random_bytes` | `drivers/char/random.c:437`, `_get_random_bytes`, `crng_make_state` | Depends on evolving global/per-CPU CRNG state, reseeding and locks; caller output ownership does not make generator state public | Kernel-private-state boundary case. Code-page export alone does not provide the required state semantics; the fixed plan withholds carrier construction. |

These assessments classify semantic requirements, not completed adaptation.
The prospective cases have no new registration or runtime test in this batch.
Actual modified SLOC, carrier pages and runtime correctness must come from
the later permitted construction/validation, not from estimates in this table.

## Interpreting the actual checker logs

The driver invokes the complete existing checker once per fixed entry, using
the configured Shim list with the requested entry itself removed from that
list. It records pass/fail/incomplete, visited functions, static references,
indirect sites, instrumentation, hard failures and missing/unanalysable functions
separately. A visited-function count describes this checker traversal with
those Shim boundaries; it is not automatically the final exported closure size.

The current unprivileged process can read symbol names from `/proc/kallsyms`,
but every address is zero. The checker stores these zeros and displays an
instruction's local offset as its “runtime” address. Source inspection of
`AcademicReuseEngine._load_kallsyms()` and `_get_runtime_display()` shows that
this map is used only for display; ELF symbol resolution and static analysis
use the configured image. Accordingly, use logged function/local offsets and
ELF facts, and treat the displayed runtime column as unavailable. No address
restriction was changed and no attempt was made to obtain privileged addresses.

`readelf -SW` shows that this debug image labels `.rodata` with `WA`, which
explains the checker's `WRITABLE` label for table references. ELF section flags
are not an observation of the booted kernel's final PTE permissions. Source
read-only tables, static ELF flags and live mapping permissions are distinct
fields; do not infer live writable mappings from this label.

Early complete records show `xxh32` checker PASS and `crc32_le` rejection of
an absolute table address. The latter is a build/address-representation obstacle,
not evidence that its lookup table is semantically private mutable state.
All remaining outcomes must be taken from the completed eight-case result set.
No checker or exporter code was changed to turn a rejection into a success.
