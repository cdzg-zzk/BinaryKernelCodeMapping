# VKSO READ/UPDATE 并发性能实验报告

> 正式实验批次：`20260728T043508Z-update-concurrent`  
> 空闲 update-side 对照批次：`20260728T031855Z-update-side`  
> 实验平台：Intel NUC 裸机，Linux 5.15.198，TSC clocksource  
> 对比对象：原生 raw vDSO 与最终 VKSO  
> 报告范围：公开用户态 reader、完整 `timekeeping_update()` writer 及
> seq 一致性协议在并发条件下的相互影响

## 1. 实验目的

本报告独立回答以下问题：

1. 当用户态持续读取时间时，VKSO 与 raw vDSO 的公开 reader 谁更快；
2. reader 满负载时，完整 `timekeeping_update()` writer 是否受到更多
   cache-line/seq 竞争；
3. VKSO 的 private/shared 发布设计是否真正缩短了 seq 保持奇数的窗口；
4. 重试概率下降能否抵消 VKSO reader 的固定入口成本；
5. update-side 的改善是否以牺牲用户态读取性能为代价；
6. 当前实验能够支持哪些设计结论，不能支持哪些结论。

本报告测量 reader 与 writer 同时运行的情况。单独的 reader 和空闲 writer
结论分别见：

- [`VKSO_READ性能实验报告_20260728.md`](../baremetal/VKSO_READ性能实验报告_20260728.md)
- [`VKSO_UPDATE性能实验报告_20260728.md`](VKSO_UPDATE性能实验报告_20260728.md)

阅读本报告不依赖上述文档；所需实验参数、结果和原因分析均在本文重新给出。

## 2. 核心结论

### 2.1 用户态 reader

在每秒约 0.5 亿至 2.8 亿次调用的饱和读取条件下：

- `CLOCK_MONOTONIC`：Raw **52.211 cycles/call**，VKSO
  **51.889 cycles/call**，VKSO 少 **0.322 cycle / 0.616%**，应判断为
  **基本持平、略快**；
- `CLOCK_MONOTONIC_RAW`：Raw **51.861 cycles/call**，VKSO
  **53.349 cycles/call**，VKSO 多 **1.488 cycles / 2.870%**；
- `CLOCK_MONOTONIC_COARSE`：Raw **10.047 cycles/call**，VKSO
  **12.092 cycles/call**，VKSO 多 **2.045 cycles / 20.350%**。

`COARSE` 的百分比较大，是因为基线只有约 10 cycles；绝对差仍是约 2 cycles。
这里的“饱和”表示 Raw 和 VKSO 各自尽可能快地循环调用，而不是人为固定相同
calls/s。`MONOTONIC` 两侧吞吐只差 0.62%，最接近等强度；`MONOTONIC_RAW`
和 `MONOTONIC_COARSE` 的吞吐分别相差 2.79% 和 16.91%，writer 对比会同时
受到 reader 实现和实际读取强度影响。

### 2.2 完整 update writer

在三个公开 reader 满负载场景中，完整 `timekeeping_update()` 的典型值为：

- 与 `MONOTONIC` 并发：Raw **140 cycles**，VKSO **128 cycles**，
  VKSO 快 **12 cycles / 8.571%**；
- 与 `MONOTONIC_RAW` 并发：Raw **140 cycles**，VKSO **128 cycles**，
  VKSO 快 **12 cycles / 8.571%**；
- 与 `MONOTONIC_COARSE` 并发：Raw **133 cycles**，VKSO **128 cycles**，
  VKSO 快 **5 cycles / 3.759%**。

但 `MONOTONIC` 场景的 Mean/P95/P99 分别退化
**1.280% / 5.914% / 3.155%**，所以只能说典型 writer 更快，不能宣称
整个延迟分布都更优。`MONOTONIC_RAW` 和 `MONOTONIC_COARSE` 的
Mean/P95/P99 则均小幅改善。

其中 `MONOTONIC` 的 reader 吞吐最接近，是 writer -12 cycles 最有力的
并发证据；RAW/COARSE 场景由于 Raw 实际执行了更多 reads/s，不能把全部 writer
差值只归因于 publication 协议。

### 2.3 seq 竞争

- HRES：重试由 **69.54 次/百万**降至 **4.74 次/百万**，
  减少 **93.184%**；
- RAW：重试由 **99.16 次/百万**降至 **4.72 次/百万**，
  减少 **95.240%**；
- 两种协议的 VKSO observer 固定读取成本都比 Raw 多约
  **1.003 cycle / 2.32%**。

重试分解表明，Raw 和 VKSO 的 `changed_seq` 数量近似相同，真正减少的是
reader 看见 odd seq 后的自旋次数。这与 VKSO“先在 private snapshot 派生，
再短时间打开 shared seq 发布”的实现完全一致。

### 2.4 总体判断

本实验验证了 VKSO shared_data 发布协议的结构优势：

- writer 典型延迟在常规并发场景下降；
- seq 不可读窗口显著缩短；
- retry 减少 93%～95%；
- 没有出现时间倒退、CPU migration 或功能错误。

但它也证明 retry 优势不能自动转化为所有 reader 更快。Raw 的重试本来就低于
万分之一，而 VKSO 的 wrapper、显式 MM_data/context 依赖和 namespace 判断是
每次调用都支付的固定成本。因此最终结论是：

