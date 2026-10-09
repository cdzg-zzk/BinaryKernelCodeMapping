# 两配置完整软件发布：证据汇总

两项固定矩阵均已完成并停止：16次不同启动、256窗、511,996周期样本，每后端/记录器/配置两次启动。Normal为255,999样本，no-retpoline为255,997样本；两项分别完成原CSV、归档与功能/恢复核验。本汇总不新增采集，不替代所要求的物理机制解释。

## 记录器是否改变后端比较

D=(VKSO−Raw)Current−(VKSO−Raw)Legacy，单位TSC ticks。分别显示两块，不能将块间符号翻转平均掉。

| 配置 | 负载 | D第一块 | D第二块 | 两块等权D | σ=3峰位D：第一/第二块 |
| --- | --- | ---: | ---: | ---: | --- |
| Normal | idle | -60.4998 | -77.9992 | -69.2495 | -2 / -1 |
| Normal | MONOTONIC | -24.4124 | -18.3289 | -21.3707 | +4 / +2 |
| Normal | RAW | -83.9909 | -69.4046 | -76.6977 | +32 / +34 |
| Normal | COARSE | -58.5195 | -75.5774 | -67.0484 | +186 / +53 |
| no-retpoline | idle | -51.4591 | -30.2495 | -40.8543 | +27 / +34 |
| no-retpoline | MONOTONIC | +66.8041 | +31.8873 | +49.3457 | +29 / +33 |
| no-retpoline | RAW | -72.7849 | -53.8166 | -63.3007 | +56 / +57 |
| no-retpoline | COARSE | +43.3648 | -44.9965 | -0.8159 | +82 / +81 |

Normal四负载D均在两块为负；no-retpoline的idle/RAW为负、MONOTONIC为正，COARSE则翻转。尤其MONOTONIC的记录器相对效应在两配置中方向相反，不能把记录器误差建模为跨配置通用常数。no-retpoline COARSE两块等权D接近零不能支持测量无影响。

Normal COARSE第一块峰位D对带宽敏感（σ=2/3/5为+187/+186/+53），第二块为+53/+53/+51；no-retpoline默认峰位D为+82/+81。峰位、完整均值、占比和尾部必须分别报告，不能强行对应同一物理峰。

## 实际发布成本

下表为两次启动各自完整样本均值的等权平均，另列两次启动均值的观察范围，不是置信区间。逐启动样本数、中位数、p95/p99、最大值及三个带宽主峰见per-boot-costs.csv；全部尾部保留。

| 配置 | 后端 | 记录器 | 负载 | 等权均值 | 两次启动均值范围 |
| --- | --- | --- | --- | ---: | --- |
| Normal | Raw | Current | idle | 473.709 | 467.207～480.212 |
| Normal | Raw | Current | MONOTONIC | 631.831 | 628.014～635.647 |
| Normal | Raw | Current | RAW | 968.889 | 968.527～969.251 |
| Normal | Raw | Current | COARSE | 1024.833 | 1023.290～1026.376 |
| Normal | Raw | Legacy | idle | 426.313 | 424.288～428.339 |
| Normal | Raw | Legacy | MONOTONIC | 626.942 | 621.271～632.613 |
| Normal | Raw | Legacy | RAW | 919.077 | 915.772～922.383 |
| Normal | Raw | Legacy | COARSE | 982.190 | 980.785～983.596 |
| Normal | VKSO | Current | idle | 405.204 | 403.022～407.387 |
| Normal | VKSO | Current | MONOTONIC | 437.438 | 429.031～445.846 |
| Normal | VKSO | Current | RAW | 440.036 | 436.439～443.633 |
| Normal | VKSO | Current | COARSE | 452.178 | 448.387～455.969 |
| Normal | VKSO | Legacy | idle | 427.058 | 420.603～433.514 |
| Normal | VKSO | Legacy | MONOTONIC | 453.921 | 446.700～461.142 |
| Normal | VKSO | Legacy | RAW | 466.922 | 466.893～466.951 |
| Normal | VKSO | Legacy | COARSE | 476.584 | 471.983～481.184 |
| no-retpoline | Raw | Current | idle | 400.350 | 397.696～403.004 |
| no-retpoline | Raw | Current | MONOTONIC | 534.374 | 527.615～541.133 |
| no-retpoline | Raw | Current | RAW | 960.007 | 959.793～960.222 |
| no-retpoline | Raw | Current | COARSE | 976.829 | 935.649～1018.010 |
| no-retpoline | Raw | Legacy | idle | 337.647 | 334.688～340.605 |
| no-retpoline | Raw | Legacy | MONOTONIC | 552.068 | 540.524～563.612 |
| no-retpoline | Raw | Legacy | RAW | 872.333 | 868.517～876.150 |
| no-retpoline | Raw | Legacy | COARSE | 944.896 | 924.043～965.749 |
| no-retpoline | VKSO | Current | idle | 414.606 | 409.382～419.829 |
| no-retpoline | VKSO | Current | MONOTONIC | 438.012 | 435.802～440.221 |
| no-retpoline | VKSO | Current | RAW | 439.924 | 437.685～442.163 |
| no-retpoline | VKSO | Current | COARSE | 451.141 | 441.803～460.479 |
| no-retpoline | VKSO | Legacy | idle | 392.757 | 387.680～397.833 |
| no-retpoline | VKSO | Legacy | MONOTONIC | 406.361 | 404.996～407.726 |
| no-retpoline | VKSO | Legacy | RAW | 415.551 | 412.337～418.764 |
| no-retpoline | VKSO | Legacy | COARSE | 420.024 | 411.510～428.538 |

## 跨配置变化的适用范围

configuration-contrasts.csv逐后端/记录器/负载给出Normal−no-retpoline等权均值差、四种跨启动组合的观察范围和两次主峰。两个矩阵在不同时段采集，块编号相同不表示同一时刻配对；配置组涉及多个缓解选项，不能单独归因于retpoline。

计时覆盖完整软件发布路径：序列开始、UPDATE、正式timekeeper复制和最终序列结束，记录追加位于终点后。沿用原RDTSCP计时约定，不等于存储全局可见或读者观察到发布的延迟；也不是旧函数内窗口与新窗口相减后的“复制成本”。

现有证据已证明记录器改变相对比较，且该效应依赖配置与分布部分。两配置各自的条件成本、占比、分位秩尾部贡献和完整ECDF均已保存。自然多峰形成、VKSO/Raw占比差和缓解配置峰位差仍缺唯一物理机制证据；已停止的布局、节流及排序先导不因此自动追加。

- [Normal完整证据](../full-publication-recorder-normal/step-07-review/interpretation.md)。
- [no-retpoline完整证据](../full-publication-recorder-control/step-07-review/interpretation.md)。
- [逐启动成本](per-boot-costs.csv)、[后端及记录器效应](backend-and-recorder-effects.csv)、[配置变化](configuration-contrasts.csv)。
- [结构化汇总与来源绑定](comparison.json)，由本目录summarize.py复现。
