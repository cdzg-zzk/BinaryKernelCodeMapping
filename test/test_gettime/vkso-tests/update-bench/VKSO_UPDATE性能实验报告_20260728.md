# VKSO UPDATE-SIDE 最终性能实验报告

> 正式实验批次：`20260728T031855Z-update-side`  
> 启动稳定性对照批次：`20260728T025421Z-update-side`  
> 实验平台：Intel NUC 裸机，Linux 5.15.198，TSC clocksource  
> 对比对象：原生 raw vDSO update-side、最终 VKSO update-side  
> 报告范围：完整 `timekeeping_update()` writer；不包含用户态 reader 和
> read/update 并发

## 1. 实验目的

本报告独立回答以下问题：

1. VKSO 替换原生 vDSO 发布逻辑后，完整 `timekeeping_update()` 是更快还是
   更慢；
2. 典型延迟、平均延迟和 P95/P99 长尾分别改变多少；
3. 实验是否真正比较了功能等价、配置一致的 Raw/VKSO 镜像；
4. 性能差异来自公共 timekeeping 工作，还是 Raw/VKSO 各自的数据发布协议；
5. 第一轮实验中的 VKSO 长尾是否属于稳定实现成本；
6. 当前结果能支持什么结论，不能支持什么结论。

本报告与
[`VKSO_READ性能实验报告_20260728.md`](../baremetal/VKSO_READ性能实验报告_20260728.md)
互相独立。READ 报告评价 reader；本报告评价 writer/update-side。
后续正式并发结果见
[`VKSO_READ_UPDATE并发性能实验报告_20260728.md`](VKSO_READ_UPDATE并发性能实验报告_20260728.md)。

## 2. 核心结论

- 正式实验中，完整 `timekeeping_update()` 的多轮中位结果为：
  - Mean：Raw **131.736 cycles**，VKSO **129.431 cycles**，
    VKSO 快 **2.305 cycles / 1.750%**；
  - Median：Raw **126 cycles**，VKSO **122 cycles**，
    VKSO 快 **4 cycles / 3.175%**；
  - P95：Raw **168.6 cycles**，VKSO **169 cycles**，
    仅差 **0.4 cycle / 0.237%**，可视为持平；
  - P99：Raw **454 cycles**，VKSO **488.53 cycles**，
    VKSO 高 **34.53 cycles / 7.606%**。
- 扣除两次有序 TSC 读取的共同最小开销 33 cycles 后：
  - Mean：VKSO 快 **2.334%**；
  - Median：VKSO 快 **4.301%**。
  扣除只改变百分比分母，不改变 Raw/VKSO 的绝对差。
- 合并两侧全部约 5.6 万个原始样本后，结论仍一致：
  VKSO Mean 快 **2.535%**、Median 快 **2.381%**、P95 基本持平。
- VKSO P99 略高不等于极端峰值更严重：
  `>1000 cycles` 和 `>5000 cycles` 的样本比例都低于 Raw，
  本轮观测到的最大值也是 Raw 更高。
- 第一轮未等待系统稳定时，VKSO Mean/P95/P99 分别表现为
  **+5.620% / +7.131% / +24.898%**。增加 120 秒稳定期后变为
  **-1.750% / +0.237% / +7.606%**，而 Median 的 **-4 cycles**
  完全复现。这证明第一轮的主要长尾不是固定 VKSO 代码成本。
- 从实现看，Raw 与 VKSO 的公共 timekeeping 工作相同。差异集中在：
  - Raw 调用 `update_vsyscall()`，维护两组 vDSO clocksource 数据和两个
    seq；
  - VKSO 调用 `vkso_time_publish()`，维护裁剪后的 shared_data 和一个
    seq。
- 在本次 TSC 实验路径中，VKSO 少发布两个 mask 字段、少两次 seq store，
  并复用 monotonic/boottime 派生结果。这个结构性缩减与测得的
  **2–4 cycles** 典型收益相符；但完整函数基准没有单独计时 publication
  子函数，因此这是由源码和结果共同支持的实现解释，不是单变量因果分解。
