# UPDATE 双峰诊断

这是独立的诊断运行，不属于 32 次正式 Clocktime campaign。它只使用 normal
配置的 Raw/VKSO UPDATE 内核。`start` 仍导出原来的四列正式样本；诊断命令
`diagnose` 在**计时结束后、timekeeper 锁释放前**补记状态，并单独导出当前
writer CPU 上的 4096 个空 `rdtsc_ordered` 计时对。诊断内核和正式内核的绝对
UPDATE 耗时不可直接合并。

在 `test/test_gettime/vkso-tests/baremetal/` 执行一次构建和安装。输出路径必须
尚不存在。若本地没有 Raw 源码，固定构建入口会从 Linux Kernel Archives 下载
原版 5.15.198 tarball，校验 SHA-256，缓存到 `artifacts/source-cache/`，之后
不再重复下载。无网络时也可以设置 `RAW_SOURCE` 指向已有源码，或设置
`RAW_TARBALL` 指向同一原版 `.tar.xz` 文件。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
JOBS=4 OUT="$DIAG_PACKAGE" BUILD_VARIANT=normal ../update-bench/build-update-images.sh
python3 ../update-bench/stateful.py verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
```

`--normal-only` 复用已安装的两个 normal UPDATE GRUB 条目，并只替换其镜像与
配置；旧 no-retpoline 条目不变。必须先有正式实验安装过的 GRUB 条目。
正式结果目录和旧包不会被修改。

Raw 启动（这条命令会重启）：

```bash
../update-bench/boot-update-once.sh raw-normal
```

重启后重新设置包路径，再采集。输出目录必须尚不存在。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
./experiment.sh diagnose --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-bimodal-raw-normal-boot1"
../update-bench/boot-update-once.sh vkso-normal
```

第二次重启后：

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-bimodal-normal-v1"
./experiment.sh diagnose --package "$DIAG_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-bimodal-vkso-normal-boot1"
```

建议再各启动一次，分别用 `boot2` 输出目录。每次采集是 4 个场景 × 3 轮 ×
10 秒 writer 窗口，另有稳定期和功能核验。`diagnose` 会验证实际运行的镜像、
config、boot cmdline、auxv、包、ABI、公开 API 与 VKSO 物理页；错误内核会
在计时前失败，不会把失败记录标为 COMPLETE。

全部采集后汇总；缺少某次运行时从 `--runs` 列表去掉即可。

```bash
./experiment.sh diagnose-report \
  --runs "$PWD/results/update-bimodal-raw-normal-boot1" \
         "$PWD/results/update-bimodal-vkso-normal-boot1" \
         "$PWD/results/update-bimodal-raw-normal-boot2" \
         "$PWD/results/update-bimodal-vkso-normal-boot2" \
  --out "$PWD/results/update-bimodal-report.json"
```

报告按**启动**保留每个场景的模式占比、两个模式的中位 TSC ticks、空计时对
分布、状态标记条件下的高峰比例、以及秒内相位分桶。模式边界沿用先前正式
normal 结果的谷值：Raw 120、VKSO 110 TSC ticks；这是描述性分组，不能
单凭数值边界认定 Raw/VKSO 的高低峰属于相同内部状态。若某标记在各次启动
都稳定预测高峰，下一步再做独立的分段计时诊断，验证对应阶段的耗时来源。

## 分阶段定位

上面的状态诊断已经完成：秒进位不能解释绝大多数高峰。下一轮使用同一
`experiment.sh diagnose` 入口，加 `--stage` 启用独立的分阶段采样。它需要新的
normal UPDATE Raw/VKSO 镜像；只编译这两个镜像，不需要重建 READ 或
no-retpoline 镜像。`UPDATE_STAGE_DIAG=1` 是独立 Kconfig 选项；正式 UPDATE
镜像保持关闭。每个阶段边界使用 ordered TSC，因此这轮的完整 UPDATE
耗时会受到插装影响，不能与未插装正式结果比较。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export STAGE_PACKAGE="$PWD/artifacts/update-stage-normal-v1"
JOBS=4 UPDATE_STAGE_DIAG=1 OUT="$STAGE_PACKAGE" BUILD_VARIANT=normal \
  ../update-bench/build-update-images.sh
python3 ../update-bench/stateful.py verify --package "$STAGE_PACKAGE"
sudo env NORMAL_PACKAGE="$STAGE_PACKAGE" \
  ../update-bench/install-update-grub.sh --normal-only
```

按下面顺序执行四次独立启动。每条 `boot-update-once.sh` 会重启；重启后重新
`cd` 并设置 `STAGE_PACKAGE`（或把下面的 `export` 写入登录环境）。输出目录
必须不存在，不得复用上一轮结果。

```bash
# 第一次 Raw 启动
../update-bench/boot-update-once.sh raw-normal
# 重启后
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export STAGE_PACKAGE="$PWD/artifacts/update-stage-normal-v1"
./experiment.sh diagnose --stage --package "$STAGE_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-stage-raw-normal-boot1"
../update-bench/boot-update-once.sh vkso-normal
# 重启后
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export STAGE_PACKAGE="$PWD/artifacts/update-stage-normal-v1"
./experiment.sh diagnose --stage --package "$STAGE_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-stage-vkso-normal-boot1"
../update-bench/boot-update-once.sh raw-normal
# 重启后
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export STAGE_PACKAGE="$PWD/artifacts/update-stage-normal-v1"
./experiment.sh diagnose --stage --package "$STAGE_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-stage-raw-normal-boot2"
../update-bench/boot-update-once.sh vkso-normal
# 重启后
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export STAGE_PACKAGE="$PWD/artifacts/update-stage-normal-v1"
./experiment.sh diagnose --stage --package "$STAGE_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-stage-vkso-normal-boot2"
```

```bash
./experiment.sh diagnose-report \
  --runs "$PWD/results/update-stage-raw-normal-boot1" \
         "$PWD/results/update-stage-vkso-normal-boot1" \
         "$PWD/results/update-stage-raw-normal-boot2" \
         "$PWD/results/update-stage-vkso-normal-boot2" \
  --out "$PWD/results/update-stage-report.json"
```

报告逐启动、逐场景保留完整耗时直方图，以及总耗时最低/最高四分位对应的
各段中位耗时。Raw 的第一发布段是 `update_vsyscall`，第二段是
`update_pvclock_gtod`；VKSO 的顺序相反，第二段为
`tk_publish_read_state`。阶段耗时包含 ordered TSC 边界开销，未做常数扣除。
最高/最低四分位只是探索性分组，不等于已经证明的两个内部状态。如果插装后
完整耗时不再呈双峰，就不能从这些分段数据断定原双峰的原因。

## 单边界低扰动诊断

七个阶段时间戳改变了原双峰的占比，因此不能用上一节的分段结果直接给原双峰
命名。`diagnose --split` 每次 UPDATE 只增加**一个** ordered TSC 时间戳；
同一次启动交替记录目标阶段前、后的两个边界。Raw 选择 `update_vsyscall`
前后，VKSO 选择 `base_real` 前后。每个边界窗口内都有完整 UPDATE、
边界前和边界后的原始样本；两个窗口是顺序采集，不是逐次调用配对。
只测空闲和 monotonic 读者两种场景，避免重复整个正式 campaign。

