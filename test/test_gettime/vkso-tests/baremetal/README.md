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

`experiment.sh` is the only reader collection entry point. It fixes all
parameters through `experiment.conf`, enforces the four-case order, verifies
the booted kernel and package identity, refuses overwrites, preserves failed
collections under `results/<run>/incomplete/`, and stores the complete raw
CSV, functional logs, interrupt snapshots and environment metadata. It does
not generate a performance conclusion.

The independent Chinese report for the completed four-image run
`20260727T124135Z-vkso-final` is
[`VKSO_READ性能实验报告_20260727.md`](VKSO_READ性能实验报告_20260727.md).
