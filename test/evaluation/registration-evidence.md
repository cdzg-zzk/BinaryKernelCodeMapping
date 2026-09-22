# Registration evidence: baseline path and subsequent observations

The source audit below describes the 2026-09-11 baseline after `09740b2`,
followed by its isolated runtime observations. On 2026-09-12, the modified
manager/module gained explicit completion results and removed fixed waits;
[the new evidence](registration-completion-evidence.md) includes full LZ4 and
error-path guest validation. Baseline statements below retain their original
implementation identity. Owner pinning and transactional rollback remain open.

## Executed path

`run.sh` loads the algorithm owner and calls `vkso exec`. In
[`vkso`](../../vkso), `exec_with_replacement()` builds/loads
`page_cache_replace.ko` as needed and starts the manager with `replace --hold`.
It waits for `manager.pid`, runs the benchmark command, and signals the
manager to restore before the runner unloads the owner module.

[`manager.cpp`](../../page_cache_replace/manager.cpp) validates the supplied
page plan, sends replacement batches, sleeps two seconds, protects the file
with the immutable flag, and writes its state/PID files. The hold process
restores on its handled termination signals. The PID file therefore follows
the manager's two-second wait; it is not an acknowledgement of each kernel
page operation. Restore likewise sleeps two seconds after sending requests.

[`page_cache_replace.c`](../../page_cache_replace/page_cache_replace.c)
receives virtual addresses and file offsets through `nl_recv_msg()`, calls
`batch_process_pages()`, resolves each kernel address to a `struct page`, and
inserts it through `add_page_to_cache()`. Restore removes the page-cache entry,
invalidates user mappings, clears the backup record, and drops page references.

## Claim-to-implementation ledger

| Contract or cost | Located implementation | Current evidence and remaining work |
| --- | --- | --- |
| Resident page references | `add_page_to_cache()` calls `get_page()` before insertion; `restore_page_cache()` drops page-cache and temporary references | Page-reference operations exist. Observe the successful full lifecycle and reference/accounting balance in the controlled diagnostic session. |
| Owner module references | The registration request contains addresses/offsets, the backup records contain mapping/index data, and the traced registration path has no owner-module acquisition/release | The manuscript's claim that the manager holds both module and page references is not established by this implementation. Page references alone do not demonstrate owner-module reference ownership. Inspect module refcounts during an active controlled mapping before testing any unload boundary. |
| Normal owner lifetime | Each algorithm runner waits for `vkso exec` to return before unloading its owner; manager restores when the command finishes | This supplies ordered normal cleanup, not proof that a concurrent module unload is refused. The new deployment runner observes final absence of the owner, without claiming more. |
| Registration completion | Manager checks send results and then sleeps; the kernel callback logs the result but sends no per-request completion result | A successful send, two-second delay, and PID file cannot supply exact kernel completion time or certify all registered pages. Observe kernel completion separately for group B; include the actual waits in full command wall time. |
| Partial registration failure | `batch_process_pages()` breaks on a failing page and returns its error; earlier successful page operations remain recorded. The callback logs failure. | No transactional rollback is performed by that batch function. Manager-level eventual cleanup must be distinguished from rejecting a partially registered session before use. Failure-path behavior needs an isolated fixture. |
| File integrity and mapping permissions | Manager's immutable-file handling and builder's ELF permissions; normal loader tests already exist | Reuse existing loader evidence. Exercise the planned mapping-operation matrix on controlled test pages; do not infer a complete VM/file contract from ELF flags. |

The source audit is stronger than a repository-wide keyword absence: it
follows the runtime entry, request format, page resolver, registration loop,
backup records, user manager, and normal cleanup. It still does not demonstrate
the effects of every kernel VM/module operation. In particular, no live owner
unload, partial-registration injection, or mapping mutation was attempted
during Clocktime collection.

## Consequences for group B

1. Measure current behavior first: ready-carrier registration, first valid
   call, full command wall time, kernel completion, restoration, and owner
   unload are distinct events. Neither two seconds nor the manager PID file
   is an exact registration-completion measurement.
2. Reuse the Clocktime observer's `page_addresses`/`pages` debugfs interface
   and user pagemap method for actual algorithm PFNs, while separately
   recording owner/module allocation, manager, carrier, private bindings,
   and page-table costs. Its existing declared-closure union is not a net
   system-memory measurement.
3. Run the boundary fixtures in an isolated instance using the project's
   test pages. Observe owner refcounts first; do not perform a destructive
   live unload merely to infer that a source-level reference is absent.
4. If the intended contract requires explicit owner pinning, acknowledged
   registration, and transactional rollback, implementing those affects
   `page_cache_replace` and its manager protocol. Under the user's existing
   restriction on foundational changes, present the concrete change and its
   reason before modifying that implementation. This audit does not authorize
   or claim to have completed such a change.

Group B remains open. The current benchmark's controlled owner lifetime and
successful output checks are useful evidence within their scope; they do not
close the broader lifetime and failure-atomicity claims in the manuscript.

## Isolated runtime observations, 2026-09-12

[`registration_qemu.py`](registration_qemu.py) runs the existing packaged
5.15.198 kernel, `vkso_m09_clock.ko`, `page_cache_replace.ko`, manager and
Clocktime PFN observer in a private KVM guest. It has a fresh ext4 image and
no network or shared host filesystem. The host loads no modules. The full
registration implementation is unchanged; a two-page synthetic file supplies
one controlled file offset for the mechanism checks. This fixture neither
calls a reduced Clocktime API nor measures API/setup performance.

