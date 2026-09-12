# Exact119 module-layout fields

The installed debug ELF and DWARF confirm the meanings in
[interpretation.json](interpretation.json). [identity.json](identity.json)
records its SHA-256/build ID; [package-versions.txt](package-versions.txt)
identifies the exact `5.15.0-119.129` debug/header packages. No 186 source
implementation is used as proof.

- `/proc/modules` prints `core_layout.size + init_layout.size`, but its displayed address is only `core_layout.base` (or zero when hidden).
- `/sys/module/NAME/coresize` reads `core_layout.size`; `initsize` reads `init_layout.size`.
- The exact119 successful `do_init_module` path clears both init base and size before returning. Completed stable loads should therefore have zero initsize and equal proc/core sizes; actual guest state still needs its ordinary observation.

Use visible core base plus sysfs coresize for the core-layout interval.
The proc total does not locate the init allocation and cannot define a
contiguous core-plus-init interval. It provides no authority to probe a
freed init allocation.

[gdb.log](gdb.log) contains field offsets and byte disassembly.
[bindings.log](bindings.log) resolves the actual sysfs callback bindings,
sequence show callback, format strings and module.list offset. The latter
matters: m_show receives the list node at module+8, so its +0x140/+0x190
loads read size fields at module+0x148/+0x198. The header excerpt confirms
that layout.size is the total code+data size of that layout.

These are read-only binary/type observations. No kernel code, host module,
guest or inferior process was executed. No source or kernel was downloaded.
The evidence does not measure the lifetime or full memory cost of any module.