**VKSO 改善了发布侧和读写竞争，但用户态 reader 尚未在所有时钟上全面超过
raw vDSO；主要剩余问题是固定入口路径，而不是锁或 retry。**

## 3. 被测对象与数据身份

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

镜像和源树身份：

| 对象 | SHA-256 |
|---|---|
| Raw Image | `e639416310ce2b105f4560893741e0fce3fd3b3cecc24331faacc5784477895c` |
| VKSO Image | `ca43e0605bed6c39f0f285c99d13178c77c120dc71f0e1d7b17070c2a4c501af` |
| Raw source tree | `fdba196b751997d68e900c4c958e9a3d1181644f6cbe6041f3d32b84a66720d0` |
| VKSO source tree | `39a7ecda00197c3b8d04fba079709f097a6c61e65a2cf4238b0a6e7984b356c8` |
| Experiment config | `f843a7e1f59859fe00a071f5397d9c2b4d16df480b1fdee4f1d9730368797268` |
| Benchmark binary | `e2572918878e0a0c4a24952f7d7416d34661fd6c3362d9bbb9bdc3cabfb1a70c` |
| libkernel.so | `3faf6d3c8884a9dfafb49f0217b3f24167c1977d8f69c9700bf4f435f0cea13b` |
| Benchmark header | `095c3c20828e7b265c259e7cde8dbf986ee613ff5ecec068f709131db4dc4e55` |
| Benchmark recorder | `d07856a6eacf537ee050f2abb09ac3259d1f0d42748a8aec1867965b89464517` |

构建 manifest 中 `git_worktree_dirty=1`，因为构建时实验脚本和报告尚未全部提交。
这不妨碍结果身份确认：两个 Image、两个源树、配置、benchmark 和
`libkernel.so` 都有独立 SHA-256。

### 3.2 正式结果身份

正式结果目录：

```text
test/test_gettime/vkso-tests/update-bench/results/
└── 20260728T043508Z-update-concurrent/
    ├── raw/
    ├── vkso/
    ├── update-comparison.csv
    └── CONCURRENT_SUMMARY.md
```

关键结果哈希：

| 文件 | SHA-256 |
|---|---|
| `CONCURRENT_SUMMARY.md` | `97c9520e1761bc75346811fe6f163dfcf4cd10b3db29a8626b1498146e0dc61b` |
| `update-comparison.csv` | `f56698bc8df6edb48a4a76b7e3809a30bd3125cd06d5f756963479d4d91bf2a8` |
| Raw `writer-rounds.csv` | `f91274cc74447c3a4ea13e223c1e3d9878d678ae2d2ab50795e34b9717554dad` |
| VKSO `writer-rounds.csv` | `95f6452533e01b655e6e5815c596f801726d09dc87d6af44f8f88d2ac4196c8d` |
| Raw `reader-rounds.csv` | `328f57a4e6500ff512441c58f426aaefd982568ad12ac2a70fd4f4ea84231a12` |
| VKSO `reader-rounds.csv` | `35cb637ec6dcd9ba0dea7928e49ec6896c73c4ef2f7c8c370514f6f8397ff143` |

## 4. 测量方法

### 4.1 并发关系

每轮实验同时存在两条路径：

```text
隔离 CPU 2：公开用户入口持续读取时间
                       │
                       │ 共享时间数据/seq/cache line
                       ▼
内核 periodic tick：完整 timekeeping_update()，约 250 次/秒
```

reader 固定在隔离 CPU 2；SMT 关闭，其他中断被引导到 housekeeping CPU。
writer 是真实 periodic timekeeping 更新，不是仅调用
`update_vsyscall()`/`vkso_time_publish()` 的微基准。

负载生成器不限制固定 QPS，而是让每个实现各自以最大吞吐运行。因此本实验回答
“端到端饱和负载下系统表现如何”，不等价于“相同 calls/s 下每次 cache-line
竞争成本是多少”。后一个问题需要额外的节流/定频 reader 实验。

### 4.2 三个公开 reader 场景

每个场景先执行 100,000 次 warmup 和单调性验证，再连续读取 15 秒：

| 场景 | Raw 用户入口 | VKSO 用户入口 |
|---|---|---|
| `monotonic` | raw `__vdso_clock_gettime` | `__vkso_clock_gettime` wrapper |
| `monotonic_raw` | raw `__vdso_clock_gettime` | `__vkso_clock_gettime` wrapper |
| `monotonic_coarse` | raw `__vdso_clock_gettime` | `__vkso_clock_gettime` wrapper |

循环按 65,536 次为一个 batch，只在 batch 之间通过 syscall 读取 wall time。
这次 syscall 位于总计时区间内，但被 65,536 次用户入口调用摊薄，并且 Raw 与
VKSO 使用同一测量程序。主指标：

```text
tsc_cycles_per_call = 整个负载区间 TSC 差 / 成功调用次数
calls_per_second    = 成功调用次数 / 实际 wall time
```

因此这里测到的是应用实际使用的完整公开入口，不是只测共享 core。

### 4.3 seq observer 场景

