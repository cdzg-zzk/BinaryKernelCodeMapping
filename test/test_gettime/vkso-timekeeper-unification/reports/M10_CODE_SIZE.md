# M10 源码规模与“为何增长”审计

## 1. 结论

本次统计先由人工按语义划分文件和行区间，再由脚本做去空行、去纯注释后的
算术。脚本不决定代码归属。比较范围固定为同一组 x86-64 功能：

- `clock_gettime`、`clock_getres`、`gettimeofday`、`time`、`getcpu`；
- 七种 global clock；
- CPU/alarm/dynamic/invalid fallback；
- time namespace；
- TSC、PVClock、Hyper-V 源码能力。

当前结果不是“VKSO 增加很多”。真正的同范围结果是：

| 互斥口径 | Raw SLOC | VKSO SLOC | VKSO - Raw |
|---|---:|---:|---:|
| 运行时功能 | 801 | 1,070 | +269 |
| 运行时机制 | 546 | 316 | -230 |
| **运行时小计** | **1,347** | **1,386** | **+39（+2.90%）** |
| 功能专属构建/链接 | 158 | 57 | -101 |
| **产品功能合计** | **1,505** | **1,443** | **-62（-4.12%）** |

因此，VKSO 的运行时源码接近持平；把各自实际需要的功能专属构建/链接代码
纳入后，VKSO 总体少 62 SLOC。项目已有的通用 `make_dll`、manager 和页面替换
基础设施不计入 kernel/user 产品合计，但必须作为项目机制另行披露。

另外单列：

| 非产品主表 | Raw | VKSO | 处理 |
|---|---:|---:|---|
| 最终配置不执行的兼容桩 | 14 | 9 | 不计产品；VKSO 只剩 TIME_NS 通用桩 |
| ABI/assert/probe/内核自测 | — | 340 | 不计产品 |

专用 VKSO kernel 不再支持 `CONFIG_VKSO_TIME=n`。原来的 148 SLOC VKSO 关闭
模式、旧 global callback 和空桩已经删除；Raw/no-vDSO 由独立源码树承担。

相对本分支起点 `d89f2e5` 的 Git 物理行 churn 也解释了“看起来增加很多”的
现象：当前范围为新增 872、删除 706；其中测试文件
`vkso_time_test.c`单独新增 173、删除 4 行。排除该 T1 测试后，产品源码实际是
新增 699、删除 702，**净减少 3 个物理行**。Git churn 反映重写过程，不替代下文
Raw/VKSO 最终 SLOC 对照。

与已验证的 `4d34fc1` 基线相比，当前候选另外增加 15 SLOC，用于把
`ns >= 1 second` 的极冷归一化外提。它不增加常用 TSC 路径的动态指令，
并使目标 reader 机器码减少 160 B；是否最终保留仍由裸机结果决定。

## 2. 为什么功能代码仍比 Raw 多

逐类结果：

| 类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| U1 用户 public ABI/算法或 wrapper | 359 | 179 | -180 |
| S1 kernel/user 共享 global 算法 | — | 386 | +386 |
| K1 普通 kernel global reader | 194 | 238 | +44 |
| K2 canonical producer | — | 52 | +52 |
| K4 syscall/dispatcher | 132 | 137 | +5 |
| E1 cycles/environment provider | 116 | 78 | -38 |
| **运行时功能** | **801** | **1,070** | **+269** |

增长并不是多了一份 mult/shift/base 换算公式，而是边界代码：

1. Raw 把用户算法、clock 分派、fallback 和 ABI 入口写在一个 vDSO 实现中。
   VKSO 为了让同一 core 同时被 kernel/user 调用，显式保留了 U1 wrapper、
   S1 typed core 和 K1 kernel ABI adapter。
2. 用户 wrapper 为裸机热路径直接跳到 typed reader，没有调用统一大
   dispatcher。它减少运行时比较和间接层，但源码比“一个通用 wrapper”更展开。
