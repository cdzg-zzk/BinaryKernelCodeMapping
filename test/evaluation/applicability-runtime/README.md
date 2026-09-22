# Typed built-in API observations

`applicability_runtime.c` calls the actual kernel exports through ordinary
module imports. `applicability_user.c` calls the carrier's typed public API.
Both retain complete raw functional outputs; neither measures performance.
`protocol.h` defines the fixed vectors and portable references, while
`types_check.c` checks the generated API declarations in the guest.

Use the isolated launcher rather than loading this module on the host:

```sh
python3 test/evaluation/applicability_runtime_qemu.py \
  --output test/evaluation/results/applicability-runtime-new
```

The complete protocol, independent reference provenance, page classification,
raw archive and replay commands are in
[applicability-evidence.md](../applicability-evidence.md).