每轮分别完成 50,000,000 次 HRES 和 50,000,000 次 RAW 协议读取。Raw 和
VKSO observer 都读取语义等价的字段：

```text
seq
cycle_last
mult
shift
base seconds
base nanoseconds
ordered TSC
seq recheck
```

失败被拆分为：

- `odd_seq`：第一次观察时 writer 正在发布；
- `changed_seq`：payload 读取过程中 seq 发生变化；
- `retries = odd_seq + changed_seq`。

observer 是为隔离 seq 协议而写的对称循环，不是完整
`clock_gettime()` 生产路径。

### 4.4 writer 测量边界

插桩位于完整 `timekeeping_update()` 的入口与出口：

```text
start = rdtsc_ordered()
    完整 timekeeping_update()
end = rdtsc_ordered()
sample = end - start
```

样本包含公共 timekeeping 工作，以及 Raw `update_vsyscall()` 或 VKSO
`vkso_time_publish()`。所有正式样本均为 `action=0`，没有混入
clock-set、NTP-clear 或 mirror 慢路径。

两次有序 TSC 的共同最小成本为 **33 cycles**。正文主表使用未扣除的实测
cycles；corrected 指标只用于确认结论。

### 4.5 实验参数

每个 backend：

```text
stabilize_seconds=120
repeats=15
load_seconds/round=15
warmup=100000
seq_iterations/protocol/round=50000000
updates_per_second≈250
cpu=2
clocksource=tsc
```

关键启动参数：

```text
nokaslr clocksource=tsc tsc=reliable nosmt
isolcpus=domain,managed_irq,2 nohz_full=2 rcu_nocbs=2
irqaffinity=0-1,3 idle=poll
processor.max_cstate=0 intel_idle.max_cstate=0
nmi_watchdog=0 nowatchdog audit=0
```

收集脚本还关闭 turbo，并把 CPU policy 设置为固定 performance 状态。Raw 和
VKSO 都在功能矩阵完成后对称等待 120 秒，才开始正式采集。

### 4.6 统计口径

对每个指标：

1. 每轮单独计算 writer 的 Mean/Median/P95/P99 或 reader 的平均
   cycles/call；
2. 对 15 轮的同名指标取中位数；
3. `Δ = VKSO - Raw`；
4. `Δ% = (VKSO / Raw - 1) × 100%`。

负值表示 VKSO 开销更低。

## 5. 实验有效性

| 检查 | Raw | VKSO | 判断 |
|---|---:|---:|---|
| 完成标记 | 有 | 有 | 通过 |
| backend probe | raw vDSO | VKSO auxv/MM_data | 正确 |
| 功能矩阵 | 76/76 pass | 76/76 pass | 通过 |
| 功能矩阵文本 | 76 行 | 76 行 | 两侧完全相同 |
| rounds | 15 | 15 | 一致 |
| reader CPU | 2 | 2 | 一致 |
| load 时长 | 15 s | 15 s | 一致 |
| warmup | 100,000 | 100,000 | 一致 |
| seq iterations | 50,000,000 | 50,000,000 | 一致 |
| 稳定等待 | 120 s | 120 s | 一致 |
| clocksource | TSC | TSC | 一致 |
| TSC pair min | 33 | 33 | 一致 |
| CPU migration | 0 | 0 | 通过 |
| 时间倒退 | 0 | 0 | 通过 |
| 非零 writer action | 0 | 0 | 通过 |

公开 reader 三个场景中：

- Raw 每个场景记录 **56,265** 个 writer 样本；
- VKSO 分别记录 **56,264 / 56,263 / 56,262** 个样本；
- 每轮均为 3,749～3,751 次更新，符合 250 Hz × 15 秒；
- 所有样本均为 periodic `action=0`。

seq observer 场景的 writer 样本数为 Raw **5,775**、VKSO **5,910**。这是因为
VKSO observer 每次固定多约 2.32% cycles，完成同样的 1 亿次协议读取需要约
2.32% 更长时间，从而自然观察到更多 periodic updates。writer 表中比较的仍是
每次 update 延迟，但 seq 场景的样本数量并非严格相同，解释尾部时必须保留
这一限制。

Raw/VKSO 的 `/proc/cmdline` 除启动 Image 名外完全一致。运行时 config 的差异
是实现选择本身：Raw 保留 native vDSO，VKSO 移除 native vDSO 并启用 VKSO；
benchmark 和运行参数一致。

## 6. 并发公开 reader 结果

### 6.1 cycles 与吞吐量

