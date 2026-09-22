# Full-plan registration, rollback and recovery

Protocol v3 replaces the single-carrier, 256-entry batch registry with dynamic
per-transaction records. The current manager and page module pass the private
exact119 transaction matrix and the full registered LZ4 CLI workflow. These
are functional and failure-path observations, not setup or application
performance measurements. [The latest notification run](registration-notification-evidence.md) adds FIFO
completion, actual root/sudo wrapper paths and the ordinary ext4 file/VMA
matrix, and reruns all three algorithms. Group B still requires setup,
complete resource measurements and source-page boundary work.

## Linked-image identity before staging

[The identity transaction run](results/registration-identity-qemu-20260912-attempt02/result.json)
uses boot `4586c4eb-487b-4c51-a535-e7a5a3db8365`. The builder records each
owner's descriptor symbol, srcversion, actual module name and GNU build ID,
and the supplied vmlinux's GNU build ID. After BEGIN pins the owners, the
manager checks the descriptor's module in kallsyms and compares the expected
IDs with `/sys/module/<module>/notes/.note.gnu.build-id` and `/sys/kernel/notes`.
Only a matching deployment proceeds to STAGE. Missing or malformed identity
metadata is rejected. Owner layout and protocol v3 are unchanged: linked-image
checking belongs to the deployment manager, while the kernel retains source
version, owner-reference and source-range checks.

The same fixture sources built in the same directory with and without
`KCFLAGS=-fno-inline` have identical srcversion `E463A82A258B5407AB36EB1` but
different GNU build IDs. Their init text differs (235 versus 20 bytes); the
300 inert test pages are not a performance workload. Supplying the other real
build's ID, a wrong module name, or a wrong kernel ID causes the actual manager
to refuse after BEGIN, send RELEASE, and leave no page binding, ready PID or
recovery state. The logs contain no STAGE or COMMIT for these cases. The full
three/300-page matrix, sparse slots, five interruption points and lost-ACK
recovery also pass. [The independent audit](results/registration-identity-qemu-20260912-attempt02/independent-audit.json)
checks both real ELF artifacts, their source versions and init text, manager
and module identity, and the actual request logs. Twenty-two builder tests,
including four build-ID tests using the C++ note reader, pass; five runner
cleanup tests also pass.

