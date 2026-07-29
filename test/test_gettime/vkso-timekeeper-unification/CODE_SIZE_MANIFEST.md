# 代码规模语义清单

## 1. 用途

本文件定义 Raw/VKSO clock/time 功能的人工语义统计边界。脚本只能对本清单
确认的文件、符号或行区间求和，不能自动决定代码归属。

M00 先冻结旧报告口径；M01 补齐符号级所有权；M08 删除旧实现后重新审计；
M10 生成最终源码和机器码数字。

## 2. 统计规则

### 2.1 产品运行时代码

计入：

- 对目标 clock/time ABI 的实际成功路径和 fallback；
- global-time shared algorithm；
- kernel producer/private 状态中仅为目标读取语义必需的部分；
- publisher、shared ABI、MM_data 选择和必要映射接入；
- user ABI wrapper；
- CPU/alarm/dynamic 等目标 ABI 必需 backend 边界；
- PVClock/Hyper-V 源码支持；
- 最终启用配置需要的构建/链接胶水。

不计入产品运行时代码、但单独披露：

- `static_assert`、编译期 layout 验证；
- `CONFIG=n` stub；
- benchmark、probe、QEMU/裸机脚本和报告；
- 通用 `make_dll`/manager/page-cache 项目基础设施；
- x32、IA32、legacy vsyscall 和本实验明确关闭的功能；
- 其他内核子系统仍使用、但目标 ABI 不再依赖的旧 reader；
- 过渡 compat/bridge 代码。

### 2.2 共享代码归属

VKSO core 位于 kernel tree 且由项目机制导出给用户执行，归为
“kernel/user shared”，不能同时计入 kernel 专属和 user 专属。

用户 wrapper 只计 ABI、context/environment 绑定和 syscall fallback。若用户
目录出现 seq、delta、mult/shift、base 或 normalize 的第二份实现，必须标记为
重复代码并在 M08 前删除。

### 2.3 源码与机器码

- SLOC：去除空行和纯注释后的有效源码行；
- Git churn：单独报告新增/删除物理行，不替代 SLOC；
- machine code：按目标 symbol 的真实 `st_size` 求和；
- 不用 `libkernel.so` 文件大小、整个 `.text` 或压缩 Image 大小代替目标符号；
- shared payload、MM payload、映射页和 ELF 元数据分别报告。

## 3. 互斥分类

| ID | 类别 | Raw 典型内容 | VKSO 目标内容 |
|---|---|---|---|
| U1 | user public ABI wrapper | `__vdso_*` entry/clock switch | `__vkso_*` wrapper、context 绑定、fallback |
| S1 | shared global algorithm | 无 kernel/user 共享机器码 | seq、delta、mask、mult/shift、base、offset、normalize |
| K1 | kernel public reader | `ktime_get_*` 目标依赖算法 | root-namespace typed 薄 wrapper |
| K2 | producer/private | 目标读取所需 timekeeper 更新 | canonical state 的直接维护 |
| K3 | publisher/data ABI | `update_vsyscall`/vdso_data | v11 header/state/scalar publisher |
| K4 | syscall/dispatcher | global `k_clock`/syscall 分派 | typed global path + cold backend |
| B1 | CPU/alarm/dynamic backend | Raw 必需后端边界 | 原语义后端边界 |
| C1 | MM/context/namespace | VVAR/timens | MM_data v3/VVAR special mapping |
| E1 | environment provider | vDSO TSC/PV/HV | kernel clocksource + user TSC/PV/HV |
| G1 | 功能构建/链接胶水 | vDSO linker/image/Kbuild | VKSO section/export/wrapper glue |
| P1 | 项目通用机制 | 不适用/既有 vDSO infra | make_dll/manager/page replacement |
| X1 | 过渡/兼容 | 不适用 | compat conversion、双 ABI、临时 bridge |
| T1 | 验证 | vDSO tests | assert/probe/QEMU/bare-metal/报告 |

任何有效行只能进入一个 ID。公共 include 或 helper 若服务多个类别，按直接语义
责任归入一个主类别，并在注释中列出消费者，不按消费者重复计数。

## 4. M00 旧实现锚点

权威旧清单：

- `vkso-tests/code-size/source-manifest.tsv`
- `vkso-tests/code-size/binary-symbol-manifest.tsv`
- `vkso-tests/code-size/incremental-source-manifest.tsv`
- `vkso-tests/code-size/VKSO开发工作量与代码规模评估_20260728.md`

旧实现的 60 SLOC `vkso_time_compat.h` 归入 `X1`。本次重构的结构目标是：

- `X1` 最终为零；
- Raw 的 user global algorithm 与 kernel global reader 重复维护，VKSO 由
  `S1` 单一源定义取代；
- `U1` 与 `K1` 只保留必要 ABI 适配，不把算法包装成多层转发；
- `K2 + K3` 只保留 producer 和最短发布，不引入第二套数据模型；
- `P1` 单列，既不能隐藏为零，也不能全部归给 clock/time 功能。

## 5. 后续补全点

M01 必须为每类补充：

- 精确文件和 symbol；
- 共享 header 的唯一归属；
- Raw/VKSO 功能对应关系；
- 其他 reader 保留代码为何不属于目标切片；
- 由同一源模板生成多份机器码时的实例数量和原因。

M08 必须确认：

- `X1=0`；
- U1/S1/K1/K2/K3/K4 无重复公式；
- 没有仅靠改名隐藏的旧实现；
- 测试和 `CONFIG=n` stub 未混入产品 SLOC。

M10 才填写最终 SLOC、Git churn、symbol bytes 和 payload bytes。
