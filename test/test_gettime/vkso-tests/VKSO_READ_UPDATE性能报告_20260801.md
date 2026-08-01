# VKSO READ / UPDATE / CONCURRENT 统一性能报告

## 1. 报告状态与范围

本文是当前 VKSO 实现的最终、独立、自包含性能报告。它只使用三个已完成
且通过归档校验的最终结果，不复用旧测量窗口或旧批次的数字：

| 实验 | 最终结果 | 主要回答的问题 | 归档 SHA-256 |
|---|---|---|---|
| READ | [`20260801T164548Z-vkso-final`](baremetal/results/20260801T164548Z-vkso-final) | 公开用户时间接口的独立读性能 | `0435f5ad24a5714762fe05f0da5d9f40743a369eea531c35ace6b7b04c7fffe8` |
| UPDATE | [`20260731T182559Z-update-side-final`](update-bench/results/20260731T182559Z-update-side-final) | 无持续 reader 时完整 `timekeeping_update()` 的成本 | `f90e1afdab60c99571b4029368b86266763fef2f35f8fe874f6900775662fc9f` |
| CONCURRENT | [`20260801T173610Z-update-concurrent-final`](update-bench/results/20260801T173610Z-update-concurrent-final) | 持续公开 reader 与正常周期 writer 共存时双方的性能 | `c61443685106602a160f073e99417a3e32143fcb8559efd649f31d7d502fab7e` |

此前基于 `invoke()` 或没有在 duration-control syscall 后重新恢复同路径状态的
并发数据已经废弃，不进入本文。本文也不依赖旧 O7/O4 报告才能理解；跨版本
优化历史不属于这三个最终实验的统计范围。

## 2. 最终结论

当前实现从 READ、UPDATE 和 CONCURRENT 三方面看都可以保留，但正确结论
不是“VKSO 所有指标都更快”：

1. 独立 READ 的 20 个公开入口等权几何平均，Normal 比 Raw 慢
   `0.941%`，No-retpoline 比 Raw 快 `0.275%`，整体处于接近 Raw 的范围。
2. 三个 fallback 的总体性能已经修复：Normal 与 Raw 基本相同
   （`-0.051%`），No-retpoline 快 `0.886%`；扣除同镜像显式 syscall 后，
   VKSO fallback veneer 比 Raw 少 `3.1–8.0 cycles`。
3. 当前 READ 的主要弱项是极短 `gettimeofday` 入口：分组几何平均
   Normal 慢 `12.168%`、No-retpoline 慢 `9.330%`。其中最显眼的
   `gettimeofday(NULL,NULL)` 实际绝对差只有约 `2 cycles`，但 Raw 基线
   只有约 `6 cycles`，所以百分比被放大到约 `33%`。
4. 独立 UPDATE 以每轮平均校正成本为主指标，Normal 的完整
   `timekeeping_update()` 平均快 `13.176%`，No-retpoline 快 `4.111%`；
   两个变体的 P99 都降低约 `32.5%`。
5. UPDATE 的典型 Median 并没有变快：Normal 高 `5 cycles`，
   No-retpoline 高 `4 cycles`。Mean/P99 变好而 Median 变差说明分布形状
   和长尾发生变化，不能只选一个分位数概括全部 writer 性能。
6. 修正后的并发公开 READ 与独立 READ 基本对齐。高精度路径中，VKSO
   绝对多 `0.232–2.019 cycles/call`；coarse 多 `0.901–1.374 cycles/call`。
   coarse 的百分比为 `8.98%–13.69%`，主要因为 Raw 基线只有约
   `10 cycles`。
7. 并发时 writer 的每轮 Mean corrected 点估计在所有场景都更低：Normal
   低 `3.16%–10.73%`，No-retpoline 低 `1.95%–12.20%`。更稳定的收益
   集中在 monotonic_raw/coarse 和长尾；monotonic 的均值差较弱。
8. seq 微基准中，VKSO 每个“成功的受 seq 保护快照”固定多约
   `2.006–2.007 cycles`，但 retry 更少。这是底层协议诊断结果，
   不等于每个公开 `clock_gettime()` 都固定慢 2 cycles。

综合判断：当前结构没有出现功能问题、fallback 回归或 writer 负担膨胀，
READ 的净开销也保持在少量 cycles 范围。因此当前优化值得保留。正式结论
必须同时保留 reader 的固定小开销、writer 的平均/长尾收益，以及极短
`gettimeofday` 路径的剩余弱项。

## 3. 实验身份与完整性

### 3.1 共同实现身份