- 后续并发实验进一步显示，在三个公开 reader 饱和场景下，VKSO writer
  Median 仍低 **5～12 cycles**，而 odd-seq 自旋减少约 **99%**。这补足了
  空闲 update 实验无法回答的读写竞争问题。
- 最终判断是：**VKSO 没有以 reader 优化为代价拖慢 timekeeping writer；
  相反，完整 update-side 的典型和平均开销降低约 2%–3%，P95 与 Raw
  持平，只在 P99 分位点存在轻微劣势。**

## 3. 被测镜像与数据身份

### 3.1 构建身份

| 项目 | 值 |
|---|---|
| Kernel release | `5.15.198` |
| Git commit | `9ad92a19598c52b7c28bc5bfc3f999d68edd2de2` |
| 编译器 | GCC `11.4.0` |
| 编译变体 | `normal` |
| update benchmark | `CONFIG_TIMEKEEPING_UPDATE_BENCH=y` |
| 配置差异检查 | `implementation_selects_only` |
| Raw native vDSO | `present` |
| VKSO native vDSO | `absent` |
| production test probe | `absent` |

镜像与源树身份：

| 对象 | SHA-256 |
|---|---|
| Raw Image | `e639416310ce2b105f4560893741e0fce3fd3b3cecc24331faacc5784477895c` |
| VKSO Image | `ca43e0605bed6c39f0f285c99d13178c77c120dc71f0e1d7b17070c2a4c501af` |
| Raw source tree | `fdba196b751997d68e900c4c958e9a3d1181644f6cbe6041f3d32b84a66720d0` |
| VKSO source tree | `39a7ecda00197c3b8d04fba079709f097a6c61e65a2cf4238b0a6e7984b356c8` |
| Experiment config | `f843a7e1f59859fe00a071f5397d9c2b4d16df480b1fdee4f1d9730368797268` |
| Benchmark header | `095c3c20828e7b265c259e7cde8dbf986ee613ff5ecec068f709131db4dc4e55` |
| Benchmark recorder | `d07856a6eacf537ee050f2abb09ac3259d1f0d42748a8aec1867965b89464517` |

构建 manifest 中 `git_worktree_dirty=1`，因为构建时工作树还包含实验脚本和报告
修改。实验身份不依赖这个布尔值：两个实际 Image、两个独立 kernel source
tree、配置文件以及 benchmark 源文件都有单独 SHA-256，本报告以这些哈希和
实际启动镜像为权威身份。

### 3.2 正式结果身份

正式结果目录：

```text
test/test_gettime/vkso-tests/update-bench/results/20260728T031855Z-update-side/
```

关键结果哈希：

| 文件 | SHA-256 |
|---|---|
| `update-comparison.csv` | `c432cafa7c0119aef726716df6c268411177b3ea1edf46ac586bbafff473ac16` |
| Raw `update-summary.csv` | `6f04073141f4a0b5b852588a53839e81c43520d4cb1548fa52b5b09c68221377` |
| VKSO `update-summary.csv` | `bb424d3f57d293e0a71d7a7f3c5f27ee6efee674ccae6da4ec83b0d4f6b0e3f7` |
| Raw `writer-rounds.csv` | `5c34647f3bb48ea2caf5f7870d589903550f5fe09561f6c41eb06d11022c9e31` |
| VKSO `writer-rounds.csv` | `1c0a0ecfa57bd0a0742b893bcf296d44c638fa868dfa8de0cfcfbbd87f06510c` |

## 4. 测量范围与方法

### 4.1 测量边界

插桩位于完整 `timekeeping_update()` 的入口与出口：

```text
start = rdtsc_ordered()
    完整 timekeeping_update()
end = rdtsc_ordered()
sample = end - start
```

它覆盖：

- NTP action 判断；
- leap-state 和 ktime 数据更新；
- Raw `update_vsyscall()` 或 VKSO `vkso_time_publish()`；
- `update_pvclock_gtod()`；
- `base_real` 和两个 fast timekeeper 更新；
- clock-was-set、shadow mirror 等 action 分支。

