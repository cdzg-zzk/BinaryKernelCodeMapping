# Registration completion and error propagation

This records protocol v1. The subsequent [owner-aware protocol v2](registration-owner-evidence.md)
adds cooperative module references and source-field-aware release; its archives
are separate from the completion-only observations below.

Observed on 2026-09-12 with the modified full page module and manager, in
private Linux `5.15.0-119-generic` guests. This closes the false-success and
fixed-wait portion of group B. Transactional rollback, owner references,
query/recovery semantics, complete setup decomposition and memory accounting
remain outstanding.

The shared [protocol header](../../page_cache_replace/protocol.h) defines
versioned request/result types. A result carries the operation, echoed Netlink
sequence, actual kernel errno, completed page prefix, failure index and kernel
callback time. The manager checks the kernel sender and full result before
publishing ready or reporting restoration success. A full-sized zero-count
HELLO precedes a modifying request: an old module ignores it without touching
pages, and the new manager refuses to proceed without a versioned reply.
The socket remains open through the request and response. This follows the
[Linux Netlink request/reply model](https://docs.kernel.org/6.1/userspace-api/netlink/intro.html),
where a successful send does not replace reading the operation's result.

The manager's two `sleep(2)` calls are removed. Held-session signals are blocked
before ready publication and delivered through `sigsuspend`, avoiding a lost
signal between testing the flag and sleeping. A failed request stores recovery
inputs without publishing `manager.pid`. A failed restore returns nonzero and
retains manager state. `vkso` propagates manager/fallback/unload errors; algorithm
runners retain their owner after a failed session instead of silently unloading.

## Guest outcomes

The [completion matrix](results/registration-completion-qemu-20260912-attempt01/result.json)
uses boot ID `37bf29a7-326d-457b-a93a-f6abde6a075e`. The archive includes the
actual module/manager sources, binaries, guest driver, kernel command and logs.

| Case | Actual result |
| --- | --- |
| Short payload / legacy request type / empty batch | EMSGSIZE / EPROTONOSUPPORT / EINVAL; zero completed pages |
| Unaligned offset / offset past file end | EINVAL / ERANGE; zero completed pages and failure index 0 |
| Request from UID/GID 65534 without capabilities | EPERM |
| One valid source followed by an address independently checked to lack a present PTE | ENOMEM, completed prefix 1, failure index 1; manager exits 255 and does not publish ready |
| Backing after that failed batch | First page still uses source PFN; recovery state exists. Explicit one-page restore succeeds and fresh mapping contains original file bytes |
| Two subsequent complete registration/release sessions | Source PFN while registered; original file bytes after restoration |
| External restore followed by held manager's restore | Held manager receives ENOENT, exits 255, retains state and does not print successful session restoration |
| New manager with archived old exact119 page module | HELLO gets no completion; manager exits 255 without changing file backing |

The partial-failure case proves correct error reporting, **not rollback**.
The fixture explicitly restores the applied prefix. The external-restore case
also shows that whole-session recovery is not yet idempotent. Owner refcount
remains zero. All test modules were unloaded only after the fixture verified
its remaining mappings no longer used source PFNs. No kernel panic, BUG or
WARNING appeared.

The separate [full LZ4 application session](results/lz4-completion-qemu-20260912-attempt01/result.json)
uses boot ID `0ed165d5-eb7c-40c3-82b1-81d55aa14458`. All 24 complete Silesia
input/block pairs pass compression/decompression and stock cross-decoding with
the modified helper bindings. Five pages match source PFNs. Both registration
and restoration return `status=0 completed=5`; normal release removes source
backing from fresh mappings and unloads the test modules.

## Timing scope

`kernel_operation_ns` spans callback entry through validation, mutex waiting,
file lookup, batch work and file close, ending before reply allocation/send.
It includes the existing per-page debug printing. `exchange_wall_ns` spans
userspace send through receipt/validation of the response; HELLO exchanges are
separate records. Socket creation and HELLO overhead are outside each modifying
exchange and must still be included in full setup wall time.

In the LZ4 functional guest, five-page registration records 152,384,025 ns in
the callback and 152,421,838 ns for the exchange; restoration records 32,292,636
and 32,308,664 ns. These single diagnostic observations check timing boundaries.
They include guest scheduling and verbose console output, and are not formal
physical-machine setup latency or new algorithm performance measurements.

## Validation and remaining implementation

`make -C page_cache_replace -j2` builds the exact119 module and static manager.
The kernel build emits the existing compiler-package-string difference and
skips module BTF without a configured vmlinux; no compiler error remains.
`python3 -m unittest discover -s test/evaluation -p test_session_cleanup.py -v`
passes five tests, including nine algorithm-runner subcases, using the actual
shell cleanup functions with local command stubs. These cover status propagation
and whether an unload is attempted; they do not simulate kernel lifetime.

The existing backup array now rejects capacity overflow instead of silently
losing records, serializes module requests and can be reused after complete
release. It is still a 256-entry registry, not the planned dynamically staged
transaction mechanism. The [transaction plan](proposals/registration-transactions.md)
continues to govern owner pinning, full-plan validation/commit, cross-batch
rollback, identity-aware release, failed-recovery retention, file protection
and mapping boundaries. Formal B/C/E collection follows that common mechanism
and the final owner/helper build.
