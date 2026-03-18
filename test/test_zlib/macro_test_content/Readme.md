# `macro_test_content` 宏观实验计划

## 1. 文档目的

本文档用于指导后续窗口在 `pigz` 场景下完成论文所需的宏观测试与结果整理。
目标不是在这里直接给出最终实验结论，而是提供一套清晰、可执行、可复现、便于留痕的实验方案。

本文档默认服务于以下工作流：

- 已经完成 `zlib_lkm` 的代码构建和 stub DSO 生成
- 已经能够得到机制侧导出的 [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)
- 已经具备 4 组待测对象对应的可执行文件：
  - `A`: `pigz`
  - `B`: `pigz_user`
  - `C`: `pigz_lkm`
  - `D`: `pigz_upstream_user`
- 已经具备 1 组补充控制对象：
  - `D_trim`: `pigz_upstream_user_trim`
- 已经具备 4 份本地实验库：
  - `B`: [libzlib_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/libzlib_user.so)
  - `C`: [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)
  - `D`: [libzlib_upstream_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/libzlib_upstream_user.so)
  - `D_trim`: [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)
- `page cache replace manager` 可以被正确启动

后续所有宏观实验结果、原始日志、`perf` 输出、CSV 汇总、结论文档，都应统一沉淀在本目录中，避免散落在其他路径。

## 2. 背景与当前状态

本项目当前的目标，不再只是比较“系统基线”和“机制版本”两组对象，而是将 `pigz` 场景中的 4 组主对象和 1 组补充控制对象统一纳入宏观实验计划：

- `A`: 旧 baseline，`pigz` + 系统 `libz.so.1`
- `B`: 用户态控制组，`pigz_user` + `libzlib_user.so`
- `C`: 机制组，`pigz_lkm` + `libzlib_lkm.so`
- `D`: 新 baseline，`pigz_upstream_user` + `libzlib_upstream_user.so`
- `D_trim`: 瘦身控制组，`pigz_upstream_user_trim` + `libzlib_upstream_user_trim.so`

这里的关键点不是单纯比较几个“都能压缩”的程序，而是把差异拆解到不同层级：

- `A -> D`：系统发行版 `libz.so.1` 与本地重编译 upstream `zlib` 的差异
- `D -> D_trim`：完整 upstream `zlib` 与瘦身 upstream `zlib` 之间，由整库规模、导出 API 和 DSO 布局带来的差异
- `D_trim -> B`：瘦身 upstream `zlib` 与 `zlib_lkm` 同源用户态副本之间的差异
- `B -> C`：相同核心实现进入机制映射路径后的额外代价
- `A -> C`：论文最终最关心的端到端差异

当前我们已经走通了“直接链接本地库”路线，而不是 `LD_PRELOAD + wrapper` 路线。按当前仓库真实状态：

- `A` 使用系统 `libz.so.1`
- `B` 直接链接 [libzlib_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/libzlib_user.so)，同时保留系统 `libz.so.1` 作为缺失少量路径时的兜底
- `C` 直接链接 [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)，同时保留系统 `libz.so.1` 兜底；机制库本身还依赖 `libshim.so`
- `D` 直接链接 [libzlib_upstream_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/libzlib_upstream_user.so)，不再依赖系统 `libz.so.1`
- `D_trim` 直接链接 [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)，不依赖系统 `libz.so.1`

此前的正确性验证已经说明：

- `B` 的本地用户态控制库已经能够正确驱动 `pigz_user`
- `C` 的机制库本身已经通过单元与集成测试，`pigz_lkm` 已可正确压缩
- `D` 的本地 upstream 重编译库已经完成 round-trip 与 bitwise 一致性检查
- `D_trim` 的瘦身 upstream 重编译库已经完成 round-trip 与 bitwise 一致性检查
- `A` 作为系统基线可直接作为参照组使用

因此，后续宏观实验的重点应转向：