需要重新构建 normal 的 Raw/VKSO 两张 UPDATE 镜像。旧的
`update-stage-normal-v1` 包不含 split schema，不能复用。新输出路径必须不存在。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
JOBS=4 UPDATE_STAGE_DIAG=1 BUILD_VARIANT=normal \
  OUT="$PWD/artifacts/update-split-normal-v1" \
  ../update-bench/build-update-images.sh
./experiment.sh verify --package "$PWD/artifacts/update-split-normal-v1"
sudo env NORMAL_PACKAGE="$PWD/artifacts/update-split-normal-v1" \
  ../update-bench/install-update-grub.sh --normal-only
```

下面的 `boot-update-once.sh` 每次都会重启。每次重新登录后，先执行
`cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal`，再执行
对应的采集命令。不要复用已有结果目录，也不用执行 `experiment.sh begin`。

```bash
../update-bench/boot-update-once.sh raw-normal
# 重启后
./experiment.sh diagnose --split --package "$PWD/artifacts/update-split-normal-v1" \
  --case raw-normal --out "$PWD/results/update-split-raw-normal-boot1"

../update-bench/boot-update-once.sh vkso-normal
# 重启后
./experiment.sh diagnose --split --package "$PWD/artifacts/update-split-normal-v1" \
  --case vkso-normal --out "$PWD/results/update-split-vkso-normal-boot1"

# 先汇总这一对启动并检查整段分布；若双峰未保留，不必继续 boot2
./experiment.sh diagnose-report \
  --runs "$PWD/results/update-split-raw-normal-boot1" \
         "$PWD/results/update-split-vkso-normal-boot1" \
  --out "$PWD/results/update-split-pilot.json"
```

pilot 已完成。与同一次 VKSO 启动的无标记对照相比，单边界时间戳改变了
完整 UPDATE 的分布；因此停止本诊断，不执行第二对 split 启动。

## 无中间时间戳的状态诊断

无标记样本的主要簇约为 84/136 TSC ticks，单边界样本的低簇移至约
124 ticks，上部还出现 160–176 ticks。不能把单边界的前/后耗时直接
归因于原始双峰，也不能按固定时间戳开销修正。

改用 `diagnose-state-report` 分析已经收集的**无中间时间戳**样本。
它逐启动报告原始整段耗时直方图、历史谷值分组、秒相位区间、进位状态，
以及秒中段连续 UPDATE 的高低状态转移。状态是在整段计时结束后记录的；
本步骤只读现有结果，不改内核、不重启、不重新采集。输出文件必须尚不存在：

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
./experiment.sh diagnose-state-report \
  --runs "$PWD/results/update-bimodal-raw-normal-boot1" \
         "$PWD/results/update-bimodal-vkso-normal-boot1" \
         "$PWD/results/update-bimodal-raw-normal-boot2" \
         "$PWD/results/update-bimodal-vkso-normal-boot2" \
         "$PWD/results/update-split-vkso-normal-unmarked-control" \
  --out "$PWD/results/update-no-marker-state-report.json"
```

五次启动在报告中分别保留，不把不同包版本或相邻 UPDATE 样本当作独立
系统实验。报告可以检验秒进位、相位和持续性解释了多少高峰，但它不会凭
相关性宣布具体内核阶段或缓存事件为原因。如果这些状态仍不能解释双峰，
再选择针对剩余假设的诊断，避免继续插入中间 TSC。

## 无中间插装的 Intel PT pilot

现有状态报告仍不能解释多数高峰。下一轮先用 Intel PT 的硬件控制流跟踪
检查原双峰是否保持，再判断能否解码 `timekeeping_update` 内部的快慢路径。
`diagnose-pt` 只采 idle 一轮：原有整段 UPDATE 计时持续 10 秒，其中
5 秒启用 Intel PT；启用/关闭时记录样本序号，边界外的样本不用于
判断跟踪是否改变分布。跟踪只选 CPU0 的内核 `timekeeping_update` 地址区间，
不在 UPDATE 函数内部新增时间戳或探针。结果中保留原始 writer CSV、
跟踪区间、perf.data 和同一次启动的内核代码快照。先做当前 VKSO 启动的 pilot，
不要立即做 Raw 或全量测试。新的结果目录必须尚不存在。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
./experiment.sh diagnose-pt \
  --package "$PWD/artifacts/update-split-normal-v1" \
  --case vkso-normal \
  --out "$PWD/results/update-pt-vkso-normal-pilot3"
