# qemu

这个目录当前对应的是 `crc32_le` 函数级 benchmark 的 QEMU/KVM 运行链路。

目前的 guest 里会：

- 直接使用 guest kernel 内建的 `crc32_le_micro`
- 只加载 `micro_pseudo.ko`，通过 `/proc/micro_pseudo/run` 比较 `crc32_le` 和 `crc32_le_micro`
- 分别在 `retpoline / noretpoline` 两套 guest 中运行
- 默认把结果写到 `results/crc32_le/<timestamp>_qemu/`

`run_micro_qemu.sh` 现在会根据环境自动选择：

- 有可写 `/dev/kvm` 时使用 `q35,accel=kvm` 和 `-cpu host`
- 否则退回 `q35,accel=tcg` 和 `-cpu max`

如果退回到 `tcg`：

- guest 里的硬件 PMU 不可用
- `perf stat -e cycles,instructions,...` 会显示 `<not supported>`
- 这时主结果应以 guest 内部 `rdtsc` 归一化后的 `cycles/call`、`cycles/byte` 为准

当前保留下来的脚本有：

- `analyze_guest_modules.sh`
- `build_guest_kernels.sh`
- `build_guest_initramfs.sh`
- `guest_init.sh`
- `guest_runner.sh`
- `parse_qemu_serial.py`
- `run_micro_qemu.sh`

其中 `analyze_guest_modules.sh` 的作用是：

- 不启动 QEMU
- 直接复用 `retpoline / noretpoline` guest 的 build 目录
- 在宿主机外面把 `micro.c` / `micro_pseudo.c` 按 guest kernel 那套编译选项重新编一遍
- 导出对应的 `objdump/readelf`