- 4 组主对象的端到端耗时与吞吐
- `D` 与 `D_trim` 之间由整库规模、导出 API 和 DSO 布局引入的差异
- 压缩率与 bitstream 一致性
- 单线程与多线程下的差异
- `perf` 视角下的整体代价变化
- 用 `A/D/B/C` 的链式关系解释最终差异来自哪一层

## 3. 实验目标

后续宏观测试建议围绕下面 4 个问题展开：

1. 4 组对象是否在目标参数组合下保持正确输出，尤其是 `B/C/D`
2. 与系统基线相比，机制版的端到端性能损失或收益是多少
3. 机制版是否改变压缩率或输出 bitstream 语义
4. 观察到的性能差异更像是：
   - 做了更多工作
   - 还是同样工作做得更慢

对论文来说，这 4 个问题分别对应：

- 正确性
- 可用性
- 公平性
- 归因能力

对主对象和补充控制组，建议优先采用下面的解释顺序：

- 先看 `A -> C`，回答“系统基线和机制版最终差多少”
- 再看 `B -> C`，回答“同源控制组进入机制后多了多少代价”
- 再看 `D -> D_trim`，回答“完整 upstream 整库规模/导出 API/布局本身带来了多少差异”
- 再看 `D_trim -> B`，回答“从瘦身 upstream 重编译变成 `zlib_lkm` 同源用户态副本后，差异是否已经出现”
- 最后看 `A -> D`，回答“系统发行版 `libz.so.1` 与本地 upstream 重编译之间本身有多大差异”

## 4. 对比对象定义与边界

### 4.1 `A`：系统旧 baseline

`A` 定义为：

- 可执行文件：[pigz](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz)
- 源码边界：
  - `pigz` 可执行文件来自仓库内 `pigz-2.8`
  - `zlib` 后端不使用本仓库源码重编译，直接使用系统安装的 `libz.so.1`
- 链接边界：
  - 当前 `readelf` 显示其直接依赖 `libz.so.1`
  - 不依赖任何本地 `libzlib_*.so`
- 运行前置：
  - 不需要 `manager`
  - 不需要额外 `LD_LIBRARY_PATH`
- 实验角色：
  - 这是“真实系统环境下的旧 baseline”
  - 用来给出论文最外层的端到端参照

### 4.2 `B`：`zlib_lkm` 的用户态控制组

`B` 定义为：

- 可执行文件：[pigz_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_user)
- 本地库：[libzlib_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/libzlib_user.so)
- 源码边界：
  - 源码目录是 [zlib_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user)
  - 该目录由 `zlib_lkm` 源码复制而来
  - 只做少量用户态适配，例如分配器和共享库构建所需改动
  - 不应再引入独立的 wrapper 路线，也不应在这里改压缩算法逻辑
- 链接边界：
  - 当前 `readelf` 显示 `pigz_user` 同时依赖 `libzlib_user.so` 和系统 `libz.so.1`
  - 压缩主路径应由 `libzlib_user.so` 提供
  - 少量未覆盖的路径，例如 `inflateBack*`，仍可能由系统 `libz.so.1` 兜底
- 运行前置：
  - 不需要 `manager`
  - `RUNPATH` 已指向 `zlib_user/`，通常不需要额外 `LD_LIBRARY_PATH`
- 实验角色：
  - 用来隔离“系统发行版 `libz`”与“`zlib_lkm` 同源实现”之间的差异
  - 是 `B -> C` 机制开销分解里的直接前置对照组

### 4.3 `C`：机制组

`C` 定义为：

- 可执行文件：[pigz_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_lkm)
- 机制库：[libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)
- 源码边界：
  - 源码目录是 [zlib_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm)
  - 这里应保持为纯 `LKM/PIC` 源码工作区
  - 相比 upstream `zlib`，只保留 `LKM/PIC` 运行所必需的适配，不承载 `B` 的用户态分支逻辑
- 链接边界：
  - 当前 `readelf` 显示 `pigz_lkm` 同时依赖 `libzlib_lkm.so` 和系统 `libz.so.1`
  - [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so) 本身依赖 `libshim.so`
  - 压缩主路径由机制库提供，少量缺失路径仍可能由系统 `libz.so.1` 兜底