```

`pilot1` 因 perf 控制确认消息带结尾 NUL 字节而失败。`pilot2` 已录得可解码的
5 秒 PT 数据，但 perf 提前停止的非零退出码使脚本在保存 writer CSV 前退出。
两次失败目录都保留；当前版本会在停止后验证 PT 文件包含完整 AUX 数据和
目标函数调用，再接受有效记录。使用新的 `pilot3` 目录。这个命令需要在仍
运行该包的 VKSO normal 内核时执行，会调用 sudo，但不会重启或构建内核。
结束后先检查 `run.json` 的 COMPLETE、`pt-validation.json` 的 PASS、
`idle/round-00.json` 中的 `intel_pt` 范围、`idle/round-00-pt/data`
与 `pt-shape.json`。`pt-shape.json` 按同一次启动的跟踪前、跟踪中、
跟踪后分别列出完整 UPDATE 耗时直方图，并在两处开关边界各舍弃
50 个样本。先看每组 `distribution_sufficient`，再比较形状和已有
无标记对照。样本序号本身不能保证与 PT 调用逐一对齐；只有另用状态
和调用数验证配对后，才能做逐次调用的分段分析。只有双峰形状保留且
跟踪可解码，才进行 Raw pilot。Intel PT 的分支/
周期包不是逐次缓存未命中事件；即使看见慢路径，也需另证缓存或
分支预测等具体微架构原因。

### VKSO pilot3 结果（2026-09-25）

`results/update-pt-vkso-normal-pilot3` 使用已验证的 `update-split-normal-v1`
包，与 `update-split-vkso-normal-unmarked-control` 属于同一次启动。结果校验和、
包身份、功能检查、环境恢复均通过；2,500 个 CPU0 周期性 UPDATE 样本无丢失。
PT 文件覆盖 5.00036 秒，并可解码目标函数；perf 提前停止的进程退出码为
`-15`，因此以数据验证而非该退出码判断本 pilot。解码时出现两处 PT
overflow；下述分段比较排除了各 overflow 前后 50 ms。

完整 UPDATE 的两簇仍在。跟踪中 1,150 个边界外样本按历史 110 ticks
谷值分组，低簇 245 个、中位 89 ticks；高簇 905 个、中位 142 ticks。
跟踪后 1,127 个样本对应为 181 个、中位 85 ticks，以及 946 个、
中位 141 ticks。跟踪前只有 23 个可用样本，不能作为稳定对照。
同启动较早的三轮无标记 idle 结果低/高簇中位均为 85/140 ticks，
高簇比例分别为 67.2%、66.9%、69.9%；本 pilot 跟踪中、跟踪后的
高簇比例为 78.7%、83.9%。**峰的位置仍在，比例发生变化；不能说 PT
没有扰动，也不能把比例变化直接归因于 PT。**

PT 解码得到 1,250 次连续 `timekeeping_update` 调用，与 writer 样本
编号 73–1322 一一对应。分支轨迹中的 `0xffffffff8111eecd` 是
`cmp` 后的 `ja`，控制 monotonic 时间纳秒进位；该分支是否出现与对应
writer 行的 `monotonic_carry` 在 1,250 次调用中完全一致。1,249 个
完整的函数内分支序列只有两种，除这条进位分支外相同，分别出现
644 和 605 次；两组按 110 ticks 分出的高簇比例约 78.8% 和 78.6%。
因此这个可见分支**不是** VKSO 双峰的解释。PT 地址过滤仅覆盖
`timekeeping_update`，不能由此排除被调用函数内部的行为。

用 PT 的纳秒时间戳定位相邻分支区间，并按同次 writer 样本选取低簇
78–100 ticks、高簇 125–155 ticks；排除跟踪边界和两处 overflow
附近后，分别保留 225 和 541 次调用：

| 区间 | 低簇中位 | 高簇中位 | 差值 |
|---|---:|---:|---:|
| 第一次 `update_fast_timekeeper`（fast-mono 调用到下一调用） | 3 ns | 3 ns | 0 ns |
| 第二次 `update_fast_timekeeper`（fast-raw 调用到返回后分支） | 3 ns | 21 ns | 18 ns |
| 第二次调用返回后的剩余部分 | 15 ns | 15 ns | 0 ns |

宽分组（≤110 与 111–250 ticks）也把约 18 ns 的差值放在第二次调用。
上述窄分组在对应 writer 样本中的中位数为 89/138 ticks，差 49 ticks。
该调用是 `update_fast_timekeeper(&tk->tkr_raw, &tk_fast_raw)`，执行
无条件的 seqcount 更新和两个 `tk_read_base` 副本写入；`tk_fast_raw`
按 cacheline 对齐。**VKSO 双峰的主要耗时位置因此定位到 fast-raw
状态发布。** PT 时间戳是解码得到的纳秒估计，不能把 18 ns 当成正式
延迟指标，也不能据此断定具体是缓存未命中、跨核一致性还是其他硬件停顿。
Raw normal 的对应 pilot 已完成，结果见下。当前结果不应分成两个独立的
正式性能实验；若在论文中展示双峰，应同时保留每次启动的完整分布、
两簇中心及各自比例。

### Raw pilot1 与跨实现结论（2026-09-25）

`results/update-pt-raw-normal-pilot1` 与 VKSO pilot 使用同一个包的
Raw/VKSO 镜像。Raw 结果校验和、包身份、功能检查、环境恢复均通过；
2,500 个 CPU0 周期性 UPDATE 样本无丢失。PT 覆盖 5.00038 秒、
可解码 1,250 次 `timekeeping_update`；也有两处 overflow，下述
分段分析排除各 overflow 前后 50 ms。PT 的调用序列对应 writer
编号 84–1333；相邻偏移与整段耗时相关性远低于该偏移。

Raw 跟踪期间的 1,150 个边界外样本，以历史 120 ticks 谷值分组，
低簇 767 个、中位 104 ticks；高簇 383 个、中位 150 ticks。
跟踪后 1,116 个样本对应为 782 个、中位 100 ticks，以及 334 个、
中位 144 ticks。同启动的跟踪前只有 34 个可用样本。此前两次独立
Raw 无标记启动的低/高簇中位约为 100/136 与 99/136 ticks，
高簇比例 30.1% 和 28.7%；本 pilot 跟踪中/后为 33.3% 和 29.9%。
峰和比例均不可直接当作无扰动正式结果，尤其高峰位置发生了偏移。

Raw 的 1,249 个完整 `timekeeping_update` 函数内分支序列完全相同，
所以 Raw 双峰也不是该函数内部两条显式分支路径。按 writer 样本的
低簇 90–110 ticks、高簇 130–155 ticks 分组，并排除跟踪边界、
两处 overflow 附近后，分别保留 672 与 213 次调用：

| 区间 | Raw 低簇中位 | Raw 高簇中位 | 差值 |
|---|---:|---:|---:|
| 第一次 fast-mono 调用之前 | 14 ns | 15 ns | 1 ns |
| 第一次 fast-mono 调用 | 5 ns | 4 ns | −1 ns |
| 第二次 fast-raw 调用 | 3 ns | 18 ns | 15 ns |
| 第二次调用返回后的剩余部分 | 14 ns | 14 ns | 0 ns |

该窄分组对应 writer 中位数为 103/146 ticks，差 43 ticks。
Raw 与 VKSO 的 `update_fast_timekeeper` 函数均为 122 字节，机器码
逐字节相同；`tk_fast_raw` 在两个镜像里都按 cacheline 对齐。
**在这两次保留双峰形状的 PT pilot 中，快慢耗时差都主要出现在发布
fast-raw 状态的同一调用中，而不是各自不同的 vDSO/VKSO 发布步骤。**
PT 只能把耗时定位到
这段无条件的 seqcount/数据副本写入；当前证据尚不能区分缓存行
所有权转移、缓存容量/索引冲突、写缓冲或其他微架构停顿。
Raw/VKSO 高峰比例不同也不能单凭这两个 PT pilot 归因于物理共享；
PT 对峰值或比例的扰动也使原始无跟踪双峰的同一成因仍属强证据推断，
不是严格证明。应以原来未跟踪、按启动汇总的结果进行性能比较。

### 缓存行共享干预

PT 把额外耗时定位到 `update_fast_timekeeper(&tk->tkr_raw,
&tk_fast_raw)`，但还不能区分缓存行所有权转移、本核缓存冲突等原因。
`diagnose-cacheline` 不改内核镜像或 writer 计时点；同一次启动顺序采集
基线、CPU1 读取静态 `linux_banner` 的负载对照、CPU1 读取
`tk_fast_mono` 的共享对照、CPU1 读取 `tk_fast_raw` 的干预、末尾基线。
VKSO 启动交换 mono/raw 两组顺序。读取通过只读 `/proc/kcore` 完成，
从运行中 `/proc/kallsyms` 和 ELF 程序头解析目标地址，且每个 8 秒 writer
窗口内至少记录三次读者活动进度。运行前仍验证包、当前内核、ABI、公开
API 和物理共享。每组保留完整 UPDATE CSV、校准 CSV、读者日志及形状汇总。
它是诊断数据，不能合入正式性能结果。

当前 Raw normal UPDATE 启动上先执行：

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-split-normal-v1"
./experiment.sh verify --package "$DIAG_PACKAGE"
./experiment.sh diagnose-cacheline --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-cacheline-raw-normal-pilot2"
```

Raw 的 `run.json` 为 `COMPLETE` 后切换到 VKSO normal UPDATE 启动：

```bash
../update-bench/boot-update-once.sh vkso-normal
# 重启后重新进入 baremetal 目录：
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
export DIAG_PACKAGE="$PWD/artifacts/update-split-normal-v1"
./experiment.sh diagnose-cacheline --package "$DIAG_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-cacheline-vkso-normal-pilot1"
```

