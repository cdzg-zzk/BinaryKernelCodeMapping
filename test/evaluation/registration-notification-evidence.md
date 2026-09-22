# Registration notification and ordinary file/VMA behavior

The current `vkso` wrapper waits for manager events through a private FIFO.
The [exact119 guest run](results/registration-notify-qemu-20260912-attempt03/result.json)
and [independent audit](results/registration-notify-qemu-20260912-attempt03/independent-audit.json)
pass with boot `aa0b3b6e-322e-46a9-a23c-ae3b315514ed`. This run also repeats
the complete v3 three/300-page transaction, sparse-slot, identity, interruption
and lost-response matrix. It measures behavior, not setup performance.

## Completion and state ownership

`manager --hold --notify-fifo` sends START after persisting its recovery state,
READY after successful COMMIT and ready-state persistence, and DONE with its
exit status after cleanup. Each event carries the manager PID and transaction
ID. The wrapper blocks on the FIFO instead of polling the ready file every
250 ms. Its non-root cleanup path waits for DONE instead of polling process
existence every 100 ms. A timeout reports an incomplete operation; it does not
establish successful registration or release.

The wrapper creates a unique mode-0600 FIFO in a private session directory.
Manager state records that path and its process PID before changing the
carrier. Cleanup signals or restores only state belonging to this session.
Launching a second wrapper no longer unlinks a shared ready/state file before
the manager can acquire its runtime lock. This runtime directory still permits
one wrapper session; separate kernel transactions require separate manager
runtime directories and disjoint source PFNs.

| Actual path | Observed result |
| --- | --- |
| Root wrapper and manager | Application starts after READY; normal cleanup receives release completion |
| UID 65534 wrapper, real `sudo -b` manager | Application UID remains 65534; manager UID is 0; DONE and cleanup succeed |
| Competing wrapper during an active application | Runtime lock rejects the second manager; original state remains byte-identical, first manager and application remain active, and source PFN is preserved |
| New wrapper with a dead manager's recovery state | New application is not started; existing state is preserved; explicit restore succeeds |
| Wrapper killed after START, manager stopped before registration | After resumption, the manager commits, cannot deliver READY to the closed FIFO, releases its transaction and exits; no application starts |
| Ordinary file passed as notification destination | Manager rejects it and preserves its bytes |

The interrupted-manager log retains the generic phrase “Restore signal
received.” In this case cleanup is triggered by failed READY delivery after
the wrapper exits, not by an observed SIGTERM to the manager. The wrapper's
background child closes its inherited FIFO descriptor before exec, allowing
the manager to observe the loss of the reader.

The fixture executes the actual `as_root`, `hold_state_owned`, `cleanup_session`
and `exec_with_replacement` functions extracted from the archived `vkso`.
Only fixture build/preparation helpers are replaced, since the real manager,
registration module and owner are already present. The three complete algorithm
runs below separately exercise the build/export path. The sudo configuration
is confined to the private initramfs, prepared by
`registration_sudo_initramfs.py`; host accounts and sudo configuration are
unchanged. Raw wrapper logs, state snapshots and the ordinary-user application
record are under the run's `evidence/validation/` directory.

## Ordinary file and mapping operations

The caller has UID/GID 65534 and owns a mode-0666 carrier in a writable
directory. A hardlink exists before registration. For every file operation,
the same caller first succeeds on an ordinary control file. During active
registration, each of `open(O_RDWR)`, same-size truncate, rename, unlink,
hardlink creation, chmod and utime returns EPERM on both carrier names: 14
denials with seven successful controls. This tests immutable behavior on the
guest's ext4 carrier filesystem.

A read-only MAP_SHARED mapping rejects `mprotect(RW)` with EACCES. Adding
execute permission succeeds and preserves bytes; the inert fixture is never
executed. `msync(MS_SYNC)`, `madvise(DONTNEED)` and
`posix_fadvise(DONTNEED)` preserve the resident bytes, and the privileged
observer confirms the same source PFN before and after these operations.
MAP_PRIVATE writes remain isolated from the shared source; a forked child's
write also leaves the parent's private value unchanged. The unprivileged
process's masked pagemap is not used to infer COW PFNs.

## Current complete algorithm runs

All three runs use the current manager, registration module and wrapper.
The payload audits compare their archived binaries and sources with the
working implementation and verify owner/vmlinux identity checks before STAGE.

| Algorithm | Full functional and collection coverage | Archive |
| --- | --- | --- |
| LZ4 | 432 cross-backend decode checks; 18 component processes and 36 rows; 192 four-backend CLI operations over all 12 files and two block sizes; the separate 24 registered input/block pairs retain 48 traces; five shared PFNs | [Run](results/lz4-notify-qemu-20260912-attempt01/result.json), [full audit](results/lz4-notify-qemu-20260912-attempt01/independent-audit.json), [payload audit](results/lz4-notify-qemu-20260912-attempt01/registration-payload-audit.json) |
| BCH | 10,752 complete decode checks across the original three backends and parameter/error matrix; four shared PFNs | [Run](results/bch-notify-qemu-20260912-attempt01/result.json), [payload audit](results/bch-notify-qemu-20260912-attempt01/registration-payload-audit.json) |
| XZ | 42 diagnostic rows, 882 complete decodes and 84 complete-output comparisons; four shared PFNs | [Run](results/xz-notify-qemu-20260912-attempt01/result.json), [payload audit](results/xz-notify-qemu-20260912-attempt01/registration-payload-audit.json) |

Boot IDs are `c77dd5f7-df98-49a6-bbb6-72496d2e84fd`,
`b5954916-c861-4900-a4d8-a50bafe3b9a5` and
`180b0cf0-51c8-4f0c-81d6-255ccf3347ad`, respectively. Every active owner has
one registration reference. Release removes source PFNs from fresh mappings,
all test modules unload, and no run reports a kernel panic, BUG or WARNING.
LZ4's one-round CLI run validates collection; the formal plan retains four
rotated rounds per independent deployment. Guest timing values do not replace
physical-host performance measurements.

## Remaining group B work

[Subsequent setup runs](setup-evidence.md) use this notification implementation
with optional shell timing hooks and exec-ready. They cover all three real
closures; the original notification archives retain their executed wrapper.


Notification and the ordinary ext4 file/VMA matrix above are implemented and
observed. The setup collector is now implemented and validated. Formal setup measurements,
the 1/2/4/8/16/32-page scan, complete resource accounting, unfiltered first-touch
collection and memory pressure remain open. Resource accounting must include the FIFO/pipe
and descriptors as well as manager memory, owner residency, transaction records
and retained terminal records. Removing a polling interval does not establish
a measured latency improvement. Built-in page publicness and the supported
runtime code-rewriting boundary also remain to be completed.

Earlier notification attempts retain their executed versions. Attempt 01
preceded the inherited-descriptor and non-FIFO handling fixes; attempt 02
covers the root path, while attempt 03 adds actual sudo execution. Previous
identity and transaction archives keep their original manager identities.