| 项目 | 值 |
|---|---|
| Git commit | `adfe3138e1388c34cb58051d33b2047682ac1a28` |
| Candidate `source.patch` SHA-256 | `d1c1ac2253702a2adfdb1dec96a88fb2585ce7af1055ef9e6e1bff34992678fa` |
| VKSO source tree SHA-256 | `a3a9894b6bf89bbec7a9b86b90aaaa867693e2037a8af797262a4f03ed92946c` |
| Kernel | Linux `5.15.198` |
| Compiler | GCC `11.4.0` |
| Benchmark flags | `-O2 -std=gnu11 -Wall -Wextra -Werror` |
| CPU | CPU 2，隔离、`nohz_full=2`、`rcu_nocbs=2`、SMT关闭 |
| Clocksource | TSC，`tsc=reliable` |
| 变体 | Normal；No-retpoline 诊断对照 |

READ 使用未打开 writer recorder 的镜像；UPDATE/CONCURRENT 镜像打开
`CONFIG_TIMEKEEPING_UPDATE_BENCH=y`。因此三类镜像和测试二进制不要求
字节相同，但 VKSO 功能源码哈希完全相同。READ 的 reader 测量协议是 v3，
CONCURRENT 的外层 load 测量协议是带同路径条件化的 v4；这属于测量工具
协议差异，不是被测 VKSO 实现差异。

### 3.2 代码量与统计范围

本节沿用 M11 正式代码规模审计口径，不以 Git 净增行作为 Raw/VKSO
代码量结论。人工清单先选取两侧等价的 x86-64 `clock_gettime/getres`、
`gettimeofday`、`time`、`getcpu`、七种 global clock、fallback、time namespace
和 TSC/PVClock/Hyper-V 范围；`count_manifest.py` 再去掉空行和纯注释，计算
lexical SLOC。共有的 timekeeper producer、CPU/alarm/dynamic backend 在两侧同时排除，
防止整文件统计造成重复归因。

Raw 侧仍使用 M11 冻结的 Linux 5.15.198 清单与计数；VKSO 侧以 M11
`adfe313` 为完整基表，对 `6656f97` 实际影响的语义行区间按相同规则
重新计数。因此主结论表示“当前完整 VKSO 与完整 Raw”，不是只表示
最后一次提交的 churn。

| 互斥口径 | Raw SLOC | 当前 VKSO SLOC | VKSO - Raw |
|---|---:|---:|---:|
| 运行时功能 | 857 | 885 | +28（+3.27%） |
| 运行时机制 | 490 | 363 | -127（-25.92%） |
| **运行时小计** | **1,347** | **1,248** | **-99（-7.35%）** |
| 功能专属构建/链接 | 158 | 57 | -101（-63.92%） |
| **产品功能合计** | **1,505** | **1,305** | **-200（-13.29%）** |

#### 3.2.1 运行时功能分层

| 类别 | Raw | 当前 VKSO | 差异 |
|---|---:|---:|---:|
| U1 用户 public ABI/算法或 wrapper | 359 | 68 | -291 |
| S1 kernel/user 共享 global 算法 | 0 | 310 | +310 |
| K1 普通 kernel global reader | 194 | 223 | +29 |
| K2 canonical producer | 56 | 47 | -9 |
| K4 syscall/cold backend | 132 | 149 | +17 |
| E1 cycles/environment provider | 116 | 88 | -28 |
| **合计** | **857** | **885** | **+28** |

#### 3.2.2 运行时机制分层

| 类别 | Raw | 当前 VKSO | 差异 |
|---|---:|---:|---:|
| C1 MM/context/namespace 映射 | 371 | 207 | -164 |
| C2 用户 context 启动 | 0 | 74 | +74 |
| K3 shared ABI/publisher | 119 | 82 | -37 |
| **合计** | **490** | **363** | **-127** |

“VKSO 代码比 Raw 多”只对运行时功能子层成立（多 28 SLOC）。把运行时
机制也纳入后，VKSO 少 99 SLOC；再加上功能专属构建/链接，完整产品代码
少 200 SLOC。VKSO 把 Raw 用户算法收敛为共享 core，但必须显式保留两个
环境边界和用户 context 启动；节省主要来自不再维护 Raw 的完整 VVAR/vDSO
映射与链接机制。

#### 3.2.3 最后 fallback 重构的语义增量

| 层 | M11 | 当前 | 变化 |
|---|---:|---:|---:|
| U1 | 71 | 68 | -3 |
| S1 | 291 | 310 | +19 |
| K1 | 212 | 223 | +11 |
| K4 | 158 | 149 | -9 |
| K3 | 78 | 82 | +4 |
| 其他运行时与 G1 | 473 | 473 | 0 |
| **产品合计** | **1,283** | **1,305** | **+22** |

这 22 SLOC 换来统一 clock 分类契约：用户入口和内核 syscall/ordinary-reader
边界各自分类，shared core 只处理 hres/coarse，native clock 不再穿过 shared core
再 fallback。

#### 3.2.4 reader 机器码闭包

机器码仍沿用 M11 的边界：Raw 为 public vDSO、其独有 cycle helper 和普通
kernel reader；VKSO 为用户 wrapper/cold failure、shared core、普通 kernel reader
以及 provider failure 必须的 private reader。kernel `gettimeofday` failure 只属于 syscall
路径，和 Raw K4 一样不进 reader closure。