先对照每个结果目录的 `cacheline-shape.json` 与
`*/round-00-kcore-reader.log`。若两个基线稳定、静态读取不改变慢簇，而
raw 读取使慢簇比例显著增加，则支持目标缓存行受跨核共享影响；
mono 读取也可能拖慢完整 UPDATE，因为它同样被 writer 更新，不能把
mono 对照变慢简单解释成普通后台负载。这项主动干预仍不能证明**原本**
双峰由自然运行时的跨核读取引起，也不能量化具体 RFO/HITM 次数。
任何一种情形都要先核查基线前后漂移、完整直方图和读者进度，
再决定是否增加定向硬件事件采样。`/proc/kcore` 或 root 可见内核符号不可用时，
入口会明确失败，不会生成完成状态。

`update-cacheline-raw-normal-pilot1` 已执行到 `static-read`，但旧版收集器
在保存读者元数据时重复创建已有的 `round-00.json`，故 `run.json` 是 `FAIL`；
内核模块已恢复。该不完整目录保留作错误记录，不作为诊断结果。
修复后 Raw 重跑使用上面的 `pilot2` 新目录。

### Raw pilot2 / VKSO pilot1 结果（2026-09-25）

`results/update-cacheline-raw-normal-pilot2` 与
`results/update-cacheline-vkso-normal-pilot1` 分属两次正确的 UPDATE normal
启动。两组 `run.json` 均为 `COMPLETE`、环境恢复为 `PASS`，结果目录校验和
全部通过；每个窗口恰有 2,000 个 CPU0 周期性 UPDATE 样本，丢失数为零。
三个读取场景均记录了 8 次位于 writer 窗口内的读者进度；两次启动、五个
窗口的空计时对中位数均为 37 TSC ticks。下表的比例只是样本超过历史谷值
（Raw 120、VKSO 110 ticks）的比例，主动读取后不能把它直接称为原始
“高峰状态”的概率。

| 启动 | 场景 | UPDATE 中位 ticks | 超过谷值 | 低侧中位 ticks | 高侧中位 ticks |
|---|---|---:|---:|---:|---:|
| Raw | 前基线 | 105 | 38.35% | 100 | 154 |
| Raw | 静态读取 | 113.5 | 31.05% | 112 | 144 |
| Raw | fast-mono 读取 | 152 | 100% | — | 152 |
| Raw | fast-raw 读取 | 162 | 100% | — | 162 |
| Raw | 后基线 | 130 | 54.55% | 102 | 148 |
| VKSO | 前基线 | 136 | 67.90% | 85 | 142 |
| VKSO | 静态读取 | 135 | 65.10% | 85 | 167 |
| VKSO | fast-raw 读取 | 146 | 100% | — | 146 |
| VKSO | fast-mono 读取 | 146 | 100% | — | 146 |
| VKSO | 后基线 | 138 | 60.35% | 83 | 156 |

**干预结论：**跨核持续读取任一被更新的 fast 状态，足以使完整 UPDATE
分布移到原历史谷值之上；只读取静态内核数据没有产生这种整体迁移。
这说明 fast 状态发布对跨核共享敏感，与缓存行所有权成本相容。
它没有证明原始双峰由自然发生的跨核读取造成：Raw 前后基线的高侧占比
从 38.35% 漂移到 54.55%；静态读取也改变 Raw 低侧和 VKSO 高侧的
中心；mono/raw 两组是顺序采样，不能从 Raw 的 152/162 ticks 差值
推断 raw 发布本身比 mono 发布多 10 ticks。现有内核源码中，正常收集
路径没有持续调用 `ktime_get_raw_fast_ns()` 的已知读者。

因此论文中的原始双峰仍需按各次启动的完整分布报告，不能拆成两个
经证明的内部状态。若要给出微架构原因，下一步先在**不主动读取 fast
状态**的原始窗口里，筛查 writer CPU 的 RFO/L2 与跨核 HITM 事件；
若有信号，再尝试将事件定位到单次慢调用。单纯重复上述主动干预
不会补上这个因果环节。

### PMU 窗口筛查（部分试跑，暂不重复）

`diagnose-pmu` 复用同一个已安装的 normal UPDATE 包，不编译内核。
它重采五个窗口，并在每个 writer 窗口同步启停 CPU0 的三个硬件计数器：
`l2_rqsts.rfo_hit`、`l2_rqsts.rfo_miss` 和
`ocr.demand_rfo.l3_hit.snoop_hitm`。perf 控制线程固定在 CPU3，
主动读取线程仍固定在 CPU1。第一和最后一个窗口无主动读者；静态读取
提供后台负载对照，fast-raw/mono 读取提供受控干预。每个窗口输出原始
UPDATE 样本、`round-00-pmu.csv`、`round-00-pmu.log`、
`round-00-pmu.json`，并汇总到 `pmu-window-report.json`；脚本拒绝未计数、
复用不充分或时长不足的硬件事件。

下面保留该入口的执行形式供复核；根据本节末尾的试跑分析，当前不建议
立即重复相同窗口。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_PACKAGE="$PWD/artifacts/update-split-normal-v1"
./experiment.sh diagnose-pmu --package "$DIAG_PACKAGE" --case vkso-normal \
  --out "$PWD/results/update-pmu-vkso-normal-pilot2"
```

只有 `run.json` 为 `COMPLETE` 后再切换 Raw：

```bash
../update-bench/boot-update-once.sh raw-normal
# 重启、重新登录后
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_PACKAGE="$PWD/artifacts/update-split-normal-v1"
./experiment.sh diagnose-pmu --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-pmu-raw-normal-pilot1"
```

这些是**整个 CPU0** 在窗口内的事件计数，与同时采集的 UPDATE 分布
按窗口对应，并不是每次 `timekeeping_update` 的事件数，也不能直接把
CPU0 上的其他活动归到 fast-raw 写入。特别是 HITM 只涉及其他核持有
已修改数据的情形；受控的只读线程可能持有共享副本，因此 HITM 为零
不等于所有跨核一致性流量均为零。这轮的用途是筛查假设，不能直接给
每个快/慢样本命名。若自然基线与阳性干预的计数不能形成可解释的差异，
不应继续重复相同窗口；应转向单次调用级别的定向插装，或在论文中
保留未归因的双峰分布。

`results/update-pmu-vkso-normal-pilot1` 完成了前基线、静态读取、fast-raw
读取三个窗口，每组 2,000 个无丢失 UPDATE 样本，计数器运行比例均为
100%、计数时间约 8.02 秒；`raw-share` 的完整计数 CSV 已写出。但旧版
收集器把 perf 在受控 SIGINT 后的非零退出码直接当作失败，因此未进行
最后两组，`run.json` 为 `FAIL`，环境恢复为 `PASS`。该目录的校验和
全部通过，作为不完整试跑保留，不作为正式证据。收集器现已改为先验证
计数及覆盖时间，并保留 perf 退出码作元数据。

| VKSO 窗口 | 超过 110 ticks 的 UPDATE 比例 | L2 RFO hit | L2 RFO miss | RFO HITM |
|---|---:|---:|---:|---:|
| 前基线 | 64.05% | 18,516 | 55,240 | 1,587 |
| 静态读取 | 68.30% | 21,892 | 51,671 | 1,285 |
| fast-raw 读取 | 100% | 32,868 | 104,096 | 2,006 |

CPU0 整体每窗有数万次 RFO miss，而 UPDATE 只有 2,000 次；fast-raw
干预相对静态读取多出的 52,425 次 miss 也远超过目标写入次数。
这些计数显然包含大量非目标活动，不能把基线慢簇归因为 fast-raw
的 RFO miss 或 HITM。窗口级筛查已达到其分辨率上限，故**暂不要求重跑
pilot2 或 Raw 对照**；要继续查具体原因，应先设计能够将事件与单次
UPDATE 对齐的采集方式。

### 计时前缓存行准备：Raw normal 单镜像试验

`diagnose-cacheprep` 在同一次 Raw normal 启动中顺序采五个 8 秒窗口：
前基线、控制缓冲区准备、`tk_fast_raw` 准备、控制缓冲区准备、后基线。
准备动作在 UPDATE 起始 TSC 之前执行：对相隔 64 字节的两条缓存行各
做一次值不变的锁定 OR 操作。控制组对独立缓冲区做完全相同的操作。
运行期间没有另一个核持续读取 fast 状态。该动作会主动改变目标行的
缓存所有权，只用于因果诊断；结果不能并入正式 Raw/VKSO 性能比较。

专用配置 `CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG` 仅在这个 Raw 诊断
镜像中启用。正式 UPDATE 镜像仍从原来的计时入口开始，不执行准备动作，
也不分配控制缓冲区。新包的 manifest 标为 `raw_cacheprep_diagnostic=1`，
正式 campaign 会拒绝它。第一次若没有对应 Raw Kbuild 缓存，仍需完整
编译 Raw 一次；之后相同源码和配置复用缓存，只编译有变化的对象。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_BASE="$PWD/artifacts/update-split-normal-v1"
DIAG_PACKAGE="$PWD/artifacts/update-cacheprep-raw-normal-pilot"
JOBS=4 UPDATE_CACHE_PREP_DIAG=1 ../update-bench/build-update-images.sh raw-normal \
  --package "$DIAG_BASE" --out "$DIAG_PACKAGE"
./experiment.sh verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
../update-bench/boot-update-once.sh raw-normal
# 重启、重新登录后：
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_PACKAGE="$PWD/artifacts/update-cacheprep-raw-normal-pilot"
./experiment.sh diagnose-cacheprep --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-cacheprep-raw-normal-pilot1"
```

