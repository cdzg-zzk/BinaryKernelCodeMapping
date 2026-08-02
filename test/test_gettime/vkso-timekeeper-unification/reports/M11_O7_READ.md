# M11 / O7 最终 READ 性能

> **历史快照。** 本文记录 fallback 边界重构前的 O7 READ，用于解释
> 为什么必须进行 `6656f97` 修复，不再代表当前最终性能。有效最终
> READ 为 `20260801T164548Z-vkso-final`，并与 UPDATE/CONCURRENT 统一报告在
> `vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md`。

## 1. 结论

最终 READ 结果完整且可用。normal 与 no-retpoline 四组均完成，功能矩阵逐字
一致，stderr 为空，归档 SHA-256 通过。最终 VKSO 复现了 O4 的成功路径收益，
没有出现新的 read 回归。

三个问题的直接答案：

1. **Raw 稳定。** 相对四个近期同源码、同 benchmark 批次的稳健中位数，当前
   Raw 各接口组变化在 `-0.21%` 到 `+0.27%`，hres 组仅 `+0.044%`。极短
   coarse 接口当前回到历史常见的约 17.06 cycles；上一 O4 批次的 18.52
   cycles 是批次漂移，不是 Raw 代码变化。
2. **最终 VKSO 稳定复现 O4。** 相对上一 reusable-text O4 批次，hres 组变化
   不到 `0.001%`，fallback `-0.064%`，PMU instructions/branches 逐接口相同。
   相对 O3 pre-O4 基线，最终 hres `-0.348%`、coarse `-10.563%`、
   getres `-11.671%`、gettimeofday `-10.692%`；cold fallback 只退化
   `+0.677%`。
3. **最终 VKSO 与 Raw 已接近，但 hres/coarse 仍有固定边界成本。** normal
   hres 几何平均多 1.55 cycles（`+2.738%`）；五个接口分别多
   0.87～2.98 cycles。coarse 多 2.33/3.03 cycles；gettimeofday、time、
   getcpu 基本持平，realtime getres 反而快 1.98 cycles。cold fallback
   normal 多 `3.696%`，no-retpoline 多 `1.510%`，符合 cold callback 和
   retpoline 的预期成本。

因此 READ 门槛支持保留 O3、O4 和 ITS/reusable-text；没有证据支持继续扩大
ABI、MM 或 wrapper 特化来追逐剩余数个 cycles。

## 2. 输入与完整性

- 结果：`vkso-tests/baremetal/results/20260731-o7-final-read`
- tag：`vkso-o7-final-code-20260731`
- commit：`adfe3138e1388c34cb58051d33b2047682ac1a28`
- 四组顺序：raw-normal、vkso-normal、raw-no-retpoline、
  vkso-no-retpoline
- CPU 2，500000 iterations，31 repeats，10000 warmup，PMU enabled
- seq：每组、每 protocol 100000000 reads
- benchmark SHA-256：
  `16dc6bdc438477596486c4e183706ecbf015e992245dd26cbe01aefae1088597`
- 四份 `functional.matrix` SHA-256：
  `55cb60189197b7995c98325d7c519c7470f9e6051f20f679e32189c8d59c67f7`
- 四组 `perf.stderr`、`seq.stderr`：均为 0 bytes
- 四个 `complete`：存在
- 归档：`20260731-o7-final-read.tar.gz`，SHA 校验通过

normal 与 no-retpoline 都使用干净 package；Raw/VKSO 同 mitigation 下配置只含
实现选择差异。当前和历史对照使用同一个 benchmark、实验配置和 Raw source-tree
SHA-256 `df11ad6c...`。

本文以每个接口 31 次采样的中位数为基本值。接口组百分比是各接口 cycles
比值的几何平均，不能替代逐接口绝对 cycles，尤其是 13～20 cycles 的短路径。

## 3. Raw 稳定性

Raw 稳定性不只对照紧邻的一次采集，而是使用四个近期同 Raw source、同
benchmark 批次的逐接口中位数再取稳健中位数：

- `20260730T053229Z-vkso-final`
- `20260730T110954Z-vkso-final`
- `20260730-its-static-thunk-candidate-read`
- `20260730-its-reusable-text-read`

`20260730T143832Z-o3-fullwidth` 的 Raw hres 曾整体漂移 5～9 cycles，已在 O3
报告中识别为批次异常，故不用于稳健中心，但仍保留为历史证据。

| Raw 接口组 | 当前 vs 历史稳健中位数 |
|---|---:|
| hres clock_gettime | +0.044% |
| coarse clock_gettime | +0.010% |
| fast clock_getres | +0.129% |
| gettimeofday | +0.272% |
| time/getcpu | -0.094% |
| cold fallback | -0.209% |

代表接口：