- 运行前置：
  - `page cache replace manager` 必须已启动，并且 mapping 已完成
  - 当前 `RUNPATH` 已包含 `so/` 与 `make_dll/`，但若运行环境被覆盖，仍可显式设置 `LD_LIBRARY_PATH`
- 实验角色：
  - 这是论文机制组的正式对象
  - `B -> C` 是估计机制额外代价的最关键对比

### 4.4 `D`：本地 upstream 新 baseline

`D` 定义为：

- 可执行文件：[pigz_upstream_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user)
- 本地库：[libzlib_upstream_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/libzlib_upstream_user.so)
- 源码边界：
  - `zlib` 源码来自 [pigz_macro/zlib-1.2.11](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/zlib-1.2.11)
  - `D` 的构建封装位于 [zlib_upstream_user/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/Makefile)
  - 目标是直接把完整 upstream `zlib` 源码编译成本地用户态动态库，而不是再走 `zlib_lkm` 的复制或机制链路
- 链接边界：
  - 当前 `readelf` 显示 `pigz_upstream_user` 只依赖 `libzlib_upstream_user.so`
  - 不再依赖系统 `libz.so.1`
- 运行前置：
  - 不需要 `manager`
  - `RUNPATH` 已指向 `zlib_upstream_user/`
- 实验角色：
  - 这是“本地重编译 upstream zlib”的新 baseline
  - 用来隔离系统发行版实现和本地源码重编译之间的差异

### 4.5 `D_trim`：瘦身 upstream 控制组

`D_trim` 定义为：

- 可执行文件：[pigz_upstream_user_trim](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user_trim)
- 本地库：[libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)
- 源码边界：
  - `zlib` 源码仍来自 [pigz_macro/zlib-1.2.11](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/zlib-1.2.11)
  - 构建封装位于 [zlib_upstream_user_trim/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/Makefile)
  - 只保留 `pigz` 实际需要的 upstream `zlib` 最小源码闭包
  - 当前导出 API 已压缩为 `pigz` 真正依赖的 15 个符号
- 链接边界：
  - 当前 `pigz_upstream_user_trim` 只依赖 [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)
  - 不依赖系统 `libz.so.1`
- 运行前置：
  - 不需要 `manager`
  - `RUNPATH` 已指向 `zlib_upstream_user_trim/`
- 实验角色：
  - 用来隔离完整 upstream 整库规模、导出 API 和 DSO 布局这一层因素
  - 是解释 `D -> B` 之前必须经过的补充控制组

### 4.6 主对象与补充控制组的差异分解方式

建议正式写报告时默认按下面方式解读：

- `A -> D`
  - 主要观察系统发行版 `libz.so.1` 与本地 upstream 重编译之间的差异
- `D -> D_trim`
  - 主要观察完整 upstream 整库规模、导出 API 和 DSO 布局本身会不会影响宏观结果
- `D_trim -> B`
  - 主要观察从“瘦身 upstream 用户态源码”切换到“`zlib_lkm` 同源用户态副本”后，差异是否已经出现
- `B -> C`
  - 主要观察机制映射、导出、跳转和运行时前置条件带来的额外代价
- `A -> C`
  - 这是论文最终需要展示的端到端主结果

### 4.7 对比原则

实验执行时应尽量保证下面这些条件一致：

- 同一台机器
- 同一套输入
- 同一组 `pigz` 参数
- 同样的线程数
- 同样的压缩级别
- 同样的重复次数
- 同样的校验流程

不要在一次实验里同时改动太多变量，否则性能差异难以归因。

## 5. 论文中的核心假设

建议后续窗口在实验时默认围绕以下假设组织分析：

### 假设 A：正确性优先

如果机制版不能稳定输出正确压缩结果，则本轮性能数据无论文价值。

### 假设 B：同源实现应减小压缩率差异

既然当前机制版压缩路径来自同源 `zlib` 提取逻辑，那么与系统 `zlib` 的压缩率差异理论上不应特别大。
如果出现明显差异，需要优先检查：

