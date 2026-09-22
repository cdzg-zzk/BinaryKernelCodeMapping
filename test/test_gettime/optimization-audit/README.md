# Clocktime/VKSO 优化空间调查

后续进展：下面保留调查当时的实现与证据状态。namespace 共享页现已实现并通过新内核验证，见 [namespace-sharing](../namespace-sharing/README.md)；本目录旧版数据不变。

本次结论：**有进一步优化空间，最确定的是 namespace 元数据的物理共享；当前证据不支持通过几处简单 reader 改写获得普遍性能提升。** 完整实现、归档镜像和正式 20-boot 数据保持原样。这里保存独立候选、诊断记录和下一阶段方案，不替换论文的正式结果。

## 1. 依据与检查范围

调查使用当前 `linux-5.15.198-vkso/` 源码、Normal 正式包、正式实验中捕获的完整 Copy carrier，以及同一台 i7-1165G7 的受控 reader 诊断。CodeGraph 未返回相关内核函数，后续直接检查了对应源码和最终机器码。

已经完成：

- 用原封不动的正式 VKSO 镜像启动 KVM，观测 5 组同时存活进程的 MM_data 和完整 carrier PFN；
- 用正式配置及 GCC 11.4 的 Kbuild 编译 5 个完整 core 变体，保留源码、补丁、目标文件和汇编；
- 重建原始 wrapper 和 coarse 函数，确认它们与归档运行时机器码逐字节一致，再构造独立 carrier 候选；
- 对 3 个 carrier 运行既有完整 ABI matrix、真实 clocksource fallback 和 lifecycle 检查；
- 对 3 个 carrier 各运行 9 个进程、31 轮、7 条 reader 路径，每轮 500,000 次调用，共 5,859 个诊断样本；
- 从原始记录独立复算 PFN 集合、ELF 大小、进程配对比值和功能状态。

[audit.json](results/audit.json) 的状态为 `pass`。镜像、源文件身份及测量条件见 [provenance.json](results/provenance.json)。这里的 reader 实验是单次主机启动、固定用户布局、稳定合成快照下的代码对照；没有实际 writer，也未调整频率或系统隔离。它用于判断指令改动是否值得进入完整实验，不能替代多启动性能或应用结果。KVM 仅用于功能和物理页关系验证。

## 2. 最确定的机会：MM_data 从按 mm 分配改为按 namespace 共享

### 已证明的问题

当前 `arch/x86/kernel/vkso.c` 的 `vkso_alloc_mm_page()` 分配并清零一个 4 KiB 页面；`exec` 调用它，独立 `fork` 也分配新页并复制整页。MM_data 有效字段只有 40 B：ABI version、clock mask、monotonic offset、boottime offset。该结构没有进程私有地址。

实测结果如下。每组内所有进程在取证完成前保持存活，因此不同 PFN 不是退出后重用页面造成的。

| 场景 | 进程数 | 不同 MM_data PFN | 完整 4 KiB 内容 | 当前 MM_data 占用 | 共享一页后的页内容节省（推导） |
| --- | ---: | ---: | --- | ---: | ---: |
| root namespace，fork，不加载 carrier | 32 | 32 | 完全相同 | 128 KiB | 124 KiB |
| root namespace，exec，调用 VKSO | 1 | 1 | — | 4 KiB | 0 |
| root namespace，exec，调用 VKSO | 8 | 8 | 完全相同 | 32 KiB | 28 KiB |
| root namespace，exec，调用 VKSO | 32 | 32 | 完全相同 | 128 KiB | 124 KiB |
| 非 root namespace，exec，非零 offsets | 8 | 8 | 完全相同 | 32 KiB | 28 KiB |

每个加载 carrier 的子进程还创建 4 个线程，确认它们读取同一个 MM_data PFN。新 namespace 的 monotonic/boottime offsets 非零，clock mask 为 210；不是只验证了全部零数据的特例。原始地址、PFN、整页内容、namespace ID 见 [memory.json](results/memory/memory.json)。