正式样本全部为 `action=0`，因此没有混入
`TK_CLEAR_NTP`、`TK_CLOCK_WAS_SET` 或 `TK_MIRROR` 慢路径。

插桩由 static key 控制。未启用 benchmark 时只保留关闭的静态分支；启用时
才执行两次 `rdtsc_ordered()` 和样本记录。结束时间戳在调用 recorder 前取得，
所以写 debugfs 样本数组的成本不计入 `timekeeping_update()` cycles。

对应实现：

- [`timekeeping_update_bench.c`](../../linux-5.15.198-vkso/kernel/time/timekeeping_update_bench.c)
- [`timekeeping_update_bench.h`](../../linux-5.15.198-vkso/include/linux/timekeeping_update_bench.h)

### 4.2 实验配置

每个 backend：

```text
stabilize_seconds=120
repeats=15
update_seconds/round=15
updates_per_second=250
expected samples/round≈3750
clocksource=tsc
tsc_pair_min=33 cycles
```

启动参数：

```text
nokaslr
clocksource=tsc
tsc=reliable
nosmt
isolcpus=domain,managed_irq,2
nohz_full=2
rcu_nocbs=2
irqaffinity=0-1,3
idle=poll
intel_pstate=active
processor.max_cstate=0
intel_idle.max_cstate=0
nmi_watchdog=0
nowatchdog
audit=0
```

收集脚本还设置：

```text
turbo=off
min_perf_pct=100
max_perf_pct=100
governor=performance
```

稳定等待发生在以下操作之后：

1. 验证实际启动的 Raw/VKSO Image；
2. 核对运行中 `.config`；
3. 设置 CPU frequency policy；
4. VKSO 完成 libkernel.so 页面替换；
5. 完成 76 项 ABI/功能矩阵；
6. 等待 120 秒；
7. 才打开 update recorder。

所以功能测试、页面建立和启动后服务活动不会主动混入测量区间。

### 4.3 统计口径

正式 `update-comparison.csv` 的每个指标按以下顺序产生：

1. 每轮独立计算 count、Mean、Median、P95、P99；
2. 对 15 轮的同名指标再取中位数；
3. 计算 `Δ = VKSO - Raw`；
4. 计算 `Δ% = (VKSO / Raw - 1) × 100%`。

因此，负百分比表示 VKSO 更快。

报告同时给出全部原始样本合并后的 pooled 统计，作为聚合方法敏感性检查。
pooled 结果不是用来替换正式多轮结果，而是确认结论没有由单个 round 的
中位数组合方式制造出来。

## 5. 实验有效性

| 检查 | Raw | VKSO | 判断 |
|---|---:|---:|---|
| 完成标记 | 有 | 有 | 通过 |
| ABI matrix | pass | pass | 通过 |
| 稳定等待 | 120 s | 120 s | 一致 |
| rounds | 15 | 15 | 一致 |
| 每轮时长 | 15 s | 15 s | 一致 |
| 典型样本数/轮 | 3750 | 3750 | 一致 |
| 丢失样本 | 0 | 0 | 通过 |
| 非零 action | 0 | 0 | 通过 |
| TSC pair min | 33 | 33 | 一致 |
| 更新频率 | 250/s | 250/s | 一致 |

Raw 共记录 **56,247** 个普通更新样本，VKSO 共记录 **56,250** 个。3 个样本
的边界差来自 15 秒 `sleep` 与 250 Hz tick 的起止相位，不影响统计。

两侧 `/proc/cmdline` 除启动 Image 名外逐项一致；功能矩阵均显示
`abi_matrix_status=pass`。因此不存在把 Raw 普通内核与 VKSO update-bench
内核、或不同 CPU 隔离配置混在一起比较的问题。

## 6. 正式 update-side 结果

### 6.1 未扣除测量开销