- 参数语义是否一致
- `pigz_lkm` 是否实际绑定到了目标库
- 是否有字典、flush 或 block 边界行为差异

### 假设 C：单线程与多线程的差异来源不同

- `-p 1` 更能反映压缩器核心逻辑与机制引入的纯开销
- `-p 4` 及以上更容易暴露线程调度、拼接、块边界与系统交互代价

因此，这两类结果不能混在一起解释。

## 6. 建议的实验阶段

建议分 4 个阶段推进，而不是一次性把所有 case 全跑完。

### 阶段 1：宏观正确性回归

目的：

- 确认 `B/C/D/D_trim` 在目标参数集合下稳定可用，尤其是 `pigz_lkm`

建议覆盖的最小参数集合：

- `-p 1 -6`
- `-p 4 -6`
- `-p 1 -H`
- `-p 4 -i`

每个 case 都应执行：

- 压缩
- `gzip -t`
- `gunzip -c ... | cmp -s input -`

如果这里失败，不要继续采性能数据。

### 阶段 2：宏观耗时/吞吐测试

目的：

- 获取 `A/B/C/D/D_trim` 的端到端耗时差异，并支持后续分解分析

记录项：

- `real`
- `user`
- `sys`
- 输入大小
- 输出大小
- 吞吐量（MB/s）

### 阶段 3：压缩率与 bitstream 一致性检查

目的：

- 确认不同对象之间没有悄悄改变输出语义

推荐使用 `-n` 去掉 gzip header 中的文件名和时间戳，以便直接比对输出文件：

- `A` 输出
- `D` 输出
- `B` 输出
- `C` 输出
- 在代表性 pair 上执行 `cmp -s`

并非所有 case 都必须 bitwise equal，但至少应在一组代表性 case 上做这个检查。

### 阶段 4：`perf` 宏观归因

目的：

- 辅助判断性能差异来自哪里

推荐优先做 `perf stat`，必要时再做 `perf record/report`。

## 7. 输入集规划

后续窗口需要固定一套明确的输入语料，不要临时找文件。

建议至少覆盖 4 类数据：

### 7.1 高可压缩文本

例如：

- 源码树展开后的大文本
- 日志文件
- JSON / CSV / HTML 合集

意义：

- 观察正常文本压缩场景下的吞吐与压缩率

### 7.2 中等可压缩混合数据

例如：

- 文本与二进制混合归档
- 项目目录打包后的 tar 文件

意义：

- 更接近真实工程数据

### 7.3 低可压缩数据

例如：

- 图片集合
- 已压缩文件副本
- 接近随机的数据

意义：

- 观察“几乎压不动”时机制开销是否更显著

### 7.4 大文件场景

例如：

- 统一打包后的单个大文件

意义：

- 更适合测稳态吞吐，减少启动和文件切换噪声

### 7.5 输入规模建议

建议至少有 3 档规模：

- 小规模：几十 MB
- 中规模：几百 MB
- 大规模：1 GB 左右或更高

不建议只用一个小文件做所有结论，因为那样很容易被启动开销主导。

## 8. 参数矩阵建议

宏观测试不应一上来把所有参数展开到极大，建议使用“核心矩阵 + 扩展矩阵”。

### 8.1 核心矩阵

优先执行：

- 线程数：`-p 1`、`-p 4`
- 压缩级别：`-1`、`-6`、`-9`
- 模式：
  - 默认模式
  - `-H`
  - `-i`

### 8.2 最小可交付矩阵

如果时间有限，先保证以下组合：

- `-p 1 -6`
- `-p 4 -6`
- `-p 1 -H`
- `-p 4 -i`

### 8.3 暂不建议纳入的内容

除非后续确实需要，否则宏观主实验中先不要引入：

- `-11` 或其他会切换到 zopfli 路径的参数
- 与 gzip 主压缩路径无关的格式切换实验
- 还没有通过正确性验证的边缘参数

## 9. 每个 case 的执行规范

建议对每个 case 统一采用下面流程：

