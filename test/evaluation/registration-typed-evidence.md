# Typed source-page admission

The page plan now carries `text`, `rodata` or `shared_data` into the kernel.
Protocol 4 uses a 24 B page specification and a 7,216 B request; the reply
remains 88 B. The manager and kernel must be updated together. An old v3
request receives EPROTONOSUPPORT before its old layout is interpreted.

The kernel checks cooperative owner text/RO bounds against the declared kind,
then walks the requesting task's active kernel page table. RW and USER are
combined across all levels and NX is accumulated. Text requires supervisor
RO/X, rodata requires supervisor RO/NX, and shared data requires supervisor
RW/NX. The walk resolves 4 KiB, 2 MiB and 1 GiB leaves. The mapping is checked
before any destination slot is replaced. Module descriptors remain excluded.

These checks establish admission-time type and mapping properties. They do
not establish that every byte of a built-in image page is public, and do not
serialize later privileged text or page-table changes. Built-in admission
still accepts a broad image range. Cooperative descriptors currently publish
text and RO ranges; mutable module pages have no publication descriptor.
Clocktime's built-in published state retains its separate shared-data kind;
its frozen performance records use their archived implementation, not this
protocol revision. A new shared-state runtime check is still required.

## Full transaction and scale matrices

[The full matrix](results/registration-typed-qemu-20260912-attempt01/result.json)
passes on exact119, boot `98e7cd3f-4fb6-4529-8e4d-15a8a9716720`.
It retains the three/300-page transactions, rollback/recovery, linked-image
identity, lost replies, manager interruption points, root/sudo FIFO and file/VMA
checks. Three invalid kind/reserved cases fail STAGE without retaining a
partial plan. Declaring each of three text pages as rodata or shared data gives
six EACCES COMMIT failures, all before any apply. The
[retirement reconstruction](results/registration-typed-qemu-20260912-attempt01/retirement-audit.json)
checks all 17 manager-created IDs are absent at the end.

[The scale matrix](results/registration-scale-typed-qemu-20260912-attempt01/independent-audit.json)
passes 96 sessions: 1/2/4/8/16/32 pages × prepared/evicted file cache × actual
manager/direct transport × four repetitions. It verifies 1,008 active and
1,008 restored PFNs and no terminal record after all 48 manager DONE events.
Actual module layouts are 688 B per transaction and **64 B per binding**,
including the typed specification. Live requests are 752/816/944/1,200/1,712/
2,736 B for the six sizes. Historical protocol-3 archives retain 56 B bindings.
These are allocation requests, not complete physical slab accounting. Guest
times remain collection evidence rather than formal physical-host performance.

## Actual mapping permissions under two boot policies

The same exact119 kernel, full LZ4 owner, manager and page-module binaries run
with normal protection and with the guest-only `rodata=off` boot option. A
read-only observer records source PFNs and leaf RW/NX/USER flags independently
of the registration implementation. The original kernel-reader source and
frozen Clocktime artifacts are unchanged.

| Boot policy | Direct cases | Accepted | Rejected by direct protocol | Rejected through actual manager |
| --- | ---: | ---: | ---: | ---: |
| Normal | 9 | 2 | 7 | 7 |
| `rodata=off` | 9 | 0 | 9 | 9 |

Each boot covers the actual owner's text, rodata and management pages under
all three declared kinds. Normal text and rodata registrations share the
observed PFNs and restore the original file pages on release. Under
`rodata=off`, the same text and rodata mappings are writable; the kernel
rejects even their matching kinds with EACCES. The manager reaches COMMIT,
returns failure and removes its state. Wrong kinds and management pages are
rejected under both policies. The 16 rejected direct registrations retain
the original destination bytes and PFNs; references return to baseline and
all modules unload. This controlled configuration change tests the actual RW
admission requirement without modifying executable bytes or page tables from
an experiment driver. It is not a performance comparison.

The [normal archive](results/registration-permissions-on-qemu-20260912-attempt02/result.json),
[unprotected archive](results/registration-permissions-off-qemu-20260912-attempt01/result.json)
and [independent joint reconstruction](results/registration-permissions-on-qemu-20260912-attempt02/permission-audit.json)
retain all raw mappings and manager logs. Normal attempt01 stopped because the
observer driver incorrectly assumed an ELF section start must be page aligned;
the driver now records both the exact section address and its containing page.
No product change was needed for that correction.

## Full algorithms with the typed registration implementation

The current manager, protocol header and page module in all three archives
match the worktree byte for byte. Each guest runs the original complete user
workload and the complete current-owner kernel driver in the same registration.
All 13 declared algorithm PFNs match, owner references return to baseline, and
the full source-owner modules unload after restoration.

| Algorithm | Complete kernel checks/records | Additional complete user workflow | Archive |
| --- | --- | --- | --- |
| LZ4 | 24 file/block cases, 792 trials, 1,584 rows; full output and independent liblz4 cross-decode checks | 24 CLI cases, six-backend 36-row component and 192-call four-backend workflow | [LZ4](results/lz4-typed-qemu-20260912-attempt01/kernel-cost-audit.json) |
| BCH | 10,752 decode checks, 3,588 parity checks, 1,056 timing rows | Full m=13, t=4/8, all error counts and three backends | [BCH](results/bch-typed-qemu-20260912-attempt01/kernel-cost-audit.json) |
| XZ | Three complete files, 99 full trials/rows | Original 882 complete decodes | [XZ](results/xz-typed-qemu-20260912-attempt01/kernel-cost-audit.json) |

The two full/export-ready setup sessions per algorithm also pass their raw
stamp and COMMIT/RELEASE/FORGET audits. These six registrations and 36 task
processes preserve the earlier full-task measurement protocol. Guest durations
are not independent physical deployments and do not close C/E performance.

## Built-in execution and large mapping leaves

[XXH32 and sort](results/applicability-typed-qemu-20260912-attempt02/independent-audit.json)
pass all 247/1,152 input combinations in both domains using the current
registration implementation. Each carrier shares two declared pages. Raw
source observations cover both 4 KiB and 2 MiB kernel mapping leaves; no 1 GiB
mapping is exercised. The actual manager records kernel identity verification
before STAGE and COMMIT/RELEASE/FORGET for both roots. Payload manager/module
binaries and supplied source match the worktree in the
[registration reconstruction](results/applicability-typed-qemu-20260912-attempt02/current-registration-audit.json).
The kernel C source is retained separately following that binary comparison.

Attempt01 passed the function matrix using the launcher's older prepared
registration implementation. It is excluded from the protocol-4 result. The
launcher now obtains product files from the current worktree and uses the
prepared directory for runtime dependencies/helpers; attempt02 is the actual
current-product regression. The fixed applicability denominator is unchanged.
