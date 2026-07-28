# VKSO Read/Update 并发性能实验报告

## 1. 报告范围

本报告评估当前紧凑版 VKSO 在用户态 reader 与内核
`timekeeping_update()` 并发时的表现，独立回答以下问题：

1. 饱和用户态读取时，当前 VKSO reader 相对 raw vDSO 的延迟和吞吐变化；
2. reader 持续访问 shared data 时，完整 update writer 是否出现额外竞争；
3. VKSO 的 shared-data/seq 发布协议是否缩短不可读窗口；
4. retry 减少能否抵消 VKSO reader 的固定读取成本；
5. 本轮紧凑化相对旧 VKSO 是否真正改善了并发路径。

当前正式实验：

```text
run_id=20260728T102145Z-update-concurrent
result_root=test/test_gettime/vkso-tests/update-bench/results/
            20260728T102145Z-update-concurrent
package_git_commit=66e7b1ef9b0047fd2c7f87ff6019ba91e5ee8253
implementation_commit=be35a28c983f754650c2ddb3312a4e29796a2194
```

旧版对照实验：

```text
run_id=20260728T043508Z-update-concurrent
implementation_commit=9ad92a19598c52b7c28bc5bfc3f999d68edd2de2
```

本报告正文包含完整方法和适用边界，不依赖独立 reader 或 idle update 报告。
二者只在第 12 节用于交叉解释。

## 2. 核心结论

当前紧凑版通过了并发验证，值得作为最终实现保留。

- 三个公开 reader 的最大绝对差小于 `1 cycle/call`：
  - `CLOCK_MONOTONIC` 慢 `0.911 cycle / 1.745%`；
  - `CLOCK_MONOTONIC_RAW` 慢 `0.318 cycle / 0.613%`；
  - `CLOCK_MONOTONIC_COARSE` 与 raw 完全持平。
- 旧 VKSO 最明显的 coarse 并发退化已经消除：
  `12.092 → 10.046 cycles/call`，改善 `16.917%`，相对 raw 从慢
  `20.350%` 变为持平。
- 三个公开 reader 负载下，完整 writer 的多轮 Median 均比 raw 低：
  - monotonic：低 `2 cycles / 1.538%`；
  - monotonic_raw：低 `2 cycles / 1.515%`；
  - monotonic_coarse：低 `3 cycles / 2.256%`。
- writer 不能笼统表述为全分布更快：
  monotonic 场景的 Mean 慢 `3.688%`、P99 慢 `1.556%`；另外两个公开
  reader 场景的 Mean、Median、P95、P99 均改善。
- seq observer 的 retry：
  - HRES 从 `72.30` 降至 `5.42` 次/百万，减少 `92.503%`；
  - RAW 从 `72.98` 降至 `4.48` 次/百万，减少 `93.861%`。
- retry 优势来自 odd-seq 窗口缩短：
  `changed_seq` 数量基本相同，而 `odd_seq` 减少约 `97%–99%`。
- VKSO observer 每次读取仍固定多约 `1.003 cycle / 2.32%`。raw retry
  本来只有约 `0.007%`，所以降低 retry 不足以抵消每次读取都支付的固定成本。
- 所有公开 reader 均无 CPU migration、时间倒退或功能错误，Raw/VKSO
  76 项功能矩阵完全一致。

最终可表述为：

> 当前 VKSO 在 read/update 并发下保持功能正确，公开 reader 与 raw 的差距
> 收敛到 1 cycle 以内；shared seq 的 odd 窗口显著缩短，retry 减少
> 92%–94%；三个常用 reader 负载下 writer 的典型延迟降低 1.5%–2.3%，
> 但 monotonic 场景的平均延迟仍受长尾影响。

## 3. 被测对象与数据身份

### 3.1 构建身份

| 项目 | 当前值 |
|---|---|
| Kernel release | `5.15.198` |
| package Git commit | `66e7b1ef9b0047fd2c7f87ff6019ba91e5ee8253` |
| 实现 commit | `be35a28c983f754650c2ddb3312a4e29796a2194` |
| 工作树 | clean |
| 编译器 | GCC `11.4.0` |
| 编译变体 | Normal |
| update 插桩 | `CONFIG_TIMEKEEPING_UPDATE_BENCH=y` |
| 配置差异 | `implementation_selects_only` |
| raw native vDSO | present |
| VKSO native vDSO | absent |
| production test probe | absent |