采集器先验证镜像、配置、ABI、公开 API 与模块状态，结果为
`results/update-cacheprep-raw-normal-pilot1/cacheprep-shape.json` 和各窗口的
原始 `round-00.csv`。先检查前后基线及两个控制窗口是否保持可比较的
双峰；只有在它们稳定而 `fast-raw` 窗口特异地改变慢簇时，才能把
`tk_fast_raw` 行状态当作有力的原因证据。单次启动仍只是 pilot，若信号
明确，再用独立启动复核；若基线或控制组同步变化，就保留“已定位到
fast-raw 更新阶段、微架构原因未定”的结论。目标准备若没有效应也不能
单独排除缓存行机制：在到达 fast-raw 更新前，目标行状态仍可能再次变化。

`results/update-cacheprep-raw-normal-pilot1` 已完成一次 Raw normal 独立启动。
`run.json` 为 `COMPLETE`、`environment_cleanup=PASS`；结果和包校验和
匹配，ABI、公开 API 与 fast-path 检查通过。五窗各有 1,999–2,001 个
CPU0 周期性 UPDATE 样本，无丢失；空 TSC 对的最小值均为 33 ticks，
中位数均为 37 ticks。以下高侧占比仅按旧 Raw 谷值 120 ticks 划分，
并非已识别的硬件状态。

| 顺序窗口 | 中位 TSC ticks | 高侧样本 / 总数 | 高侧占比 | 低侧中位 | 高侧中位 |
|---|---:|---:|---:|---:|---:|
| 前基线 | 105 | 772 / 1,999 | 38.62% | 100 | 146 |
| 控制准备 1 | 100 | 192 / 2,000 | 9.60% | 99 | 138 |
| fast-raw 准备 | 99 | 149 / 2,001 | 7.45% | 99 | 138 |
| 控制准备 2 | 101 | 544 / 1,999 | 27.21% | 99 | 132 |
| 后基线 | 115 | 959 / 2,000 | 47.95% | 101 | 149 |

目标准备与前一控制窗口仅差 1 tick 中位数及 2.15 个百分点的高侧占比；
两者的低侧和高侧中心几乎相同。对照操作本身也大幅降低了高侧占比，
而后一控制窗口的第二个四分位段又短暂升到约 65%，说明同次启动内
存在非平稳变化。这个试跑没有观察到 `tk_fast_raw` 特有的效应，
因此不能把自然双峰命名为该缓存行的两种所有权状态，也不能将原始
双峰拆成两项可独立比较的性能结果。PT 定位到 fast-raw 更新阶段的
结论仍成立；具体微架构原因目前未定。重复同一五窗顺序不足以补上
目标特异性证据；论文应保留逐次样本及完整分布。

### 下一步：逐次 UPDATE RFO 计数（待目标机执行）

上述缓存行准备试验的等开销对照也压低了慢簇，因此不能再用同类
预热操作给自然双峰命名。新的 `diagnose-percall-pmu` 改为被动记录：
为 CPU0 固定两个内核 PMU 计数器，分别计数 L2 RFO hit 与 miss；
每次 UPDATE 在起始 TSC 前读取一次、结束 TSC 后再读取一次。
PMU 读取发生在 **TSC 计时窗口外**，每条原始样本同时保留完整
UPDATE ticks 和两个事件增量。UPDATE 调用持有 `timekeeper_lock`
且关中断；计数器在启动窗口时固定并校验，结束时核验运行时间。
这避免了旧的 8 秒 CPU0 总计数无法对应单次调用的问题。

该方式仍可能因计时前的 `RDPMC` 改变自然分布。因此同次启动按
“基线、PMU、基线、PMU、基线”顺序各采 8 秒，先检查 PMU 窗口是否
保留与基线可比较的快慢两簇。若两簇消失，计数与原双峰不能关联；
若保留，再比较高、低样本的 RFO hit/miss 增量。计数器覆盖整个
`timekeeping_update()`，不能仅凭关联把事件定位到 `tk_fast_raw`
的某一条缓存行；此前 PT 的阶段定位是独立证据。

本试验仅构建一个 **Raw normal 诊断镜像**，不重编 VKSO，也不进入
正式 campaign。专用 Kconfig 只在这个 Raw 镜像启用；第一次对应
Raw Kbuild 缓存为空时仍需完整编译一次，后续同配置可增量编译。

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_BASE="$PWD/artifacts/update-split-normal-v1"
DIAG_PACKAGE="$PWD/artifacts/update-percall-rfo-raw-normal-pilot-v2"
JOBS=4 UPDATE_PERCALL_PMU_DIAG=1 ../update-bench/build-update-images.sh raw-normal \
  --package "$DIAG_BASE" --out "$DIAG_PACKAGE"
./experiment.sh verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
../update-bench/boot-update-once.sh raw-normal
# 重启、重新登录后：
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_PACKAGE="$PWD/artifacts/update-percall-rfo-raw-normal-pilot-v2"
./experiment.sh diagnose-percall-pmu --package "$DIAG_PACKAGE" --case raw-normal \
  --out "$PWD/results/update-percall-rfo-raw-normal-pilot1"
