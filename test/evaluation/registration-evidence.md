# Registration evidence: current call path and outstanding checks

Source audit on 2026-09-11, after `09740b2`. This records the implementation
reached by the algorithm runners, not an observation of a new deployment.
No registration code or live mappings were changed.

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