镜像、源树和实验程序：

| 对象 | SHA-256 |
|---|---|
| Raw Image | `e639416310ce2b105f4560893741e0fce3fd3b3cecc24331faacc5784477895c` |
| VKSO Image | `8dccb7ac9f255b81155206ca5a9309fc8ef57a6e5d84f2a08d9e2fdb39a0cf9b` |
| Raw source tree | `fdba196b751997d68e900c4c958e9a3d1181644f6cbe6041f3d32b84a66720d0` |
| VKSO source tree | `df32187680ba910d98c58775fa8b119a1db5703e03fb9ef5c3ac6fc1422b1cb8` |
| Experiment config | `f843a7e1f59859fe00a071f5397d9c2b4d16df480b1fdee4f1d9730368797268` |
| `vkso-time-bench` | `f0fc08af8945b90f3ba37cda93482752938e1747441abe3a7d591e8fbea2ed3c` |
| `libkernel.so` | `9aa8c6d50477e40f0f8d68a4bb86076b8408e53bca14c2bb5a88df92b9bf84c9` |
| benchmark header | `095c3c20828e7b265c259e7cde8dbf986ee613ff5ecec068f709131db4dc4e55` |
| benchmark recorder | `d07856a6eacf537ee050f2abb09ac3259d1f0d42748a8aec1867965b89464517` |

Raw update 镜像与上一轮正式实验相同，VKSO 镜像来自当前紧凑实现。因此旧/新
并发实验中 raw reader 的高度一致可以作为测量路径稳定性的额外证据。

### 3.2 结果身份

结果目录：

```text
test/test_gettime/vkso-tests/update-bench/results/
└── 20260728T102145Z-update-concurrent/
    ├── raw/
    ├── vkso/
    ├── update-comparison.csv
    └── CONCURRENT_SUMMARY.md
```

关键结果哈希：

| 文件 | SHA-256 |
|---|---|
| `CONCURRENT_SUMMARY.md` | `e5702c014568a2913a4bab75724d000df18cda5a40040720a61641ba67760c7a` |
| `update-comparison.csv` | `b04557b3ee24ba77fc4410c3fcda1eaedded62fccf9eb32018234e1e9cf95479` |
| Raw `update-summary.csv` | `5e73a2acf8ca68bca6736940428cebb073c2e893220a5336a2122c107ce05ce2` |
| VKSO `update-summary.csv` | `abd78caebea4e14519b35c4f0ca2cf4c9be9dde858d96e6570949196ac533f66` |
| Raw `writer-rounds.csv` | `899b7f6a053b42d4e35381f10e7afdb8f327ede570d57d66bba4dfb2aa84bab8` |
| VKSO `writer-rounds.csv` | `ddbc6df60e8b18bf2f8584671fa860fb9896985f25ae862b5608c34335fe0546` |
| Raw `reader-rounds.csv` | `7941adbd20d83521d38d3df6d136b5a8a2956c42c10de9525e9325e97fa8d82d` |
| VKSO `reader-rounds.csv` | `e569027fcb296b80508ac78c738ff2deb4ac54a771aac947382aacf0b42ab61d` |

## 4. 测量关系

### 4.1 并发拓扑

每轮同时存在用户 reader 和真实内核 writer：

```text
隔离 CPU 2：公开用户入口或 seq observer 持续读取
                           │
                           │ shared data / seq / cache line
                           ▼
内核 periodic tick：完整 timekeeping_update()，约 250 updates/s
```

这不是只调用 `vkso_time_publish()` 的微基准。writer 样本覆盖完整
`timekeeping_update()`：

```text
start = ordered TSC
    leap/ktime 更新
    raw update_vsyscall() 或 VKSO vkso_time_publish()
    pvclock/base_real/fast timekeeper 更新
    action 与 mirror 处理
end = ordered TSC
```

正式样本的 `action` 全部为 0，没有混入 clock-set、NTP-clear 或 mirror
慢路径。记录器在结束时间戳之后写样本，因此 debugfs 记录本身不计入 cycles。

### 4.2 公开 reader

测试三个频繁使用且代表不同数据路径的接口：

