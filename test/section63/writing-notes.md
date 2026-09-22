# Evaluation writing references

Read on 2026-09-20 for organization, not as evidence for VKSO's measurements.

- [ORC, OSDI 2023, §5.1 and §5.3–5.4](https://www.usenix.org/system/files/osdi23-sartakov.pdf): names the native environments and intermediate configurations before interpreting their costs. The execution discussion connects component separation to complete application costs. For VKSO, keep Native/Stock as the primary denominators and explain what each intermediate version changes.
- [KSplit, OSDI 2022, §7.2](https://www.usenix.org/system/files/osdi22-huang-yongzhe.pdf): distinguishes marshaling microbenchmarks from application performance and explains how the workload's limiting resource affects the result. For VKSO, keep section 6.2's mechanism ablations separate from actual exports and explain the full operation that incurs the observed cost.

Section 6.3 should briefly define its versions and workloads, then devote most
text to the observed user costs, the kernel comparison, and the BCH/XZ causal
controls. Full workload matrices, source diffs and experiment orchestration
belong to this report. The main paper figure and table retain the primary
comparison even when an auxiliary comparison looks more favorable.
