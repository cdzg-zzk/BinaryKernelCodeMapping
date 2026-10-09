# READ evaluation 正文候选

VKSO 将用户与内核的共同时间计算集中到共享实现，同时保持低读取成本。我们在 Retpoline 和 no-retpoline 两种配置下分别比较 Raw 与 VKSO，每种组合进行四次独立启动。每个接口每次启动测量 31 个批次，每批包含 500,000 次调用。表中报告启动内批次成本中位数的跨启动中位数，并给出以启动为单位的 95% bootstrap 区间。

七类用户 `clock_gettime` 快路径的 VKSO−Raw 差值为 −1.006～+1.006 TSC ticks/call。Retpoline 下，高精度读取的最大增量为 1.001 ticks；两个 coarse 接口分别增加 1.000 和 1.006 ticks，对应 6.624% 和 6.662%。no-retpoline 下，MONOTONIC、MONOTONIC_RAW 和 BOOTTIME 在四个启动块中均更快，中位成本分别下降 1.002、1.006 和 1.005 ticks。该结果表明，共享计算及用户侧适配将这些接口的最大中位读取增量控制在约一个 TSC tick。

共享实现还降低了其他公开入口的成本。两种配置下，`clock_getres`、`gettimeofday` 和两种 `time` 调用共五项时间快路径均在四个启动块中取得更低中位成本，节省 0.969～2.050 ticks；`getcpu` 另节省约 1.004 ticks。`clock_getres(REALTIME)` 的降幅约为 13.58%，`time(&seconds)` 为 28.33%～28.34%。前者直接读取共享分辨率，后者通过 IFUNC 将稳定调用绑定到共享秒值读取入口，保留完整公开 API 语义。

内核侧通过普通导出接口进入共享核心。三种 READ 接口的中位成本差为 −2.728～+1.087 ticks；Retpoline 的 `ktime_get_raw_ts64` 和 no-retpoline 的 `ktime_get_ts64` 在四个启动块中均更快，分别下降 1.516 和 2.728 ticks。用户态与内核态因此能够在复用共同计算的同时保持接近 Raw 的读取成本，并在多项公开入口上获得稳定的启动中位成本下降。

三项用户 fallback 单独比较。两种配置的六项中位成本差均为负，范围为 −9.221～−1.738 ticks。这些时钟在入口分类后进入系统调用，其绝对成本和启动区间列于 fallback 表；共享快路径的收益与完整系统调用路径分别报告。

## 图注

**主要 READ。** 七类用户 `clock_gettime` 与三个普通内核读取接口的 VKSO−Raw 成本差，单位为 TSC ticks/call。实心点为两后端跨启动中位数之差，横线为逐项 95% 启动 bootstrap 区间，空心点为四个匹配启动块内的中位差，重合点覆盖绘制。每后端、每配置各四次独立启动。负值表示 VKSO 更快。用户与内核区域分隔；两组编译配置分别呈现。

**其他公开快路径。** 五项时间工作负载及 getcpu 的成本差，统计口径同主图。十二项配置/工作负载对照在全部四个启动块中均为负，表明这些入口的中位成本下降在不同启动间保持一致。

**Fallback。** PROCESS_CPUTIME 的 clock_gettime/clock_getres 以及 REALTIME_ALARM 的 clock_gettime 完整调用成本差，统计口径同主图。宽区间反映启动间变动；图中所有启动块均保留。