Raw symbol size 冻结自 M11 normal 干净构建。当前 VKSO kernel symbol 使用与
`reader-load-v4-normal/vkso.config` 字节一致的配置重建 `vmlinux`，用户 symbol
直接取自正式 READ 包的 `libkernel.so`。所有数字都是 ELF `st_size` 或已验证
的非重叠本地 symbol body，不是页对齐后的 DSO/镜像文件大小。

| reader closure | Raw | 当前 VKSO |
|---|---:|---:|
| 用户 public/wrapper/cold | 1,515 B | 139 B |
| 用户私有依赖 / shared core | 142 B | 1,188 B |
| 普通 kernel reader | 982 B | 407 B |
| kernel clock private reader/failure | 0 B | 321 B |
| **合计** | **2,639 B** | **2,055 B** |
| **VKSO - Raw** | — | **-584 B（-22.13%）** |

当前 VKSO 比 M11 fallback 重构前的 2,076 B 还少 21 B（-1.01%）。用户边界
分类使 wrapper/cold 增大 34 B，拆分 hres/coarse 后 shared core 增大 4 B；但
普通 kernel reader 缩小 14 B，kernel clock failure/private 合计缩小 45 B，总闭包
净减 21 B。一次性 C2 启动的 196 B text 和 40 B private data 仍不进
reader closure。逐 symbol 证据见 `FINAL_BINARY_SYMBOLS.tsv`。

#### 3.2.5 独立统计项

下列代码不混入 1,305 SLOC 产品主表：

- ITS/reusable-text 为通用项目机制 P1，84 SLOC；
- 编译期和运行时验证 T1 现为 366 SLOC，其中本轮新增 6 SLOC clock ID
  一致性断言；
- 实验工具提交 `120cd91` 物理净增 1,285 行，用于固定测量窗口、
  boot/collect、包校验和结果归档，不进入内核或 `libkernel.so` 运行时路径；
- 文档、生成镜像、模块、DSO 和结果 CSV。

可复现证据为 `M11_SOURCE_MANIFEST.tsv`、`M11_SOURCE_COUNTS.csv` 以及当前受影响
行的 `FINAL_SOURCE_DELTA.tsv`。该组合同时保留冻结 Raw 基表、完整 M11 VKSO 基表
和最后重构的每行区间重算结果。

#### 3.2.6 本轮 Git 物理 churn（次级口径）

代码量以接纳本轮 fallback 边界重构前的 `adfe313` 为基线，以运行时实现
提交 `6656f97` 为终点，使用 `git diff --numstat --no-renames` 统计物理行。
该口径包含代码、声明、注释和空行，因此表示源码维护量，不等同于纯 SLOC、
目标文件字节数或执行指令数。

主统计范围只包含本轮实际改变的 8 个运行时/ABI 文件：

| 范围 | 文件数 | 新增 | 删除 | 净变化 |
|---|---:|---:|---:|---:|
| 内核共享头文件与边界契约 | 2 | 84 | 26 | **+58** |
| 内核执行实现 | 4 | 97 | 117 | **-20** |
| 用户 ABI 与入口汇编 | 2 | 51 | 51 | **0** |
| **运行时/ABI 合计** | **8** | **232** | **194** | **+38** |

具体文件范围如下：

- 内核共享头文件：`include/linux/vkso_time.h`、`include/vkso/time.h`；
- 内核执行实现：`kernel/time/posix-timers.c`、`time.c`、`vkso_time.c`、
  `vkso_time_core.c`；
- 用户 ABI/入口：`functional/vkso_abi.h`、`vkso_user_entry.S`。

净增 38 行主要来自统一 clock ID 常量、分类接口、静态约束和接口契约；实际
内核执行实现净减 20 行，用户入口汇编净增 0 行。因此不能把“净增 38 行”
解释成热路径增加了 38 行机器码，也没有为每一种新物理页继续追加一套运行时
补丁。clock 分类统一在环境边界完成，hres/coarse 共享核心只保留各自的数据
读取职责，结构比重构前更集中。

实验工具单独统计：提交 `120cd91` 修改 22 个 benchmark、收集、四镜像驱动、
包校验和分析文件，新增 1,542 行、删除 257 行，净增 1,285 行。这部分用于
固定测量窗口、自动 boot/collect、结果归档和可复现性校验，不进入内核或
`libkernel.so` 运行时路径，不能与上述 38 行相加后评价 VKSO 实现复杂度。

以下内容明确排除在本轮运行时代码量之外：

- `adfe313` 之前已经存在的 O4 ITS/reusable-text 修复及其构建期校验；它们在
  基线和终点中同时存在，不属于本轮增量；
- 未修改的 Linux 5.15.198 源码、生成的内核镜像、模块、DSO 和结果 CSV；
- README、本文性能报告以及其他说明文档；
- benchmark、QEMU、GRUB、收集器和结果分析代码。