| 指标 | Raw cycles | VKSO cycles | 差值 | Δ% | 判断 |
|---|---:|---:|---:|---:|---|
| Mean | 131.736 | 129.431 | **-2.305** | **-1.750%** | VKSO 更快 |
| Median | 126.000 | 122.000 | **-4.000** | **-3.175%** | VKSO 更快 |
| P95 | 168.600 | 169.000 | +0.400 | +0.237% | 持平 |
| P99 | 454.000 | 488.530 | +34.530 | +7.606% | VKSO 较高 |

Mean 与 Median 同时改善，说明收益不是由极少数低延迟样本制造。P95
只差 0.4 cycle，低于 TSC 测量和跨轮扰动的分辨能力，应报告为持平。

### 6.2 扣除 TSC pair 最小开销

| 指标 | Raw corrected | VKSO corrected | 差值 | Δ% |
|---|---:|---:|---:|---:|
| Mean | 98.736 | 96.431 | **-2.305** | **-2.334%** |
| Median | 93.000 | 89.000 | **-4.000** | **-4.301%** |
| P95 | 135.600 | 136.000 | +0.400 | +0.295% |
| P99 | 421.000 | 455.530 | +34.530 | +8.202% |

两边都减去 33 cycles，所以绝对差完全不变。corrected 百分比看起来更大只是
因为分母变小。33 cycles 是独立观察到的最小 TSC pair 成本，并非每个样本的
精确测量误差；corrected 结果只能作为敏感性说明，不能取代未扣除的实测值。
论文主表应优先报告未扣除的 cycles。

### 6.3 全部原始样本 pooled 检查

| 指标 | Raw | VKSO | VKSO 相对 Raw |
|---|---:|---:|---:|
| 样本数 | 56,247 | 56,250 | +3 |
| Mean | 133.422 | 130.040 | **-2.535%** |
| Median | 126 | 123 | **-2.381%** |
| P95 | 169 | 170 | +0.592% |
| P99 | 469 | 491 | +4.691% |
| `>500 cycles` | 0.850% | 0.919% | +0.069 percentage point |
| `>1000 cycles` | 0.069% | 0.053% | VKSO 更低 |
| `>5000 cycles` | 0.0249% | 0.0213% | VKSO 更低 |
| 最大观测值 | 20,201 | 9,295 | VKSO 更低 |

正式多轮结果和 pooled 结果都显示：

- Mean 改善约 2%；
- Median 改善约 2%–3%；
- P95 持平；
- P99 略高。

这说明结论不依赖某一种聚合方法。

## 7. 为什么必须增加 120 秒稳定期

第一次批次 `20260728T025421Z-update-side` 没有显式稳定等待。两轮结果对比：

| 指标 | 未稳定 VKSO Δ% | 120 s 稳定后 VKSO Δ% | 变化 |
|---|---:|---:|---|
| Mean | +5.620% | **-1.750%** | 异常退化消失 |
| Median | **-3.125%** | **-3.175%** | -4 cycles 完全复现 |
| P95 | +7.131% | +0.237% | 恢复持平 |
| P99 | +24.898% | +7.606% | 长尾显著收敛 |

未稳定 VKSO 的第 2 轮中，前约 11 秒出现成片高延迟，而同一轮最后几秒又恢复
到约 102–130 cycles。固定代码路径不可能在同一轮内自行增加数百 cycles 后
再消失，因此那部分主要来自启动后的系统扰动、频率/缓存状态或不可屏蔽的
NMI/SMI，而不是 VKSO 固定算法。

120 秒不是为了丢弃不利样本，而是根据第一轮持续约 105 秒的收敛过程，在
Raw 和 VKSO 两侧对称设置同样的实验前置条件。正式数据没有删除任何计时区间
内的 round 或 sample。

## 8. 性能差距的实现原因

### 8.1 两侧公共工作相同

Raw 5.15.198 的核心顺序是：

```text
tk_update_leap_state()
tk_update_ktime_data()
update_vsyscall()
update_pvclock_gtod()
base_real update
update_fast_timekeeper(mono)
update_fast_timekeeper(raw)
action/mirror handling
```

