# BCH live control and workload allocations

The complete [attempt01](results/bch-heap-qemu-20260912-attempt01/README.md)
passed in boot `15bda703-bf88-4ea1-ba26-da3afa33af3d`. All 567 raw snapshots
replayed successfully; real ELF/source/API coverage was independently checked.
The full original correctness matrix passed, followed by normal restoration
and module unload. Requested bytes are identical for the native and registered
backends: 92,388 B after initialization and 92,930/92,958 B while the t4/t8
context is live. The linked record reports physical interval coverage, overlaps
and allocator-usable bytes separately. Paper Table 23 uses requested live bytes.

This observation extends the existing library/owner page census to persistent
BCH control allocations and the original benchmark's C workload buffers. It
uses the complete unchanged BCH owner and native DSO, the actual exporter and
registration workflow, and the original full correctness matrix in one exact119
private guest. It does not collect timing samples or change the algorithm,
page-cache mechanism, owner lifetime, checker, exporter or shim.

## Configuration and scope

Three controlled roles use 1, 4 and 16 simultaneously alive independent loaders:
native before owner load, native with the dedicated owner loaded, and registered
carrier. Each loader constructs both original parameter cases, m=13 with t=4/8,
and one seeded 512-byte payload plus parity per case. It holds one full-decode
context at a time, first t=4 then t=8, with errors=t and the original trial-0
error-vector seed. This is a resource observation of those live objects; the
complete original three-backend, 128-trial correctness matrix is run separately
in the same registration session.

[`bch_heap_probe.c`](bch_heap_probe.c) includes the unchanged original
`bch_bench.c`, reusing its backend selection, control construction, C allocation,
error generation, decode preparation, full output/location verification and
context release helpers. Per-backend case initialization uses the same codeword
length and seed. The allocation inventory covers the public control structure,
all thirteen pointed-to persistent allocations, two codewords, and the one live
context's work/difference/error-location buffers. The BCH algorithm remains in
the selected full DSO; the observer does not implement a substitute BCH.

The observer verifies the actual user-space allocator bindings before querying
`malloc_usable_size`. Reports distinguish requested bytes, allocator-usable
bytes, and the physical pages covering requested allocation intervals. The
second quantity excludes chunk metadata and does not measure total allocator
cost. Temporary generator-polynomial construction allocations already freed
before `bch_init` returns are outside the live inventory.

Each group stops at nine barriers: before target load, loaded, all library
PT_LOAD pages touched, controls initialized, t4 context verified/live, t4 context
released, t8 context verified/live, t8 context released, and controls released.
The C observation library is already loaded before the baseline. Its PT_LOAD
pages are recorded separately from the target and shim. All loaders reach a
barrier before any process is sampled, and none advances until the group census
finishes. Raw maps, smaps, status and VMA-indexed pagemap bytes are retained.

Heap pages are observed after natural initialization/use; they are not forcibly
faulted by dereferencing every allocation. Overlapping allocation intervals
retain their memberships. Physical unions deduplicate control, workload,
library, shim and whole-owner PFNs before comparing roles. A covering page can
contain allocator metadata or unrelated objects, and a private VMA or pagemap
exclusive bit does not prove global ownership. After free, no former allocation
address is dereferenced; whole-process observations include allocator retention
and observer activity and cannot isolate physical memory returned by BCH.

The owner-loaded native role is a controlled preload, not evidence that an
original kernel workload requires the dedicated owner. Manager, page tables,
observer/runtime allocations and module-external/slab allocations are separate
from the selected allocation/library/owner union. This experiment therefore
extends the accounted scope without claiming a whole-system net saving.

## Entry point

```sh
python3 test/evaluation/bch_heap_qemu.py \
  --output test/evaluation/results/bch-heap-qemu-20260912-attempt01
```

The wrapper requires a fresh output and an ordinary host account on the current
exact119 host. It reuses the prepared private KVM image, builds the full owner,
both ordinary comparison DSOs and original benchmark afresh, and adds the
independent observer. It does not load host modules or install a service. Build
commands, consumed sources and binary identities are retained. Guest process
and raw-data audits are required before this observation is reported as a
result.