另外，32 个进程完整 carrier 的用户映射共有 36 个不同 PFN：4 个共享页（两 text、一 shared state、一 private-entry RX 页）与 32 个绑定后的私有 RW 页；加上 MM_data 后为 68 页。这里的 “private entry” 指它不与内核 text 共用，普通 DSO 的这页 RX 仍可在用户进程间共享。观测再次说明此前“声明闭包 3 页”的证据不等于整个部署只有 3 页。

### 为什么可以改变所有权

当前 MM_data 的内容是 time namespace 的函数，不是 mm 的函数。同一 namespace 的 offsets 在首个任务进入后冻结，后续切换 namespace 改变的是 mm 所引用的对象。只读内容可以由 namespace 持有，各 mm 保留自己的稳定虚拟地址。

同版本原生 Linux 已有相应生命周期模式：`time_namespace` 持有 `vvar_page`，创建 namespace 时分配，在 namespace commit 时初始化并在切换时清除旧映射的 PTE，使其重新 fault 到正确页面。对应原生源码从本地 Linux 5.15.198 源码包提取，保存在 [raw-reference](results/raw-reference/)。它证明这种所有权模式有现成实现依据；不能直接把原生 vDSO 代码不加适配地移入 VKSO。

### 建议方案 A：namespace-owned MM_data

保持 MM_data ABI v3 的字段、auxv 编号和用户虚拟地址契约，改变物理页所有权：

1. root namespace 持有一张 canonical 只读数据页；每个非 root namespace 持有自己的数据页。分配失败在创建/建立映射的可返回错误阶段处理。
2. 在 offsets 冻结处填写 ABI、offsets 和 mask。初始化完成后再发布可用状态；跨 CPU 读取需具备相应 release/acquire 顺序。
3. `exec` 为 mm 建立现有只读 VMA，引用所属 namespace 页；同 namespace 的 `fork` 增加页引用，不复制 4 KiB。
4. `setns` 及进入新 namespace 的 fork 更新该 mm 的 backing 选择，在合适的 mmap 锁下清除旧 PTE/TLB，然后让原有地址重新 fault。**只改 `mm->context` 指针不够**，已有 PTE 否则仍指向旧页。
5. `vkso_mm_fault()` 从 VMA 所属 mm 的状态解析 backing，避免依赖访问者的 `current`。引用计数覆盖 namespace、mm 与已建立 PTE 的寿命；切换和退出分别释放自己的引用。
6. writer 不再向其他 mm 共用的已冻结 namespace 页原地写入。全局时间快照的 seq 和 reader 算法不变。

对一个 namespace 内的 N 个已映射 mm，数据页从 N 张变为 1 张，页面内容节省为 `4096 × (N−1)` B。32 进程对应 124 KiB；这项收益无需依赖 nanosecond 级性能测量。**这是经过观测支持的设计容量推导，优化内核尚未实现，因此不是优化后整机实测值。** 多 namespace 应按实际分配的 namespace 页数 K 计算，包括提前分配但尚无任务的 namespace；VMA/PTE 和 carrier 私有 RW 页不会因此自动消失。

验证下一版实现时，直接复用本次 census，将 MM_data 预期从同 namespace N 个 PFN 改为 1 个；同时覆盖 root/non-root、fork、exec、setns 往返、旧 namespace 释放以及实际时间 offset。既有 namespace ABI 测试仍需全部通过，页数与 reader 指令应分别验收。

**优先级：最高。** 它消除已观察到的按进程重复数据页，也避免不使用 VKSO carrier 的普通进程仍支付整页私有分配。尚未测量 fork/exec 延迟改善，不给出速度收益承诺。

## 3. 性能候选：空参数入口存在可消除成本，但不适合默认采用

归档机器码显示 `vkso_gettimeofday_core()` 在判断 `tv == NULL` 前保存 rbp、rbx、r12–r15；空参数请求仍经过这组保存与恢复。首先尝试在 C 源码提前返回，GCC 仍保留保存/恢复，函数从 282 B 增为 302 B。这一版本淘汰。