| 场景 | Raw | VKSO |
|---|---|---|
| monotonic | `__vdso_clock_gettime(CLOCK_MONOTONIC)` | VKSO 标准 wrapper |
| monotonic_raw | `__vdso_clock_gettime(CLOCK_MONOTONIC_RAW)` | VKSO 标准 wrapper |
| monotonic_coarse | `__vdso_clock_gettime(CLOCK_MONOTONIC_COARSE)` | VKSO 标准 wrapper |

每轮先执行 100,000 次预热和单调性检查，再持续运行 15 秒。负载程序每
65,536 次调用才读取一次 wall time，因此主循环主要测公开用户入口。

reader 不限速，而是让每个实现以最大吞吐运行。本轮 Raw/VKSO 吞吐差异最大
只有 `1.70%`，coarse 仅差 `0.02%`，所以 writer 面临的读取强度比旧实验更
接近，但仍不能当作严格相同 QPS 的单变量 cache-line 实验。

### 4.3 Seq observer

每轮分别执行：

```text
50,000,000 次 HRES 协议读取
50,000,000 次 RAW 协议读取
```

Raw/VKSO observer 读取语义相同的字段：

```text
seq -> cycle_last/mult/shift/base -> ordered TSC -> seq recheck
```

失败拆分为：

- `odd_seq`：第一次观察时 writer 正在发布；
- `changed_seq`：读取 payload 期间 seq 发生变化；
- `retries = odd_seq + changed_seq`。

observer 用于隔离发布协议，不是完整 `clock_gettime()` 生产路径。

### 4.4 实验参数

```text
repeats=15
load_seconds=15
warmup=100000
seq_iterations=50000000
stabilize_seconds=120
cpu=2
clocksource=tsc
tsc_pair_min=33 cycles
```

两侧共同启动参数：

```text
nokaslr clocksource=tsc tsc=reliable nosmt
isolcpus=domain,managed_irq,2 nohz_full=2 rcu_nocbs=2
irqaffinity=0-1,3 idle=poll
intel_pstate=active processor.max_cstate=0 intel_idle.max_cstate=0
nmi_watchdog=0 nowatchdog audit=0
```

采集脚本还关闭 turbo，将 min/max performance 设为 100%，并使用 performance
governor。120 秒稳定等待发生在镜像/config 校验、页面替换和功能矩阵之后。

## 5. 实验有效性

| 检查 | Raw | VKSO | 结论 |
|---|---:|---:|---|
| 完成标记 | 有 | 有 | 通过 |
| 功能矩阵 | 76 项 | 76 项 | 一致 |
| 功能矩阵 SHA | `61edf4f...` | `61edf4f...` | 完全一致 |
| ABI matrix | pass | pass | 通过 |
| namespace lifecycle | pass | pass | 通过 |
| reader/writer 文件 | 60/60 | 60/60 | 完整 |
| repeats | 15 | 15 | 一致 |
| load 时间 | 15 s | 15 s | 一致 |
| 稳定等待 | 120 s | 120 s | 一致 |
| TSC pair min | 33 | 33 | 一致 |
| 公开场景典型 writer 样本/轮 | 3751 | 3751 | 一致 |
| 非零 action | 0 | 0 | 无慢路径混入 |
| CPU migration | 0 | 0 | 通过 |
| time reversal | 0 | 0 | 通过 |

两侧 `/proc/cmdline` 除 Image 名外一致，运行时 config 与 package config
逐字节相同。实验没有把普通内核、update-bench 内核或不同 CPU 隔离配置混用。

## 6. 并发 reader 结果

| 场景 | Raw cycles/call | VKSO cycles/call | 绝对差 | 差异 |
|---|---:|---:|---:|---:|
| monotonic | 52.210819 | 53.121759 | +0.910939 | +1.7447% |
| monotonic_raw | 51.855432 | 52.173102 | +0.317670 | +0.6126% |
| monotonic_coarse | 10.046920 | 10.046079 | -0.000841 | -0.0084% |

对应吞吐：

| 场景 | Raw calls/s | VKSO calls/s | 差异 |
|---|---:|---:|---:|
| monotonic | 53,687,301 | 52,775,510 | -1.698% |
| monotonic_raw | 54,055,783 | 53,734,629 | -0.594% |
| monotonic_coarse | 278,995,767 | 279,053,535 | +0.021% |