VKSO 的顺序是：

```text
tk_update_leap_state()
tk_update_ktime_data()
update_pvclock_gtod()
base_real update
vkso_time_publish()
update_fast_timekeeper(mono)
update_fast_timekeeper(raw)
action/mirror handling
```

leap、ktime、PVClock、fast timekeeper、mirror 等公共工作没有被删掉，但
publication 在完整函数中的相对位置发生了变化：Raw 先
`update_vsyscall()`、再 `update_pvclock_gtod()`；VKSO 先更新 PVClock/base，
再 `vkso_time_publish()`。正式样本又全部是 `action=0`，所以主要实现差异是：

```text
Raw:  update_vsyscall()
VKSO: vkso_time_publish()
```

不过本实验测量完整函数，结果同时包含 publication 位置变化可能造成的寄存器、
缓存和指令布局影响，不能把全部 2～4 cycles 都机械归到 store 数量。

VKSO 当前代码见：

- [`timekeeping.c`](../../linux-5.15.198-vkso/kernel/time/timekeeping.c)
- [`vkso_time.c`](../../linux-5.15.198-vkso/kernel/time/vkso_time.c)

Raw 对照为 Linux stable v5.15.198 的 `kernel/time/timekeeping.c` 和
`kernel/time/vsyscall.c`。

### 8.2 Raw `update_vsyscall()` 做什么

在 TSC 可用于 vDSO 的普通路径上，Raw：

1. 分别把 `CS_HRES_COARSE.seq` 和 `CS_RAW.seq` 置为奇数；
2. 发布两组 clock mode；
3. 发布 realtime、realtime coarse、monotonic coarse；
4. 发布 hres/raw 的 `cycle_last/mask/mult/shift`；
5. 发布 monotonic、boottime、monotonic raw、TAI base；
6. 发布 hrtimer resolution；
7. 分别把两个 seq 恢复为偶数。

按源代码标量 store 计数，TSC 普通路径约为：

```text
25 个 data field stores
4 个 seq stores
2 个 write barriers
```

x86-64 在该版本中没有额外的 `__arch_update_vsyscall()` 或
`__arch_sync_vdso_data()` 实际工作，它们内联为空。

### 8.3 VKSO `vkso_time_publish()` 做什么

VKSO：

1. 先在 private/local snapshot 中派生全部 shared 时间值；
2. 把唯一的 `shared->seq` 置为奇数；
3. 用标量 `WRITE_ONCE` 发布 shared_data；
4. 把同一个 seq 恢复为偶数。

TSC 普通路径约为：

```text
23 个 data field stores
2 个 seq stores
2 个 write barriers
```

与 Raw 相比，VKSO：

- 不在 shared_data 中发布两个 clocksource mask；
- 只维护一个共享 seq，而不是 HRES_COARSE/RAW 两个 seq；
- 先计算 monotonic shifted time，再复用于 coarse、hres 和 boottime；
- 避免 Raw monotonic coarse 路径中的独立 `__iter_div_u64_rem()`；
- 把派生计算放在 seq odd 窗口之前，使读者不可读区间只包含最终标量发布。

最后一点主要降低 reader retry 窗口，不直接删除 writer 的派生计算；但它让
shared 发布协议更清晰，也避免为了缩短 odd 窗口而复制第二套算法。

### 8.4 为什么收益只有 2–4 cycles

VKSO 确实减少了发布字段、seq store 和重复派生，但
`timekeeping_update()` 还包含大量两侧相同的公共工作。测量边界覆盖的是完整
函数，不是单独的 `update_vsyscall()`/`vkso_time_publish()`。

因此：

- 发布子路径的缩减会被公共工作稀释；
- x86 store buffer 可以并行吸收相邻标量 store；
- Raw 的部分 helper 被编译器内联；
- 33 cycles 的共同 TSC 测量成本不影响绝对差，但使总值更大。