第二个候选在已有私有入口判断 `tv | tz == 0`，直接返回 0；其余请求继续进入原 shared core，不改变 syscall fallback。候选保留两 text 页和 shared-state 页的内核共享，新增判断不复制时间算法。

| 路径 | 原 carrier（TSC ticks/call） | 候选 | 配对中位成本变化 |
| --- | ---: | ---: | ---: |
| `gettimeofday(NULL,NULL)` | 约 9.05 | 7.02 | −22.36%，约少 2 ticks |
| 仅 timezone | 约 13.05 | 13.05 | 约 0% |
| 仅 timeval | 约 56.22 | 56.52 | +0.52% |
| timeval + timezone | 约 56.23 | 56.96 | +1.30% |

这些是本次受控代码诊断值，不是正式报告中 6.021/8.028 cycles 的替代值。两组实验的状态、调用位置和运行条件不同。

源码补丁见 [entry-null.patch](results/carriers/entry-null.patch)。候选通过真实 VKSO 镜像上的完整 ABI matrix、非零 namespace、setns、provider syscall fallback 和 lifecycle 检查。数值与各进程范围见 [reader summary](results/readers/summary.json)，完整功能记录见 [functional](results/functional/)。

**决定：保留为原因验证，不建议默认合入。** 它说明短路径回归并非不可消除，但将代价转移到实际取时间的调用。单纯优化这一项可以美化 20 接口的等权平均，却不能证明应用更快。若应用 profile 不能证明空参数调用重要，就不值得付出这个交换。

## 4. 代码量与热点改写：需要看生成结果，不能按源码直觉判断

下表使用正式配置与 GCC 11.4 Kbuild，统计 `vkso_time_core.o` 和 `vkso_time_cycles.o` 的 `.vkso.text` section 总字节，包含对象内部对齐。不包含其余内核 reader、private wrapper 或 thunk，因此不等于论文的 2,055 B 完整 reader closure。

| 变体 | 两对象 `.vkso.text` 字节 | 变化 | 验证与判断 |
| --- | ---: | ---: | --- |
| 当前实现 | 1,191 | — | 对照 |
| coarse 在读快照后检查 offset | 1,191 | 0 | 单函数 136→129 B，但 7 B 被对齐填充吸收；未观察到稳定加速 |
| gettimeofday 在 C 中提前处理 NULL | 1,207 | +16 | 单函数 +20 B；寄存器保存未消失，淘汰 |
| 强制高精度换算只生成一个非内联函数体 | 1,255 | +64 | 合并后增加参数/调用成本，总量反而更大，淘汰 |
| cold provider/normalize 改为保存调用者寄存器 | 1,272 | +81 | 热路径六组寄存器保存仍在，冷函数增大；没有合入依据 |

coarse 候选通过每次运行 60,000 个 root/namespace/NULL-MM 数值对照、真实镜像 ABI 和 provider/lifecycle 检查。原函数和原 wrapper 的逐字节重建也通过。诊断中 realtime coarse 的配对中位比约 0.99996，root monotonic coarse 约 1.00023，namespace monotonic coarse 约 1.00089，不能称为有意义的加速。所有进程比值范围均保留，未删除偶发较慢的对照进程。