```

结果保存在五个窗口的 `round-00.csv`、`round-00.json` 和
`percall-pmu-shape.json`。采集器要求每个 CPU0 样本的 PMU 读数有效、
计数器几乎全程运行，并执行与之前相同的 ABI、公开 API、镜像/config
和清理检查。若双峰形状保留且两个 PMU 窗口均显示慢样本特异的 RFO
事件增量，再用独立启动复核，并考虑进一步定位到 fast-raw 阶段；
否则保留“fast-raw 阶段耗时已定位、具体硬件原因未定”的论文表述。

2026-09-25 Raw pilot `update-percall-rfo-raw-normal-pilot1` 已收集五个窗口，
但采集器的 CSV 头检查错误地要求整行只包含 `percall_pmu_active=...`，
因此封存的 `run.json` 标为 FAIL。修复解析器后，独立生成
`update-percall-rfo-raw-normal-pilot1-offline-report.json`；原始结果与
FAIL 记录保持不变。全部五个窗口约有 2000 条 CPU0 周期 UPDATE 样本，
两个 PMU 窗口的计数器运行校验为 PASS。以历史 120 TSC ticks 阈值
统计，三个普通基线的慢样本比例为 35.8%、37.1%、37.8%，两个逐次
PMU 窗口只有 9.0%、11.0%。计数器读取显著改变了被测分布；本次
不能用 PMU 事件分组为自然双峰指定硬件原因，也不应把离线报告
当作正式采集 PASS。

对本次三个未启用 PMU 的基线窗口做离线分层：5,998 条 CPU0 周期
UPDATE 中，`ktime_carry=1` 的 277 条有 81.9% 超过 120 ticks；
`ktime_carry=0` 的 5,721 条仍有 34.7% 超过该阈值。进一步排除
一秒边界附近，只保留 100–900 ms 且无进位的样本，三个窗口的
慢样本比例仍为 31.6%、34.6%、34.5%，快慢峰仍可见。因此进位
与部分慢样本相关，但不能解释主要双峰；此前 PT 的进位分支分析
也不能据此改写为“已找到双峰原因”。

### 无额外诊断插桩的跨启动对照（2026-09-25 离线分析）

分别检查 `results/20260923T164954Z-clocktime-full` 与
`results/20260924T065535Z-clocktime-full` 的 UPDATE/idle 原始 CSV。
每个 campaign 有四种内核、每种四个独立启动；每次启动内部 15 轮，
约 56,250 条 CPU0 周期性 UPDATE 样本。32 个启动目录均为
`COMPLETE`、环境恢复 `PASS`，各自的 `SHA256SUMS` 校验通过。
每个 campaign 内同配置使用相同包；两个 campaign 的包不同，
下表不把它们合并为一个性能估计。

峰位单位为 **TSC ticks**：先合并单次启动内部的 15 轮，再找
70–110 与 121–165 ticks 范围内五格滑动直方图的局部峰。
`P(>120)` 是单次启动超过固定阈值的样本比例范围，仅供展示
混合比例变化；Raw/VKSO 的谷值不同，不能把它直接当成相同
内部状态的发生概率。

| Campaign | 内核 | 快峰范围 | 慢峰范围 | 四次启动的 P(>120) 范围 |
|---|---|---:|---:|---:|
| 20260923 | Raw normal | 95–99 | 148 | 53.2–57.1% |
| 20260923 | VKSO normal | 83 | 140 | 59.4–61.6% |
| 20260923 | Raw no-retpoline | 93 | 144–146 | 47.6–56.0% |
| 20260923 | VKSO no-retpoline | 85 | 126–128 | 49.1–56.4% |
| 20260924 | Raw normal | 95–99 | 146–148 | 42.9–51.3% |
| 20260924 | VKSO normal | 83 | 138–140 | 56.5–59.8% |
| 20260924 | Raw no-retpoline | 93 | 144–146 | 47.1–52.2% |
| 20260924 | VKSO no-retpoline | 85 | 126–128 | 51.6–59.4% |

两峰之间五格滑动计数的最低值，相对两峰中较低峰的高度，32 次启动
均不超过 0.38；其中 31 次不超过 0.15。因此双峰并非单靠预设
搜索区间强行产生的两个局部最大值。

独立的 `update-bimodal-normal-v1` 诊断包又提供 Raw/VKSO 各两次
启动、每次三轮 idle 的带状态 CSV；四次结果均为 `COMPLETE` 且
校验和通过。两次 Raw 的快/慢峰分别为 99/136、97/136 ticks；
两次 VKSO 为 83/130、85/132 ticks。Raw 在无进位且纳秒相位位于
100–900 ms 的样本中，`P(>120)` 仍为 25.8%、24.9%；VKSO 为
43.4%、57.8%。所有这些启动的 `clock_mode`、`shift`、闰秒待处理
和 realtime 进位标志都不变。可见双峰不只出现在 VKSO，也不由
已记录的进位、时钟模式或秒边界单独解释。

峰位跨启动较稳，而固定阈值比例在同一启动的不同轮次也会变动。
因此论文可以报告**双峰分布、峰位和启动级比例**，但现有证据不足
以将快慢峰命名为两种已确认的 timekeeping 内部状态，也不应把
两峰分别当成独立的系统实验。当前最明确的定位仍是 PT 将额外
耗时集中到 `update_fast_timekeeper(tkr_raw)` 区间；该区间内部的
具体硬件或缓存原因未确定。

### 目标缓存行的非锁定预取

锁定 OR 的**控制行**和逐次 PMU 读取都曾压低慢峰，因此不能把
此前变化归因于 `tk_fast_raw`。新 `diagnose-prefetch` 在同一个
Raw normal 诊断内核中，对 `tk_fast_raw` 或独立控制缓冲区的两条
缓存行分别执行两条 `PREFETCHT0`（读预取）或两条 `PREFETCHW`
（写意图预取）。它不执行锁定读改写、不在 UPDATE 的 TSC 计时
窗口内读计数器或增加时间戳。预取只是提示，并不保证请求完成；
每种指令的控制组检验计时前操作本身是否改变双峰。

十一个 8 秒窗口按“基线、读控制、读目标、写控制、写目标、
基线、写目标、写控制、读目标、读控制、基线”运行，在同一次
启动中反转目标/控制顺序。若两个控制组和三段基线均保留可比较
的双峰，只有写目标反复压低慢峰，则支持写所有权相关的延迟；
若读/写目标都压低慢峰，则更倾向于目标行缓存驻留或通用访问
延迟。控制也改变双峰则试验仍受计时前操作干扰；目标无效也不能
排除缓存机制，因为预取只是提示。任何目标特异结果仍需独立
启动复核，再区分本核冲突与跨核所有权转移。

该试验复用现有 `CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG` 的 Raw
增量构建缓存；旧 `prepctl/prepraw` 行为保持原样，新命令只在带
`raw_prefetch_diagnostic=1` 标记的新包上开放。首先执行：

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
DIAG_PACKAGE="$PWD/artifacts/update-prefetch-raw-normal-pilot"
JOBS=4 UPDATE_CACHE_PREP_DIAG=1 ../update-bench/build-update-images.sh raw-normal \
  --package "$PWD/artifacts/update-split-normal-v1" --out "$DIAG_PACKAGE"
./experiment.sh verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
../update-bench/boot-update-once.sh raw-normal
```

重启、重新登录后：

```bash
cd /home/zzk/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
./experiment.sh diagnose-prefetch \
  --package "$PWD/artifacts/update-prefetch-raw-normal-pilot" \
  --case raw-normal \
  --out "$PWD/results/update-prefetch-raw-normal-pilot1"
```

