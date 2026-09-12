# Algorithm evidence and repetition audit

Verified 2026-09-11 against the current runners and the archives listed below.
No new algorithm performance measurements have been collected in this stage.

## Existing result identity

| Algorithm / archive | Deployment and process boundary | Complete raw matrix | Primary comparison |
| --- | --- | --- | --- |
| [LZ4](../test_lz4/results/) | One owner load and registration; 7 outer rounds, 105 timed processes (round × block × backend) | 210 rows; compression/decompression share each harness invocation | Kernel-backed adapted Linux 5.15 source vs. the same source in a no-SIMD user DSO with test-local REP helpers |
| [BCH](../test_BCH/results/) | One owner load and registration; one process loads all backends before 11 outer rounds | 1,056 rows; m13t4/m13t8 and all configured operations/error counts | Kernel-backed adapted Linux 5.15 source vs. that adapted source in a user DSO; helper bindings/build domain differ |
| [XZ](../test_xz/results/formal-20260806/) | One owner load and registration; one process loads both backends before 7 outer rounds | 42 rows; 3 inputs × 2 backends × 7 rounds, 20 decodes per row | Same four Linux 5.15 decoder source files, owner build vs. ordinary user DSO |

The archive metadata reports 7/11/7 rounds respectively. Top-level runners
load and export once, then invoke `run_under_replacement.sh` once. LZ4's shell
loop invokes the official benchmark for each round/block/backend. BCH's
`main()` loads the three libraries before `run_benchmark()`; XZ similarly
loads its libraries before the outer loop. These are measurement repetitions
within a deployment, not repeated owner reloads or independent boots.

LZ4's upstream 1.9.3 DSO and BCH's earlier author standalone branch remain
separate practical user-space references. They are not source-identical to
the kernel owner. LZ4's native/no-SIMD comparison changes both compiler
settings and memory helpers, so it does not isolate SIMD alone. BCH's
`kernel-native` uses libc compatibility helpers rather than reproducing all
kernel compilation and binding details. XZ's user DSO uses ordinary `-O2
-fPIC` compilation, whereas the owner disables kernel-only instrumentation
and unsupported instructions. None of these comparisons alone isolates page
backing from every compilation/helper effect.

The owners are test modules, `vkso_lz4.ko`, `vkso_bch.ko`, and `vkso_xz.ko`.
Their runners do not replace the running kernel's original subsystem users.
Consequently, these algorithms establish export and same-source execution;
they do not demonstrate removal of an existing stock kernel/user duplicate.
Net memory accounting must include a newly added owner where applicable.
Clocktime's integrated kernel replacement is a different deployment case.

Adaptation sources are the LZ4 [Makefile](../test_lz4/Makefile), owner sources
and user compatibility layer; BCH [ADAPTATIONS.md](../test_BCH/ADAPTATIONS.md)
and source diff; and XZ [ADAPTATIONS.md](../test_xz/ADAPTATIONS.md). Their
compiler restrictions and dependency-binding changes feed the applicability
ledger in group D. Final closure/page-map audits describe ELF structure and
declared replacement targets; active PFN and full resource accounting remain
group B evidence.

## BCH diagnostic targets

Recomputed from `total_ns / iterations`, pairing the kernel-backed and
same-source user observations within each of the 11 archived rounds:

| m13t8, 512-byte input | Errors | Median latency ratio | Minimum–maximum round ratio |
| --- | ---: | ---: | ---: |
| decode-precomputed | 2 | 1.209496 | 1.077730–1.518721 |
| decode-precomputed | 0 | 0.987736 | 0.968622–1.006477 |
| decode-full | 2 | 1.038553 | 1.025456–1.088334 |
| decode-full | 0 | 1.003388 | 0.999709–1.005244 |

Values above one mean greater latency for kernel-backed execution. The ranges
are descriptive within-deployment observations, not confidence intervals.
The two-error precomputed case is slower in every archived round, whereas the
zero-error fast path is near parity. Full decode also times encoding the
damaged payload and XOR with the received ECC. Precomputed decode prepares
that ECC difference before timing; both modes pass `syn=NULL` and retain
syndrome calculation, error-locator construction and root solving when the
difference is nonzero. Neither timed mode applies the returned bit flips.
For zero errors, full decode returns immediately after its ECC comparison;
precomputed decode still runs the zero-syndrome locator path. The zero-error
control therefore has a different early-return boundary in the two modes.

In `bch_bench.c`, the error vector is generated once per
round/case/operation/error-count before the backend loop. Every backend in
that comparison receives the same vector. The deterministic seed changes
across rounds. Calibrated iteration counts can differ by backend, so compare
per-operation costs rather than total sample duration. Backend order rotates
with round, case, operation, and error count. These observations eliminate
different error positions within a paired comparison as an explanation;
they do not establish a hardware or layout cause for the regression.
The seed also includes operation mode, so full and precomputed rows do not
share error positions. Subtracting their times is not a paired measurement
of the removed ECC-preparation work.

For two valid errors, both t=4 and t=8 select the degree-two root solver.
The larger t increases ECC width, syndrome count and the Berlekamp–Massey
iteration bound; it does not itself select a higher-degree root branch.
The [decode-path audit](bch-decode-path-evidence.md) links these facts to
source and original-hash-matching binaries. It does not identify which
instructions or layout effects caused the measured regression.

The full redeployment campaign preserves all cases and seeds. After examining
its per-deployment results, use the four rows above for a focused PMU/helper
diagnostic, separate from the uninstrumented main measurements. A stage-cost
diagnostic must reuse identical payloads and error positions across both
decode modes, and record their exact vectors and invocation order. Runtime
path evidence should distinguish syndrome work, error-locator construction
and the degree-two root branch without treating t=8 as a higher-degree case.
Actual
in-kernel execution cost of an adapted owner remains a separate group C
deliverable; the existing user-side and copied-closure results do not supply it.