最后一项使用 GCC 的 `no_caller_saved_registers` 属性；其语义见 [GCC x86 属性文档](https://gcc.gnu.org/onlinedocs/gcc/x86-Attributes.html)。本次目标编译器实际生成结果比属性名称更重要：指定了冷函数保存寄存器，并没有让热函数自动成为无栈叶函数。

源码、补丁与完整汇编见 [codegen](results/codegen/)。这些尝试支持的判断是：**当前小型 reader 已经过较充分的局部压缩；常见的“提前判断”“抽公共函数”“让冷函数保存寄存器”都不能直接视为收益。** 它们不证明全局最优，也不排除经过重新设计的热/冷分界有进一步收益。

## 5. 后续优化顺序与停止条件

| 顺序 | 方案 | 当前证据 | 下一步验收 |
| --- | --- | --- | --- |
| P0 | namespace-owned MM_data | 活进程 PFN 重复、相同 payload、冻结语义及原生生命周期参考均已确认 | 同 namespace 一页；fork/exec/setns 的语义与寿命正确；完整资源账本 |
| P1 | 审查完整 carrier 的每进程 RW 成本 | 每个加载进程确实产生 1 页 RW backing；40 B context 与 ELF metadata 同页 | 判断是否能复用已有进程存储，且不增加每次调用的 TLS/间接访问；目前只有定位，没有已验证方案 |
| P2 | 应用接入后按实际热点选择 reader 改动 | 当前接口等权平均不代表应用调用分布；NULL 特例已有明确交换代价 | 证明实际调用经过 VKSO，记录 clock mix，再以吞吐/延迟决定优化价值 |
| P3 | 更深的 high-resolution 热/冷重构 | 当前 prologue/spill 已定位，简单编译属性方案未奏效 | 在保留 provider、namespace、失败路径的完整实现中，生成更短热路径并进行配对实测 |

P1 不能简单合并“用户可写 context”和“内核发布、用户只读 MM_data”：它们权限与所有权不同。改用 TLS、改变公共绑定 ABI 或调整 carrier 元数据布局，都需要同时算调用开销、初始化和页占用；目前不把它们列为已证明的净节省。

现有 writer 跨启动波动很大，本次没有从均值推断 writer 实现低效，也没有通过删减共享字段或取消 fallback 寻找好看的数值。正式状态下 `cycles.mask` 的发布与其读取用途可以作为后续很小的清理项，但单个字段减少不改变 4 KiB 页分配，不列为主优化。

判断是否继续投入，建议采用明确停止条件：

- P0 达成物理页共享且功能不变后，先形成完整资源结果；不要等所有微小路径都最快才整理论文。
- Reader 改动若只改善无实际权重的特例，或转移成本、增加字节而无实测收益，保留诊断后停止合入。
- 应用级证据完成后，再判断真实热点是否值得付出 ABI/结构重构成本。当前证据没有证明 VKSO 可普遍超过原生 vDSO。

## 6. 复查与复现

仅复查已有结果，无需 root、模块或虚拟机：

```bash
python3 test/test_gettime/optimization-audit/audit_results.py
```

重跑 reader 诊断（输出目录须不存在）：

```bash
python3 test/test_gettime/optimization-audit/run_readers.py \
  test/test_gettime/optimization-audit/results/carriers /tmp/clocktime-readers-new
```

重新构造候选 carrier：

```bash
python3 test/test_gettime/optimization-audit/build_carriers.py \
  test/test_gettime/optimization-audit/results/codegen /tmp/clocktime-carriers-new
```

重跑物理页 census 与候选功能验证：

```bash
python3 test/test_gettime/optimization-audit/run_memory.py /tmp/clocktime-memory-new
python3 test/test_gettime/optimization-audit/run_memory.py /tmp/clocktime-functional-new \
  --candidates test/test_gettime/optimization-audit/results/carriers
```

虚拟机使用已有 `reader-load-v4-normal` 正式包和 `revision/results/qemu-read-final/initramfs.cpio.gz`，依赖 KVM、QEMU、ext4/debugfs 工具。模块加载与 clocksource 切换仅发生在虚拟机。脚本不会重启主机。

重新做代码生成检查，先将 `linux-5.15.198-vkso/` **完整复制**到独立临时目录，复制正式包 `vkso.config` 为该目录的 `.config`，运行 `make olddefconfig prepare`，然后：

```bash
python3 test/test_gettime/optimization-audit/codegen.py \
  /tmp/独立内核源码副本 /tmp/clocktime-codegen-new
```

`codegen.py` 会在所给副本中切换候选源码并编译，不能把正在维护的源码目录作为参数。它最终恢复该副本的原 core/header 源码；构建对象仍是诊断产物。正式源码、本次基线镜像及历史结果没有被替换。
