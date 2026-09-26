# Clocktime：按完整分布比较 Raw 与 VKSO

分析日期：2026-09-26。主数据为 `20260924T065535Z-clocktime-full`，
历史对照为 `20260923T164954Z-clocktime-full`。两轮分别验证、分别统计，
不合并成八次同版本实验；业务/PT/PMU 等诊断数据不进入本报告。

## 数据与统计口径

两轮均通过现有完整 campaign 校验，包括结果、冻结工具、包身份、
功能及共享证据。每轮 32 个不同 boot ID，每个实现/配置/测量模式有
4 次独立启动。最新一轮包含 7,936 个用户 READ 批次、1,488 个内核
reader 批次、3,599,939 次 action=0 UPDATE，以及 1,986,908 个并发
reader 批次；UPDATE 记录没有 dropped 样本。

主指标：每个 boot 内对全部观测求算术均值，再等权平均四个 boot。
Δ = VKSO−Raw；负数表示 VKSO 成本更低。单位为 **TSC ticks**，不是
unhalted core cycles。READ 和两种 reader 的观测是完整调用批次平均，
UPDATE 才是逐次发布区间耗时。不同模式之间不混算，也不把两种峰
当成两个独立系统实验。UPDATE 不包含 timekeeper lock 等待或完整
定时器中断；并发 reader 覆盖包围 writer 的完整负载窗口。

每项另给出四个 block 的 Raw/VKSO boot 均值差和 pointwise bootstrap
95% 区间；四个 block 仅有 4⁴=256 种重采样序列，区间覆盖能力有限，
且没有多重比较校正。区间跨零不代表等价，区间不跨零也不替代更多
独立启动的稳定性证据。完整区间见机器生成的报告。

主指标不删除长尾、不扣计时开销。UPDATE 有 3 次 action=0 发生在
CPU2，其余均在 CPU0；原协议按 action=0 纳入的三次仍保留。另算仅
CPU0 的敏感性，任一 Raw/VKSO 差值变化不超过 0.00334 ticks。

## 用户公开 API READ

下表是 boot 均值的等权均值；每个单元中的次序为 Raw / VKSO。

| API | Normal Raw / VKSO | Δ | No-retpoline Raw / VKSO | Δ |
| --- | ---: | ---: | ---: | ---: |
| clock_gettime_realtime | 54.191 / 54.016 | -0.175 | 54.190 / 54.463 | +0.273 |
| clock_gettime_monotonic | 54.198 / 54.647 | +0.449 | 54.198 / 53.473 | -0.726 |
| clock_gettime_monotonic_raw | 54.193 / 54.673 | +0.480 | 54.206 / 53.609 | -0.597 |
| clock_gettime_boottime | 54.202 / 54.950 | +0.748 | 54.192 / 53.570 | -0.622 |
| clock_gettime_tai | 54.193 / 55.115 | +0.922 | 54.194 / 55.046 | +0.851 |
| clock_gettime_realtime_coarse | 15.097 / 16.102 | +1.004 | 15.097 / 15.095 | -0.002 |
| clock_gettime_monotonic_coarse | 15.099 / 16.172 | +1.073 | 15.097 / 15.237 | +0.140 |
| clock_getres_realtime | 15.094 / 13.045 | -2.049 | 15.093 / 13.045 | -2.047 |
| clock_getres_realtime_coarse | 14.052 / 13.078 | -0.973 | 14.052 / 13.079 | -0.973 |
| gettimeofday_tv | 56.211 / 55.203 | -1.008 | 56.210 / 55.201 | -1.008 |
| time_null | 7.024 / 6.022 | -1.002 | 7.025 / 6.023 | -1.002 |
| time_pointer | 7.024 / 5.918 | -1.107 | 7.025 / 7.303 | +0.279 |
| getcpu_both | 14.600 / 12.825 | -1.774 | 14.609 / 12.906 | -1.703 |
| clock_gettime_process_cpu_fallback | 870.070 / 867.993 | -2.078 | 843.772 / 842.718 | -1.054 |
| clock_getres_process_cpu_fallback | 592.303 / 585.086 | -7.217 | 575.675 / 563.165 | -12.510 |
| clock_gettime_realtime_alarm_fallback | 684.827 / 671.805 | -13.022 | 670.648 / 662.287 | -8.361 |