1. 确认当前待测对象的运行环境有效
2. 若当前对象包含 `C`，确认 `manager` 已启动且 mapping 已完成
3. 先做 1 次 warmup，不计入最终数据
4. 正式执行 5 次
5. 每次都做正确性校验
6. 记录原始输出、日志、耗时、文件大小
7. 对 5 次结果计算平均值和标准差

如果条件允许，建议：

- 基线和机制版交替执行，而不是把基线先全跑完再跑机制版
- 避免机器同时跑其他重负载任务

### 9.1 正式开跑前的主对象与补充控制组核对项

建议在正式宏基准开始前，至少完成下面核对：

- `A`
  - 确认 [pigz](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz) 仍直接依赖系统 `libz.so.1`
- `B`
  - 确认 [pigz_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_user) 仍依赖 [libzlib_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/libzlib_user.so)
  - 同时确认系统 `libz.so.1` 仍在依赖链中，避免把当前边界记错
- `C`
  - 确认 [pigz_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_lkm) 仍依赖 [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)
  - 确认 `manager` 已启动，mapping 已完成
  - 确认 [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so) 的 `libshim.so` 依赖可被解析
- `D`
  - 确认 [pigz_upstream_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user) 仍只依赖 [libzlib_upstream_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/libzlib_upstream_user.so)
  - 确认依赖链里没有重新混入系统 `libz.so.1`
- `D_trim`
  - 确认 [pigz_upstream_user_trim](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user_trim) 仍只依赖 [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)
  - 确认 [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so) 只导出瘦身后的目标 API 集，而不是完整 upstream API 集

如果这些核对不过，不建议直接开始正式计时。

## 10. 正确性检查要求

正确性是所有性能数据的前置门槛。

### 10.1 必做检查

每个输出都应至少经过：

- `gzip -t out.gz`
- `gunzip -c out.gz | cmp -s input -`

### 10.2 推荐附加检查

在代表性 case 上使用 `-n` 后比较下列对象对：

- `A vs D`
- `D vs B`
- `B vs C`
- `A vs C`

用途：

- 用于检测 bitstream 是否一致
- 用于发现表面上“能解压”但内部编码行为已变化的问题

### 10.3 失败处理原则

如果某个 case 失败，应立即记录：

- 输入名
- 参数
- 执行命令
- 错误现象
- 是否基线通过而机制失败

并暂停后续同类 case，不要在错误状态上继续堆积数据。

## 11. 性能指标建议

### 11.1 基础指标

每个 case 应记录：

- 输入大小
- 输出大小
- 压缩比
- `real`
- `user`
- `sys`
- 吞吐量

### 11.2 建议使用 `/usr/bin/time`

建议用统一格式输出，便于后续汇总到 CSV。

### 11.3 吞吐量计算

建议统一按输入大小计算：

- `throughput = input_size / real_time`

并固定单位，例如 MB/s。

## 12. `perf` 数据建议

宏观测试中，`perf` 的定位是“辅助归因”，不是替代端到端时间。

### 12.1 `perf stat`

建议优先收集：

- `cycles`
- `instructions`
- `task-clock`
- `branches`
- `branch-misses`
- `cache-misses`
- `context-switches`
- `cpu-migrations`
- `page-faults`

从这些指标中重点观察：

- IPC 是否下降
- cache/branch 行为是否恶化
- 是否存在明显的额外系统或调度开销

### 12.2 `perf record/report`

当 `perf stat` 已经显示两边确有显著差异时，再挑选代表性 case 进行：

- `perf record`
- `perf report`

重点关注：

- `deflate`
- `fill_window`
- `longest_match`
- Huffman/trees 相关路径
- CRC 相关路径
- 机制引入的导出或跳转相关路径

## 13. 结果存放规范

本目录建议作为本轮宏观实验的统一落点。

建议使用下面的子目录结构：

- `inputs/`
  - 输入说明、输入清单、来源描述
- `raw_logs/`
  - 每次命令执行的原始 stdout/stderr
- `time_data/`
  - `/usr/bin/time` 原始结果
