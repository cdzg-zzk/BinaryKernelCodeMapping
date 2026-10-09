# Clocktime READ：结果、解释与正文材料

READ 证据整理已完成。两种配置共 16 次独立启动、38 项接口/配置对照全部保留，统计从原始批次重新计算，与已有主表的点估计一致。

**主要结果：七类用户 clock_gettime 快路径的中位成本差为 −1.006～+1.006 TSC ticks/call；三种普通内核 READ 为 −2.728～+1.087 ticks。其他五项公开时间快路径及 getcpu 在两种配置的四个启动块内均降低中位成本。**

- [结果表](tables.md)：Raw、VKSO、绝对差、95% 区间和百分比，覆盖全部 38 项对照。
- [逐启动结果](boot-results.md)：四个启动块、配对区间、删一块敏感性与完整均值差。
- [正文候选段落](evaluation-text.md)：直接陈述共享读取的收益和成本。
- [逐接口调用路径](call-paths.csv)及[实际构建指令](entry-disassembly.md)：解释用户入口、共享计算、内核适配与 fallback。
- 图：[主要 READ](read-main.pdf)、[其他快路径](read-other.pdf)、[fallback](read-fallback.pdf)。同名 SVG 可编辑，PNG 可预览。

## 实验对象与计时边界

正式数据为 `baremetal/results/20260929T040650Z-clocktime-full/block-01..04/read/`。每块包含 Raw/VKSO 与 Retpoline/no-retpoline 的四次独立启动。源码版本为 `cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb`；包名为 `clocktime-auto-53f692884c64-clean-{normal,no-retpoline}`。读取测量使用 clean 镜像，不包含 UPDATE 发布记录器。

环境是 Intel Core i7-1165G7、Linux 5.15.198、GCC 11.4.0、TSC clocksource。固定 CPU 2，performance governor、关闭 turbo，记录的隔离和启动参数见 `validation.json`。两后端在各配置下使用匹配的编译配置。`configurations.csv` 列出 RETPOLINE、RETHUNK、CPU_UNRET_ENTRY、CPU_SRSO、MITIGATION_ITS：这里比较两组编译配置，不能把组间变化分解为单个 retpoline 指令的成本。

每接口每启动有 31 个批次，每批先预热 10,000 次，再计时 500,000 次调用。用户态 31 批依次分给 7 个进程（5、5、5、4、4、4、4 批），并非 7 个并发读者。接口顺序按轮次和进程编号轮转。内核三接口也轮转测量顺序。合计 7,936 个用户批次和 1,488 个内核批次，即 4,712,000,000 次计时调用。

用户端通过正常动态链接调用完整公开 API，初始化、首次解析和首次触页在计时之前；每个批次以 `LFENCE/RDTSCP/LFENCE` 包围。内核端测量 `ktime_get_ts64`、`ktime_get_raw_ts64`、`ktime_get_coarse_ts64`，批次以 `rdtsc_ordered()` 包围，循环中包含结果校验累加。主表单位是批次总 TSC ticks 除以调用数；保留循环、正常入口和校验的成本，不减去空循环基线。用户和内核表分别与各自 Raw 比较。

全部启动的公开 API、选定快路径 syscall denial、ABI 检查通过；VKSO 的页身份检查通过。性能覆盖是 root namespace、TSC provider 的上述接口；其他 namespace 的功能证据见工作 1、2 的证据包。

## 统计口径

主统计量保持已有协议：先计算每个启动的 31 个批次平均耗时的中位数，再分别取 Raw/VKSO 四个启动中位数的中位数，最后求 VKSO−Raw。一次批次是 500,000 次调用的平均成本，表中的中位数不是单次调用延迟的 p50。

主表以启动为重采样单位，对每个后端的四次启动有放回抽样四次，枚举全部 256×256 种组合，取中位数差分布的 2.5% 和 97.5% 分位数。区间为逐接口的经验 bootstrap 区间。它刻画当前四次启动的变动，不是所有接口同时成立的 95% 界限，也不执行等价性检验。因此正文直接报告增量，不使用未经定义的“可忽略”判断。

四个 campaign block 内配对另有 256 种联合重采样结果。内层批次不跨内核配对。附表还列出删去任一完整启动块后的同一统计量，以及全部批次参与的等权启动均值差。这些敏感性结果与主结果并列，统计量没有按结果好坏切换。

## 结果如何解释

