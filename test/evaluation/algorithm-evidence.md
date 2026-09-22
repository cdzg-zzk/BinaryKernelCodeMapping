# Algorithm evaluation evidence

The [current section 6.3 results](../section63/README.md) contain the complete
LZ4/BCH/XZ user and same-owner kernel experiment. [Methods](../section63/methods.md)
define the baselines, adopted source changes, workloads and paired statistics.

Functionality and physical-page observations have separate scopes:
[LZ4](lz4-helper-baseline-evidence.md), [BCH](bch-functional-evidence.md),
[XZ](xz-functional-evidence.md), and [kernel-driver validation](kernel-cost-evidence.md).
Their guest timing records are not physical-host performance samples.