| Raw 接口 | 历史稳健中位数 | 当前 | 变化 |
|---|---:|---:|---:|
| clock_gettime realtime | 56.231 | 56.232 | +0.001% |
| monotonic | 56.212 | 56.227 | +0.026% |
| monotonic_raw | 58.254 | 58.338 | +0.145% |
| realtime coarse | 17.061 | 17.063 | +0.010% |
| monotonic coarse | 17.060 | 17.062 | +0.010% |
| gettimeofday both | 65.232 | 65.230 | -0.003% |
| clock_getres realtime | 15.057 | 15.094 | +0.243% |
| CPU fallback | 878.884 | 877.231 | -0.188% |

`gettimeofday(tv)` 当前为 65.226 cycles，比稳健中心多 1.003 cycles；同一
core 的 `gettimeofday(both)` 保持不变，PMU instructions/branches 也不变，
因此属于单个短 benchmark 形态的批次偏移，不是 Raw reader 整体回归。

相对紧邻 O4 批次，Raw hres 组显示 `+0.739%`，但几乎完全由上一批次
monotonic_raw 异常偏低造成；当前 58.338 cycles 与更早多个批次的
58.20～58.34 一致。上一批次 Raw coarse 的 18.52 cycles 同样异常偏高，
当前 17.06 回到历史中心。用紧邻单批次直接相减会把 Raw 自身漂移误算成
VKSO 代码效果。

Raw 当前与上一批次的 PMU instructions 中位数最大差仅 0.00014/call，branches
最大差仅 0.00004/call，进一步证明执行路径未变化。

## 4. 最终 VKSO 与历史 VKSO

### 4.1 与上一 O4 reusable-text 结果

上一批次和最终 tag 的 VKSO source-tree SHA-256 都是
`411949474afc3e969c866b7f8b5d2627c5bc9ba7e2b59c3afb4e03eff308d5e2`。
上一批次是在修复提交前的 dirty package 上采集，最终批次则来自 clean tag；
二者源码内容相同，最终批次完成了可复现性闭环。

| VKSO 接口组 | 最终 vs 上一 O4 |
|---|---:|
| hres clock_gettime | -0.000% |
| coarse clock_gettime | -1.861% |
| fast clock_getres | +0.609% |
| gettimeofday | -1.092% |
| time/getcpu | +0.090% |
| cold fallback | -0.064% |

hres 五个接口逐个变化都不超过 `0.002%`。coarse/gettimeofday 的亚 cycle 到
0.9 cycle 差异均为改善或短路径漂移。最终与上一 O4 的 PMU instructions
逐接口最大差为 0.00024/call，branches 最大差为 0.000052/call，即动态工作
完全一致。

### 4.2 与 O3 pre-O4 基线

| VKSO 接口组 | 最终 vs O3 |
|---|---:|
| hres clock_gettime | -0.348% |
| coarse clock_gettime | -10.563% |
| fast clock_getres | -11.671% |
| gettimeofday | -10.692% |
| time/getcpu | +0.029% |
| cold fallback | +0.677% |

PMU 解释与 O4 设计一致：

- 五个 hres 成功路径每次 `-7 instructions/-2 branches`；
- 两个 coarse 每次 `-8 instructions/-3 branches`；
- 四个 gettimeofday 形态每次 `-10 instructions/-3 branches`；
- realtime getres 约 `-1 instruction/-1 branch`；
- time/getcpu 动态工作基本不变；
- fallback 进入 environment-specific cold callback，允许小于 1% 左右的退化。

这说明最终 clean tag 保留了 O4 的真实动态工作减少，不是上一 dirty package 的
偶然结果。

## 5. 最终 VKSO 与同批次 Raw

### 5.1 normal 逐接口

| 接口 | Raw cycles | VKSO cycles | VKSO - Raw | 百分比 | 指令差 | 分支差 |
|---|---:|---:|---:|---:|---:|---:|
| clock_gettime realtime | 56.232 | 57.199 | +0.967 | +1.720% | +14 | +3 |
| monotonic | 56.227 | 58.203 | +1.977 | +3.516% | +23 | +6 |
| monotonic_raw | 58.338 | 59.206 | +0.868 | +1.489% | +20 | +4 |
| boottime | 56.231 | 59.206 | +2.975 | +5.291% | +28 | +8 |
| TAI | 56.230 | 57.200 | +0.970 | +1.724% | +20 | +6 |
| realtime coarse | 17.063 | 19.390 | +2.327 | +13.638% | +11 | +2 |
| monotonic coarse | 17.062 | 20.088 | +3.025 | +17.732% | +19 | +3 |
| process CPU fallback | 877.231 | 917.269 | +40.038 | +4.564% | +88 | +26 |
| realtime alarm fallback | 688.792 | 712.570 | +23.779 | +3.452% | +110 | +27 |
| getres realtime | 15.094 | 13.114 | -1.980 | -13.117% | -2 | 0 |
| getres realtime coarse | 13.701 | 14.360 | +0.659 | +4.811% | -2 | +2 |
| getres CPU fallback | 594.505 | 612.806 | +18.301 | +3.078% | +27 | +13 |
| gettimeofday tv | 65.226 | 64.725 | -0.501 | -0.768% | +12 | +1 |
| gettimeofday timezone | 18.199 | 18.209 | +0.010 | +0.055% | +5 | +1 |
| gettimeofday both | 65.230 | 64.225 | -1.005 | -1.540% | +8 | +1 |
| gettimeofday null | 16.999 | 17.072 | +0.073 | +0.431% | +9 | +1 |
| time null | 17.060 | 17.059 | -0.001 | -0.004% | -2 | +1 |
| time pointer | 16.056 | 16.116 | +0.060 | +0.372% | -2 | +1 |
| getcpu both | 20.069 | 20.118 | +0.049 | +0.244% | 0 | 0 |
| getcpu null | 20.069 | 20.069 | +0.000 | +0.000% | 0 | 0 |

