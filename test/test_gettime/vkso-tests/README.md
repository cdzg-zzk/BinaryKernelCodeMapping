# VKSO experiments

This directory contains only the maintained VKSO validation paths:

- `functional/`: the user ABI matrix and the private `libkernel.so` entry
  wrapper used by functional and performance tests.
- `baremetal/`: reproducible four-image reader experiment.
- `update-bench/`: reproducible update-side and read/update concurrency
  experiments.

The final READ, UPDATE and CONCURRENT results, measurement boundaries, complete
tables and unified interpretation are documented in
[`VKSO_READ_UPDATE性能报告_20260801.md`](VKSO_READ_UPDATE性能报告_20260801.md).

Historical milestone directories and historical result analyses are not part
of the maintained experiment.