因此 `+232/-194`、净增 38 行只表示最后一轮编辑量。代码规模和是否值得
保留以前述完整语义 SLOC 为主口径：当前 VKSO 产品代码为 1,305 SLOC，
比 Raw 少 200 SLOC；本轮本身语义净增 22 SLOC。实验工具仍只作复现性成本
单列，不算作生产运行时负担。

### 3.3 数据完整性

| 检查项 | READ | UPDATE | CONCURRENT |
|---|---:|---:|---:|
| complete case | 4/4 | 4/4 | 4/4 |
| 功能矩阵 | 4/4 pass | 4/4 pass | 4/4 pass |
| 正式重复 | 每case 31轮 | 每case 15轮 | 每场景 15轮 |
| 原始 writer CSV | — | 60 | 240 |
| 原始 reader CSV | `perf.csv` 每case 1240行 | — | 240 |
| writer 正式样本 | — | 224,989 | 698,848 |
| writer dropped | — | 全部0 | 全部0 |
| writer action | — | 全部 `action=0` | 全部 `action=0` |
| reader migration/reversal | 无迁移重试失败 | — | 全部0/0 |
| 归档校验 | pass | pass | pass |

三个实验的 12 份 `functional.matrix` SHA-256 都是：

```text
55cb60189197b7995c98325d7c519c7470f9e6051f20f679e32189c8d59c67f7
```

UPDATE 收集结束时曾发生压缩文件权限错误，但错误发生在原始 CSV 全部写完
之后。修复所有权后生成的归档已通过 SHA-256 校验；计时数据、样本数量和
分析结果未受影响。

## 4. 测量与统计口径

统一差异定义：

```text
delta% = (VKSO / Raw - 1) × 100%
```

负值表示 VKSO 更快，正值表示 VKSO 更慢。

### 4.1 独立 READ

READ 使用 `direct-user-api-steady-batch-v3`：

- 直接在每个具体 API 的循环中调用 Raw vDSO 或 VKSO wrapper，不包含旧的
  通用 `invoke()` 分发层；
- 每条路径每个样本先做 `10,000` 次同路径预热，再计时 `500,000` 次；
- 每个 API/路径重复 31 次，分布在 7 个新进程中；
- `setarch -R` 固定用户地址布局；
- TSC 与 PMU 同时采集，正式单 API 值取 31 轮中位数；
- 分组结果是各 API `VKSO/Raw` 比值的等权几何平均，不按调用频率加权。

### 4.2 独立 UPDATE

UPDATE 在没有持续 reader load 的情况下，仅记录正常周期
`timekeeping_update()`：

- 每case 15轮，每轮15秒，测得更新率约250次/秒；
- 插桩覆盖完整 `timekeeping_update()`；
- Raw/VKSO 的 TSC pair 最小开销均为 `33 cycles`；
- `corrected_cycles = measured_cycles - 33`；
- 主指标先计算每轮所有 update 的 Mean corrected，再对15轮 Mean 取中位数；
- Median/P95/P99 也先按轮计算，再对15轮同名指标取中位数。

Mean corrected 代表长期 writer CPU 工作量，是主指标；Median 表示典型分位，
P95/P99 描述长尾。三者回答的问题不同。

### 4.3 CONCURRENT

并发公开 reader 使用 `direct-user-api-conditioned-load-v4`：

- 测量循环与独立 READ 使用相同的具体公开 API 调用体；
- 每批计时 `500,000` 次；
- duration-control syscall 在计时区间外；
- 每次 duration-control syscall 后，先做 `10,000` 次同路径条件化调用，
  再开始下一批计时；
- 每轮持续15秒，每场景15轮；
- `tsc_cycles_per_call` 只包含50万次正式调用；
- `total_calls_per_second` 包含正式调用和占每批2%的条件化调用，因此本文
  以 cycles/call 为 reader 主指标，吞吐率作为交叉检查。

该实验没有人为提高 update 频率。writer 仍是系统正常的约250 Hz周期更新，
recorder 只记录它；因此它回答的是“饱和 reader 与正常 writer 共存时双方
表现如何”，不是高频注入式 writer 压力测试。独立 READ 本身也会遇到正常
周期更新，所以不能把两种实验的差直接全部解释成“并发额外成本”。

### 4.4 seq 诊断

seq 微基准只测“读取seq → 读取必要字段和TSC → 再次校验seq”的最小快照
协议，并分别统计成功快照的平均 cycles、odd-seq 和 changed-seq retry。
它用于判断发布窗口、竞争重试和协议进展，不是公开 API 总成本。

## 5. 独立 READ 结果

### 5.1 分组结果

