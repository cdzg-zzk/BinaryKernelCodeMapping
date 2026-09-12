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

## Observed expansion of the fourth candidate

A read-only snapshot at **2026-09-12 06:56:34 UTC** explains why the ongoing
`hex_dump_to_buffer` check has reached functions outside formatting. At capture,
controller PID 14474 and checker PID 15248 were live, and the campaign result
file contained only the first three completed candidates. The snapshot contained
1,608 first-enqueue events and 1,578 analysis-entry events; its last analysis
entry was `rpm_resume`. These are counts in an incomplete log, not a final
visited-function total or a fourth-candidate verdict. The original checker and
the eight-candidate selection were left unchanged.

The preserved queue messages reconstruct **44 first-discovery edges** from
`hex_dump_to_buffer` to `blkg_create`. The beginning is:

```text
hex_dump_to_buffer → snprintf → vsnprintf → format_decode
→ __warn_printk → vprintk → vprintk_deferred → vprintk_emit
→ console_unlock → __cond_resched → __schedule → panic
```

The remaining recorded ancestry proceeds through console unblank/redraw and
sysfs notification, then a lock slow path and task release, RCU allocation,
page reclaim, swap allocation, scheduled discard, and block-cgroup association:

```text
panic → unblank_screen → do_unblank_screen → redraw_screen → sysfs_notify
→ kernfs_find_and_get_ns → down_read → rwsem_down_read_slowpath → wake_up_q
→ __put_task_struct → task_numa_free → kvfree_call_rcu → __get_free_pages
→ alloc_pages → __alloc_pages → get_page_from_freelist → node_reclaim
→ __node_reclaim → shrink_node → shrink_node_memcgs → shrink_lruvec
→ shrink_inactive_list → shrink_page_list → add_to_swap → get_swap_page
→ get_swap_pages → scan_swap_map_slots → scan_swap_map_try_ssd_cluster
→ swap_do_scheduled_discard → blkdev_issue_discard → __blkdev_issue_discard
→ bio_associate_blkg → bio_associate_blkg_from_css → blkg_create
```

This is **static dependency ancestry, not an observed execution path**. The
checker records a queue edge only when a target is first added; an already
queued or visited target does not produce another such record. Consequently,
these messages neither recover the complete dependency graph nor establish
that all branch conditions on this chain can hold in one invocation.

Eight selected edges were checked directly against the configured exact119
debug ELF, whose GNU build ID is
`822098bf89027e54e3aa301e90cc5b8e5c80f479`. The checks read only those caller
bodies and retain short instruction windows:

- The three `hex_dump_to_buffer → snprintf` calls load the fixed format strings
  `%s%16.16llx`, `%s%8.8x`, and `%s%4.4x`.
- `snprintf → vsnprintf → format_decode → __warn_printk → vprintk` consists of
  actual direct calls in the image. The `format_decode` warning call references
  `Please remove unsupported %%%c in format string\n`.
- The selected `__schedule → panic` call references
  `corrupted stack end detected inside scheduler\n`.
- `swap_do_scheduled_discard → blkdev_issue_discard` and
  `bio_associate_blkg_from_css → blkg_create` also have direct transfers in that
  image.

The fixed caller formats and the generic formatter's warning branch explain
the first expansion into error reporting. This does not establish that normal
hex formatting executes the warning, scheduler panic, swap, or discard paths.
The other recorded edges remain log evidence in this bounded inspection; no
whole-chain feasibility proof or additional checker run was attempted.

The current checker source, verified identical to the campaign-start commit,
explains the traversal behavior:

- `functions_checker.py:531–536` disassembles the function body and iterates its
  instructions without specializing it for the caller's format arguments or
  proving the branch predicates along a path.
- At `669–690`, configured Shim interception applies to a PC-relative target
  only in the `SHN_UNDEF` branch. `vprintk` is in the captured effective Shim
  list, but the image defines it, so the checker queues it as a local executable
  symbol. Merely listing a helper does not stop this defined-symbol traversal.
- At `699–704`, a direct call/jump without a relocation can enqueue a function
  resolved in the same section. The local executable-symbol branch can also
  follow executable-symbol references; its queue label alone is not proof of a
  call. The eight image checks above therefore independently verify their
  selected control transfers.
- `471–496` processes the queue until it is empty. A recorded absolute-address
  failure does not end that traversal; a privileged instruction ends the
  current function's scan while other queued functions remain eligible.

These observations explain a substantial expansion through the full generic
formatter and its error-reporting dependencies. They do not quantify which
checker operations account for elapsed time, establish a terminal outcome, or
show that the caller-owned formatting API semantically requires all of those
kernel services. Any future dependency binding or specialization would need
to preserve the complete selected API and receive its own validation; this
inspection applied neither.

The [path evidence directory](results/applicability-path-20260912/README.md)
contains original numbered log excerpts, all 44 ancestry edges, selected ELF
bytes/strings, checker source excerpts and identity, effective Shim rules, and
the campaign state captured alongside the log. Re-parsing the archived excerpts
reconstructs the same 44 edges. The complete 1,782,655-byte snapshot is retained
locally at the path in `snapshot.json`; it is not added to Git.