在这个边界下稳定获得 2–4 cycles，而不是几十 cycles，符合实现规模。
不能因为设计上“共享同一份数据”就期待 update 成本归零：writer 仍必须在
timekeeper 更新后，以 seq 协议把 reader 所需的新状态发布到共享页。

这里的“符合”表示结果方向与静态结构缩减一致。要精确回答少一个 seq 或少两个
mask 各贡献多少 cycles，需要在同一内核二进制内对 publication 子路径做受控
A/B；当前完整函数实验没有提供这种分解。

### 8.5 为什么 P99 仍略高

P99 对约 1% 的边界样本非常敏感。本轮 VKSO `>500 cycles` 只比 Raw 多
0.069 percentage point，就足以把 P99 从 469 推到 491 cycles。

但更高阈值显示：

- VKSO `>1000 cycles` 比例更低；
- VKSO `>5000 cycles` 比例更低；
- VKSO 最大值 9,295，低于 Raw 的 20,201 cycles。

所以不能把 P99 的 +4.7% pooled 差异解释成 VKSO 出现更严重的极端慢路径。
更合理的判断是：两侧在 400–600 cycles 的不可屏蔽干扰/缓存长尾分布略有
差异，而 VKSO 的固定 fast path 仍然更短。要研究严格 worst-case latency，
需要独立记录 NMI/SMI、CPU residency 和多次独立启动，不能只用本实验 P99。

### 8.6 性能原因的证据强度

| 判断 | 证据 | 可信度 |
|---|---|---|
| VKSO Median/Mean 更低 | 正式15轮与pooled结果方向一致 | 高，限本机本次启动 |
| 第一轮大退化主要是未稳定扰动 | Median复现，120秒后Mean/P95显著恢复 | 较高 |
| VKSO publication 静态工作更少 | 一个seq、较少store、复用派生值 | 高，源码事实 |
| 2～4 cycles全部来自少store/seq | 完整函数未隔离子路径且顺序改变 | 中低，不能精确归因 |
| P99差异是确定的架构长尾 | 单次启动、极端阈值方向不一致 | 低，不应这样表述 |

因此最可靠的性能陈述是“完整 writer 的典型和平均值降低”，而不是为每一个
cycle 指定唯一微架构来源。

## 9. 对 VKSO 设计的意义

本实验给出三个重要判断。

第一，shared_data 并不等于“完全没有 update”。共享页避免 reader 再走额外
复制或 syscall，但 kernel writer 仍需在 timekeeper 变化后发布一致快照。

第二，VKSO 的裁剪是有效的。它没有同时维护原生 vDSO VVAR 和 VKSO shared
两套发布；当前 VKSO 镜像中 native vDSO 已移除，`timekeeping_update()` 只调
`vkso_time_publish()`。因此这里测到的不是“兼容代码叠加后的双重成本”。

第三，private/shared 拆分没有造成 writer 退化。先在 private/local 状态中
派生、再短时间将 shared seq 置为奇数完成发布的设计，既使典型 update
快 2%–3%，又缩短了 reader 看见 odd seq 的时间。后续并发实验已经证明：
HRES/RAW retry 分别下降
**93.18% / 95.24%**，其中 odd-seq 自旋减少约 **99%**；三个公开 reader
场景下 writer Median 也仍低于 Raw。

并发实验同时保留一个重要边界：它让 Raw 和 VKSO reader 各自以最大吞吐运行，
并非强制相同 calls/s。因此它证明的是端到端饱和条件下 VKSO 典型 writer 没有
退化，而不是相同请求率下的纯 cache-coherence 差值。

## 10. 三类实验的关系与实验边界

三类正式实验的边界和主结论：

| 实验 | 主测量边界 | 最可靠结论 |
|---|---|---|
| Standalone READ | 完整用户入口、syscall、PMU | 用户入口等权平均慢0.839%，典型绝对差约1 cycle |
| 空闲 UPDATE（本报告） | 完整 periodic `timekeeping_update()` | Mean快1.750%，Median快3.175%，P95持平 |
| READ/UPDATE 并发 | 饱和reader + 完整writer + seq分解 | odd窗口显著缩短；writer Median改善；部分reader仍有固定成本 |