| 分组 | Normal差异 | VKSO胜/总 | No-ret差异 | VKSO胜/总 |
|---|---:|---:|---:|---:|
| 全部20项 | **+0.941%** | 9/20 | **-0.275%** | 7/20 |
| 17项非fallback | +1.117% | 7/17 | -0.167% | 4/17 |
| 3项fallback | -0.051% | 2/3 | **-0.886%** | 3/3 |
| 7项主要 `clock_gettime` | +3.726% | 3/7 | +1.027% | 0/7 |
| 4项 `gettimeofday` | **+12.168%** | 0/4 | **+9.330%** | 1/4 |
| 2项直接 `clock_getres` | -6.041% | 1/2 | -6.693% | 1/2 |
| 2项 `time` | **-18.204%** | 2/2 | **-18.339%** | 2/2 |
| 2项 `getcpu` | 0.000% | 1/2 | +4.446% | 0/2 |

“胜/总”只表示中位 cycles 更低的 API 数。整体几何平均接近 Raw，并不表示
每个 API 都持平；极短入口中 1–2 cycles 会变成很大的百分比。

### 5.2 20个公开入口全量结果

单位为 `TSC cycles/call`。

| API | Raw Normal | VKSO Normal | 差异 | Raw No-ret | VKSO No-ret | 差异 |
|---|---:|---:|---:|---:|---:|---:|
| `clock_getres` process CPU fallback | 585.050 | 586.107 | +0.181% | 565.679 | 558.318 | -1.301% |
| `clock_getres` realtime | 8.028 | 6.042 | -24.738% | 8.028 | 6.042 | -24.740% |
| `clock_getres` realtime coarse | 6.022 | 7.064 | +17.302% | 6.106 | 7.063 | +15.681% |
| `clock_gettime` boottime | 53.196 | 53.186 | -0.018% | 53.196 | 53.217 | +0.040% |
| `clock_gettime` monotonic | 53.194 | 53.186 | -0.014% | 53.193 | 54.190 | +1.874% |
| `clock_gettime` monotonic coarse | 10.035 | 11.085 | +10.467% | 10.035 | 10.037 | +0.014% |
| `clock_gettime` monotonic raw | 52.184 | 54.347 | +4.145% | 52.184 | 53.185 | +1.919% |
| `clock_gettime` process CPU fallback | 869.545 | 868.978 | -0.065% | 842.828 | 839.464 | -0.399% |
| `clock_gettime` realtime | 53.193 | 52.184 | -1.897% | 53.192 | 53.987 | +1.495% |
| `clock_gettime` realtime alarm fallback | 679.501 | 677.683 | -0.268% | 665.733 | 659.364 | -0.957% |
| `clock_gettime` realtime coarse | 10.037 | 11.077 | +10.357% | 10.035 | 10.036 | +0.009% |
| `clock_gettime` TAI | 53.194 | 55.192 | +3.755% | 53.196 | 54.190 | +1.868% |
| `getcpu(cpu,node)` | 12.042 | 12.042 | -0.000% | 11.038 | 12.042 | +9.090% |
| `getcpu(NULL,NULL)` | 12.042 | 12.042 | +0.000% | 12.042 | 12.042 | +0.000% |
| `gettimeofday(tv,tz)` | 57.222 | 58.203 | +1.714% | 57.221 | 58.203 | +1.715% |
| `gettimeofday(NULL,NULL)` | 6.021 | 8.028 | +33.327% | 6.021 | 8.028 | +33.324% |
| `gettimeofday(NULL,tz)` | 9.031 | 10.035 | +11.114% | 9.032 | 9.032 | -0.000% |
| `gettimeofday(tv,NULL)` | 55.204 | 57.993 | +5.052% | 55.203 | 58.159 | +5.355% |
| `time(NULL)` | 6.021 | 5.018 | -16.665% | 6.021 | 5.018 | -16.665% |
| `time(&value)` | 5.018 | 4.028 | -19.716% | 5.018 | 4.015 | -19.980% |

### 5.3 Fallback veneer

为了分离 syscall 内核执行时间，按每轮计算：

```text
fallback veneer = 公开入口 cycles - 同镜像显式 syscall cycles
```

下表为31轮 veneer 差值的中位数，单位为 cycles：

| Fallback | Raw Normal | VKSO Normal | VKSO-Raw | Raw No-ret | VKSO No-ret | VKSO-Raw |
|---|---:|---:|---:|---:|---:|---:|
| `clock_getres` process CPU | 8.275 | 0.288 | **-7.987** | 5.917 | -0.314 | **-6.231** |
| `clock_gettime` process CPU | 12.360 | 6.426 | **-5.934** | 9.692 | 6.601 | **-3.092** |
| `clock_gettime` realtime alarm | 9.826 | 4.964 | **-4.862** | 10.547 | 5.490 | **-5.056** |

负 veneer 值可能由独立测量噪声和两个调用点的前端状态差异造成，不能解释成
“零成本 syscall”。重要结论是 VKSO 不再在 fallback 前执行完整共享数据
准备；六组入口总成本中只有 Normal `clock_getres` 慢 `0.181%`，其余均与
Raw 持平或更快，三项的分组结果也为持平或更快。

### 5.4 PMU与独立seq诊断

对17个非fallback API，先求每个API的31轮PMU中位数，再求逐API
`VKSO-Raw` 差值的中位数：