| 接口 | Raw cycles/call | VKSO cycles/call | cycles 差值 | cycles Δ% | Raw calls/s | VKSO calls/s | 吞吐变化 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CLOCK_MONOTONIC` | 52.211 | 51.889 | **-0.322** | **-0.616%** | 53,689,639 | 54,021,879 | **+0.619%** |
| `CLOCK_MONOTONIC_RAW` | 51.861 | 53.349 | +1.488 | +2.870% | 54,052,531 | 52,543,362 | **-2.792%** |
| `CLOCK_MONOTONIC_COARSE` | 10.047 | 12.092 | +2.045 | +20.350% | 279,008,289 | 231,827,127 | **-16.910%** |

cycles 和 throughput 方向一致，说明不是仅有 TSC 统计公式产生的差异。
吞吐变化与 cycles 百分比不完全互为倒数，是因为每轮按完整 batch 停止，
wall-time 边界略有不同。

### 6.2 轮间分布

| 接口/实现 | 最小 | Q1 | 中位数 | Q3 | 最大 | MAD |
|---|---:|---:|---:|---:|---:|---:|
| MONOTONIC Raw | 52.209 | 52.210 | 52.211 | 52.212 | 52.230 | 0.001 |
| MONOTONIC VKSO | 51.195 | 51.344 | 51.889 | 52.047 | 52.180 | 0.254 |
| MONOTONIC_RAW Raw | 51.735 | 51.788 | 51.861 | 51.909 | 52.638 | 0.065 |
| MONOTONIC_RAW VKSO | 53.070 | 53.204 | 53.349 | 53.647 | 54.173 | 0.152 |
| MONOTONIC_COARSE Raw | 10.047 | 10.047 | 10.047 | 10.082 | 10.285 | 0.000 |
| MONOTONIC_COARSE VKSO | 12.091 | 12.091 | 12.092 | 12.092 | 12.094 | 0.000 |

`MONOTONIC_RAW` 和 `MONOTONIC_COARSE` 的差距跨轮方向稳定。
`MONOTONIC` 的 VKSO 轮间波动明显大于 Raw，虽然中位数略快，但 -0.616%
不适合被表述成跨平台或确定性的性能提升，本文将其归类为基本持平。

### 6.3 与 standalone READ 的交叉复核

| 接口 | Standalone Raw/VKSO | Standalone Δ% | 并发 Raw/VKSO | 并发 Δ% |
|---|---:|---:|---:|---:|
| MONOTONIC | 58.583 / 57.662 | **-1.57%** | 52.211 / 51.889 | **-0.62%** |
| MONOTONIC_RAW | 58.689 / 57.278 | **-2.40%** | 51.861 / 53.349 | +2.87% |
| MONOTONIC_COARSE | 17.064 / 18.064 | +5.86% | 10.047 / 12.092 | +20.35% |

两组绝对 cycles 不能直接相减：

- standalone 每个样本执行 500,000 次调用并同时采集 PMU；
- 并发实验执行 15 秒持续 batch load；
- 两组使用不同 kernel Image（并发镜像启用 update recorder）；
- 循环、计时边界和代码布局并不相同。

可以做的是稳定性判断：

- `MONOTONIC` 两组都显示 VKSO 基本持平或略快；
- `MONOTONIC_COARSE` 两组都显示稳定的 1～2 cycles 固定退化；
- `MONOTONIC_RAW` 的符号翻转，说明 standalone Normal 的优势不具有跨负载
  稳定性，不能把任一单次结果写成普遍架构结论。

## 7. 并发完整 writer 结果

### 7.1 未扣除 TSC 测量成本

| 场景 | 指标 | Raw cycles | VKSO cycles | 差值 | Δ% |
|---|---|---:|---:|---:|---:|
| monotonic | Mean | 143.164 | 144.997 | +1.833 | +1.280% |
| monotonic | Median | 140.000 | 128.000 | **-12.000** | **-8.571%** |
| monotonic | P95 | 186.000 | 197.000 | +11.000 | +5.914% |
| monotonic | P99 | 475.500 | 490.500 | +15.000 | +3.155% |
| monotonic_raw | Mean | 147.873 | 146.643 | **-1.230** | **-0.831%** |
| monotonic_raw | Median | 140.000 | 128.000 | **-12.000** | **-8.571%** |
| monotonic_raw | P95 | 196.000 | 191.000 | **-5.000** | **-2.551%** |
| monotonic_raw | P99 | 484.500 | 476.500 | **-8.000** | **-1.651%** |
| monotonic_coarse | Mean | 146.059 | 145.180 | **-0.879** | **-0.602%** |
| monotonic_coarse | Median | 133.000 | 128.000 | **-5.000** | **-3.759%** |
| monotonic_coarse | P95 | 196.000 | 189.500 | **-6.500** | **-3.316%** |
| monotonic_coarse | P99 | 513.000 | 510.000 | **-3.000** | **-0.585%** |
| seq_protocol | Mean | 147.369 | 154.391 | +7.022 | +4.765% |
| seq_protocol | Median | 126.000 | 128.000 | +2.000 | +1.587% |
| seq_protocol | P95 | 203.800 | 215.000 | +11.200 | +5.495% |
| seq_protocol | P99 | 582.240 | 677.420 | +95.180 | +16.347% |

### 7.2 扣除共同 TSC pair 最小成本

两侧同时扣除 33 cycles 后，绝对差不变：

| 场景 | Corrected Mean Δ% | Corrected Median Δ% | Corrected P95 Δ% | Corrected P99 Δ% |
|---|---:|---:|---:|---:|
| monotonic | +1.664% | **-11.215%** | +7.190% | +3.390% |
| monotonic_raw | **-1.070%** | **-11.215%** | **-3.067%** | **-1.771%** |
| monotonic_coarse | **-0.778%** | **-5.000%** | **-3.988%** | **-0.625%** |
| seq_protocol | +6.140% | +2.151% | +6.557% | +17.329% |

corrected 百分比更大只是因为分母变小，论文主表应优先使用未扣除的实测
cycles。

### 7.3 与空闲 update-side 的关系

独立空闲批次测得：

| 状态 | Raw Median | VKSO Median | VKSO 相对 Raw |
|---|---:|---:|---:|
| idle | 126 | 122 | -4 cycles / -3.175% |
| monotonic load | 140 | 128 | -12 cycles / -8.571% |
| monotonic_raw load | 140 | 128 | -12 cycles / -8.571% |
| monotonic_coarse load | 133 | 128 | -5 cycles / -3.759% |

与 idle 相比：

- Raw 在高精度 reader 饱和时，典型 writer 从 126 增到 140 cycles；
- VKSO 从 122 增到 128 cycles；
- `MONOTONIC_COARSE` 下 Raw 增到 133，VKSO仍为 128。

这是跨批次辅助比较，不应当作严格配对统计；但它与同一并发批次中 VKSO
writer 中位数更低的方向一致，说明 VKSO 的较短发布协议减少了典型读写竞争。

还必须考虑读取强度：

- `MONOTONIC` 吞吐只差 0.62%，其 writer Median 140 → 128 cycles
  是最接近等负载的证据；
- `MONOTONIC_RAW` 中 Raw 吞吐高 2.79%，存在轻度压力不等；
- `MONOTONIC_COARSE` 中 Raw 吞吐高 16.91%，存在明显压力不等。

因此“VKSO 在常规并发下 writer Median 较低”成立；“相同读取频率下三个场景
都确定快 5～12 cycles”则超出了本实验能够证明的范围。

## 8. seq 竞争结果

### 8.1 重试率与读取成本

| 协议 | Raw retries/百万 | VKSO retries/百万 | retry 差值 | retry Δ% | Raw cycles/read | VKSO cycles/read | cycles Δ% |
|---|---:|---:|---:|---:|---:|---:|---:|
| HRES | 69.540 | 4.740 | **-64.800** | **-93.184%** | 43.1505 | 44.1535 | +2.324% |
| RAW | 99.160 | 4.720 | **-94.440** | **-95.240%** | 43.1511 | 44.1537 | +2.323% |

对应概率：

```text
Raw HRES  = 0.006954%
VKSO HRES = 0.000474%
Raw RAW   = 0.009916%
VKSO RAW  = 0.000472%
```

即 VKSO 分别把 HRES 和 RAW 的 retry 降至 Raw 的约 **1/14.7** 和
**1/21.0**。

### 8.2 retry 分解

| 协议 | 实现 | retries 中位数 | odd_seq | changed_seq |
|---|---|---:|---:|---:|
| HRES | Raw | 3,477 | 3,298 | 179 |
| HRES | VKSO | 237 | 54 | 183 |
| RAW | Raw | 4,958 | 4,766 | 191 |
| RAW | VKSO | 236 | 49 | 188 |

`changed_seq` 几乎没有变化：

- HRES：179 → 183；
- RAW：191 → 188。

这符合两侧都执行约 250 次/秒 timekeeping 更新的事实。巨大差异来自：

- HRES `odd_seq`：3,298 → 54，减少 **98.36%**；
- RAW `odd_seq`：4,766 → 49，减少 **98.97%**。

所以实验不是通过减少更新频率“制造”低 retry，而是证明 VKSO writer 将 seq
保持奇数的时间缩短了。

`odd_seq` 是 observer 紧循环中看见奇数的次数，不是独立 writer 事件数：同一次
writer odd 窗口可能被 reader 连续观察多次。因此“减少约 99%”应解释为
odd-window 暴露量/自旋量显著降低，而不能直接换算成 writer 次数减少 99%。
两侧 observer 固定路径只差约 2.3%，不足以解释两个数量级的 odd 差异。

### 8.3 为什么 retry 少很多却仍多约 1 cycle

reader 的平均成本可以近似写为：

```text
平均成本 = 每次调用都支付的固定成本
         + retry 概率 × 一次失败尝试的成本