采集器另存 `prefetch-shape.json`、每窗 CSV/校准数据和结果校验和。
这是单内核诊断，不需要 `experiment.sh begin`，不进入正式 campaign。

`results/update-prefetch-raw-normal-pilot1` 已在 Raw normal 诊断镜像上完成。
包与结果校验和通过，`run.json` 为 `COMPLETE`、环境恢复为 `PASS`；
每个窗口有 1,999–2,001 个 CPU0 周期性 UPDATE 样本，无丢失。
11 个窗口的空 TSC 对中位数均为 37 ticks。下表的高侧比例仍只按
历史 120 ticks 谷值划分，不能直接解释为已识别的硬件状态。

| 顺序窗口 | `P(>120)` | 低侧中位 ticks | 高侧中位 ticks |
|---|---:|---:|---:|
| 前基线 | 45.8% | 101 | 148 |
| 读控制 1 | 42.2% | 101.5 | 148 |
| 读 fast-raw 1 | 41.2% | 101 | 142 |
| 写控制 1 | 41.3% | 101 | 142 |
| 写 fast-raw 1 | 28.3% | 101 | 140 |
| 中基线 | 30.9% | 101 | 140 |
| 写 fast-raw 2 | 28.0% | 101 | 140 |
| 写控制 2 | 45.8% | 101 | 142 |
| 读 fast-raw 2 | 49.2% | 101 | 146 |
| 读控制 2 | 32.5% | 101 | 144 |
| 后基线 | 38.5% | 101 | 146 |

两次写目标预取比相邻写控制低 13.0 和 17.8 个百分点，值得继续检验；
但夹在两次写目标之间的**无预取中基线也只有 30.9%**，与目标窗口
几乎相同。三个无预取基线从 30.9% 到 45.8% 漂移；按每窗四个
约 2 秒片段划分，高侧比例甚至在 11.0%–63.0% 之间变化。
例如写目标 2 的四段依次为 51.6%、24.8%、17.6%、17.8%，
后基线为 54.4%、44.4%、12.0%、43.0%。这些时间变化与目标预取
的表观效果处于同一量级，而两次写目标窗口相邻于同一个低比例时段，
不是两次独立的因果复现。写目标后高侧峰仍存在，中位 140 ticks。
排除进位且只取 100–900 ms 相位后，两个写目标窗口高侧比例为
23.3%、22.9%，中基线为 26.8%；上述混杂并非进位或秒边界筛选
就能消除。

合并既往结果，能较有把握定位的是**可见快慢差主要落在
`update_fast_timekeeper(tkr_raw, tk_fast_raw)` 的无条件发布区间**：
Raw/VKSO 的 PT pilot 均指向该区间，函数内分支、已记录的进位和
时钟模式不能解释主要双峰。跨核持续读取 fast 状态足以把 UPDATE
推向高耗时分布，说明发布路径对缓存共享敏感；但正常基线中没有
证据证明同样的跨核读取正在发生。锁定控制行和逐次 PMU 读取也会
改变分布，本次非锁定预取的中基线又与目标窗口同时变低。
因此当前最具体的可支持结论是 **fast-raw 写入发布路径存在可变耗时**；
尚不能确定是 `tk_fast_raw` 的缓存行所有权转移、RFO miss、缓存
索引冲突还是其他流水线停顿，更不能命名为两种 timekeeping 内部状态。
正式性能分析
继续按启动保存和汇总完整双峰分布，不能把两峰拆成两个独立实验。

### 当前证据的关键混杂与后续诊断准则

重新检查未插桩的 `20260924T065535Z-clocktime-full`：Raw normal 的四次
启动共 60 个 idle 轮次，每轮约 15 秒。将每轮拆成四个约 3.75 秒片段，
片段内 `P(>120)` 范围为 11.0%–92.3%；VKSO normal 的对应范围为
37.6%–92.1%。这说明秒级的混合比例漂移在正式数据中也存在，并非
新预取试验才出现。顺序运行的几个 8 秒窗口无法凭一次启动把目标预取
效应同时间漂移分离。

还有一个此前未拆开的结构性混杂：PT 定位到的 `tk_fast_raw` 发布总是
**第二次** `update_fast_timekeeper()` 调用。现有试验没有区分“目标
数据行较慢”与“第二次连续发布较慢”。单独交换顺序只能解除这一层
混杂，本身不能证明缓存所有权、写缓冲或任何其他具体硬件原因。

后续不再按候选原因依次增加预取、PMU 或延迟操作。先实现和预检一个
**同启动、平衡顺序、保留逐次数据**的诊断：原顺序与交换两次 fast
发布顺序的诊断模式交错运行；每种模式都有无额外中间计时的完整 UPDATE
样本和对应 Intel PT 调用区间。窗口顺序需反向/随机平衡，分析以窗口
和启动为单位，不把连续调用当独立复现实验。预先验证两种模式中的
自然双峰仍存在、PT 可解码且不会把分布变成另一种形状；否则该模式
停止分析，不再用其解释原始双峰。只有慢区间在重复的平衡窗口中明确
跟随调用位置或目标对象，才进入下一层具体硬件归因。

