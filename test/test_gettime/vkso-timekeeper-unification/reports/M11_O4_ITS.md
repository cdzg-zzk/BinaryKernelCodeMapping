# M11 O4 cold backend 与 ITS 最终决策

## 1. 结论

保留两项改动：

- O4 cold backend/tail-entry：提交 `f8d5d16`；
- secondary-mapped ITS/reusable-text 修复：提交 `0c1215f`。

O4 删除了成功 read 路径为冷 fallback 支付的 wrapper 往返成本。两次独立
normal 裸机采集都显示常用接口改善或中性；冷 fallback 的小幅退化只发生在
原本就进入 syscall/backend 的低频路径。ITS 修复不改变这些 hot-path
机器码，只保证启动期改写后的相对分支仍能到达被二次映射的静态 thunk。

本轮不再继续 O5，也不需要重复 normal read 性能测试。只有后续再次修改
reader、wrapper、ITS 改写或 reusable-text 页面构造，或单独执行 O7 的
no-retpoline release gate 时，才重新进入对应裸机门槛。

## 2. 证据与可复现性

对照结果：

- O3 基线：`vkso-tests/baremetal/results/20260730T143832Z-o3-fullwidth`；
- O4 静态 thunk 候选：
  `vkso-tests/baremetal/results/20260730-its-static-thunk-candidate-read`；
- O4 通用 reusable-text 最终结果：
  `vkso-tests/baremetal/results/20260730-its-reusable-text-read`。

三批结果使用同一 CPU 2、500000 iterations、31 repeats、10000 warmup 和
100000000 次 seq 读取。最终结果中的 Raw/VKSO 测试程序 SHA-256 均为
`16dc6bdc438477596486c4e183706ecbf015e992245dd26cbe01aefae1088597`。

最终镜像是在修复尚未提交时构建，因此 manifest 记录基线提交 `0cdfef8` 和
`git_worktree_dirty=1`。这不是把未知 dirty 状态当成提交证据：镜像记录的
VKSO source-tree SHA-256 为
`411949474afc3e969c866b7f8b5d2627c5bc9ba7e2b59c3afb4e03eff308d5e2`，
提交 `0c1215f` 后同一源树复算值完全相同。提交只固化了已经测量的文件内容。

## 3. 正确性

- Raw/VKSO 两个 case 均有 `complete` 标记；
- 两侧 `functional.matrix` 均为 98 行，内容完全相同，SHA-256 均为
  `55cb60189197b7995c98325d7c519c7470f9e6051f20f679e32189c8d59c67f7`；
- 两侧 `perf.stderr` 和 `seq.stderr` 均为空；
- package `SHA256SUMS` 全部通过；
- 构造器 12 项单元测试通过，覆盖 reusable-text 清单缺失/为空时 fail-closed
  以及目标所在整页保持 native；
- 默认、TIME_NS、Hyper-V 配置和 normal/no-retpoline QEMU 验证已通过。

最终通用方案和早期静态候选的 private wrapper 页（DSO offset `0x3000`）
SHA-256 都是
`f3947cf9eaf6bdb4b33b27dd6fdb3746670b6890df83f15031cf409a498e6e09`。
关键 wrapper/shared-core 的地址和大小也相同；裸机 PMU 的成功路径
instructions/branches 完全一致。因此两批之间的 cycles 差异属于运行噪声，
不是 ITS 通用化新增的执行开销。

## 4. O4 性能

下表以 O3 的 VKSO wrapper 中位数为基线；百分比是各组接口 cycles 比值的
几何平均。静态候选和最终通用方案分别来自独立裸机批次。

| 接口组 | 静态候选 vs O3 | 最终方案 vs O3 | 成功路径 PMU 变化 |
|---|---:|---:|---|
| hres clock_gettime | -0.347% | -0.348% | 每次 -7 instructions、-2 branches |
| coarse clock_gettime | -10.655% | -8.867% | 每次 -8 instructions、-3 branches |
| gettimeofday | -5.519% | -9.706% | 每次 -10 instructions、-3 branches |
| clock_getres | -12.173% | -12.206% | realtime 约 -1 instruction/-1 branch |
| time/getcpu | -0.003% | -0.061% | 基本不变 |
| cold fallback | +0.503% | +0.742% | 只在 backend/syscall 路径增加冷分派 |

最终批次中，hres 的代表值为：

- realtime：57.200 → 57.199 cycles；
- monotonic：58.203 → 58.203 cycles；
- boottime：59.207 → 59.207 cycles；
- monotonic_raw：59.208 → 59.207 cycles；
- TAI：58.203 → 57.200 cycles。

相对同批次 Raw，最终 VKSO 的 realtime/monotonic/boottime 分别多
0.973/1.976/2.975 cycles；realtime/monotonic coarse 分别多
1.355/1.819 cycles。`gettimeofday(tv)` 与 Raw 相同，`both` 快 0.775
cycles，`null` 慢 0.073 cycles；time/getcpu 基本相同。

seq 压力结果为 Raw 43.151 cycles/read、VKSO 45.157 cycles/read。最终
VKSO case 记录到较多本地 timer interrupt，但中位数和 PMU 指令仍复现静态
候选；不能把单次 interrupt 数量差异解释为代码回归。O3 批次的 Raw hres
自身还出现过 5～9 cycles 的批次漂移，因此 O4 判断使用直接 VKSO 对照和两次
O4 复现，不使用跨批次 Raw-normalized 差分。

## 5. 代码量与可读性

O4 提交的 Git 物理行 churn 为 `+97/-67`，净增 30 行；其中包含 kernel/user
两个环境的显式 backend 契约。成功 wrapper 机器码减少 69 B，user wrapper
合计减少 16 B，共享 core 合计增加 32 B，另有 32 B thunk 只由冷路径到达。

ITS/reusable-text 提交按逻辑基线计算：

- kernel runtime：`alternative.c` 与 `vkso.h` 合计 `+29/-4` 物理行；
- DSO 构造器：`+56/-5`；
- build glue：6 行，清单：5 行；
- 单元测试：24 行；文档不计入产品运行时代码。

`alternative.c` 在精简 kernel overlay 中以完整文件首次纳入 Git，所以提交
统计显示新增 1889 行；相对上游原文件的真实逻辑差异只有 `+12/-3`。

该修复没有为每个物理页增加一段内核判断。内核只有一个通用
“指令是否位于 secondary-mapped text”谓词；新增 thunk 只需在
`reusable_text.txt` 增加符号根，构造器会校验 owner/函数类型、求 KRG 闭包并
自动映射目标所在 RX 页。相比硬编码页地址，这个边界更小，也能处理未来目标
移动到不同页的情况。

按 M10 的产品 SLOC 口径纳入 O4/ITS 后，VKSO 约 1298 SLOC，Raw 为
1505 SLOC，VKSO 仍少 207 SLOC（13.75%）。构建期校验和测试单列，不能误算成
read 热路径或内核常驻算法。

## 6. 最终判断

O4 值得保留：常用成功路径的动态指令、分支和 cycles 收益明确，代码增长集中
在可读的双环境 fallback 契约，低频冷路径退化小于 1% 左右。

ITS/reusable-text 修复也必须保留：没有它，启动期 ITS 会把 secondary-mapped
代码中的相对分支改到只在 kernel 地址空间可达的动态 thunk，最终表现为隐式
运行时崩溃。当前方案将这个二次映射约束显式化并 fail-closed，同时不改变
reader hot path。