**用户 clock_gettime。** 高精度的两侧路径都执行周期读取、转换和序列验证；VKSO 在 carrier 中完成 clock ID 分类及地址空间依赖注入，然后跳入共享核心。不同 clock ID 选择不同基址和 namespace 分支，因此逐接口报告。Retpoline 中 BOOTTIME、TAI 的增量分别为 0.833、1.001 ticks；no-retpoline 中 MONOTONIC、MONOTONIC_RAW、BOOTTIME 分别降低 1.002、1.006、1.005 ticks，四块方向一致。

**coarse 用户读取。** 无需周期转换，Raw 基线约 15.099 ticks。Retpoline 中两个 coarse 接口分别增加 1.000、1.006 ticks，对应 6.624%、6.662%；no-retpoline 中差值为 −0.004、−0.001 ticks。短路径上的约一个 tick 应与百分比一起阅读。

**其他时间接口与 getcpu。** `clock_getres` 的共享入口直接读取已发布分辨率或返回 coarse 常量；`gettimeofday` 和 `time` 通过 IFUNC 在计时之前绑定入口，稳定调用进入 carrier/共享实现。两种配置下，五项时间快路径分别节省约 0.969～2.050 ticks；getcpu 节省约 1.004 ticks。全部十二项配置/工作负载对照的四个启动块中位差均为负，完整均值差也为负。源码及实际指令解释了执行路径，精确到一个 tick 的收益没有被强行归因于某一条指令。

**普通内核 READ。** 测量模块直接调用原导出接口；VKSO 的 root adapter 提供固定时钟、NULL MM_data 和内核 context，再进入共同核心。三接口两配置的最大中位增量为 1.087 ticks，同时有 1.516～2.728 ticks 的中位下降。Retpoline 的 raw 时间读取、no-retpoline 的 monotonic 读取在四块中均下降。coarse 内核接口的启动中位数存在约 9/10 或 9/11 ticks 的跨启动变化，图和附表保留这些点；用户/内核或两配置的差异不能统一解释成一个固定“跨域费用”。

**fallback。** PROCESS_CPUTIME 与 REALTIME_ALARM 在 carrier 分类后直接执行系统调用。这些对照度量完整 fallback，六项中位差均为负（−9.221～−1.738 ticks）。no-retpoline 的 process CPU time 一项启动变动更大，其差值区间为 [−43.209,+2.522] ticks；这在 fallback 图和结果表中独立呈现，不用于解释共享高精度计算的收益。

**均值与启动波动。** 主结论讨论上述中位成本；完整均值另表展示。七类 clock_gettime 的均值差为 −0.822～+1.175 ticks，三种内核接口为 −2.051～+0.665 ticks。个别接口的中位差和均值差符号不同，但全部其他公开时间快路径和 getcpu 的均值差仍为负。附表提供每项精确值与删除一个启动块后的范围。

## 文件与复算

| 文件 | 内容 |
| --- | --- |
| `summary.csv` | 38 项主统计和敏感性结果 |
| `boot-statistics.csv` | 304 个启动×接口单元，包括均值、批次 p95 和范围 |
| `block-deltas.csv` | 152 个匹配启动块差值 |
| `process-statistics.csv` | 用户进程层摘要，仍属于启动内观测 |
| `build-identities.csv` / `configurations.csv` | 16 个启动的实际产物关联和配置项 |
| `validation.json` | 原始矩阵、单位、环境、完整性及点估计复现结果 |
| `call-paths.csv` / `entry-disassembly.md` | 全部 19 个工作负载路径与实际产物指令 |
| `tables.md` / `table-*.tex` | 全结果与可插入 LaTeX 的分组表 |
| `read-*.svg/pdf/png` | 可编辑矢量图、论文用 PDF、预览图 |
| `verification.json` / `verification.log` | 最终复算、数值检查及图表检查记录 |

在仓库根目录执行：

```bash
python3 test/test_gettime/vkso-tests/direct-api/read_evaluation.py --check
python3 test/test_gettime/vkso-tests/direct-api/read_paths.py --check
python3 test/test_gettime/vkso-tests/direct-api/read_report.py --check
python3 test/test_gettime/vkso-tests/direct-api/verify_read_evidence.py
```

去掉前三条的 `--check` 可重建对应派生结果。依赖 Python 3、NumPy、CairoSVG、binutils，以及本地保留的正式 campaign 和两个 clean 实验包。复算不启动目标机实验、不加载模块、不重启。
