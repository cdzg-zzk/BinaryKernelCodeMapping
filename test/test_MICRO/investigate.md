# 如何回头做微基准测试

## 1. 总体思路：先围绕根因设计实验，再用实验解释现象

后续微基准不要再按“某个 case 为什么快了或慢了”来临时拼装。那样做很容易把不同现象都绕回同一批根因，最后虽然收集了很多数据，却很难形成稳定结论。

更合适的流程是：

- 先把潜在根因收敛成少数几类；
- 再为每一类根因设计受控实验；
- 最后用这些实验去解释宏基准里已经观察到的现象。

当前最值得围绕的根因只有三类：

- 原因 A：源码级 PIC、伪造 GOT、手工基址恢复带来的影响；
- 原因 B：用户态编译和内核态编译形成的汇编 / 代码生成差异；
- 原因 C：cold-start、缺页、映射建立等因素。

其中：

- 原因 C 已经做得比较充分；
- 原因 A 和原因 B 才是下一轮微基准的主线。

## 2. 原因 A：源码级 PIC / 伪造 GOT 改造

这一类问题要回答的是两件事：

- “伪造 GOT / 手工基址恢复”这种源码改造本身，代价到底有多大；
- 它是不是当前宏基准差异的主因。

### 2.1 比较对象

这一类比较对象固定为两组：

- `K_native vs K_pseudo`
- `U_native vs C`

两组的角色不一样：

- `K_native vs K_pseudo` 是隔离实验，是原因 A 的硬证据；
- `U_native vs C` 是真实对象的总体现象，只能作为补充，不应单独写成“PIC 改造代价”的直接证明。

### 2.2 为什么 `K_native vs K_pseudo` 必须存在

`U_native vs C` 里面混着很多东西：

- 源码级 PIC / 伪 GOT 改造；
- 用户态与内核态的编译差异；
- 真实系统里的 steady-state 执行差异。

所以它不能单独回答“PIC 改造到底值多少钱”。

只有 `K_native vs K_pseudo` 才能把变量压到最小：

- 同样的编译环境；
- 同样的执行位置；
- 同样的控制流骨架；
- 唯一变化只是“原生取址”与“伪造 GOT / 手工基址恢复”。

### 2.3 源码选择：不局限于 zlib，但也不能随便挑函数

这里不建议只从 zlib 里抽函数，也不建议在各个工程里随便挑很多不相关的函数。

更好的方式是：

- 脱离具体项目；
- 直接围绕“代码模式”设计一套通用 kernel suite；
- 让这套 suite 覆盖我们真正关心的几类访问和控制流形态。

这样做的好处是：

- 覆盖面更广；
- 结论不依赖 zlib 这一类工作负载；
- 也更适合反过来解释 zlib 宏基准。

### 2.4 建议的通用代码模式套件

建议固定做 `5` 类代码模式，每类做 `2` 个强度版本：

- `light`
- `heavy`

这样总共是 `10` 个 mini-kernel，规模可控，但覆盖面已经足够。

建议的 `5` 类模式如下。

#### 模式 1：`TableLookup`

特征：

- 循环里反复访问多个只读静态表；
- 索引来自输入数据或中间状态；
- 最终做简单累加、聚合或状态更新。

它适合观察：

- 原生静态表访问与伪造 GOT 基址恢复之间的差异；
- 多表并发访问时，寄存器压力是否上升；
- 手工 `base()` helper 会不会引入额外地址计算。

#### 模式 2：`BitstreamEmit`

特征：

- 移位、掩码、bit accumulator；
- 小型 code table；
- 短小 helper 和条件分支。

它适合观察：

- 表访问与位操作混合时的寄存器使用；
- helper 边界对栈帧和 spill/reload 的影响；
- 与 `compress_block / send_bits` 这类热点相似的访问模式。

#### 模式 3：`WindowScan`

特征：

- 滑动窗口；
- rolling state；
- 候选扫描；
- 提前退出和条件分支。

它适合观察：

- 搜索密集路径下，伪造 GOT 是否放大寄存器压力；
- 循环体较长时，地址恢复和分支布局的影响；
- 与 `deflate_fast / deflate_slow / longest_match` 相似的热点形态。

#### 模式 4：`StateMachine`

特征：

- `switch` 或多层 `if/else`；
- 配合一张或多张只读转移表；
- 状态更新和多出口。

它适合观察：

- 表访问和基本块布局一起变化时的效果；
- 用户态 / 内核态编译器对分支和块布局的不同处理方式；
- padding / NOP / 分支落点变化是否明显。

#### 模式 5：`HelperChain`

特征：

- 同一逻辑拆成 `3` 到 `5` 个小 helper；
- helper 共享只读表和局部状态；
- helper 之间有明显调用链。

它适合观察：

- prologue / epilogue；
- callee-saved 寄存器策略；
- inline / noinline 边界；
- 源码级 PIC 改造是否会改变 helper 链的成本。

### 2.5 每个 mini-kernel 的构造原则

对每一个 mini-kernel，都应同时准备两份源码：

- `K_native`
- `K_pseudo`

