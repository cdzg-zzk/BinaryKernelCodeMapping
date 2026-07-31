# Four-image VKSO reader experiment

The final reader experiment has four cases, always collected in this order:

1. raw vDSO, normal mitigation configuration;
2. VKSO, normal mitigation configuration;
3. raw vDSO, retpoline/rethunk disabled;
4. VKSO, retpoline/rethunk disabled.

`build-all.sh` constructs both package pairs from one base configuration and
one compiler environment. `verify-packages.sh` rejects implementation-external
raw/VKSO configuration differences and non-retpoline-related cross-variant
differences. It also requires byte-identical benchmark executables.

For the normal mitigation build, `reusable_text.txt` lists the static x86
thunks that runtime-patched VKSO branches may reach. The DSO builder treats
them as native dependency roots and maps their RX pages independently; the
list does not assume that those symbols remain on one physical page.

`experiment.sh` is the only reader collection entry point. It fixes all
parameters through `experiment.conf`, enforces the four-case order, verifies
the booted kernel and package identity, refuses overwrites, preserves failed
collections under `results/<run>/incomplete/`, and stores the complete raw
CSV, functional logs, interrupt snapshots and environment metadata. It does
not generate a performance conclusion.

The independent Chinese report for the final completed four-image run
`20260728T013904Z-vkso-final`, including the Base2 optimization comparison,
is [`VKSO_READ性能实验报告_20260728.md`](VKSO_READ性能实验报告_20260728.md).

The independent update-side report for the stabilized paired run
`20260728T031855Z-update-side` is
[`VKSO_UPDATE性能实验报告_20260728.md`](../update-bench/VKSO_UPDATE性能实验报告_20260728.md).
It measures the complete `timekeeping_update()` writer and explains the
performance difference between native `update_vsyscall()` and
`vkso_time_publish()`.

The independent read/update concurrency report for paired run
`20260728T043508Z-update-concurrent` is
[`VKSO_READ_UPDATE并发性能实验报告_20260728.md`](../update-bench/VKSO_READ_UPDATE并发性能实验报告_20260728.md).
It evaluates public readers, the complete update writer, and seq retry
behavior while read and update execute concurrently.

These three reports are complementary rather than interchangeable:
standalone READ uses the public-entry/PMU harness, UPDATE measures the complete
idle writer, and CONCURRENT uses sustained saturated readers. Absolute cycles
from different harnesses must not be subtracted as though they shared one
measurement boundary.