Two guest sessions completed. [Attempt 01](results/registration-qemu-20260912-attempt01/evidence/validation/observations.json)
observed three reader processes and the ordered lifecycle. [Attempt 02](results/registration-qemu-20260912-attempt02/evidence/validation/observations.json)
added an ordinary UID/GID 65534 reader with no effective capabilities. The
file belonged to that UID with mode 0666, so its file-operation denials did
not result from a missing DAC write permission. All ordinary-user operations
were performed after the manager ready file appeared; pre-existing writable
descriptors and the interval before immutable activation were not exercised.

| Invariant or question | Exercised path | Required observation | Actual result in attempt 02 | Implementation location |
| --- | --- | --- | --- | --- |
| Shared physical backing | Three independent initial readers and one unprivileged `MAP_SHARED` reader | All faulted aliases match the kernel PFN | All four match PFN 33099 | `add_page_to_cache()` and the normal file-fault path |
| Read-only PTE integrity | Ring-3 store through a read-only private mapping | Store faults | Child receives SIGSEGV (11) | Normal page protection |
| Private write integrity | Root and UID 65534 `MAP_PRIVATE`, `mprotect(RW)`, then store | COW page differs from kernel backing; fresh source mapping unchanged | Private PFNs 36097 and 257585; fresh source remains 33099 with unchanged bytes | Normal private COW path |
| Shared write permission | UID 65534 read-only fd, `MAP_SHARED`, then `mprotect(RW)` | Write permission is refused | EACCES (13) | File-backed mapping permission checks |
| Registered file integrity for new operations | UID 65534 opens RDWR or truncates the owned mode-0666 file after ready | Operations are refused | Both return EPERM (1) | Manager immutable-file state |
| Ordered release | Close every reader, signal manager, verify restored bytes, unload owner | Original file backing returns before owner unload | Restored PFN 260979 with original bytes; manager exits 0; owner unload succeeds | Manager restore and runner ordering |
| Independent owner pin | Read `/sys/module/vkso_m09_clock/refcnt` before registration, after ready, with readers, and after restore | Explicit module pin would increase the refcount | All seven observations are 0 | Registration path has no owner-module acquisition |

The guest console, manager log, page plan and kernel PFN records are retained
beside each observation file. Neither guest produced a kernel panic, BUG or
WARNING. The expected user-mode SIGSEGV was captured as the write-protection
result. Attempt 01 independently observed owner refcount 0 at all six phases,
three matching source PFNs, private COW and successful ordered cleanup.

These results establish the exercised mapping and normal-release behavior.
They confirm that this registration path does not increase the tested owner's
module refcount; no active-owner unload was attempted. Other owners,
page-reference balance, page-co-location policy and whole-session
time/resource accounting remain separate B requirements.

## Partial registration and completion reporting

The [partial-failure session](results/registration-qemu-20260912-partial01/evidence/validation/observations.json)
uses the same complete packaged implementation in a fresh guest. Its plan has
two offsets: the first names an existing owner text page; the second names a
canonical, non-present vmalloc-range address. The existing kernel PFN observer
checks that the second address has no present mapping before submission. No
module or kernel source is modified to inject the failure.

The manager's plan validation accepts both aligned entries. The kernel
registers the first page, fails to resolve the second and logs `-ENOMEM`
(-12). Nevertheless, the manager prints replacement success and creates its
ready file. At that point the first file offset still maps source PFN 26135,
while the second retains the original file bytes. This is an observed partial
carrier exposed at ready, rather than just a source-derived rollback concern.
Owner refcount is 0 before submission and at ready.

On orderly termination, the kernel restores the first offset, then reports
`-ENOENT` (-2) because the second offset has no backup. The manager again
prints success and exits 0. Both offsets contain their original bytes after
this particular cleanup, and owner unload succeeds. Thus this case shows
successful recovery of the one installed binding, but inaccurate registration
and restoration completion reporting. It does not establish recovery of
arbitrary partially completed multi-batch sessions.

| Contract question | Exercised path | Actual result | Interpretation |
| --- | --- | --- | --- |
| Failed registration is withheld from use | Existing source page followed by an unresolved page in one batch | Kernel error -12, manager ready and success message, first source PFN still accessible | Current failure-atomicity contract is not met |
| Manager completion reflects kernel outcome | Restore the same two-offset plan | Kernel restores offset 4096, errors -2 at offset 8192; manager reports success and exits 0 | Fixed wait/send success does not propagate kernel completion errors |
| Controlled cleanup preserves original contents | Close mappings before requesting restore | Both original page contents present; ordered owner unload succeeds | Observed recovery of this fixture only |

The [guest console](results/registration-qemu-20260912-partial01/console.log)
and [manager log](results/registration-qemu-20260912-partial01/evidence/validation/manager-hold.log)
retain both sides of these outcomes. The fixture prints
`registration_observation=complete`; it deliberately does not label the
atomicity contract as passing. No kernel panic, BUG or WARNING occurred.
Acknowledged operations and transaction rollback remain implementation work
requiring the concrete foundational-change review described above.