两者必须满足：

- 计算语义一致；
- 输入数据和输出校验一致；
- 循环结构一致；
- helper 划分一致；
- 唯一允许变化的是静态对象取址方式。

`K_native` 的要求：

- 直接使用原生静态表 / 静态对象访问；
- 不引入手工 `base()` helper；
- 不做人为的伪 GOT 包装。

`K_pseudo` 的要求：

- 只把静态表、静态 descriptor、静态 helper 的访问方式，改成 `zlib_lkm` 那种手工基址恢复写法；
- 改造风格应尽量贴近 [deflate.h](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm/deflate.h) 和 [trees.c](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm/trees.c) 里的真实做法；
- 不额外引入与问题无关的环境改造。

### 2.6 `K_native vs K_pseudo` 的执行方式

这组 mini-kernel 建议不要通过用户态共享库去跑，而是直接做成一组小型内核 benchmark 模块。

推荐做法：

- 每个模式各做一个小型 benchmark LKM；
- 模块内同时包含 `native` 与 `pseudo` 两个入口；
- 通过同一套内核侧 driver / procfs / ioctl 触发执行；
- 在模块内部完成多轮迭代；
- 用户态只负责下发参数、读取结果、调用 `perf stat`。

这样能最大限度保证：

- 编译环境一致；
- 执行位置一致；
- 比较对象只差源码级改造。

### 2.7 原因 A 的判据

若 `K_native vs K_pseudo` 在多类模式上都表现为：

- `cycles/iter` 或 `cycles/byte` 差异很小；
- `instructions/iter` 或 `instructions/byte` 差异很小；
- `IPC`、`branch-miss`、`L1I/iTLB` 没有系统性恶化；

则可以比较有力地说明：

- 源码级 PIC / 伪造 GOT 改造本身不是主因；
- 它至多是一个次要因素。

此时再看 `U_native vs C`，就更容易把剩余差异解释到原因 B。

## 3. 原因 B：用户态和内核态的汇编 / 代码生成差异

这一类问题要回答的是：

- 为什么正常用户态实现和 `C` 的实际执行效果不同；
- 这种差异是否主要来自 user/kernel 编译形成的汇编与代码布局不同。

### 3.1 比较对象

这一类比较对象固定为：

- `U_native vs C`

这里建议明确：

- `U_native` 指 [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)，也就是 `D_trim`；
- `C` 指 [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)。

这里不使用完整 `D`，是为了避免把 footprint / export / layout 这类外围因素重新混回来。

### 3.2 这一组实验回答什么，不回答什么

`U_native vs C` 不是“纯 codegen 隔离实验”。

但在当前方案里，它仍然是最有现实意义的一组比较，因为它直接对应：

- 正常用户态实现；
- 我们真正交付 / 运行的 `C`。

因此，这一组实验的任务是：

- 给出真实总差异；
- 再结合原因 A 和原因 C 的结果，去判断这份总差异里有多少最可能来自 user/kernel 的汇编与代码生成差异。

也就是说，原因 B 在写作上应表述成：

- “基于排除法和证据链的最有力解释方向”；

而不是：

- “已经唯一证明全部差异只来自汇编”。

### 3.3 执行方式

这一组建议统一使用 direct zlib API harness，而不是继续通过 `pigz`。

harness 建议固定只调用：

- `zlibVersion`
- `deflateInit2_`
- `deflate`
- `deflateReset`
- `deflateEnd`

并遵守下面这些规则：

- `dlopen()` 指定目标库；
- `dlsym()` 拿函数指针；
- `dladdr()` 校验函数确实来自目标 `.so`；
- 预先分配并预触达输入 / 输出 buffer；
- 正式测量前至少 warmup `3` 次；
- 单线程、单核固定；
- 每个点至少重复 `9` 次；
- 用 `perf stat -x, -r 9` 收集事件。

### 3.4 这组实验应保留的 workload

这里不需要再做大而全的 workload sweep，只保留最能放大差异的少数 workload：

- 主 workload：`text64M.txt + level=6 + Z_DEFAULT_STRATEGY`
- 对照 1：`random64M.bin + level=1 + Z_DEFAULT_STRATEGY`
- 对照 2：`text64M.txt + level=6 + Z_HUFFMAN_ONLY`

它们的作用分别是：

- 主 workload：放大搜索密集路径；
- 对照 1：观察非搜索主导时差异是否还明显；
- 对照 2：削弱 match-search，观察差异是否缩小。

### 3.5 原因 B 的静态证据

这一组实验必须固定收集反汇编与函数级静态证据。

重点关注这些函数：

- `deflate_slow`
- `deflate_fast`
- `longest_match`
- `fill_window`
- `compress_block`

每个函数要至少比较：

- 函数体积；
- 栈帧大小；
- `sub/add rsp`；
- spill/reload；
- padding / NOP；
- 是否存在额外间接跳转；
- 静态表访问与地址计算方式；
- 入口 / 退出布局；
- helper 调用边界。

已有可复用材料：

- [2026-03-17_bcdt_asm_report.md](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/macro_test_content/reports/2026-03-17_bcdt_asm_report.md)