GNU build ID identifies the linked image. It does not certify later ELF edits
or runtime code rewriting; [GNU ld documents this distinction](https://sourceware.org/binutils/docs/ld/Options.html).
Deployment still requires the supported runtime rewriting policy and current
addresses. This is not an independent kernel-side authentication interface.
The initial variant copied to another directory had a different srcversion
and was rejected by preparation before boot; both that attempt and a separate
LZ4 preparation failure caused by a nonexistent owner path remain archived.

The manager's no-owner path also passes a fresh [built-in export run](results/applicability-identity-qemu-20260912-attempt01/result.json),
boot `4139a335-a8e3-42fb-9476-c912f2d4bed0`. XXH32's 247 vectors and sort's
1,152 cases match independent references in the original kernel and actual
user carrier. Each has two shared source pages; sort retains one generated
thunk page. Fresh mappings after release no longer use the source PFNs and
all test modules unload. [The independent audit](results/applicability-identity-qemu-20260912-attempt01/independent-audit.json)
confirms empty owner manifests, matching kernel build IDs before STAGE and
the unchanged complete functional/PFN protocol. This reruns the same two
prospective cases and does not change the eight-case denominator.

## Prepared slots and interruption recovery

[The preceding transaction run](results/registration-prepared-qemu-20260912-attempt01/result.json)
uses boot `124fe84c-9a06-4af3-b0fb-736da91dcbb0`. It repeats the complete
three/300-page matrix and adds sparse indices 1, 64, 4,096 and 262,144, spanning
several xarray levels. All selected pages recover their original bytes. The
current module prepares ordinary target cache pages, then replaces an occupied
xarray slot directly while holding both page locks and the xarray lock. It
rechecks that the slot still contains the prepared page. The store cannot need
an expanded tree: it changes a single existing page entry to another page
entry. The previous delete-and-insert sequence and `xas_nomem` allocation retry
are removed from apply.

This uses the occupied-entry behavior in [Linux xarray.c](https://raw.githubusercontent.com/torvalds/linux/v5.15/lib/xarray.c).
The old ordinary file page is removed from NR_FILE_PAGES accounting, its
mapping is cleared, and its cache/preparation references are dropped. Its
existing memcg charge stays with that ordinary page until its final release;
it is not transferred to an already allocated kernel source page. The file's
nrpages is unchanged by replacement and decreases when that binding is
removed. Optional cleancache invalidation occurs during preparation, before
any source binding. The source reference/field restoration and COW behavior
are unchanged. The [audit and disassembly](results/registration-prepared-qemu-20260912-attempt01/independent-audit.json)
retain the executed code identity and the absence of an explicit allocator or
xas_nomem in apply, in addition to the actual sparse-slot and rollback checks.

Manager state now records carrier device/inode and intended immutable ownership
**before** changing the flag. Recovery checks the saved inode before releasing
or changing file flags. The guest kills the actual manager after durable state
creation, after setting immutable, after BEGIN, after STAGE, and after COMMIT
but before ready. A new manager restores every case; no source binding or
manager state remains. A BEGIN that reaches transaction allocation but is
rejected retains its terminal error for QUERY. Dropping an ETXTBSY rejection
reply is recovered with that exact errno, followed by successful cleanup.
When no transaction was created, an explicit kernel ENOENT allows cleanup;
a live transaction cannot disappear through ordinary module unload because
it pins the registration module. Pre-existing immutable remains set after a
normal replace/release cycle. The manager's stop checkpoints are activated
only by the guest's VKSO_TEST_STOP_AT environment variable.

## Identity-build complete algorithm workflows

All three runs below use the same identity-checking manager/module source and binaries
as the identity-checked transaction fixture. The manager checks the matching
owner and vmlinux IDs after BEGIN and before STAGE in every archived log. BCH and XZ owners are freshly built from their
complete current sources, including the cooperative descriptor; the LZ4 run
uses its recorded cooperative owner. The launchers copy current repository
components into the prepared guest environment, materialize owner headers in
the source snapshot and generate old-kernel-compatible BTF. The unchanged
algorithm workloads are rerun with a required owner refcount of 1.

| Workflow | Actual coverage and release | Archive |
| --- | --- | --- |
| BCH | m=13, t=4/8, all 0..t errors, 128 vectors, three backends and two decode paths; 10,752 decode checks; four shared PFNs | [Run](results/bch-identity-qemu-20260912-attempt01/result.json), [audit](results/bch-identity-qemu-20260912-attempt01/independent-audit.json) |
| XZ | All three full inputs, two backends, seven outer rounds and 20 timed repeats; 42 diagnostic rows, 882 complete decodes and 84 full-output comparisons; four shared PFNs | [Run](results/xz-identity-qemu-20260912-attempt01/result.json), [audit](results/xz-identity-qemu-20260912-attempt01/independent-audit.json) |
| LZ4 CLI | All 24 Silesia input/block pairs, full compression/decompression and stock cross-decoding; 48 operation traces; five shared PFNs | [Run](results/lz4-identity-qemu-20260912-attempt02/result.json), [audit](results/lz4-identity-qemu-20260912-attempt02/independent-audit.json) |

The three boot IDs are `9bae57cd-0903-4242-a59c-dbbf53611d05`,
`504817ad-a046-44f2-8830-1872d0de8731` and
`bd49c106-e442-482a-99de-4cea64a05872`, respectively. Each has owner refcount 1
while registered, removes all source PFNs from fresh mappings on release and
unloads every test module. All three finish without kernel panic, BUG or
WARNING. These checks do not provide new physical-host performance results. The earlier
prepared-slot algorithm runs remain archived with their original managers.
XZ's guest timing fields remain diagnostic. The new owner/layout and manager
costs still need formal setup, per-process support and owner-resource accounting.

## Implementation and identity

The request contains protocol version, operation, a random 64-bit transaction
ID, target device/inode, and a complete page plan transmitted by STAGE in
chunks of at most 256 entries. BEGIN holds the carrier file and cooperative
owner descriptors before source lookup. It rejects an existing writer or
writable shared mapping using `deny_write_access` and `mapping_deny_writable`.
The manager durably records the transaction ID, carrier identity and intended
immutable ownership before changing the flag or sending BEGIN. A runtime-directory
lock prevents two managers from overwriting the same recovery file; successful
COMMIT precedes publication of the ready PID.

COMMIT checks all source ranges, target bounds and duplicate source PFNs,
resolves and references all source pages, drains existing file writeback and
prepares target cache pages before replacing their occupied slots. Every transaction owns
its file/mapping, plan, owner references, source references and original page
fields. Different carriers can have concurrent transactions using disjoint
source PFNs. A source PFN already held by another transaction is rejected.
The source page's fields and insertion reference are established before its
xarray entry is published.

An apply error triggers reverse-order rollback over the entire plan. A release
error does not stop the remaining releases. If a binding remains, the state is
RECOVERY_REQUIRED and file protection, owner references and source references
remain held. RELEASE retries only applied bindings and is idempotent after
RESTORED or ABORTED. Terminal records retain result identity for QUERY while
releasing the page-plan allocation and live resources. FORGET or module
unload removes the terminal record.

The manager uses one Netlink socket for BEGIN/STAGE/COMMIT. It checks the
kernel sender, sequence, transaction ID, operation and state. A missing reply
causes QUERY; the recovered last operation and sequence must match the lost
request. The manager does not blindly reapply a batch. An independent manager
can recover by the persisted transaction ID after the original process exits.
The permission boundary remains CAP_SYS_ADMIN using kernel sender credentials.

Write exclusion follows the counters in [Linux fs.h](https://raw.githubusercontent.com/torvalds/linux/v5.15/include/linux/fs.h).
Release retains the inode/invalidation/page/xarray lock order and keeps the
source page locked through cache removal and user-PTE invalidation, consistent
with the fault rechecks in [Linux filemap.c](https://raw.githubusercontent.com/torvalds/linux/v5.15/mm/filemap.c).
The exact119 headers and module build are retained with each run. These source
references explain the implementation; the guest matrix establishes only the
paths actually exercised.

## Initial v3 transaction matrix

[Attempt 04](results/registration-transaction-qemu-20260912-attempt04/result.json)
uses boot `bfa320b1-2cda-48b7-b6d2-0bea3753ea7d` and the corresponding complete manager
and page module. Its [fixture source](registration-transaction-fixture/)
provides 300 distinct inert resident pages with the same cooperative descriptor
contract. The pages are never called as an algorithm. They exercise the full
registration implementation beyond the transport chunk boundary; no API or
throughput claim is inferred from their content.

| Exercised path | Observation |
| --- | --- |
| BEGIN with an existing writable fd | ETXTBSY; no transaction or binding; original file preserved |
| BEGIN with a shared writable VMA after closing its original fd | ETXTBSY; original file preserved |
| Invalid source at each position of a three-page plan | COMMIT rejects before apply; ABORTED, zero applied pages |
| Injected apply error at each position of a three-page plan | EIO, complete rollback, original contents and baseline references restored |
| 300-page plan staged as 256 + 44 | No binding during STAGE; exact STAGE retransmissions leave staged count unchanged; successful COMMIT reports 300 applied pages |
| Apply error at zero-based index 0, 150, 255, 256 or 299 of that plan | EIO; ABORTED with zero applied pages; all 300 file pages recover original content |
| RELEASE error at the middle of three pages | Both other pages restored; one residual binding and owner references retained; unload refused |
| Retrying RELEASE, then repeating it | Residual page restored; both calls return terminal RESTORED |
| Apply failure followed by a rollback failure | RECOVERY_REQUIRED; subsequent RELEASE removes the residual binding |
| Persistent read mapping and private COW | Read mapping recovers original file bytes; COW retains its modified byte |
| Same source PFN requested for another carrier | Second COMMIT returns EBUSY without disturbing the first binding |
| Two carriers with disjoint source PFNs | Both ACTIVE concurrently; independent release returns references to baseline |
| Three processes faulting with MADV_DONTNEED during RELEASE | All exit normally and observe the original file after release; 131, 53 and 9 loop iterations recorded |
| Dropped COMMIT reply | QUERY reports ACTIVE with the lost request's operation, sequence and status |
| Actual manager loses COMMIT and RELEASE replies | Two QUERY recoveries; ready follows confirmed commit; normal exit restores file and removes state |
| Manager killed after ready | Persisted transaction ID allows a new manager to restore and clear state |
| Manager encounters RELEASE error | Nonzero exit with state and backing retained; a new manager successfully retries |
| Competing manager using the same runtime directory | Rejected without replacing the live session's recovery state |

The concurrent readers accept each copied byte from either the source or the
original file during the transition, and require the complete original page
after release. This does not assert atomic publication to arbitrary existing
observers or an atomic multi-byte read during unmapping.

The fixture keeps a userspace Netlink socket open. That socket itself pins the
page module: its baseline refcount is 1. One transaction raises it to 2 and
raises the source-owner refcount from 0 to 1. Two disjoint transactions raise
these to 3 and 2. After all transactions are released and the transport socket
closes, both refcounts are zero and every test module unloads. Transport and
transaction pins are accounted separately.

## Initial v3 registered application

[The initial v3 LZ4 run](results/lz4-transaction-qemu-20260912-attempt02/result.json)
uses boot `f975db45-8674-4d6c-bdb0-47b31ad2739c` with the same manager and page
module as transaction attempt 04. It retains the complete LZ4 implementation
and CLI, the cooperative LZ4 owner, and the three private helper bindings.
All 24 Silesia input/block pairs complete compression/decompression and stock
cross-decoding. All 48 operation traces identify carrier calls and the actual
helper bridges/providers. Four text pages and one RO page match source PFNs,
and post-release mappings no longer use those PFNs. The normal-release stage
completes and every test module unloads. Neither this run nor the transaction
fixture reports a kernel panic, BUG or WARNING.

The [independent audit](results/registration-transaction-qemu-20260912-attempt04/independent-audit.json)
compares the then-current manager/module source and binaries with both initial v3 payloads,
rechecks all six 300-page files after rollback/release, and checks the complete
24-case application matrix, 48 traces, owner reference and five before/after
PFN pairs. Five existing shell cleanup tests and syntax checks pass.

To rerun the transport-boundary matrix with freshly built current components:

```sh
make -C page_cache_replace
make -C test/evaluation/registration-transaction-fixture
python3 test/evaluation/registration_completion_qemu.py \
  --output test/evaluation/results/registration-transaction-new \
  --kernel /tmp/vkso-guest-kernel-119/extracted/boot/vmlinuz-5.15.0-119-generic \
  --initramfs test/evaluation/results/lz4-binding-qemu-20260912-attempt06/initramfs.cpio.gz \
  --owner test/evaluation/registration-transaction-fixture/vkso_tx_fixture.ko \
  --owner-source-dir test/evaluation/registration-transaction-fixture
```

The output directory must not exist. This launcher now defaults to the v3
driver; older drivers require their matching historical module and manager.

## Remaining work and retained attempts

The occupied-slot implementation now removes the xarray reallocation gap
identified in the initial v3 run. The five manager interruption points and
lost rejected-BEGIN reply are covered by the current run above. The error
injection matrix exercises apply/release failures; it does not measure failure
rates under memory pressure.

Linked-image identity is now checked by the manager as described above.
Built-in page publicness, the supported runtime-rewriting boundary, the
formal setup/resource accounting remain
to be completed. Callback timings are diagnostic until the setup-to-first-result
collector and complete deployment runs are integrated. Functional evidence
for all three current cooperative owners is available above.

Attempt 01 failed the harness's initial refcount assertion: it had omitted the
open Netlink socket's own module reference. It performed no registration.
Attempt 02 passes the three-page matrix with the actual LZ4 owner. Attempt 03
adds the 300-page fixture, concurrent faulting and crash recovery. Attempt 04
also verifies shared writable mappings, persistent COW, manager runtime
exclusion and manager release-error recovery, with atomic durable state writes.
The two full LZ4 passes retain their actual manager builds separately. Earlier
[v1 completion](registration-completion-evidence.md) and
[v2 owner](registration-owner-evidence.md) records remain historical evidence;
their limitations are not descriptions of v3's implemented rollback behavior.
