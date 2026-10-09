# Clocktime UPDATE：函数内成本、负载响应与完整样本分解

本轮完成 UPDATE 的离线结果解释，覆盖两配置、两后端、四负载、每组合四次独立启动，共 16 次 UPDATE 启动、960 个采集窗口和 3,599,774 次周期发布。全部样本保留，完整均值与既有正式结果一致。

**在指定插桩条件下，VKSO 发布均值对受测读取负载的变化范围更小。** Retpoline 中，VKSO 四种负载的发布均值为 121.649～122.528 ticks，范围宽度为 0.878 ticks；Raw 为 116.718～132.303 ticks，宽度为 15.585 ticks。no-retpoline 对应宽度为 VKSO 2.083、Raw 17.843 ticks。三种读取负载相对 idle 的成本变化，VKSO 均小于 Raw，六项配置/负载对照在四个启动块中的方向全部一致。

- [完整结果表](tables.md)：均值、区间、低高侧条件成本、占比、尾部和负载响应。
- [逐启动表](boot-results.md)：四个启动的完整均值、高侧占比和尾部贡献。
- [正文候选](evaluation-text.md)：函数内成本、完整发布成本、负载响应、分布组成及记录器敏感性；两种计时范围分别成段。
- 图：[完整均值差](update-mean.pdf)、[负载响应](update-load-response.pdf)、[四项分解](update-decomposition.pdf)、[Retpoline 分布](update-distribution-normal.pdf)、[no-retpoline 分布](update-distribution-no-retpoline.pdf)。同名 SVG 可编辑，PNG 可预览。
- [测量与机制证据](measurement-and-mechanism.md)：计时范围、匹配记录器对照与剩余机制缺口。

后续[16启动匹配记录器对照](../../update-bench/mechanism-evidence/recorder-matrix-16-boots/README.md)
已证明VKSO−Raw相对均值差也随记录器改变；[固定地址guard控制](../../update-bench/mechanism-evidence/guard-control-boot1-review/README.md)
及[元数据布局先导](../../update-bench/mechanism-evidence/layout-control-boot1-review/README.md)
均未达到各自预定大幅主峰移动条件，停止同类重复。布局先导新增83,998样本、
16个块级峰移为−5～+5 ticks；guard与布局来自同一启动。以下正式数值与原始样本保持不变，
其解释限定为指定插桩条件下的观测成本。后续[固定入口旧记录主体](../../update-bench/mechanism-evidence/record-body-control-boot1-review/README.md)
新增71,996样本，八块峰移−3～+3 ticks，原版参照复现但未达到重复门槛，亦停止同类追加。
三项固定镜像控制来自同一启动。正文候选已纳入结果，具体物理机制仍未确定。

[两配置完整发布矩阵](../../update-bench/mechanism-evidence/full-publication-two-configurations/README.md)
另有16次独立启动、256窗、511,996样本，覆盖Normal/no-retpoline、两后端、两记录器、每单元两启动。
正文候选已整合32个绝对均值、48个逐块差值及Normal主体/尾部贡献和主峰带宽敏感性，
[逐项数字绑定](full-publication-prose-binding.json)通过；原函数内结果保持单独解释。
Normal四负载记录器相对效应在两块均为负；no-retpoline MONOTONIC为正、COARSE翻转。
对应[逐启动成本](../../update-bench/mechanism-evidence/full-publication-two-configurations/per-boot-costs.csv)、
[后端与记录器效应](../../update-bench/mechanism-evidence/full-publication-two-configurations/backend-and-recorder-effects.csv)、
[Normal图表](../../update-bench/mechanism-evidence/full-publication-recorder-normal/step-07-review/interpretation.md)
与[no-retpoline图表](../../update-bench/mechanism-evidence/full-publication-recorder-control/step-07-review/interpretation.md)均已保存。
三个机制问题的证据及剩余工作见[测量与机制证据](measurement-and-mechanism.md)，没有新增重启指令。

## 完整成本及其负载响应

这里测量插桩版本 `timekeeping_update` 内从起始时间戳到结束时间戳的发布路径。Raw 包含 vDSO 状态发布与 fast timekeeper 更新，VKSO 包含共享状态发布与同类 fast timekeeper 更新，另含此函数内共同的计时状态维护。调用者已持有 timekeeper_lock，因此不包含获取锁的等待，也不代表完整 timer interrupt。
[四个正式镜像的边界审计](../../update-bench/mechanism-evidence/update-dependency-audit/README.md)
进一步确认：序列计数开始在进入UPDATE之前，函数返回后还有shadow到正式timekeeper的复制
（Raw 280字节、VKSO 264字节）及序列提交，均未包含。正文所称完整均值指全部样本及尾部，
不能推广为整个周期发布成本；后者的[Raw/VKSO首组先导](../../update-bench/mechanism-evidence/full-publication-pair-boot1-review/README.md)
之后已完成上述两配置记录器矩阵及独立启动重复。
样本 action=0；显式 clock-set/NTP-reset 等其他 action 不在该矩阵中。

`timekeeping_update_bench_finish` 先取结束时间戳，再调用 recorder 写入记录。记录追加在计时区间外，但插桩生成的代码以及前序记录行为仍可影响测得成本。主表保留原始 TSC ticks，不扣除记录中的最小空时间戳对 33 ticks。本文结果绑定当前插桩方案，READ 的 clean 镜像不进入 UPDATE 统计。

每次启动依次运行 idle 和三种公开 clock_gettime 读者负载，每负载 15 个约 15 秒的 writer 窗口。单个读者绑定 CPU 2、通过完整公开 API 连续批量读取；writer 窗口嵌在已经启动的读者区间内。读者是闭环连续负载，不是按固定请求率注入。960 个窗口的 writer 起止及 load-batch 握手已核对，四个实际记录在 CPU 2 的周期样本照常保留，其余发布在 CPU 0。每个启动先合并该负载全部窗口，再计算均值；四个启动等权。