接口组几何平均：

| normal 接口组 | Raw | VKSO | VKSO - Raw |
|---|---:|---:|---:|
| hres clock_gettime | 56.645 | 58.196 | +2.738% |
| coarse clock_gettime | 17.063 | 19.736 | +15.667% |
| fast clock_getres | 14.380 | 13.723 | -4.573% |
| gettimeofday | 33.871 | 33.716 | -0.459% |
| time/getcpu | 18.225 | 18.253 | +0.153% |
| cold fallback | 710.863 | 737.139 | +3.696% |

coarse 的百分比看起来较大，是因为 Raw 只有约 17 cycles；更有意义的绝对差为
2.33/3.03 cycles。该差异与 VKSO 为 MM/context、clock-id 和共享 core 支付的
11～19 条额外指令一致，是当前架构边界，不是 O4 回归。

成功路径 branch misses 大多低于 0.002/call，没有系统性 VKSO 增长；CPU
fallback 的 branch misses Raw/VKSO 都约 0.13/call，主要来自 cold syscall/
scheduler 路径。

### 5.2 no-retpoline 敏感性

| no-retpoline 接口组 | Raw | VKSO | VKSO - Raw |
|---|---:|---:|---:|
| hres clock_gettime | 56.604 | 58.198 | +2.816% |
| coarse clock_gettime | 18.066 | 19.589 | +8.430% |
| fast clock_getres | 14.360 | 13.649 | -4.948% |
| gettimeofday | 33.813 | 34.873 | +3.136% |
| time/getcpu | 18.449 | 18.248 | -1.087% |
| cold fallback | 693.162 | 703.632 | +1.510% |

hres normal/no-retpoline 的 VKSO cycles 几乎逐字一致，说明 O4 成功路径不依赖
关闭 retpoline。cold fallback 相对 Raw 的差距从 normal `3.696%` 降到
no-retpoline `1.510%`，证明其中一部分确实是间接 cold callback 的 mitigation
成本。

进一步使用同批 direct-syscall 数据拆分后，最大的 process-CPU fallback
差距 40.038 cycles 中，34.365 cycles（85.8%）位于 syscall 进入后的
VKSO 内核二次共享分派，用户态外壳只占 5.673 cycles。完整根因、
PMU 拆分和可选的内核 direct-bypass A/B 见 `M11_O7_FALLBACK.md`。

no-retpoline `gettimeofday(null)` 为 19.445 cycles，normal 为 17.072；两者
instructions/branches 相同，且历史 no-retpoline VKSO 该接口曾在 18.1～20.1
cycles 间变化。因此不能把该 2.37-cycle 单接口差异解释成代码或 mitigation
回归。no-retpoline 只用于敏感性分析，不是建议关闭生产安全配置。

## 6. Seq protocol

| 配置 | backend | protocol | cycles/read | retries/million |
|---|---|---|---:|---:|
| normal | Raw | hres | 43.1511 | 150.36 |
| normal | VKSO | hres | 45.1581 | 42.21 |
| normal | Raw | raw | 43.1513 | 124.65 |
| normal | VKSO | raw | 45.1573 | 40.36 |
| no-retpoline | Raw | hres | 43.1508 | 117.80 |
| no-retpoline | VKSO | hres | 45.1578 | 15.86 |
| no-retpoline | Raw | raw | 43.1512 | 104.72 |
| no-retpoline | VKSO | raw | 45.1571 | 20.46 |

VKSO protocol 固定多约 2.007 cycles/read（约 `+4.65%`），与 O3 和两个 O4
批次的 45.157 cycles/read 完全一致。VKSO retries 明显低于 Raw；changed-seq
事件仍在相同数量级，差异主要来自 odd-seq 观测窗口。retry 数也受本地 timer
interrupt 对齐影响，因此用每批的绝对值描述，不把单次中断数当成代码回归。

## 7. READ 决策

- 保留 O3 full-width delta；
- 保留 O4 cold backend/tail-entry；
- 保留 ITS/reusable-text 正确性修复；
- normal 是生产结论，no-retpoline 只证明 mitigation 敏感性；
- 不继续 O5/O6 read 特化；
- O7 下一门槛是最终 UPDATE-SIDE，再执行 READ/UPDATE 并发。

最终项目结论仍需等待 UPDATE 和并发数据，READ 单项不能替代 writer 与争用验证。