### 3.6 原因 B 的动态证据

这一组实验统一收集下面这些指标：

- `real_sec`
- `cycles`
- `instructions`
- `cycles/byte`
- `instructions/byte`
- `IPC`
- `branches`
- `branch-misses`
- `cache-references`
- `cache-misses`

如果机器允许，再补：

- `L1-icache-loads`
- `L1-icache-load-misses`
- `iTLB-loads`
- `iTLB-load-misses`

只作为 sanity check 的指标：

- `page-faults`
- `minor-faults`
- `context-switches`
- `cpu-migrations`

说明：

- 这些前端与微架构指标是证据层，不是单独的原因层；
- 它们的作用，是帮助判断“差异到底像不像 codegen / 布局 / 分支组织的结果”。

### 3.7 原因 B 的判据

若 `U_native vs C` 在主 workload 上表现为：

- `instructions/byte` 没有显著减少；
- 但 `cycles/byte` 更低；
- `IPC` 更高；
- `branch-miss` 或 `L1I/iTLB` 更优；

同时原因 A 已经显示源码级 PIC / 伪 GOT 改造代价不大，
原因 C 又已排除了 cold-start / fault 主导，

则可以较有力地说明：

- 剩余差异最合理的解释，是用户态与内核态编译形成的汇编 / 代码生成差异；
- 包括更紧的栈帧、更少的 spill/reload、更少的 padding / NOP、更紧的入口 / 退出布局等。

## 4. 原因 C：cold-start / 缺页 / 映射

这一类已经做得比较充分，后续在微基准章节里只保留引用，不作为新的主线任务。

已有材料：

- [test_first_call.md](/home/zzk/BinaryKernelCodeMapping/test/test_first_call/test_first_call.md)
- [benchmark_single.c](/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/benchmark_single.c)
- [benchmark_no_ftrace.c](/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/benchmark_no_ftrace.c)
- [results_matrix_aggregated.csv](/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/results_matrix_aggregated.csv)

这条线主要负责解释：

- first-touch；
- first-call；
- file-backed minor fault；
- 映射建立早期成本。

但它不再用于解释当前 steady-state 宏基准主现象。

## 5. 所有微基准统一遵守的执行规则

无论是原因 A 还是原因 B，后续所有微基准都应遵守下面这些统一规则：

- 单线程或单核固定执行；
- 测试前先做预热；
- 每个点至少重复 `9` 次；
- 原始结果和 summary 同时落盘；
- 每次实验都保存环境信息；
- correctness 必须先通过，再谈性能。

推荐固定记录的环境信息：

- `uname -a`
- `lscpu`
- `/proc/cpuinfo` 摘要
- `/proc/sys/kernel/perf_event_paranoid`
- CPU governor

推荐固定保存的结果文件：

- `*_raw.csv`
- `*_summary.csv`
- `*_env.txt`
- `perf stat` 原始输出
- 必要时的 `objdump` / `readelf` / 反汇编摘录
- 一份简短说明报告

## 6. 为什么源码选择必须按“模式套件”做，而不是按“单个函数”做

这里最后再强调一次设计原则。

后续微基准不应走两种极端：

- 只从 zlib 中挑一个函数；
- 或者随意从不同项目里收集一堆彼此无关的函数。

更合适的做法是：

- 先抽象出核心代码模式；
- 再围绕这些模式构造一套小而全的 benchmark suite；
- 再用这套 suite 去解释 zlib 宏基准。

这套方法的好处是：

- 覆盖面更广；
- 结论更有普适性；
- 变量更容易控制；
- 更适合说明“我们的方法到底对哪类代码模式敏感”。

## 7. 建议的实验优先级

建议按下面顺序推进。

### 第一优先级

- 完成原因 A 的 `K_native vs K_pseudo` 通用模式套件；
- 先把“源码级 PIC / 伪 GOT 改造本身值多少钱”量清楚。

### 第二优先级

- 完成原因 B 的 `U_native vs C` direct zlib API 微基准；
- 结合已有汇编证据，把真实对象差异与 codegen 差异联系起来。

### 第三优先级

- 只在需要补强 cold-start 论证时，再回头引用或补充原因 C；
- 当前不作为主线任务。

## 8. 最终希望形成的证据链

最终希望形成下面这条收束链路：

1. 宏基准先说明：`C` 在特定搜索密集 workload 上存在稳定差异。
2. 原因 C 说明：这不是 cold-start / first-touch 主导的现象。
3. 原因 A 说明：源码级 PIC / 伪 GOT 改造本身代价有限，不足以单独解释全部差异。
4. 原因 B 再说明：真实对象 `U_native vs C` 的剩余 steady-state 差异，最有力的解释是用户态与内核态编译形成的汇编 / 代码生成差异。

这样最后得到的就不是一句模糊的“实现不同所以性能不同”，而是一条更清楚的因果链：

- 哪些差异来自源码级改造；
- 哪些差异来自 user/kernel codegen；
- 哪些只是 cold-start；
- 哪些不是当前主因。