这三类结果并不矛盾：publication 只在约 250 Hz update 时支付，而 wrapper 和
MM_data/context 是每次用户读取都支付。writer 每次节省几 cycles，不能自动
抵消高频 reader 每次多 1～2 cycles；两者必须分别报告。

本报告能够支持：

- 当前最终 VKSO 与 Linux 5.15.198 raw vDSO 的完整 periodic
  `timekeeping_update()` 对比；
- TSC、裸机、Normal mitigation 配置下的 Mean/Median/P95/P99；
- 120 秒稳定等待对结果有效性的影响；
- Raw/VKSO 发布结构与典型 cycles 差异方向一致的解释。

本报告不能单独支持：

- read 与 update 并发时的 reader latency 和 retry；该问题由并发报告回答；
- PVClock/Hyper-V 运行时 update 性能；
- 非 `action=0` 的 clock-set/NTP-clear/mirror 慢路径比较；
- 所有 CPU 微架构上都固定快 2%–3%；
- 把 15 个同一次启动内 round 当成 15 次独立启动；
- 严格实时系统的 worst-case latency 结论。

正式论文应同时报告绝对 cycles 和百分比。这里最可靠的结论不是抽象的
“快 3%”，而是：

```text
Mean    减少约 2.3 cycles
Median  减少 4 cycles
P95     相差 0.4 cycle
```

## 11. 复现实验

进入目录：

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/update-bench
```

Raw：

```bash
./boot-raw-update.sh
# 重启后
sudo ./collect-update-side.sh
```

VKSO：

```bash
./boot-vkso-update.sh
# 重启后
sudo ./collect-update-side.sh
```

`collect-update-side.sh` 默认设置：

```text
BENCH_SCOPE=update-side
STABILIZE_SECONDS=120
```

第一轮 Raw 自动创建 run_id，第二轮 VKSO 从
`.active-update-side-run-id` 读取同一 run_id 并生成：

```text
update-comparison.csv
UPDATE_SUMMARY.md
raw/update-summary.csv
vkso/update-summary.csv
raw/writer-rounds.csv
vkso/writer-rounds.csv
```

本报告正式原始数据：

```text
results/20260728T031855Z-update-side/
```

## 12. 最终结论

带 120 秒对称稳定期的正式实验表明：

1. **VKSO 完整 update-side 没有退化**；
2. **典型更新更快**：Median 从 126 降到 122 cycles，改善 3.175%；
3. **平均更新更快**：Mean 从 131.736 降到 129.431 cycles，
   改善 1.750%；
4. **P95 持平**：只差 0.4 cycle；
5. **P99 略高但极端峰值没有恶化**：高阈值样本比例和最大值反而更低；
6. **第一次实验的明显退化来自未稳定长尾**：Median 优势复现，
   Mean/P95/P99 在稳定后显著恢复；
7. **性能方向与结构缩减一致**：一个 seq、少两个 mask、少两次 seq store、
   更少重复派生；
8. **收益不会无限放大**：完整函数的公共 timekeeping 工作占主导，
   所以最终体现为稳定的 2–4 cycles。
9. **并发结果与典型值方向一致**：三个公开 reader 饱和场景下，
   writer Median 仍改善 5～12 cycles，odd-seq 自旋减少约 99%。

因此，当前 update-side 可以描述为：

**VKSO 用更紧凑的 shared_data 发布协议替代原生 vDSO VVAR 发布，在保持完整
timekeeping 更新语义和功能矩阵通过的同时，将 periodic
`timekeeping_update()` 的典型和平均开销降低约 2%–3%；该设计没有产生
双重发布成本，并在后续并发饱和实验中保持了更低的典型 writer 延迟。具体
2～4 cycles 与单个 store/seq 的贡献尚未由子路径 A/B 实验逐项拆分。**