- `perf_data/`
  - `perf stat` / `perf record` / `perf report` 结果
- `csv/`
  - 汇总后的表格
- `correctness/`
  - 正确性检查结果
- `reports/`
  - 每轮阶段性分析结论
- `scripts/`
  - 本轮实验中实际使用的脚本

目录里的内容命名应尽量包含：

- 日期
- case 名称
- 输入名
- 参数摘要
- 基线或机制标识

例如：

- `2026-03-17_text256_p4_l6_base.time`
- `2026-03-17_text256_p4_l6_lkm.time`

## 14. 建议记录的元信息

每轮实验都建议记录一份环境信息，至少包括：

- 日期
- 机器型号
- CPU 信息
- 内核版本
- `A/B/C/D` 四个可执行文件路径
- `libzlib_user.so` / `libzlib_lkm.so` / `libzlib_upstream_user.so` 路径
- `manager` 状态
- 输入集版本
- 是否启用 `perf`

这样做的目的是让后续窗口能快速回答：

- 这批数据到底是在什么环境下测出来的
- 当前结果能不能和上一轮直接比较

## 15. 结果展示建议

论文中建议最终至少形成以下内容：

### 15.1 正确性汇总表

内容建议包括：

- 输入
- 参数
- `A/B/C/D` 是否通过
- 代表性 pair 是否 bitwise equal

### 15.2 吞吐/耗时图

建议展示：

- 单线程
- 多线程
- 不同输入类型
- 不同压缩级别

### 15.3 压缩率图或表

展示：

- 输出大小
- 压缩比
- 相对基线差异

### 15.4 `perf stat` 辅助表

展示：

- cycles
- instructions
- IPC
- cache miss
- branch miss

## 16. 风险与注意事项

后续窗口执行时应特别注意以下风险：

### 16.1 运行环境风险

- `manager` 未启动
- `LD_LIBRARY_PATH` 未设置完整
- `libshim.so` 未被正确解析
- 机制版实际没有绑定到目标库

### 16.2 输入与缓存风险

- 输入文件过小，结果被启动开销主导
- 不同对象测试顺序固定，造成温度和缓存偏置
- 测试过程中机器有其他重负载任务

### 16.3 结果解释风险

- 把 correctness 未完全确认的数据直接拿去做性能结论
- 把不同输入类型的趋势混在一起解释
- 把多线程结果当成纯压缩器差异来分析

## 17. 推荐执行顺序

建议后续窗口按下面顺序推进：

1. 固定输入集与目录结构
2. 建立正确性回归脚本
3. 跑一轮最小正确性矩阵
4. 跑一轮最小时间矩阵
5. 汇总 CSV
6. 在代表性 case 上补 `perf stat`
7. 若发现显著差异，再做 `perf record/report`
8. 写阶段性分析报告

## 18. 当前窗口给后续窗口的交接结论

当前可以默认接受以下事实继续工作：

- 4 组待测对象 `A/B/C/D` 已经被正式纳入本目录的实验计划
- `A` 是系统 `libz.so.1` 基线
- `B` 是从 `zlib_lkm` 复制并做最小用户态适配后的控制组
- `C` 是 `zlib_lkm` 经机制导出后的正式机制组
- `D` 是完整 upstream `zlib` 的本地重编译 baseline
- `pigz_lkm` 直接链接机制库路线已经跑通
- wrapper 路线已被放弃，不应作为当前宏观实验主线
- 宏观实验主目录应集中在 `macro_test_content/`
- 正确性优先，性能数据必须建立在正确输出之上
- 后续窗口的主要任务应转向正式宏观测试、数据组织和结果分析，而不是继续改动待测对象边界

## 19. 本文档的使用方式

后续窗口应把本文档视为“实验总纲”，在执行时继续补充：

- 具体输入文件清单
- 实际执行命令
- 每轮实验日期
- 每轮结果摘要
- 观察到的异常与处理过程

也就是说，本文件负责给出方向、边界和结构；
具体某一轮实验的原始数据和分析结论，应继续保存在本目录的子目录和后续报告中。