| 变体 | instructions/call | branches/call | branch misses | cache misses | L1D load misses |
|---|---:|---:|---:|---:|---:|
| Normal | +5.000 | +1.000 | 约0 | 约0 | 约0 |
| No-retpoline | +5.000 | +1.000 | 约0 | 约0 | 约0 |

这说明剩余 reader 差异主要是稳定的指令/分支和依赖链成本，不是 cache miss
或 branch-miss 异常。

独立seq诊断每case执行1亿次：

| 变体 | 协议 | Raw cycles/read | VKSO cycles/read | cycles差 | Raw retries/百万 | VKSO retries/百万 |
|---|---|---:|---:|---:|---:|---:|
| Normal | hres | 43.151 | 45.158 | +2.007 | 123.41 | 23.28 |
| Normal | raw | 43.151 | 45.157 | +2.006 | 95.81 | 35.33 |
| No-retpoline | hres | 43.151 | 45.158 | +2.007 | 154.80 | 29.74 |
| No-retpoline | raw | 43.151 | 45.157 | +2.006 | 76.68 | 28.81 |

VKSO 成功快照固定多约2 cycles，但 odd-seq 暴露更短，retry 明显更少。
该表只解释底层协议，不代替前面的公开入口表。

## 6. 独立 UPDATE 结果

### 6.1 完整 writer 分布

单位为 corrected cycles/update；每项都是“轮内统计值，再取15轮中位数”。

| 变体 | 指标 | Raw | VKSO | 绝对差 | 差异 |
|---|---|---:|---:|---:|---:|
| Normal | **Mean** | 101.701 | 88.301 | **-13.400** | **-13.176%** |
| Normal | Median | 84.000 | 89.000 | +5.000 | +5.952% |
| Normal | P95 | 156.000 | 131.000 | **-25.000** | **-16.026%** |
| Normal | P99 | 465.060 | 314.040 | **-151.020** | **-32.473%** |
| No-retpoline | **Mean** | 102.468 | 98.256 | **-4.212** | **-4.111%** |
| No-retpoline | Median | 97.000 | 101.000 | +4.000 | +4.124% |
| No-retpoline | P95 | 143.000 | 145.000 | +2.000 | +1.399% |
| No-retpoline | P99 | 514.020 | 346.550 | **-167.470** | **-32.580%** |

更新率保持不变：Normal Raw/VKSO 为 `250.000/249.933 updates/s`，
No-retpoline 两边均为 `250.000 updates/s`。Normal 少一个边界样本只是
15秒窗口与250 Hz tick的相位差。

### 6.2 正确解读

- 对长期 CPU 工作量，Mean corrected 是主指标：Normal 和 No-retpoline
  分别改善 `13.176%` 和 `4.111%`。
- 对典型单次分位，Median 反而高4–5 cycles，必须如实保留。
- Normal 的 P95/P99 都更低；No-retpoline 的 P95 基本持平略差2 cycles，
  但 P99 低167.47 cycles。
- 因此不能写成“每次 update 都更快”。更准确的表述是：VKSO 降低了平均
  writer 成本和主要长尾，但改变了双峰分布的占比，使中位分位稍高。

原始 UPDATE 归档中自动生成的旧 schema-1 `UPDATE_SUMMARY.md` 只展示当时的
Median 快照。本文以上述完整 `update-comparison.csv` 和
`writer-rounds.csv` 为依据，作为最终统一口径；当前分析器可以重新生成
包含 Mean corrected 主指标的摘要。

## 7. CONCURRENT 结果

### 7.1 公开 reader

| 变体 | Reader | Raw cycles/call | VKSO cycles/call | 绝对差 | 差异 | Raw total M calls/s | VKSO total M calls/s |
|---|---|---:|---:|---:|---:|---:|---:|
| Normal | monotonic | 52.965 | 53.197 | +0.232 | +0.437% | 52.924 | 52.692 |
| Normal | monotonic_raw | 52.187 | 54.206 | +2.019 | +3.870% | 53.712 | 51.707 |
| Normal | monotonic_coarse | 10.036 | 11.410 | +1.374 | +13.693% | 279.269 | 245.646 |
| No-retpoline | monotonic | 53.197 | 54.463 | +1.266 | +2.380% | 52.696 | 51.469 |
| No-retpoline | monotonic_raw | 52.186 | 53.646 | +1.460 | +2.798% | 53.717 | 52.252 |
| No-retpoline | monotonic_coarse | 10.036 | 10.937 | +0.901 | +8.982% | 279.294 | 256.255 |

Normal monotonic 的差只有0.232 cycles，其 Raw/VKSO 轮间IQR分别为
`[52.712,53.498]` 和 `[53.196,53.199]`，明显重叠，属于接近噪声尺度。
monotonic_raw 和 coarse 在两个变体中的 Raw/VKSO IQR 都不重叠，属于
稳定的固定开销；No-retpoline monotonic 的两侧IQR也有重叠。