三项延迟与吞吐方向互相对应，说明结果不是除数或 wall-time 计算异常。

### 6.1 Monotonic

VKSO 慢约 `0.91 cycle`。该路径既读取高精度 shared data，又要应用
monotonic namespace offset。当前紧凑 ABI 已移除旧版通用 mode/context
间接层，但显式 MM_data 处理和 offset 相加仍是每次调用的固定工作。

这不是 seq 重试造成的：retry 极少，而且 VKSO retry 更低。剩余差距应归类为
入口、MM_data 和指令依赖链成本，而不是锁竞争。

### 6.2 Monotonic raw

VKSO 只慢 `0.318 cycle / 0.613%`，已经从旧版的 `+2.870%` 明显收敛。
RAW 不使用 time namespace offset，当前直接参数和 cycles 常用路径缩短后，
其固定成本接近 raw vDSO。

### 6.3 Monotonic coarse

两侧差异只有 `0.00084 cycle`，在实验分辨率内完全相等。旧 VKSO 的 coarse
统一 dispatch 和参数组织曾额外支付约 2 cycles；当前专用短路径消除了该成本。

因为该基线只有约 10 cycles，旧版 2-cycle 差异会显示成 20%，本轮必须同时
报告“约 0 cycle”和百分比，避免夸大。

## 7. 完整 writer 结果

### 7.1 未扣除测量开销

| 场景 | 指标 | Raw | VKSO | 绝对差 | 差异 |
|---|---|---:|---:|---:|---:|
| monotonic | Mean | 140.518 | 145.701 | +5.183 | +3.688% |
| monotonic | Median | 130.000 | 128.000 | -2.000 | -1.538% |
| monotonic | P95 | 186.000 | 180.500 | -5.500 | -2.957% |
| monotonic | P99 | 482.000 | 489.500 | +7.500 | +1.556% |
| monotonic_raw | Mean | 148.769 | 146.881 | -1.887 | -1.269% |
| monotonic_raw | Median | 132.000 | 130.000 | -2.000 | -1.515% |
| monotonic_raw | P95 | 195.000 | 180.000 | -15.000 | -7.692% |
| monotonic_raw | P99 | 502.500 | 469.000 | -33.500 | -6.667% |
| monotonic_coarse | Mean | 148.138 | 146.154 | -1.984 | -1.339% |
| monotonic_coarse | Median | 133.000 | 130.000 | -3.000 | -2.256% |
| monotonic_coarse | P95 | 197.000 | 180.500 | -16.500 | -8.376% |
| monotonic_coarse | P99 | 501.120 | 490.500 | -10.620 | -2.119% |
| seq_protocol | Mean | 152.527 | 149.041 | -3.487 | -2.286% |
| seq_protocol | Median | 128.000 | 129.000 | +1.000 | +0.781% |
| seq_protocol | P95 | 199.200 | 212.400 | +13.200 | +6.627% |
| seq_protocol | P99 | 576.320 | 561.580 | -14.740 | -2.558% |

公开 reader 三个场景中，Median 都略低于 raw；monotonic_raw 和
monotonic_coarse 的全部四个分布指标都更优。monotonic 的 Mean 与 P99
方向相反，说明少量长尾足以抬高均值，因此只能说“典型值和 P95 更快”，不能
说整个分布全面改善。

seq observer 完成 5000 万次读取所需时间不同，writer 典型样本数为 Raw 385、
VKSO 394。它不满足相同持续时间或相同 writer 样本数，writer `+1 cycle`
不宜作为强结论；该场景的主要指标是 reader retry。

### 7.2 TSC 开销

两边独立测得的最小 ordered-TSC pair 成本均为 33 cycles。扣除后绝对差不变，
百分比因为分母缩小而放大。例如 monotonic Median：

```text
Raw:  130 - 33 = 97 cycles
VKSO: 128 - 33 = 95 cycles
差值仍为 -2 cycles
```

33 cycles 不是每个样本的精确误差，因此正文使用未扣除 cycles，corrected
结果只作为测量敏感性检查。

## 8. Seq 竞争结果

### 8.1 总 retry 与固定成本

| 协议 | Raw retry/百万 | VKSO retry/百万 | retry 变化 | Raw cycles/read | VKSO cycles/read | 固定差 |
|---|---:|---:|---:|---:|---:|---:|
| HRES | 72.30 | 5.42 | -92.503% | 43.150545 | 44.153508 | +1.002963 |
| RAW | 72.98 | 4.48 | -93.861% | 43.151164 | 44.153642 | +1.002478 |