硬件归因需要**同一次慢调用**附近的事件或目标地址证据。当前 Tiger
Lake 的 Intel 事件定义中，`MEM_INST_RETIRED.ALL_STORES` 可提供精确
指令及线性地址；`L2_RQSTS.RFO_HIT/MISS` 和 `RESOURCE_STALLS.SB` 分别
计数 CPU 上的 RFO 和 store-buffer 满导致的停顿，但不能仅凭窗口总数
指定到 `tk_fast_raw` 的某条缓存行。参见
[Intel Tiger Lake core events](https://perfmon-events.intel.com/platforms/tigerlake/core-events/core/)。
所以采集器若不能把被动硬件样本、PT 区间和原始 UPDATE 样本可靠对齐，
就不得把相关计数写成根因。需要先对采样支持、时间轴对齐、丢包和
性能分布保真做预检，再决定是否实施。至此为止，不要求研究者重启、
重编内核或运行新一轮盲测。

重新按逐次 CSV 而非汇总直方图检查已有 Raw per-call PMU 试跑：两个
PMU 窗口中，`rfo_miss>0` 的样本分别有 39/65、33/72 次落在高侧；
但高侧样本中分别有 **140/179、187/220 次完全没有记录到 RFO miss**。
因此该事件与部分慢调用相关，却不能作为该插装运行中全部慢调用的
充分解释，更不能越过“插装改变原始双峰比例”的问题来解释自然双峰。
这也排除了继续只增加同类 RFO 窗口总计数的价值。

### 调用顺序诊断（已完成一次 Raw 试跑）

`diagnose-order` 只需重新构建 Raw normal 的诊断镜像。它在同一次启动中
按原顺序、交换顺序、交换顺序、原顺序运行四个 10 秒窗口；交换时先发布
`tk_fast_raw` 再发布 `tk_fast_mono`。目标指针在计时前选定，计时区内
两种模式共用同一对调用点。两种模式均保留完整 UPDATE 的逐次
TSC 样本；每窗中间录制 5 秒 Intel PT。`start_tsc` 是原有计时起点，
在计时结束后写入诊断记录，不在两次发布之间增加时间戳。包中保存
精确镜像的 `raw-update-disassembly.txt`，便于把 PT 地址归到各调用点。

在 `vkso-tests/baremetal` 目录执行：

```bash
DIAG_PACKAGE="$PWD/artifacts/update-order-raw-normal-pilot"
JOBS=4 UPDATE_CACHE_PREP_DIAG=1 ../update-bench/build-update-images.sh raw-normal \
  --package "$PWD/artifacts/update-split-normal-v1" --out "$DIAG_PACKAGE"
./experiment.sh verify --package "$DIAG_PACKAGE"
sudo env NORMAL_PACKAGE="$DIAG_PACKAGE" ../update-bench/install-update-grub.sh --normal-only
../update-bench/boot-update-once.sh raw-normal
```

机器重启、重新登录后，在同一目录执行：

```bash
./experiment.sh diagnose-order --package "$PWD/artifacts/update-order-raw-normal-pilot" \
  --case raw-normal --out "$PWD/results/update-order-raw-normal-pilot1"
```

不运行 `experiment.sh begin`。新模式拒绝旧包、错误内核、不完整 PT 和已
存在的输出目录。`order-shape.json` 给出四窗分布及各窗 PT 子区间分布，
原始逐次 CSV、PT data、校准和日志全部保留。历史 120 ticks 阈值仅用来
追踪两侧比例；“两侧均有样本”不等于自动证明双峰形状。分析时需先确认
原顺序两窗仍呈现此前双峰，再依据 PT 和镜像反汇编判断慢区间随目标
对象还是调用位置移动。如果两种顺序都改变了分布，诊断只能报告该
现象，不能据此推出具体缓存或流水线原因。这是诊断试跑数据，不并入
正式 Raw/VKSO 性能结果。

`results/update-order-raw-normal-pilot1` 已在 Raw normal 诊断内核上完成；
结果校验和、PT 解码、环境恢复均通过。四窗各 1,250 次 PT 调用与逐次
TSC 样本一一对应；按顺序对齐的相邻间隔残差中位数约 3–5 ticks，
错位一个样本为数百 ticks。原顺序前后两窗低/高侧中位数分别为
107/150、107/150 ticks；交换两窗为 108/152、107/172 ticks。
第一次 fast 发布调用的 PT P90 依次为 17、19、29、16 ns，第二次
四窗均为 8 ns。因此可见的额外耗时有相当一部分跟随**第一次调用
位置**，并不固定跟随 `tk_fast_raw` 对象；此前“第二次 raw 发布是
主要慢区间”的定位应修正。第一次调用很短时仍有高侧样本，故不能
把整个双峰归于这一处。

从业务情形重新分层：四窗的周期性样本全为 CPU0、`action=0`，
`leap_pending=0`、`clock_mode=1`、`shift=24`；已记录的进位状态
没有把高低两侧分开。旧 Raw 启动中 `ktime_carry` 只占约 5% 且与
慢样本相关；本次原顺序窗口中它占约 56%，其高侧比例与无进位样本
相近，说明旧关联不能作为进位导致双峰的证据。实时时钟每秒起点后
0–40 ms 各有 100/2,500 次样本，
其中高侧比例依次为 95%、87%、97%、84%；对应秒内 40–900 ms
的高侧比例仍有 44%、50%、62%、43%。边界样本只占全部样本 4%，
占高侧样本约 6%–8%，因此是可辨认的**额外慢情形**，但不足以
解释整个高峰。此前两个独立 Raw 启动的秒边界也呈现高侧富集。
边界样本逐次 PT 对齐后，`update_vsyscall()` 的平均调用时间比
100–900 ms 内样本多约 3–11 ns，而第一次 fast 发布在边界没有
同向变慢。这说明秒边界与第一次 fast 发布的变化至少是两种
需要分别分析的现象，不能直接把汇总直方图的两个峰命名为
“两种 timekeeping 业务状态”。下一步应优先记录 `update_vsyscall()`
的实际进位/循环次数及秒变更状态，并在非边界样本中继续检查
是否存在尚未记录的业务分类；避免继续猜测硬件事件。

## 业务路径定向记录

在当前已安装、已启动的 Raw order 诊断内核上，直接运行下面的命令；无需重新
构建、安装或重启，也不运行 `begin`。复用同一验证过的包。此模式进行一段
20 秒的完整 UPDATE 逐次采样，其中前 10 秒用 Intel PT 仅记录
`update_vsyscall()` 内部的分支。它把 PT 覆盖区内的样本按实时时钟秒内
相位和 `ktime_carry` 汇总，同时保留原始 CSV 和 PT 数据，以便后续核对
是否真的发生不同的业务分支或循环次数。PT 开启会改变测量环境，本轮
数据仅用于解释机制，不并入正式性能结果。

```bash
cd ~/BinaryKernelCodeMapping/test/test_gettime/vkso-tests/baremetal
./experiment.sh diagnose-business \
  --package "$PWD/artifacts/update-order-raw-normal-pilot" \
  --case raw-normal \
  --out "$PWD/results/update-business-vsyscall-raw-normal-pilot1"
```

完成后应有 `run.json` 中的 `status=COMPLETE`，以及 `idle/pt-validation.json`
中的 `validation=PASS`、`target=update_vsyscall`、`itrace=b`。
`idle/business-shape.json` 显示 PT 覆盖区的秒边界与内部样本数和高侧比例。
这只验证数据足以分析；真正的业务原因仍需解析 `idle/round-00-pt/data`
中的分支序列，并与 `idle/round-00.csv` 的逐次相位、耗时对齐。

`results/update-business-vsyscall-raw-normal-pilot1` 已完成，结果校验和、
PT 解码和环境恢复通过。PT 中按 `update_vsyscall` 返回点重组出恰好 2,500 次
调用，和逐次 CSV 中 PT 覆盖的 2,500 行一一对应。函数只有两条观测到的
分支序列：4 个分支事件的路径出现 1,410 次，全部对应
`ktime_carry=1`；6 个事件的路径出现 1,090 次，全部对应
`ktime_carry=0`。同一包对应的 `vmlinux`/`bzImage` 校验一致；反汇编确认
第一处分岔位于 `update_vsyscall+0x8a` 的纳秒进位判断。因此，
`ktime_carry` 确实反映了该函数不同的业务执行路径，而不是采样误标。

但这两条路径**都包含原双峰的两侧**。沿用 120 TSC ticks 的历史谷值，
进位路径低/高侧为 433/977 次，中位数分别为 110/154 ticks；无进位
路径为 383/707 次，中位数分别为 107/148 ticks。秒起点 0–40 ms 的
100 次都走无进位路径，其中 91 次落在高侧；同一路径在 40–900 ms
仍有 616/990 次落在高侧。之前四个 order 窗口的整段
`timekeeping_update` PT 也各只有一条外层分支序列，虽然每个窗口同时
有快、慢样本。`update_fast_timekeeper` 在该 Raw 镜像中没有条件分支。

因此，当前证据排除了“高低峰分别就是纳秒进位/无进位两种控制流”这一
解释，也没有发现另一条能把整个双峰分开的外层业务分支。秒边界是额外
慢情形，但不是整个高峰；相同分支序列内仍会出现两个耗时簇。可把峰按
耗时作为**描述性分组**报告，不能称为已经识别出的两种业务状态。