MONOTONIC_RAW 与 MONOTONIC_COARSE 负载下，VKSO 的函数内计时区间完整样本均值在两种配置的全部四块中更低：Retpoline 分别降低 9.775、10.521 ticks，no-retpoline 分别降低 6.730、6.914 ticks。idle 下 VKSO 分别增加 5.438、9.554 ticks；MONOTONIC 下分别为 −0.642、+2.965 ticks。完整表同时保留这些结果。

为直接回答“成本如何随读取负载变化”，同一启动内先减去 idle 均值，再比较两后端。Raw 的三种负载增量为 Retpoline 5.881～15.585、no-retpoline 8.672～17.843 ticks；VKSO 分别为 −0.506～+0.372、+0.478～+2.083 ticks。六项变化差的四块方向均为负，区间见 load-response.csv。这是在受测闭环负载与当前测量方案下观察到的负载响应。

## 从分布精确还原完整均值差

先按已有方法定位每个后端/配置/负载的低、高集中区：1-tick 直方图按启动等权，σ=3 ticks 高斯平滑，低峰搜索 65～125、高峰搜索 126～160 ticks，取两峰间谷值作为分界。表中的“低侧/高侧”是描述性分布区间。它们尚未对应到已识别的硬件或业务状态。

对每个匹配启动块，以 p 表示高侧占比、L 表示低侧条件均值、H 表示高侧条件均值。直接将低、高侧成本贡献与占比贡献相加，可以还原完整均值差，但此时高侧均值已包含长尾，不能再额外加一次尾部。

本轮采用四项分解。固定 T=300 ticks，先对每个观测取 min(x,T)，得到高侧条件均值 Hc；同时计算超额尾部 E=mean(max(x−T,0))。横线表示 Raw/VKSO 两个值的算术平均，Δ 表示 VKSO−Raw：

```text
完整均值差 = (1−p̄)ΔL + p̄ΔHc + Δp(H̄c−L̄) + ΔE
             低侧成本   高侧成本    占比贡献       超额尾部
```

每块先分解，再等权平均，四项之和逐块精确等于完整均值差。原始主成本没有截尾，超过 300 ticks 的观测也没有删除。表中的尾部贡献是超过 300 的超额部分；全部尾部观测自身的成本占比另列在 groups.csv 的 tail_cost_share。

八项主对照的低侧成本贡献全部为负（−16.043～−5.159 ticks），高侧占比贡献全部为正（+5.757～+14.945 ticks）。这解释了为什么 VKSO 低侧更快，却不一定具有更低整体均值。Retpoline 的两种 Raw/coarse 读取负载中，低侧与高侧成本下降共同抵消了占比增加，使总均值下降。no-retpoline 中高侧成本贡献转为正，低侧收益与尾部减少仍使这两种负载的总均值下降。

300-tick 超额尾部差在八项对照中均为负，范围 −1.627～−0.075 ticks。超过 300 ticks 的样本占比约 0.147%～0.234%，依然全部进入主均值。完整 CDF 和最大值保存了这部分信息。

## 统计与分界敏感性

主均值及四项贡献的区间通过枚举四个匹配启动块的 256 种有放回重采样获得，报告逐项 95% 百分位区间。分界相关贡献的区间条件于原分界；另外单列分界敏感性，不把切分规则的不确定性隐藏在启动 bootstrap 内。

敏感性包含 Raw/VKSO 谷值各自移动 ±5 ticks 的九种组合、σ=1.5/2/4/6 的峰定位，以及 T=180/200/240 的尾部边界。共 128 项检查，其中 5 项平滑设置无法解析两个主峰，明确记为 unresolved-peaks。全部可解析设置中，低侧成本贡献保持负值，占比贡献保持正值。尾部贡献在较低边界下可变号，不能把“300-tick 超额尾部下降”推广成任意慢侧范围都下降。所有切分变化都保持完整均值不变。

逐启动密度图显示原始启动差异，粗线只用于突出等权平均密度；完整 CDF 使用对数横轴覆盖最大观测。峰位置、条件均值、高侧占比和整体均值分别报告，不用峰位置的加权和代替均值。

## 证据文件与复算

| 文件 | 内容 |
| --- | --- |
| summary.csv / decomposition-blocks.csv | 八项完整对照与 32 个块级四项分解 |
| groups.csv / boots.csv / rounds.csv | 16 组、64 个启动×负载及 960 个窗口统计 |
| load-response.csv / load-response-blocks.csv | 六项负载相对 idle 对照及 24 个块级变化差 |
| sensitivity.csv | 128 项谷值、平滑和尾部边界敏感性 |
| histograms.csv / cdfs.csv | 64 个启动×负载分布、全部样本归一化、完整范围 CDF |
| identities.csv / configurations.csv / windows.csv | 原始启动关联、测量配置、读者/writer 窗口 |
| validation.json / verification.json / verification.log | 输入核对、代数复原、测试及渲染检查 |

在仓库根目录执行：

```bash
python3 test/test_gettime/vkso-tests/direct-api/update_evaluation.py --check
python3 test/test_gettime/vkso-tests/direct-api/update_report.py --check
python3 test/test_gettime/vkso-tests/direct-api/verify_update_evidence.py
```

去掉前两条的 --check 可重建派生结果。需要 Python 3、NumPy、CairoSVG、Pillow 及既有正式 campaign、完整 summary、峰分析结果和两个 UPDATE 包。当前生产源码和原始采集未修改。