3. 任意 Linux clocksource 都必须保持 kernel reader 正确。用户不能接收
   `clocksource *`，因此 VKSO 为非 TSC/PV/HV mode 保留一个 33 SLOC 左右的
   kernel-only cold private helper。
4. 普通 `ktime_get_*` 外部 ABI 不允许删除。它们已经是 shared core 的薄入口，
   但函数名、返回类型、WARN 和 export symbol 仍必须存在。

这说明“共享 core”消除了算法维护的第二份源定义，但不会让 ABI wrapper、
environment binding 和 kernel export symbol 自动消失。

## 3. Producer/publisher 并未变大

把生产和发布作为一个完整职责比较：

| 生产/发布职责 | Raw | VKSO |
|---|---:|---:|
| K2 canonical producer | — | 52 |
| K3 payload ABI + publisher | 175 | 109 |
| **合计** | **175** | **161** |

VKSO 反而少 14 SLOC。K2 不能孤立解释成“额外转换”：Raw 的
`update_vsyscall()`也必须从 private timekeeper 派生用户可读状态，只是它全部
计在 K3 中。

当前 VKSO 的数据所有权是：

- `struct timekeeper`继续保存 NTP、clocksource、suspend、fast/NMI 等
  kernel-private 状态；
- 全局只有一份 160-byte kernel-private canonical snapshot；
- 物理独立的 shared 页保存用户只读发布副本；
- real/shadow timekeeper 不再各自嵌入 canonical snapshot。

这次审计发现并修复了 M03 遗留的真实冗余：此前 real/shadow timekeeper 各自
携带 160-byte `vkso_read_state`，并随 mirror memcpy。修复后恢复原有
`monotonic_to_boot`，canonical state 只保留一份。相对修复前：

- `timekeeping.o` BSS 减少 144 bytes；
- canonical 修复本身使 `.text` 减少 160 bytes；
- 随后的不可达 reader fallback 清理再减少 291 bytes；
- 当前 `timekeeping.o` `.text` 为 12,936 bytes，BSS 为 928 bytes。

发布仍必须从 private canonical state 写入 R-- shared 页，否则只能把复杂计算
放进 shared seq 奇数窗口，增加用户 retry。当前不复制整页，只在最后以可审计
的 scalar stores 短发布所需字段。

## 4. 机制代码为什么显著减少

| 机制类别 | Raw | VKSO | 差异 |
|---|---:|---:|---:|
| C1 MM/context/namespace 映射 | 371 | 207 | -164 |
| K3 shared ABI/publisher | 175 | 109 | -66 |
| **运行时机制** | **546** | **316** | **-230** |
| G1 功能构建/链接 | 158 | 57 | -101 |

这正是项目机制复用产生的收益：VKSO kernel 只实现 time 专属 shared/MM
语义和链接边界，通用 ELF 导出、DSO 形成、页面替换与回收由项目基础设施
承担。论文中应把这 331 SLOC 的 kernel/build 减少作为机制复用结果，同时另表
披露项目基础设施，不能假装它不存在。

项目 P1 不加入上面的 kernel/user 合计。已有人工审计可单独披露为：

| P1 项目机制 | 统计性质 | 规模 |
|---|---|---:|
| shared_data R--/NX 支持 | Git 物理行 churn | +255 / -13 |
| private wrapper ET_REL/relocation/export 适配 | 人工语义 SLOC | 210 |
| 既有 `make_dll`、manager、page replacement、KRG | 复用基础设施 | 不归因给本次 time 功能 |

前两项是把项目能力扩展成可复用机制的投入，不是每增加一个 VKSO 接口都要重写
的 user/kernel 算法；因此论文应列为“一次性项目机制扩展”，不能混进 time
产品 SLOC，也不能隐去。

## 5. 本轮只保留的安全精简

- 删除 real/shadow timekeeper 中重复的 canonical payload；
- `coarse`、clocksource resolution 和 seconds 直接读取 canonical shared
  字段，删除永远不可能触发的 provider-failure 分支；