```

即使保守地假设每次 retry 都再花约 44 cycles：

```text
Raw HRES retry 贡献 ≈ 69.54 / 1,000,000 × 44 ≈ 0.0031 cycle/read
Raw RAW  retry 贡献 ≈ 99.16 / 1,000,000 × 44 ≈ 0.0044 cycle/read
```

VKSO 消除绝大多数 retry，理论平均收益仍不到 **0.005 cycle/read**，不可能
抵消每次固定多出的约 **1 cycle**。因此以下两个观察并不矛盾：

```text
VKSO retry 显著更少
VKSO seq observer 固定路径仍约慢 1 cycle
```

## 9. 性能差异的实现原因

### 9.1 为什么 VKSO seq 窗口更短

Raw `update_vsyscall()` 的 TSC 普通路径需要维护两组 vDSO 数据和两个 seq：

```text
约 25 个 data field stores
4 个 seq stores
2 个 write barriers
```

VKSO 的 `vkso_time_publish()` 分两阶段：

```text
阶段一：在 writer 私有栈上派生完整 next snapshot
阶段二：
    shared->seq = odd
    约 23 个标量 field stores
    shared->seq = even
```

因此 VKSO：

- 只维护一个 shared seq；
- 少发布两个 clocksource mask；
- 少两次 seq store；
- monotonic/boottime 等派生结果只计算一次并复用；
- 最重要的是，将除最终标量 copy 之外的派生计算移到 odd 窗口之前。

对应代码：

- [`vkso_time_publish()`](../../linux-5.15.198-vkso/kernel/time/vkso_time.c)
- [`timekeeping_update()`](../../linux-5.15.198-vkso/kernel/time/timekeeping.c)
- [`vkso_read_begin()` / `vkso_read_retry()`](../../linux-5.15.198-vkso/kernel/time/vkso_time_internal.h)

`odd_seq` 减少约 99% 是这项结构设计的直接运行时证据。

### 9.2 为什么常规场景的 writer 典型值更快

reader 持续读取共享时间字段，writer 更新时必须取得相关 cache line 的独占
所有权。Raw/VKSO 都存在这种硬件一致性成本；seq 不是阻塞锁，不能消除
cache-line ownership transfer。

VKSO 通过更少的发布字段、一个 seq 和较短 odd 窗口减少了典型发布工作。
因此在三个公开 reader 场景中，writer Median 均低于 Raw：

```text
-12 cycles
-12 cycles
-5 cycles
```

这与结构缩减方向一致。但完整 `timekeeping_update()` 仍包含 leap、ktime、
PVClock、fast timekeeper 等两侧相同的工作，所以不应期待几十甚至上百 cycles
的改进。

上述解释在 `MONOTONIC` 场景证据最强，因为两侧 calls/s 基本相同。RAW 和
COARSE 场景的 reader 吞吐不同，publication 缩减与压力强度差异没有被单变量
隔离，应视为端到端结果而非纯 publication 微基准。

### 9.3 为什么 writer Mean/P95/P99 不总是更好

writer 尾部同时受以下因素影响：

- reader 与 writer 的 cache-line ownership 相位；
- writer 到达时 reader 正在访问哪一组字段；
- 不可屏蔽 NMI/SMI 和缓存替换；
- 单个 shared seq 覆盖完整 VKSO snapshot；
- 15 轮仍属于每个 backend 的一次启动，不是 15 次独立启动。

因此 Median 更适合表示固定典型路径，而 P95/P99 对少量系统扰动更敏感。
`MONOTONIC` 场景出现“Median 更快但 Mean/P95/P99 更慢”，说明这轮数据不支持
“VKSO writer 全分布更优”。另一方面，`MONOTONIC_RAW` 和
`MONOTONIC_COARSE` 的四个指标方向一致，能够支持小幅改善。

`seq_protocol` 还存在不同持续时间和不同 writer 样本数，且 reader 是专用
observer 而非公开接口，所以它的 writer 长尾只用于诊断，不能覆盖三个正式
公开 reader 场景的结论。

### 9.4 为什么 MONOTONIC 基本持平

`CLOCK_MONOTONIC` 是 VKSO wrapper 的第二个优先分支。wrapper 直接：

1. 注入 `vkso_user_mm_data`；
2. 注入 `vkso_user_context`；
3. tail-jump 到专用 monotonic reader；
4. reader 完成 TSC、seq 和时间换算；
5. 根 time namespace 下，`clock_mask` 分支不应用 offset。

专用 reader 避免了共享 core 的通用 clock-ID dispatch，且更短 odd 窗口减少
偶发 retry。最终结果与 Raw 基本持平，并出现 0.322 cycle 的中位优势。

但 VKSO 轮间 MAD 为 0.254 cycle，而中位优势只有 0.322 cycle，证据不足以把
它表述为稳定架构收益。

### 9.5 为什么 MONOTONIC_RAW 慢约 1.5 cycles

当前 wrapper 为避免 jump table，使用针对常用时钟优化的浅层判断树。
`CLOCK_MONOTONIC_RAW` 不是前两个分支，需要经过更多 clock-ID 比较后才能
tail-jump 到专用 reader。

进入 core 后，它还需要：

- 显式传入 MM_data；
- 显式传入 cycles context；
- 读取独立 raw cycles/base；
- 检查 `mm_data->clock_mask`，保持 time namespace 语义；
- 保留非 TSC clock mode 和 syscall fallback 冷路径。

Raw vDSO 同样必须保持 time namespace 和 fallback 语义；VKSO 的区别是把
MM_data/context 作为显式依赖传给共享 core。Standalone PMU 中该路径相对 Raw
多约 11 条退休指令和 5 个分支，说明 wrapper/依赖组织确实存在额外静态工作。

但 standalone Normal 中它反而更快，而并发实验中慢 1.488 cycles，所以不能把
这 1.488 cycles 精确归给某一个 load 或 branch。可以确定的是：retry 已减少
95% 仍未带来更快结果，主要剩余差异属于固定路径/布局，而不是 seq 冲突；
wrapper、显式依赖和代码布局各占多少仍需同镜像定点 A/B。

### 9.6 为什么 MONOTONIC_COARSE 相对慢 20%

Raw coarse reader 只有约 10 cycles，不读取 TSC，也不进行乘法和纳秒换算。
VKSO 的绝对差只有约 2.045 cycles，但：

```text
2.045 / 10.047 = 20.35%
```

VKSO `MONOTONIC_COARSE` 仍必须：

- 在 wrapper 中识别 clock ID；
- load 显式 MM_data 地址；
- tail-jump 到专用 coarse reader；
- 执行 seq begin/retry；
- 检查 `clock_mask`，必要时应用 namespace offset。

这些固定操作在高精度 50-cycle 路径上只占几个百分点，在 10-cycle coarse
路径上则被百分比放大。该结果不表示发生了锁等待或 cache miss；15 轮 VKSO
结果稳定在 12.091～12.094 cycles，表现为稳定的固定路径差。

Raw vDSO 也处理 time namespace；这里的差异不是“VKSO有namespace而Raw没有”，
而是两侧的数据组织和入口依赖形式不同。MM_data/clock-mask 检查不能直接删除，
因为进程可以在生命周期中进入 time namespace；只在初始化时看到根 namespace
零偏移，不能证明此后永远无 offset。

### 9.7 为什么 update 收益不能补偿高频 reader 损失

本实验中 writer 约 250 次/秒，而 reader 是每秒数千万至数亿次：

```text
writer：约 250 updates/s
reader：约 5.3×10^7～2.8×10^8 calls/s
```

writer 每次节省 5～12 cycles，在系统总量上远小于 reader 每次固定增加
1～2 cycles。饱和循环只是压力场景，真实程序不会始终达到这个调用频率；但它
说明性能优先级应是：

1. 保留更短的 writer/seq 发布协议；
2. 优先压缩每次 reader 都支付的 wrapper/MM_data 固定成本；
3. 不应为了再减少已经很低的 retry 而增加 reader 常规路径。

### 9.8 性能原因的证据强度

| 判断 | 证据 | 可信度 |
|---|---|---|
| VKSO odd 窗口显著更短 | odd/change 分解、更新频率一致、源码先 prepare 后 publish | 高 |
| retry 不是剩余 reader 差异主因 | retry 贡献上界不足 0.005 cycle | 高 |
| MONOTONIC_COARSE 是固定路径退化 | 15轮极稳定、standalone同方向、无时间错误 | 高 |
| MONOTONIC writer 典型竞争较低 | calls/s 接近且Median低12 cycles | 较高 |
| RAW/COARSE writer差值全来自publication | 饱和吞吐不等，未做定频reader | 中低 |
| MONOTONIC_RAW 多1.488 cycles的唯一来源 | 无并发PMU/同镜像单变量A/B | 低，不能唯一归因 |

因此原因分析应优先引用 seq 分解、稳定固定差和接近等强度的
`MONOTONIC` 场景；对代码布局、显式参数或 cache coherence 的细分只能作为
与证据一致的解释。

## 10. 对 VKSO 设计的评价

### 10.1 已经得到验证的设计点

1. **private/shared 两阶段发布是有效的**：odd-seq 自旋减少约 99%；
2. **单一 shared seq 是可行的**：没有时间倒退或功能错误；
3. **没有双重发布**：VKSO 镜像已移除 native vDSO，只执行
   `vkso_time_publish()`；
4. **完整 writer 没有系统性退化**：三个公开 reader 场景的 Median 均改善；
5. **共享 kernel code 可以服务用户和 kernel**：76 项功能矩阵两侧一致通过。

### 10.2 尚未解决的点

1. 用户态固定入口还未在所有时钟上追平 raw vDSO；
2. `MONOTONIC_RAW` 的 wrapper dispatch 和依赖传递仍多约 1.5 cycles；
3. `MONOTONIC_COARSE` 的 MM_data/namespace 固定成本在极短路径中占比较大；
4. writer 尾延迟没有在所有场景改善；
5. 当前实验只覆盖裸机 TSC，不覆盖 PVClock/Hyper-V 运行时性能。

### 10.3 合理的后续优化边界

可以继续研究：

- 在不增加 jump table 的前提下缩短 `MONOTONIC_RAW` wrapper 深度；
- 让根 namespace 的 MM_data 表示方式更接近零成本，同时保持 `setns()` 语义；
- 检查 wrapper 与专用 reader 的代码布局/对齐是否造成稳定的 1-cycle 差异；
- 用 PMU/反汇编对 `MONOTONIC_RAW` 和 `MONOTONIC_COARSE` 做定点验证。

不应做：

- 删除 seq 一致性协议；
- 因为当前进程在 root namespace 就永久消除 MM_data；
- 用放宽功能或增加 fallback 换取快路径数字；
- 为追求更少 retry 而给每次 reader 增加固定分支；
- 根据单个 P99 或一次启动宣称 worst-case 改善。

### 10.4 三类正式实验的综合判断

| 实验 | 主测量边界 | 最可靠结果 |
|---|---|---|
| Standalone READ | 完整用户入口、syscall、PMU | Normal用户入口等权平均慢0.839%，典型绝对差约1 cycle |
| 空闲 UPDATE | 完整 periodic `timekeeping_update()` | Mean快1.750%，Median快3.175%，P95持平 |
| READ/UPDATE并发 | 饱和reader + 完整writer + seq分解 | odd窗口显著缩短；MONOTONIC writer Median改善；部分reader仍有固定成本 |

三类结果共同说明：

1. VKSO不是通过把成本从writer隐藏到第二套vDSO发布中获得结果；VKSO镜像没有
   native vDSO，也没有双重发布；
2. publication侧的静态缩减、空闲writer改善和odd-window缩短方向一致；
3. reader端仍然必须单独优化，因为它的调用频率远高于update；
4. 不能用空闲UPDATE的-4 cycles去抵消用户态每次调用的+1～2 cycles；
5. 不能把不同benchmark的绝对cycles直接相减得到“并发冲突成本”。

## 11. 实验边界

本报告能够支持：

- TSC 裸机上 Raw/VKSO 公开用户入口的并发读取性能；
- 完整 periodic `timekeeping_update()` 在 reader 压力下的延迟；
- seq odd/change retry 的分解；
- private snapshot 缩短 odd 窗口的运行时证据；
- 功能等价、启动条件一致的一次正式配对比较。

本报告不能单独支持：

- 所有 clock ID 的并发性能；本轮选择三个代表性时钟；
- syscall reader 的并发性能；
- PVClock/Hyper-V 的运行时结论；
- 多 socket/NUMA 或不同微架构上的 cache-line 成本；
- 15 轮等价于 15 次独立启动；
- 严格 worst-case latency；
- 把 seq observer 的 cycles 直接当成完整 `clock_gettime()` cycles。

论文中必须同时报告绝对 cycles 和百分比。尤其 `COARSE` 的 20.35% 实际是
约 2.045 cycles，不能只展示百分比。

## 12. 复现实验

进入目录：

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/update-bench
```

