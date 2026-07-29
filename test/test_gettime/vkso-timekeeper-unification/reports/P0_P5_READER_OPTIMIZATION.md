# VKSO reader P0～P5 优化记录

## 1. 范围与实施规则

本轮优化以 `vkso-raw-reader-p0-p2` 分支为实验分支。P0～P2进入实现与
功能验证；P3～P5只记录设计，不提前混入代码。每一项后续优化必须使用独立
提交，同时保留优化前镜像和结果，不能用后续补丁掩盖无效优化。

- P0提交：`f30a419`；
- P1/P2提交：`ecf393e`。

共同约束：

- Raw与VKSO必须使用相同的测试调用边界；
- 外部syscall ABI和`__vkso_*` ABI不变；
- shared-data ABI v11和MM_data ABI v3不变；
- 共享core不得执行syscall或访问`k_clock`；
- TSC、PVClock和Hyper-V语义必须完整保留；
- time namespace、动态clock、CPU/alarm clock及无效ID语义必须与Raw一致。

## 2. P0～P2

### P0：统一测试调用边界

Raw的`__vdso_*`与VKSO的`__vkso_*`均在初始化阶段解析为
`user_time_functions`函数指针。计时循环只通过同一个函数指针槽间接调用，
不再让Raw走函数指针而VKSO走PLT。

静态验收：

- benchmark使用`-Wall -Wextra -Werror`构建通过；
- `invoke()`反汇编中用户路径只包含`call *user_time.*`；
- timed region不再引用`__vkso_*@plt`。

### P1：单一global clock reader

七个clock类型专用reader替换为
`vkso_clock_gettime_common(clock_id, value, mm_data, context)`：

- 一处完成global clock分类；
- 高精度clock共用一份seq/cycles/base/mult/shift换算；
- coarse clock共用一份seq读取；
- `mm_data == NULL`明确表示kernel root namespace读取；
- 非NULL MM_data只对mask选中的monotonic/boottime类clock应用offset；
- 非global clock返回`VKSO_TIME_BACKEND_REQUIRED`；
- cycles provider不可用返回`VKSO_TIME_UNSUPPORTED_MODE`。

该core不执行fallback，因此仍可由kernel和user共同映射执行。

### P2：单一冷fallback

用户`__vkso_clock_gettime`只调用一次common reader；任何非零状态均进入
唯一的`clock_gettime` syscall出口。

kernel dispatcher只调用一次common reader；唯一冷出口按状态选择：

- `VKSO_TIME_UNSUPPORTED_MODE`：读取private timekeeper，随后补MM offset；
- `VKSO_TIME_BACKEND_REQUIRED`：进入原有`k_clock` backend；
- 未知状态：返回`-EINVAL`。

这保证provider失败不会通过`k_clock`再次进入同一shared reader，也保证
CPU、alarm、dynamic/PTP和无效ID仍由原有backend维持语义。

### P0～P2当前证据

- 完整kernel、模块、libkernel.so和benchmark构建通过；
- QEMU Raw/VKSO主矩阵各112行完全一致；
- Raw/VKSO无RTC alarm矩阵一致；
- seq并发、clocksource切换、suspend/resume、leap transition通过；
- VKSO early/IRQ/NMI/writer/kernel-reader自测通过；
- clock reader与public wrapper的符号机器码由1570 B降至655 B，
  减少915 B（58.3%）。

上述机器码变化只能证明代码紧凑；实际cycles、instructions和branches仍须
使用同机裸机交替实验判断。

## 3. P3：TSC与PV/HV环境依赖冷热拆分

### 目标

常用TSC路径不应因PVClock/Hyper-V支持而保存或搬运仅冷路径需要的context
寄存器；PV/HV功能仍必须存在。

### 不变量

- `clock_mode`和对应payload属于同一个seq generation；
- TSC继续保持有序读取；
- PV/HV page地址只能来自当前地址空间的`vkso_context`；
- provider失败必须返回`VKSO_TIME_UNSUPPORTED_MODE`；
- 不允许把用户地址写入全局shared页。

### 候选实现

将TSC换算入口与需要context的provider continuation分开。TSC hot path直接
读取计数器；只有`clock_mode != VDSO_CLOCKMODE_TSC`时才进入out-of-line
PV/HV continuation并使用context。是否拆函数由最终反汇编决定，不能仅依据
C源码结构判断。

### 验收门槛

- 默认、PVClock和Hyper-V配置静态构建通过；
- QEMU功能矩阵不变；
- 反汇编证明TSC成功路径不再为PV/HV context产生spill/reload；
- 裸机TSC reader的cycles/instructions下降，且代码增长受控；
- 无有效收益则整项回退。

## 4. P4：cycle mask路径优化

### 目标

减少常用`mask == U64_MAX`路径中的固定判断或地址/寄存器压力，同时保留有限
mask clocksource的正确回绕语义。

### 不变量

- `cycles <= cycle_last`时，U64_MAX路径必须保持Raw x86 vDSO的零delta语义；
- 有限mask必须使用`(cycles - cycle_last) & mask`；
- clocksource切换后首次读取不能产生大幅时间跳跃；
- shared ABI仍能表达合法provider所需的mask。

### 候选实现

优先比较两种独立方案：

1. 编译期provider专门化，让已证明只使用U64_MAX的TSC入口省去有限mask分支；
2. 保留统一入口，但调整分支布局或使用等价的低指令序列。

在没有完成所有可导出clocksource审计前，禁止直接删除mask字段或有限mask
路径。分支消失不等于cycles一定下降，必须以机器码和裸机PMU共同判断。

### 验收门槛

- U64_MAX正常、相等和后退counter测试通过；
- 有限mask wrap测试通过；
- clocksource switch与seq压力测试通过；
- TSC reader的cycles/instructions有可重复改善；
- update发布字节数不得无理由增加。

## 5. P5：MM_data检查融合

### 目标

只让需要namespace offset的clock支付一次MM检查；realtime、TAI和所有
kernel root reader不应加载MM payload。

### 不变量

- MM_data ABI v3和VVAR式per-MM映射保持不变；
- root namespace的`clock_mask == 0`语义保持；
- fork、exec、setns及同MM多线程必须立即看到正确offset；
- offset必须在对应mask位发布前完成，reader只能在mask命中后使用；
- 不得缓存一个会在setns后失效的“永远root”结论。

### 候选实现

以当前common reader为起点，检查clock选择、offset选择和mask测试能否合并为
一个冷分支。kernel root入口继续传NULL，使编译器可生成明确的root路径；
user入口仍传真实per-MM页。若要进一步消除root user检查，必须先设计可被
setns更新的绑定状态，不能仅在初始化时缓存`clock_mask == 0`。

### 验收门槛

- root和非root time namespace功能矩阵通过；
- fork/exec/setns/多线程压力测试通过；
- monotonic、raw、coarse和boottime offset均与Raw一致；
- realtime/TAI反汇编无MM payload load；
- root与namespace裸机结果分别报告，不能用root收益掩盖namespace退化；
- 没有稳定收益或代码明显复杂化时回退。

## 6. 后续顺序

后续按P3、P4、P5顺序逐项建立实验提交。每项先保存功能与反汇编证据，再构建
独立镜像做同机裸机测试；只有功能完整且性能或代码量收益可复算时才合入下一
项的起点。