- 用原 `reserved` 位置发布 `clocksource_resolution`，保持 ABI v11 大小和
  offset 不变，同时恢复 `ktime_get_resolution_ns()`的 Raw 语义；
- 用一个可读汇编宏生成四个相同 hres veneer，生成的 wrapper 机器码逐字节
  不变；
- 删除专用 VKSO kernel 中无需求的 `CONFIG_VKSO_TIME=n` 兼容实现。

没有把 public wrapper 改成统一 generic-core call，因为那虽然还能减少源码，
却会重新增加用户热路径的参数准备、比较和 call/ret。是否改变该边界必须由
裸机性能证据决定，不能只为压低 SLOC。

## 6. 当前机器码结果

源码复用不等于编译器只生成一份机器码。当前 VKSO 为七种常用 global clock
保留 typed hres 入口，以减少用户热路径的 clock-id 比较和通用分派；这些入口
共享同一组源级原语，但会被编译成多份专门化函数体。

| 同功能机器码口径 | Raw | VKSO | VKSO - Raw |
|---|---:|---:|---:|
| 用户 public entry/wrapper | 1,515 B | 446 B | -1,069 B |
| kernel reader / shared core（含 cycles cold provider） | 982 B | 2,329 B | +1,347 B |
| **user + kernel/shared core** | **2,497 B** | **2,775 B** | **+278 B（+11.13%）** |
| publisher + timezone | 575 B | 296 B | -279 B（-48.52%） |

因此，目前“源码总体减少”与“reader 机器码增加”同时成立。真实机器码增长不是
第二份数据结构或第二套源算法，而是 typed reader 专门化展开。它是否值得保留
必须由最终裸机 read 性能决定，不能直接按 SLOC 判断。

对象级候选实验已经排除了“把所有 hres 换算合成一个大 helper”：

- 全部合并可使 `vkso_time_core.o` `.text` 从 2,744 B 降至 1,624 B；
- 仅合并 mono-mult clocks 可降至 1,816 B；
- 但两者分别在每次常用读取中增加约 10 条和 6 条动态指令，来源是参数准备、
  额外 callee-saved register 和 tail jump。

当前只保留极冷归一化外提候选：常用 `ns < 1 second` 路径动态指令不增加，
`gettimeofday` 函数体逐指令保持不变，目标 reader 机器码净减 160 B。

## 7. 构建与功能验证

- 全量 x86-64 kernel、模块、manager、libkernel.so 和实验包构建通过；
- `4d34fc1` 已验证基线包：
  `vkso-tests/baremetal/artifacts/unification-m10-source-compact`；
- 当前候选生产包：
  `vkso-tests/baremetal/artifacts/unification-m10-hres-cold`；
- 当前候选 validation 包：
  `vkso-tests/baremetal/artifacts/unification-m10-hres-cold-validation-r2`；
- production 与 validation 的 QEMU Raw/VKSO 各 112 行 ABI 矩阵通过；
- Raw/VKSO no-RTC fallback 均通过；
- validation 配置的 early、cycle-delta、NMI、IRQ、writer-context 和普通
  kernel reader 自测全部通过；
- 当前生产结果目录：
  `artifacts/validation/normal-20260729T132339Z`。

这只证明精简未改变功能，不替代 M10 裸机性能测量。

## 8. 可复算证据

- 人工语义范围：`M10_SOURCE_MANIFEST.tsv`
- 逐行统计结果：`M10_SOURCE_COUNTS.csv`
- 算术工具：`vkso-tests/code-size/count_manifest.py`
- Raw：Linux 5.15.198 官方 tarball，SHA256
  `5d4c0994580dd3bbd5ffc5fcb81c22dd305b844c9d8c7b176cc41b28f7e29743`

分类范围通过同一 view/system/file 内的行区间重叠检查；每个有效产品行只进入
一个 U1/S1/K1/K2/K3/K4/C1/E1/G1 类别。
