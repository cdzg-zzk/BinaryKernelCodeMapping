# Clocktime：time namespace 共享 MM_data

已实现并用新内核验证：MM_data 从每个 `mm` 一张页改为每个 time namespace 一张页。同 namespace 的 32 个进程少用 31 张物理页（124 KiB），生产代码净减少 3 行有效代码。时间 reader 算法没有改动；本次没有测量应用或 fork/exec 性能。

## 实现

- 初始 namespace 使用一张静态、页对齐的只读用户映射数据页；其他 namespace 创建时分配一张清零页。
- 沿用 `timens_freeze_offsets()` 的锁，首次加入时写入 ABI、offset 和 mask，再以 release/acquire 发布冻结状态。冻结后不再修改页内容。
- exec/fork 保留各自的 VMA、虚拟地址与 mm 引用，共享 namespace 的物理页。用户 ABI 和 40 B payload 不变。
- setns 在 `mmap_write_lock()` 下切换 mm 的 backing，再撤销旧 PTE；下次 fault 映射新页。fork 出的旧 namespace 进程保持原内容。
- namespace、mm 和已 fault 的 PTE 分别持有引用，在各自生命周期结束时释放。

生产改动见 [production.patch](results/production.patch)，构建源码快照见 [source](results/source/)，改动前源码见 [before](before/)。`page_refs.c`、Python 脚本和结果目录均为验证工具，不进入生产路径。

## 实测内存

对照为 [原版实测](../optimization-audit/results/memory/memory.json)，新结果为 [sharing.json](results/guest/sharing.json)。两边均观测同时存活进程的 pagemap PFN；统计唯一物理页，不把多个进程的 RSS 相加。

| namespace / 场景 | 进程数 | 原 MM_data 页 | 新 MM_data 页 | 节省 |
| --- | ---: | ---: | ---: | ---: |
| 初始 / fork，不加载 carrier | 32 | 32 | 1 | 124 KiB |
| 初始 / exec，加载 carrier | 1 | 1 | 1 | 0 |
| 初始 / exec，加载 carrier | 8 | 8 | 1 | 28 KiB |
| 初始 / exec，加载 carrier | 32 | 32 | 1 | 124 KiB |
| 非初始 / exec，加载 carrier | 8 | 8 | 1 | 28 KiB |

完整 carrier 与 MM_data 的物理页并集，在 32 进程组中从 68 页降到 37 页，在 8 进程组中从 20 页降到 13 页。carrier 的每进程私有 RW 页仍存在；本改动没有消除它。

这些是 **新旧 VKSO 的页数对比**，不能据此声称整体内存低于原生 vDSO。此次对齐了原生 vDSO 按 namespace 共享时间数据的生命周期原则。VMA、PTE、namespace 对象和其他内核内存不包含在表内。每个 namespace 新增一个页指针；创建但尚无任务的 namespace 也会提前分配一页。一般情况应按实际 namespace 数计算，而非总按单页计算；每进程独立 namespace 时没有上述共享收益。

## 代码与性能边界

沿用项目 `count_manifest.py` 的词法 SLOC 计数器，对五个改动文件的相同完整文件范围进行前后比较：

| 文件 | 原 SLOC | 新 SLOC | 差值 |
| --- | ---: | ---: | ---: |
| arch/x86/kernel/vkso.c | 146 | 118 | −28 |
| include/linux/time_namespace.h | 112 | 113 | +1 |
| include/linux/vkso_time.h | 60 | 60 | 0 |
| kernel/time/namespace.c | 286 | 310 | +24 |
| kernel/time/posix-timers.c | 949 | 949 | 0 |
| 合计 | 1553 | 1550 | −3 |

这里证明本次优化没有增加生产源码总量。历史论文的 1305 SLOC 使用人工选择的语义范围，不能直接减 3 得到新论文总量；正式新版本比较需要同步更新那份范围清单。

GCC 11.4、正式 Normal 配置下，`vkso_time_core.o` 与 `vkso_time_cycles.o` 的 `.vkso.text` 合计仍为 1191 B，机器码和符号化重定位逐项一致。这不等于完整 reader closure 大小，也不能替代性能实测。fork/exec 不再分配、清零或复制 MM_data 页，但未量化其延迟收益；setns 改为切换页并撤销 PTE，也未测其成本。旧版 20-boot Normal 性能数据仍只属于旧版实现。

## 验证

[audit.json](results/audit.json) 状态为 `pass`，新内核在 4 vCPU KVM 内通过：

- 完整 ABI matrix，包括时间 namespace offset 和冻结语义；
- 实际 clocksource 切换后的 syscall fallback 与恢复；
- 90 次初始/A/B namespace 往返、同虚拟地址读取新内容、360 次时钟 syscall 夹逼检查，以及仍在 A 的兄弟进程 90 次检查；
- 100 次 namespace 创建/切换/销毁，离开后映射数归零、只剩 namespace 所有者引用；
- 16 进程并发首次加入同一新 namespace：16 个映射、33 个引用（所有者 1 + mm 16 + PTE 16），退出后回到 0 个映射、1 个引用；
- settime、TAI、NTP frequency、leap schedule/transition、suspend/resume；
- `CONFIG_TIME_NS=n` 下的架构映射对象编译。

退出进程的 `active_mm` 可能暂留在 idle CPU；引用归零检查前，测试会在各 CPU 调度父进程，以释放这类 lazy mm 引用。首次调试还修正了超过虚拟机 uptime 的负偏移测试值。这两次失败日志保存在 [harness-debug](results/harness-debug/)，生产代码没有为此增加特殊处理。

## 复现

准备应用本次源码改动、使用 `results/package/vkso.config` 和 GCC 11.4 构建完成的内核目录，然后运行（输出目录需不存在）：

```bash
python3 test/test_gettime/namespace-sharing/package.py /path/to/built-kernel /tmp/namespace-package
python3 test/test_gettime/namespace-sharing/run_vm.py /tmp/namespace-package /tmp/namespace-vm
python3 test/test_gettime/namespace-sharing/audit.py
```

前两步需要现有工具链、归档 initramfs 和 KVM 权限；只操作测试虚拟机。第三步使用已归档的前后观测和目标文件独立复算，不会重跑虚拟机。归档包沿用原 Clocktime builder 与配套加载模块，并在新内核中验证了实际加载、替换、恢复和卸载。

论文下一步应冻结这个版本，重跑对应 vDSO 对照与目标应用 macro-benchmark，再决定性能结论。当前已有充分证据写“减少按进程重复的元数据页，且生产代码未增长”，尚无依据写“应用普遍更快”或“总体内存低于 vDSO”。