双峰不是所有接口共有的同一种现象。READ 中多个接口分布很集中，
部分 VKSO 接口有批次间多档成本或尾部；没有逐次 READ 数据，不能
声称它们与 UPDATE 的逐次双峰具有相同机制。

`time_pointer` 是必须保留完整分布的例子。No-retpoline 的 124 个
VKSO 批次中，111 个约为 5.03 ticks/call，13 个约为 26–27 ticks/call；
四个 boot 的高成本批次数分别为 3、3、5、2，并非一个孤立异常点。
Raw 约为 7.025 ticks/call。原“boot 中位数再取中位数”的差为
−1.991 ticks，而完整均值差为 **+0.279 ticks**，95% 区间
[−0.407, +1.140]。因此不能只写“time(pointer) 加速约 2 ticks”。
这里记录的是批次现象，尚不推断具体业务或硬件原因。

Normal 下 monotonic、monotonic-raw、boottime、TAI 以及两个 coarse
接口的完整均值更高；getres/gettimeofday/time(NULL)/getcpu 更低。
No-retpoline 下 monotonic、monotonic-raw 和 boottime 转为更低，TAI
仍更高。接近零且区间跨零的项，例如 no-retpoline realtime-coarse，
不按四舍五入后的微小符号宣称实际提升。

## 普通内核 reader 与并发公开 reader

| 类型 | API | Normal Raw / VKSO | Δ | No-retpoline Raw / VKSO | Δ |
| --- | --- | ---: | ---: | ---: | ---: |
| 内核 reader | monotonic | 56.194 / 55.202 | -0.993 | 58.567 / 55.484 | -3.083 |
| 内核 reader | monotonic_raw | 55.718 / 54.279 | -1.439 | 54.656 / 53.353 | -1.303 |
| 内核 reader | monotonic_coarse | 9.197 / 11.039 | +1.843 | 11.023 / 8.753 | -2.270 |
| 并发公开 reader | monotonic | 54.192 / 54.998 | +0.806 | 54.192 / 53.201 | -0.991 |
| 并发公开 reader | monotonic_raw | 54.199 / 54.722 | +0.523 | 54.197 / 53.210 | -0.987 |
| 并发公开 reader | monotonic_coarse | 16.056 / 17.070 | +1.014 | 16.056 / 16.121 | +0.064 |

这些项在各自配置的四个 block 中，差值方向均一致。普通内核 reader
不经过用户公开 wrapper；并发公开 reader 经过完整用户入口，两类
结果的方向不能互相代替。

## UPDATE：完整均值与分布

| 配置 | 持续 reader 负载 | Raw | VKSO | Δ | Δ 的 95% 区间 |
| --- | --- | ---: | ---: | ---: | --- |
| Normal | idle | 123.274 | 126.325 | +3.051 | [+2.223, +3.874] |
| Normal | monotonic | 129.955 | 128.004 | -1.952 | [-3.999, +0.227] |
| Normal | monotonic_raw | 136.561 | 128.610 | -7.951 | [-10.714, -6.331] |
| Normal | monotonic_coarse | 134.032 | 128.051 | -5.981 | [-8.332, -3.630] |
| No-retpoline | idle | 120.782 | 118.192 | -2.589 | [-4.194, -0.857] |
| No-retpoline | monotonic | 128.331 | 118.678 | -9.653 | [-12.585, -7.217] |
| No-retpoline | monotonic_raw | 135.032 | 118.693 | -16.338 | [-18.230, -14.906] |
| No-retpoline | monotonic_coarse | 135.500 | 120.533 | -14.967 | [-18.695, -12.736] |