VKSO observer 的固定成本稳定多约 1 cycle。这与 standalone seq 实验一致，
说明它来自无竞争读取协议/依赖链，而不是并发 writer。

### 8.2 Odd 与 changed 分解

每轮协议执行 5000 万次；下表是 15 轮分项的中位数：

| 协议 | 后端 | odd_seq | changed_seq |
|---|---|---:|---:|
| HRES | Raw | 3435 | 180 |
| HRES | VKSO | 93 | 184 |
| RAW | Raw | 3458 | 191 |
| RAW | VKSO | 38 | 188 |

`changed_seq` 基本相同：

- HRES：180 与 184；
- RAW：191 与 188。

真正变化的是 `odd_seq`：

- HRES 减少约 `97.3%`；
- RAW 减少约 `98.9%`。

这与设计一致。VKSO 先在 private snapshot 中完成派生，随后才将 shared seq
置为奇数并复制 reader 必需字段；raw vDSO 发布需要在 reader 不可接受的 seq
窗口中维护更多发布状态。VKSO 缩短的是“writer 已进入发布、reader 只能等待”
的窗口，并没有神奇地消除 reader payload 期间恰逢新 update 的概率。

### 8.3 为什么 retry 优势没有令所有 reader 更快

Raw HRES 的 72.3 retries/百万只占：

```text
72.3 / 1,000,000 = 0.00723%
```

而 VKSO observer 的约 1 cycle 固定成本发生在每次读取。即使 retry 代价是
几十 cycles，如此低的原始概率也无法抵消每次调用的固定 1 cycle。

因此两个结论同时成立：

1. VKSO shared 发布协议在竞争语义上更好；
2. 平均 reader 延迟仍主要由无竞争快路径决定。

## 9. 与旧版并发实验比较

### 9.1 Reader

| 路径 | 旧 Raw | 旧 VKSO | 旧差异 | 当前 Raw | 当前 VKSO | 当前差异 |
|---|---:|---:|---:|---:|---:|---:|
| monotonic | 52.211 | 51.889 | -0.616% | 52.211 | 53.122 | +1.745% |
| monotonic_raw | 51.861 | 53.349 | +2.870% | 51.855 | 52.173 | +0.613% |
| monotonic_coarse | 10.047 | 12.092 | +20.350% | 10.047 | 10.046 | -0.008% |

旧/新 raw 三条路径几乎逐 cycle 相同。当前 VKSO 相对旧版：

- monotonic：慢 `2.375%`；
- monotonic_raw：快 `2.204%`；
- monotonic_coarse：快 `16.917%`。

这说明结果不是整机频率漂移。紧凑化真正改善了 RAW/coarse 路径，但当前
monotonic 的 MM_data/offset 路径比旧版多约 1.23 cycles。standalone reader
实验也观察到当前 monotonic 相对 raw 的小幅退化，所以该变化应如实保留，而
不能用总体平均掩盖。

### 9.2 Writer Median

| 场景 | 旧 Raw | 旧 VKSO | 旧差值 | 当前 Raw | 当前 VKSO | 当前差值 |
|---|---:|---:|---:|---:|---:|---:|
| monotonic | 140 | 128 | -12 | 130 | 128 | -2 |
| monotonic_raw | 140 | 128 | -12 | 132 | 130 | -2 |
| monotonic_coarse | 133 | 128 | -5 | 133 | 130 | -3 |

当前仍保持 writer Median 优势，但幅度由旧版 `5–12 cycles` 收敛为
`2–3 cycles`。idle update 实验已证明 raw Median 会在不同启动间明显移动，
所以论文应使用当前同轮结果，不再引用旧版 8.57% 作为最终实现收益。

### 9.3 Seq

| 协议 | 旧 retry 变化 | 当前 retry 变化 |
|---|---:|---:|
| HRES | -93.184% | -92.503% |
| RAW | -95.240% | -93.861% |

seq 结论跨版本稳定，说明当前 reader 紧凑化没有破坏 shared-data 的短 odd
发布窗口。

## 10. 性能差异的实现原因

### 10.1 Reader 固定成本