### 7.2 与独立 READ 的关系

下表比较同一公开调用体中 `VKSO/Raw-1` 的结果，而不是直接把两类实验的
绝对 cycles 相减：

| 变体 | Reader | 独立READ差异 | CONCURRENT差异 |
|---|---|---:|---:|
| Normal | monotonic | -0.014% | +0.437% |
| Normal | monotonic_raw | +4.145% | +3.870% |
| Normal | monotonic_coarse | +10.467% | +13.693% |
| No-retpoline | monotonic | +1.874% | +2.380% |
| No-retpoline | monotonic_raw | +1.919% | +2.798% |
| No-retpoline | monotonic_coarse | +0.014% | +8.982% |

高精度路径的方向和幅度总体一致，证明旧并发实验出现的大幅下降是测量窗口
问题，修正后的 v4 没有改变公开执行路径。No-retpoline coarse 的绝对值从
独立 READ 的 `10.037` 上升到并发的 `10.937 cycles`；独立 READ 的31轮
本身已经出现约10/11 cycles的多个稳定档位，而并发并未提高 writer 频率，
所以这一轮不能单独证明是锁竞争导致。对饱和 coarse 工作负载仍应如实使用
本次并发观测到的 `10.937 cycles/call`。

### 7.3 并发时完整 writer Mean

主指标仍是每轮 `mean_corrected_cycles`，再取15轮中位数：

| 变体 | Reader场景 | Raw | VKSO | 绝对差 | 差异 |
|---|---|---:|---:|---:|---:|
| Normal | monotonic | 106.013 | 102.662 | -3.350 | -3.160% |
| Normal | monotonic_raw | 114.066 | 102.002 | **-12.064** | **-10.576%** |
| Normal | monotonic_coarse | 113.840 | 101.621 | **-12.218** | **-10.733%** |
| Normal | seq_protocol | 114.138 | 105.849 | -8.289 | -7.262% |
| No-retpoline | monotonic | 100.307 | 98.353 | -1.954 | -1.948% |
| No-retpoline | monotonic_raw | 108.999 | 102.132 | -6.867 | -6.300% |
| No-retpoline | monotonic_coarse | 114.069 | 100.147 | **-13.922** | **-12.205%** |
| No-retpoline | seq_protocol | 116.177 | 103.499 | **-12.678** | **-10.913%** |

轮间分布进一步限定结论：Normal monotonic 的 Raw/VKSO Mean corrected
IQR分别为 `[101.482,108.129]` 和 `[98.407,106.976]`，No-retpoline
分别为 `[97.586,105.525]` 和 `[96.364,101.538]`，都有重叠；两个变体的
monotonic_raw/coarse IQR 均不重叠。因此 monotonic 的
`-3.16%/-1.95%` 点估计应写成“小幅改善或持平”，而 raw/coarse 的平均
成本降低更稳定。

### 7.4 Writer Median与长尾

下表全部是 `VKSO-Raw` corrected cycles：

| 变体 | Reader场景 | Median差 | P95差 | P99差 |
|---|---|---:|---:|---:|
| Normal | monotonic | +8.0 | -25.0 | -138.35 |
| Normal | monotonic_raw | 0.0 | -29.0 | -159.19 |
| Normal | monotonic_coarse | 0.0 | -29.0 | -200.00 |
| Normal | seq_protocol | 0.0 | -29.1 | -128.16 |
| No-retpoline | monotonic | +20.0 | -8.0 | -81.00 |
| No-retpoline | monotonic_raw | +15.0 | -30.0 | -12.00 |
| No-retpoline | monotonic_coarse | +15.0 | -30.95 | -128.50 |
| No-retpoline | seq_protocol | +14.0 | -26.1 | -133.36 |

与独立 UPDATE 一样，不能把 Mean 改善解释成每个 update 都更快：Normal
典型 Median 持平或慢8 cycles，No-retpoline 慢14–20 cycles；但 P95/P99
总体显著降低，最终使平均 CPU 成本下降。

### 7.5 seq竞争

| 变体 | 协议 | Raw cycles/read | VKSO cycles/read | 绝对差 | cycles差异 | Raw retries/百万 | VKSO retries/百万 |
|---|---|---:|---:|---:|---:|---:|---:|
| Normal | hres | 43.151 | 45.158 | +2.007 | +4.651% | 82.94 | 34.72 |
| Normal | raw | 43.151 | 45.157 | +2.006 | +4.648% | 109.94 | 18.98 |
| No-retpoline | hres | 43.151 | 45.158 | +2.007 | +4.652% | 98.46 | 80.98 |
| No-retpoline | raw | 43.151 | 45.157 | +2.006 | +4.649% | 106.68 | 65.26 |

固定约2 cycles来自这个人工拆分的快照循环本身。公开 READ 还包含入口分类、
数据定位、时间换算和返回，因此公开 API 的净差并不固定等于2 cycles。
最高 retry 也只有约110次/百万，即约0.011%；VKSO 的 changed-seq 次数与
Raw 接近，主要减少的是 odd-seq 自旋，说明 writer 对外暴露的奇数窗口更短。