Raw：

```bash
./boot-raw-update.sh
# 重启后
sudo ./collect-update-concurrent.sh
```

VKSO：

```bash
./boot-vkso-update.sh
# 重启后
sudo ./collect-update-concurrent.sh
```

`collect-update-concurrent.sh` 默认设置：

```text
BENCH_SCOPE=concurrent
STABILIZE_SECONDS=120
REPEATS=15
UPDATE_SECONDS=15
WARMUP=100000
SEQ_ITERATIONS=50000000
```

Raw 第一轮创建 run ID，VKSO 第二轮自动复用同一 ID 并生成：

```text
update-comparison.csv
CONCURRENT_SUMMARY.md
raw/writer-rounds.csv
raw/reader-rounds.csv
vkso/writer-rounds.csv
vkso/reader-rounds.csv
```

本报告正式数据：

```text
results/20260728T043508Z-update-concurrent/
```

## 13. 可用于论文的最终表述

建议把结论表述为：

> 在 Intel NUC 裸机、Linux 5.15.198 和 TSC clocksource 上，VKSO
> private/shared 两阶段发布将 HRES 和 RAW seq 重试分别降低 93.18% 和
> 95.24%，其中 odd-seq 自旋减少约 99%，证明先派生私有快照、再短时间发布
> shared_data 能显著缩短 reader 不可读窗口。与公开 reader 并发时，完整
> `timekeeping_update()` 的典型延迟在三个饱和读取场景中低 5～12 cycles；
> 其中两侧吞吐最接近的 MONOTONIC 场景低 12 cycles，是最有力的等强度近似
> 证据。
> 用户态读取方面，`CLOCK_MONOTONIC` 与 raw vDSO 基本持平，
> `CLOCK_MONOTONIC_RAW` 和 `CLOCK_MONOTONIC_COARSE` 分别多约 1.49 和
> 2.04 cycles。由于 Raw retry 原本低于万分之一，减少 retry 对平均读取成本的
> 贡献不足 0.005 cycle，不能抵消 wrapper、显式 MM_data/context 和 namespace
> 判断的每次固定成本。因此 VKSO 已验证发布侧和并发一致性优势，但最终
> reader 优化重点应转向固定入口路径，而不是继续压缩 retry。