各配置/负载的逐 boot 图中都可见低、高耗时集中区，高侧还可能有
子峰；不强制拟合恰好两个潜在状态。**中位数可能因占比越过 50% 而
跨区间跳变，不能单独代表整体成本。** Normal monotonic-raw 的旧
中位数差为 +6 ticks，而完整均值差为 −7.951 ticks；no-retpoline
idle 也从中位数差 +13.5 变为完整均值差 −2.589 ticks。方向改变来自
统计对象不同，不是本次离线分析改变了实现或采集结果。

Normal idle 的 VKSO 低侧位置更低，但按历史谷值（Raw 120、VKSO
110 ticks）划分，高侧占比为 Raw 47.84%、VKSO 60.56%。逐 block
对均值差作对称代数分解，位置项 −4.73、占比项 +7.78，合计 +3.05
ticks。No-retpoline idle 则为 −9.17 与 +6.59，合计 −2.59 ticks。
因此仅报告“低峰更快”会漏掉占比变化，单看高峰也不完整。

但这不是机制归因：改用共同阈值 100–140 ticks，某些分解项会变号，
因为阈值会切开不同位置的集中区。主均值差不受阈值影响；低/高侧
位置与占比只作为带明确阈值的补充描述，不命名为已确认业务状态。

把 UPDATE 截顶到 300 ticks 或在各 boot 内做 99% 上端 winsorization，
最新一轮的八项均值差均未改变符号。超过 300 的尾部超额对差值的
贡献绝对值不超过 0.927 ticks：本轮主要结论不是几个极端值造成的。
Normal monotonic 的四个 block 有一个为 +1.028 ticks，区间也跨零，
不据 −1.952 的点估计宣称稳定收益。其余七项方向在四个 block 中一致。

## 历史对照与结论边界

两轮 Raw READ/UPDATE 镜像身份分别保持不变；VKSO UPDATE 镜像及
用户库身份存在版本变化，不能合并样本估计同一实现的性能。即使
镜像相同，Raw normal/idle UPDATE 的四 boot 均值也从历史轮的
135.15 变为最新轮的 123.27 ticks。历史轮 block 1 为 156.51 ticks，
其中 5.33% 样本超过 300 ticks；最新轮各 boot 对应比例仅约
0.12%–0.15%。历史变化既包含高侧占比变化，也包含尾部变化。

历史 normal/idle Raw/VKSO 差为 −8.13，最新为 +3.05 ticks；这不能
直接解释为 VKSO 代码回退。最新轮在相同配置下配对的比较是本报告
主结果，历史轮独立保留，不删除异常启动，也不拿有利的历史 Raw
替换最新基线。当前数据支持“整个 Clocktime 重构在不同 API、负载和
构建配置下有收益也有开销”，不支持“所有接口更快”或把差值全归因于
代码页共享。双峰具体根因仍未证实，但不阻止报告完整期望成本。

## 产物与复算

- [完整最新报告](../baremetal/results/clocktime-distribution-analysis/20260924T065535Z-clocktime-full/report.md)
- [Normal UPDATE 图](../baremetal/results/clocktime-distribution-analysis/20260924T065535Z-clocktime-full/update-normal.png)
- [No-retpoline UPDATE 图](../baremetal/results/clocktime-distribution-analysis/20260924T065535Z-clocktime-full/update-no-retpoline.png)
- [用户 READ CDF](../baremetal/results/clocktime-distribution-analysis/20260924T065535Z-clocktime-full/read_user-no-retpoline.png)
- [历史轮报告](../baremetal/results/clocktime-distribution-analysis/20260923T164954Z-clocktime-full/report.md)
- [跨轮数值](../baremetal/results/clocktime-distribution-analysis/campaign-comparison.csv)
- [复算命令](STATEFUL.md#已采集数据的分布分析)

图形约定：Raw 蓝色实线、VKSO 橙色虚线；细线是单个 boot，粗线为
等 boot 权重分布。UPDATE 用中央直方图观察形状并标注图外尾部比例，
同时保留全范围 CDF；READ 与 kernel reader 使用全范围批次成本 CDF。
图形为本地可复算分析产物，不以视觉峰形替代原因证据。PNG/PDF 均已
生成，代表性渲染已检查。5 项新增离线统计测试和 45 项原流程单元
测试通过；本次没有执行新的目标内核测量。
