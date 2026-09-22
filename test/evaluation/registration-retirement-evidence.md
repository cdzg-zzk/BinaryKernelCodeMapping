# Completed registration records and recovery

The manager now sends FORGET after RELEASE has confirmed zero applied pages
and a RESTORED or ABORTED transaction. Successful holding sessions complete
this step before clearing their local state and emitting DONE. This removes
the previously observed accumulation of one 688-byte requested transaction
object per completed manager session. The kernel protocol and allocation
sizes are unchanged.

## Recovery behavior

FORGET removes the very record that would otherwise answer QUERY. If its
reply is lost, the manager queries the same transaction ID and accepts a
confirmed ENOENT/UNKNOWN response as completion. It still retains recovery
state when delivery or the query is unconfirmed. A failed RELEASE never
advances to FORGET.

The [full transaction guest](results/registration-retirement-qemu-20260912-attempt02/result.json)
passes in boot `816fa853-981b-4cb9-a058-5d171ecb08ae`. It reuses the existing
three/300-page matrix, owner pins, partial rollback and retry, image identity,
root/sudo notification and ordinary file/VMA cases. New interruptions occur
at the real manager checkpoints after RELEASE and after FORGET:

| Interrupted point | QUERY while manager is stopped | Reconnected restore |
| --- | --- | --- |
| RELEASE confirmed, before FORGET | RESTORED, zero applied pages | Repeats RELEASE, sends FORGET, clears managed immutable/state |
| FORGET confirmed, before local cleanup | ENOENT, UNKNOWN | Confirms transaction absence and clears managed immutable/state |
| FORGET reply deliberately dropped | Manager's subsequent QUERY returns ENOENT | Completes without leaving local state |

The existing lost COMMIT and RELEASE replies also recover, and a partial
release failure retains state until the remaining page is restored. At the
end, all 17 distinct manager-created transaction IDs found in the archived
logs return ENOENT. The source owner and registration module unload normally.
[The independent audit](results/registration-retirement-qemu-20260912-attempt02/retirement-audit.json)
replays these states and the complete notification/file evidence.

A stopped manager still owns its netlink socket. The two new checkpoints
observe source-owner refcount zero and registration-module refcount two,
corresponding to the controller and manager sockets. After manager exit the
transport returns to its one-socket baseline; after the controller closes it
returns to zero. Attempt01 retained an incorrect assertion that the stopped
manager should already match the closed-manager baseline. Its failing record
is preserved; the manager implementation did not change for the passing rerun.

## Repeated sessions and accounting

[The updated scale run](results/registration-scale-qemu-20260912-attempt02/result.json)
passes in boot `85f23a23-969a-4741-9337-82f85bff8f39`, with the original
1/2/4/8/16/32-page × prepared/evicted × manager/direct × four-round matrix.
All 96 sessions preserve their realized cache state, 1,008 active PFN matches
and 1,008 restored mappings. Each of the 48 manager sessions has a successful
FORGET in its log and an absent transaction after DONE. The direct protocol
control continues to retain its terminal record after RELEASE, then issues
its own FORGET outside its measured release interval.

The active allocation requests remain 688+56N B. The direct control retains
688 B between RELEASE and its explicit FORGET; the complete manager retains
zero transaction-object bytes after DONE. This is object lifetime and requested
allocation accounting, not a claim that the allocator returns an entire slab
page to the system at every FORGET. Complete physical resource accounting
remains outstanding.

The new manager's observed smaps RSS is 1,532–1,548 KiB, with six open file
descriptors and 65,536 B FIFO capacity. These measurements are separate from
transaction requests, and FIFO capacity is not resident memory. The external
release-to-DONE interval now includes the extra FORGET exchange. Kernel
RELEASE time remains the RELEASE result field; its cumulative prepare/apply
fields are not added again from the FORGET reply. Guest timings are collection
evidence rather than a physical performance comparison with the old manager.

[The scale audit](results/registration-scale-qemu-20260912-attempt02/independent-audit.json)
uses the archived manager source to distinguish this behavior from attempt01,
which retained records after manager exit. Historical raw data and estimates
remain unchanged. Setup auditing likewise recognizes the archived manager's
operation sequence and keeps COMMIT, RELEASE and FORGET separate.

## Complete LZ4 workflow

[The application session](results/lz4-retirement-qemu-20260912-attempt01/result.json)
passes in boot `290d2ea9-eefc-4deb-81c2-3bf406edee3e` with the preceding
kernel-cost run's full owner image and the new manager. It completes all 24
input/block functional cases, 36 six-backend component rows and 192 complete
four-backend CLI workflow calls. Five declared PFNs and normal restoration
pass. Both full export and ready-carrier setup sessions complete FORGET;
the setup audit preserves all 12 task processes and separates the additional
exchange from kernel RELEASE. See [workflow verification](results/lz4-retirement-qemu-20260912-attempt01/retirement-workflow-audit.json)
and [setup reconstruction](results/lz4-retirement-qemu-20260912-attempt01/setup-audit.json).

## Reproduction

Use [the existing transaction launcher](registration_completion_qemu.py) with
the rebuilt current manager, the full transaction fixture and the exact119
sudo-capable initramfs. The executed arguments and all copied sources and
binaries are in each archive's `command.json`, `source` and `payload`.

```sh
make -C page_cache_replace manager
python3 test/evaluation/registration_retirement_audit.py \
  test/evaluation/results/registration-retirement-qemu-20260912-attempt02
python3 test/evaluation/registration_scale_audit.py \
  test/evaluation/results/registration-scale-qemu-20260912-attempt02
```

This change addresses completed-session accumulation. B still requires complete
physical accounting, formal setup performance and source-page admission/runtime
rewriting work. The current source predicate permits the broad built-in image
range and cooperative owner text/RO ranges; transaction retirement does not
strengthen that predicate or certify final runtime instructions.