## 8. 三类实验的统一解释

| 实验 | 主指标 | 应使用的结论 | 不能推出的结论 |
|---|---|---|---|
| READ | 公开 API 31轮中位 cycles | 独立 reader 总成本与具体弱项 | writer 成本或并发额外成本 |
| UPDATE | 轮内 Mean corrected、轮间中位数 | 无持续 reader 时长期 writer CPU 成本 | 每个 update 都更快 |
| CONCURRENT | 公开 reader cycles + writer Mean/分位 | 饱和 reader 与正常 writer 共存时双方表现 | 高频 writer 压力或 seq 微基准等于公开接口 |

三个实验互相补充：

- READ 证明 fallback 修复有效、总体接近 Raw，并定位 `gettimeofday` 和部分
  high-resolution/coarse 路径的固定小开销；
- UPDATE 证明紧凑共享状态没有把 reader 优化转化为 writer 平均工作量和
  长尾负担；
- CONCURRENT 证明修正测量边界后公开 reader 没有异常退化，同时显示
  raw/coarse 的少量固定 reader 成本和 writer 长尾收益可以共存；
- seq 只负责解释发布窗口与重试，不承担公开性能结论。

因此论文或汇报中的推荐主表是：

1. READ：20项全表和分组几何平均；
2. UPDATE：Mean corrected 为主，同时列 Median/P95/P99；
3. CONCURRENT：三个公开 reader 的 cycles/call，与相同场景 writer 的
   Mean corrected；
4. seq：放在机制分析或附录中，并明确“+2 cycles不是每个公开 READ”。

## 9. 限制与后续优化优先级

### 9.1 限制

- 每个 backend/变体的最终批次只有一次系统启动；31/15轮主要描述同一次
  启动内的稳定性，不能替代跨机器、跨CPU或多次冷启动置信区间。
- Normal 与 No-retpoline 是不同代码生成/防护布局，不应平均成一个数字；
  Normal 是默认防护配置，No-retpoline 用于诊断布局与thunk影响。
- 并发实验不注入额外 writer，不能代表高于正常250 Hz的更新时间压力。
- 等权几何平均不代表真实应用调用频率；具体工作负载应按实际 API 构成
  加权，或者直接引用对应 API 的 cycles。
- 1–2 cycles在约5–10 cycles的极短接口上会表现为10%–33%，报告时必须
  同时给绝对值和百分比。

### 9.2 后续优化

在不改变结论的前提下，若继续优化代码，优先级应为：

1. `gettimeofday(NULL,NULL)`、`gettimeofday(NULL,tz)` 和 `tv,NULL`
   的入口准备与参数分支，因为它们是独立 READ 中最明确的分组弱项；
2. normal monotonic_raw/coarse 的约1–2 cycles固定成本；
3. 保持当前 fallback 早分流，不重新引入全局 MM/context 准备；
4. 不应仅为了消除 seq 微基准的2 cycles重写发布协议，因为当前 retry、
   writer Mean 和长尾已经更好，且公开 API 的净成本并非统一2 cycles。

任何被接纳的新代码变化都必须重新执行完整 READ/UPDATE/CONCURRENT
四镜像矩阵；在代码和镜像未变化时，不需要继续重复当前最终批次。

## 10. 可复核数据入口

READ：

- [`experiment-manifest.txt`](baremetal/results/20260801T164548Z-vkso-final/experiment-manifest.txt)
- 各case的 `perf.csv`、`perf-process-map.csv`、`seq.csv`、
  `functional.matrix` 和环境快照位于同一结果目录。

UPDATE：

- [`experiment-manifest.txt`](update-bench/results/20260731T182559Z-update-side-final/experiment-manifest.txt)
- [`normal/update-comparison.csv`](update-bench/results/20260731T182559Z-update-side-final/normal/update-comparison.csv)
- [`no-retpoline/update-comparison.csv`](update-bench/results/20260731T182559Z-update-side-final/no-retpoline/update-comparison.csv)
- 每个backend的 `writer-rounds.csv` 和60个原始 writer CSV 保留在结果目录。

CONCURRENT：

- [`experiment-manifest.txt`](update-bench/results/20260801T173610Z-update-concurrent-final/experiment-manifest.txt)
- [`normal/CONCURRENT_SUMMARY.md`](update-bench/results/20260801T173610Z-update-concurrent-final/normal/CONCURRENT_SUMMARY.md)
- [`no-retpoline/CONCURRENT_SUMMARY.md`](update-bench/results/20260801T173610Z-update-concurrent-final/no-retpoline/CONCURRENT_SUMMARY.md)
- 每个backend的 `reader-rounds.csv`、`writer-rounds.csv` 和480个原始
  reader/writer CSV 保留在结果目录。

本文所有正式数字均可由以上 CSV 重新计算，不依赖旧报告中的缓存结果。
