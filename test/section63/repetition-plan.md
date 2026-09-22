# BCH repetition and explanation follow-up

Requested on 2026-09-20 after the six-version campaign: repeat unstable results,
explain paper-relevant differences, then update the report and manuscript.

## Fixed repetition package

Add nine complete BCH owner load/register/user+kernel/unregister/unload cycles,
retaining the original three as well. Reuse the identical archived Owner,
Matched, kernel benchmark, Native/Adapted DSO and user benchmark binaries.
Repeat both t=4/8, all error counts, initialization and encode, full and
precomputed decode, three backends in each domain, eleven paired rounds with
the same fixed input generation. Do not select deployments by their performance.
The additional record population is `results/repeat-bch/`.

Report the original and additional populations separately before interpreting
the combined twelve-load distribution. LZ4 and XZ keep their three-load samples.
The relevant unstable observations are kernel t=4 precomputed (including zero
and two errors) and t=8 one-error precomputed. The full BCH matrix prevents
selecting only workloads that happen to stabilize.

## Explanation questions

1. Does Matched's zero/two-error variation recur with identical code and inputs?
2. Are the remaining Owner improvements explained by work executed, helper
   costs, or runtime state rather than simply asserted to be PGOT gains?
3. Can the paper's claim be supported without assigning a cause to every small
   effect? Preserve measured variation even when a controlled diagnostic explains
   a component of the difference.

The original three kernel API address records have identical Stock, Matched and
Owner entry addresses. This excludes changed entry virtual addresses as the
explanation for those three loads; it does not establish identical data placement
or cache state. Any extra instrumented diagnostics remain separate from the
unmodified formal timing population. Production source is frozen.

## Independent PMU/context crossover

After all nine ordinary repetitions finish, run three diagnostic module loads.
Within each load, retain the same six allocated contexts (three backends times
two parameters), and cyclically assign them to Stock/Matched/Owner for three
complete correctness and timing phases. Start rotations 0/1/2 across loads to
balance phase order. Verify that each context and its pointed-to buffers keep
their addresses and visit all three implementations. Kernel algorithm modules
remain unchanged; only the diagnostic observer gains counters and the crossover.

Record cycles, instructions, branch misses, L1D read misses and reference cycles
around whole batches, plus enabled/running time to reject unavailable or
multiplexed event measurements. These measurements explain behavior and are not
pooled into the uninstrumented twelve-load timing table. Compare identical
contexts and error vectors across phases, and inspect cycle/reference-cycle
ratios before attributing a wall-time change to generated code.

The first additional attempt completed user timing but the kernel collector
rejected inherited CPU affinity before kernel timing. Its raw records and
registration recovery are retained in `repeat-bch/pre-kernel-affinity-failure/`;
`repeat-bch/recovery.json` explains the corrected launcher setting. No measured
slow deployment is removed from the complete repetition population.

## User-domain PMU follow-up

The kernel crossover preserved the two-error benefit on identical contexts and
showed fewer executed instructions, but those counters do not explain the user
comparison by themselves. Three additional diagnostic registrations therefore
run the complete unchanged user workload with user-only hardware event groups
around batches. Native, Adapted and actual VKSO binaries remain unchanged.
Counter reads are outside CPU-time intervals, and all inputs and correctness
checks are retained. These three instrumented deployments remain separate from
the twelve uninstrumented BCH timing deployments.

No further performance collections are planned after these controls. The paper
will explain the material two-error/eight-error contrast and retain the observed
short-path variation without asserting an unmeasured microarchitectural cause.