当前 VKSO 复用一套导出的 core，但公开入口仍需提供显式依赖：

- shared data；
- MM_data/time namespace offset；
- 非 TSC clocksource 的 cycles context；
- 不支持 clock 的 fallback。

紧凑化已经把 MM_data 改为直接参数语义，并将 cycles context 判断移到真正
需要的冷路径。结果是 RAW/coarse 明显改善。monotonic 仍必须读取并应用
namespace offset，因此其固定依赖链没有与 root-namespace raw vDSO 完全相同。

### 10.2 Writer

Raw 与 VKSO 都执行 leap、ktime、PVClock、base_real 和 fast timekeeper 等
公共工作。主要差异仍是：

```text
Raw:  update_vsyscall()
VKSO: vkso_time_publish()
```

VKSO 将 reader 必需数据裁剪到 shared data，并在 seq 变奇数之前完成派生，
从而减少 odd 窗口。完整 writer 结果还会受到函数布局、cache line、周期性
中断和长尾影响，因此不能把全部 2–3 cycles 都机械归因于 store 数量。

### 10.3 Cache 与竞争

本实验确实让 reader 和 writer 访问同一 shared/seq cache line，但不是固定
QPS 微基准。当前三项 reader 吞吐已较接近，所以 writer 的方向具有参考价值；
若要精确分解每次 cache-line ownership transfer 的代价，还需要节流到完全
相同 QPS。该额外实验不属于当前功能验证的必要条件。

## 11. 本实验能够和不能证明的内容

能够证明：

- 当前正式 VKSO 在并发时功能正确；
- coarse 的旧固定成本已被消除；
- shared seq odd 窗口显著短于 raw；
- retry 优势在当前实现仍稳定存在；
- 三个公开 reader 负载下 writer Median 没有退化；
- 当前 reader 与 raw 的最大绝对差小于 1 cycle。

不能单独证明：

- 所有 clock ID 的并发性能，因为只选取三个代表性 reader；
- 所有 reader 都更快，monotonic 和 monotonic_raw 仍略慢；
- writer 全分布都更快，monotonic Mean/P99 方向相反；
- PVClock/Hyper-V 的运行时性能，本轮裸机使用 TSC；
- retry 减少等于应用延迟按同一比例下降；
- 每个 cycles 差都由唯一源码语句造成。

## 12. 与独立实验的关系

独立 reader 报告测无饱和 writer 压力的完整接口矩阵：

- [`VKSO_READ性能实验报告_20260728.md`](../baremetal/VKSO_READ性能实验报告_20260728.md)

独立 update-side 报告测没有用户 reader 饱和负载时的完整 writer：

- [`VKSO_UPDATE性能实验报告_20260728.md`](VKSO_UPDATE性能实验报告_20260728.md)

三类实验边界如下：

| 实验 | Reader | Writer | 回答的问题 |
|---|---|---|---|
| standalone read | 单接口延迟/PMU | 自然后台 update | 无竞争常用读取成本 |
| idle update-side | 不施加 reader load | 完整 update | writer 基础开销 |
| concurrent | 饱和公开入口/seq observer | 完整 update | 读写相互影响 |

不能将三份报告的 cycles 直接相减，因为测量循环和负载不同；应比较每份报告中
同轮 Raw/VKSO 的方向，并检查三者是否出现互相矛盾的系统性退化。

当前三者共同支持：

- reader 总体接近 raw；
- writer 没有系统性退化；
- retry 优势是真实但平均贡献很小；
- 当前剩余问题是少数 reader 的固定入口/MM_data 成本，不是锁竞争。

## 13. 最终结论

当前紧凑版完成了预期的并发验证：

1. 功能、namespace、CPU migration 和时间单调性全部正确；
2. 三个并发 reader 与 raw 的绝对差控制在 1 cycle 内；
3. coarse 旧版 20.35% 退化被完全消除；
4. 三个公开 reader 负载下 writer Median 改善 1.5%–2.3%；
5. seq retry 稳定降低 92%–94%，odd 窗口降低 97%–99%；
6. 固定 seq observer 成本仍约 1 cycle，不能被低概率 retry 优势抵消。

性能评价应到此停止，不应为了让所有单项百分比为负而重新增加通用分支或专用
fallback。后续重点应转向源码工作量和二进制规模的语义化审计。
