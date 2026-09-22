# Section 6.2 — Dependency Adaptation Overhead

- [PGOT benchmark suite](../test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/README.md)
- [Fixed-batch routine results](../test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/results/layer3-fixed-batch-v2/README.md)
- [Confirmatory routine results](../test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/results/layer3-confirmatory-v2/README.md)

Primitive tests compare address reuse/retrieval and helper-call paths. Copied
SHA-256/BCH/zlib/Zstd routines provide Data-PGOT, Func-PGOT and All-PGOT ablations.
Those mechanism-specific controls remain appropriate here. Section 6.3's new
Stock/Matched/Owner protocol applies to the actual exported LZ4/BCH/XZ owners;
it does not replace section 6.2's ablation design.