## 14. 最终结论

1. 本轮配对并发实验数据完整、条件一致、功能正确；
2. VKSO 将 HRES/RAW retry 减少 **93%～95%**；
3. odd-seq 自旋减少约 **99%**，直接验证短发布窗口设计；
4. 三个公开 reader 并发场景下，VKSO writer Median 改善
   **3.76%～8.57%**，但RAW/COARSE场景的饱和calls/s并不相等；
5. writer Mean/P95/P99 不是所有场景都改善，因此不能宣称全面尾延迟优势；
6. `CLOCK_MONOTONIC` reader 基本持平；
7. `CLOCK_MONOTONIC_RAW` reader 慢 **1.488 cycles / 2.87%**；
8. `CLOCK_MONOTONIC_COARSE` reader 慢 **2.045 cycles / 20.35%**；
9. retry 优势无法抵消固定 reader 成本，因为 retry 概率本来就极低；
10. 当前 VKSO 的核心设计方向成立，下一步若继续优化，应只针对
    wrapper/MM_data 固定路径，并严格保持功能与 namespace 语义。

因此，本次并发实验的最终评价是：

**VKSO 已经证明能以更紧凑的 shared_data 发布协议降低内核 writer 的典型
竞争成本，并显著缩短 seq 不可读窗口；它没有因新的共享结构造成更多 retry。
当前尚未全面超过 raw vDSO 的部分集中在用户态每次调用的固定入口成本，而非
发布同步机制本身。对MONOTONIC_RAW的精确固定成本来源，以及等calls/s条件下
RAW/COARSE writer的纯竞争差值，仍需单变量实验才能进一步拆分。**
