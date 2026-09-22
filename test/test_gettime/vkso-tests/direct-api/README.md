# Clocktime direct API：§6.4 候选读接口流程 v1

基线：`43c60fc68a6ec6bed5b8131927f7c17100b2f20c`。
协议：`clocktime-direct-api-v1`。这是新增、独立的候选流程，不改写历史数据。

## 本次改动与边界

主比较只有 **Raw/VKSO × Normal/no-retpoline 配置族**。Raw 调用原生 libc，由 libc 使用原生 vDSO；VKSO 显式动态链接现有 `libkernel.so`，通过公开头文件中的薄入口调用 `__vkso_*`。没有 `adapter.so`、`LD_PRELOAD`、`dlopen/dlsym` 或每次调用的 provider 选择。

`vkso_time.h` 提供 `vkso_time_clock_gettime`、`vkso_time_clock_getres`、`vkso_time_gettimeofday`、`vkso_time_time`、`vkso_time_getcpu`。参数和返回约定对应相应公开 C API；名称使用显式前缀，**不接管 libc 的标准名称，也不宣称既有应用二进制透明接入**。应用需要包含头文件、选择这些入口并重新链接。

薄入口仅完成原始负错误码到 `-1/errno` 的转换，随后/此前的真实时间计算仍在 carrier 指向的共享核心中。`time()` 返回的负秒数不被误当成错误码。`libvkso_time_init.a` 只包含一次性初始化和原有的 `vkso_user_wrapper.c`；不包含时间计算的第二份实现，也不是新的转接 DSO。

应用必须在任何调用之前成功执行 `vkso_time_init()`。它使用 `pthread_once`，初始化成功时保留调用线程的 errno；首次失败是 sticky 的，修复部署后应启动新进程。热路径不重复执行 once 检查。不要在同一进程中另行调用旧 binder 或混用其他会重写其 context 的适配器。

**共享页必须在进程启动前由现有 manager 注册，并保持到全部用户退出。** 新初始化首先检查 VKSO auxv，避免在普通 Raw 启动上触碰 carrier 状态；该检查不是物理页共享证明。carrier 内的私有汇编入口、共享时间核心、namespace 页共享、grafting 与内核生命周期代码均未修改。

本轮只实现用户公开 READ 接入与采集。PFN、内核 reader/publisher、完整并发/namespace 生命周期仍使用独立的原有验证；新 collector 不把它们冒充为已通过。

## 源码层验证

在仓库根目录：

```sh
python3 test/test_gettime/vkso-tests/direct-api/tests/test_direct.py
```

测试会在临时目录构建一个带 `vkso_test_only_mock_carrier` 标记的假 DSO，**仅验证调用端 ABI、errno、初始化、链接和工具逻辑**，退出后删除。它不能用于目标机实验，bundle builder 会拒绝该标记。

本地 Native smoke 使用真实 libc/vDSO，但它不是原论文硬件上的性能数据。本会话中 GCC 14 与 Clang 分别通过 25 个测试；GCC 11.4.0、目标内核和真实 kernel-backed VKSO 执行未在本地完成。见交付包验证记录。

## 构建：复用未修改的内核包，新增独立 sidecar

本次没有修改内核或 carrier ABI，因此可以对已构建、哈希有效的原 Normal/no-retpoline 包建立 sidecar，不需要为了用户入口变化重新构建时间核心。

两个包须保留完整原产物与 `SHA256SUMS`，包括 carrier、manager、模块、ABI matrix、四组对应镜像及配置。源码必须保留基线的 `functional/vkso_abi.h`、`vkso_user_wrapper.c/.h`；builder 会核对其 Git blob 身份。

在目标构建环境执行，路径替换为真实绝对路径：

```sh
D=test/test_gettime/vkso-tests/direct-api
python3 "$D/bundle.py" --package /absolute/final-normal \
  --out /absolute/direct-normal --cc gcc-11
python3 "$D/bundle.py" --package /absolute/final-no-retpoline \
  --out /absolute/direct-no-retpoline --cc gcc-11
```

要求 GCC **11.4.0** 与原包清单一致，依赖 Python 3.8+、Make、GNU binutils 和 C/C++ 编译器。脚本不下载依赖、不执行内核包里的程序，不改变原包，不安装内核、不重启。输出目录必须不存在且位于源码和原包之外。输出含两种 benchmark、初始化静态库、源码、编译日志、ELF/反汇编审计、构建清单和校验和。

`carrier/libkernel.so` 是指向原包 carrier 的符号链接，必须与 manager 注册的文件为**同一 inode**。不能换成复制文件。sidecar 记录原包绝对路径；迁移包的位置后应重新构建 sidecar，而不是手改清单。对两个 mitigation 变体使用同一源代码、编译器与公开调用选项；差异维度是原内核/carrier 构建配置族，不是单条 retpoline 指令。

自有应用的链接示例（manager 注册完成后才可启动）：

```sh
B=/absolute/direct-normal
gcc-11 -D_GNU_SOURCE -O2 -std=gnu11 \
  -I"$B/src/direct-api" -I"$B/src/functional" \
  "$B/src/direct-api/example.c" "$B/libvkso_time_init.a" -pthread \
  -L"$B/carrier" -Wl,--no-as-needed -lkernel -Wl,--as-needed \
  -Wl,-rpath,"$B/carrier" -o ./vkso-time-example
```

这不是将共享核心静态链接进应用。静态库只提供 setup；执行文件具有 `DT_NEEDED libkernel.so`，时间计算仍从 carrier 调用。

## 测量口径

16 个路径：七种 clock_gettime 快路径、两种 clock_getres 快路径、gettimeofday(tv,NULL)、time(NULL)、time(&t)、getcpu(cpu,node)，以及 process CPU clock 的读取/分辨率和 realtime alarm 读取三条回退路径。

不测 `gettimeofday(NULL,...)` 作为 libc 基线，也不将旧 timezone 参数行为混入对照。调用参数必须满足各入口的有效指针等前提；新增薄入口不是用户态指针访问的安全门。

每个 case 编译成独立批次函数，函数选择发生在时间戳之前。计时范围包括循环与完整公开调用，包括 VKSO 的返回值转换；不含装载、grafting、初始化、预热或输出。两侧都保留完整批次成本，不做事后空循环/包装成本扣减。

时间戳使用有 LFENCE 和编译器 memory clobber 的 RDTSCP，先检查 invariant TSC/RDTSCP 能力，固定 CPU，检查批次两端 TSC_AUX。单位为 **TSC ticks/call**，不是 unhalted core cycles；批次分布也不是单次 API 的尾延迟。所有有效批次保留，不删除不利样本。操作系统保持正常时间更新。

`--check` 使用 syscall bracket、分辨率、返回值和 errno 检查公开接口；`--check-fast` 是单独进程的 syscall-denial 诊断，含 filter 正向对照。它只检查 13 条快路径，不输出该诊断的时延，也不进入性能样本。

`--fast-only` 只供明确的本地诊断；正式 collector 不使用它，汇总器会拒绝缺少三条回退路径的数据。本会话宿主对 CLOCK_REALTIME_ALARM 返回 EINVAL，因此本地完整矩阵未通过，不能用 fast-only 结果替代。

## 目标机：先预检，再显式执行

保留原来的内核安装和启动操作。每次由操作者明确启动所需的镜像。**原 `experiment.sh collect` 仍是历史协议；本候选流程使用下面的新入口，不要混合两者输出。** Redis 在新流程中没有构建/运行步骤，不需要构造 bridge-vDSO 基线。

当前预检针对原 i7/四核配置：Linux 5.15.198、CPU 2 测量、CPU 0 控制、SMT 关闭、TSC clocksource、隔离 CPUs 1–3、固定布局，以及原流程的启动参数：

```text
nokaslr nosmt clocksource=tsc tsc=reliable
isolcpus=domain,managed_irq,1-3 nohz_full=1-3 rcu_nocbs=1-3 irqaffinity=0
idle=poll nmi_watchdog=0 nowatchdog audit=0
```

还要求 Intel P-state no_turbo=1、min/max_perf_pct=100、performance governor，并且 irqbalance 不活跃。collector 只核验，不自动改这些系统设置。与原安装命名保持一致：`/boot/vkso-final-CASE-5.15.198.bzImage`。

启动某个 case 后，先只读预检：

```sh
python3 "$D/collect.py" --case raw-normal --bundle /absolute/direct-normal
```

预检核对校验和、构建版本、运行配置/内核身份、安装镜像、原生 vDSO/auxv、clocksource、CPU、调频配置、现有模块占用及同 inode carrier。若权限不足读取系统信息，可以由 root 执行预检，但不加 `--execute` 时不加载模块。

通过后执行（该命令明确加载测试模块，并在 VKSO case 中注册/恢复 carrier）：

```sh
sudo python3 "$D/collect.py" --execute \
  --case raw-normal --bundle /absolute/direct-normal \
  --out /absolute/results/block-01/raw-normal
```

其他三组改为对应 case 和 bundle：

```text
vkso-normal         /absolute/direct-normal
raw-no-retpoline    /absolute/direct-no-retpoline
vkso-no-retpoline   /absolute/direct-no-retpoline
```

每次必须在**对应内核启动后**采集，不能在一个 boot 中把 case 名换四次。默认 31 个批次轮次分配到 7 个新进程，每路径每轮预热 10,000 次、测量 500,000 次。启动内重复不是独立 boot。

collector 先运行原包的 ABI matrix，再运行新的完整公开 API 检查与快路径拒绝 syscall 诊断，最后采样；它不会把检查中的数据写入性能表。模块和 registration 只由显式执行模式操作，不安装内核、不更改 GRUB、不重启。

正常结束和可捕获的失败都会尝试恢复。若 replace 部分失败，也会尝试 restore；若 restore 失败，不卸载 page_cache_replace，并将结果标成 FAIL、保留日志供人工恢复。不要并行运行旧 collector、另一个 manager 或其他载体会话。SIGKILL、断电或 kernel panic 无法依靠 Python finally 清理，需要按原管理流程恢复或重启。

`COMPLETE` 仅表示本次公开 READ 收集及清理完成。run.json 的 PFN 和 kernel reader/publisher 字段仍为 NOT_RUN；没有独立 PFN/两端验证时，不可据此宣称整个 §6.4 验收完成。

## 独立启动与汇总

建议至少完成四个完整启动块，每个块包含四个配置，并采用平衡顺序，例如：

```text
block 1: raw-normal, vkso-normal, vkso-no-retpoline, raw-no-retpoline
block 2: vkso-normal, raw-no-retpoline, raw-normal, vkso-no-retpoline
block 3: raw-no-retpoline, vkso-no-retpoline, vkso-normal, raw-normal
block 4: vkso-no-retpoline, raw-normal, raw-no-retpoline, vkso-normal
```

这不增加实现种类；增加的是独立启动重复。每组输出使用新目录，不覆盖失败记录或历史结果。汇总示例：

```sh
python3 "$D/results.py" /absolute/results/block-*/* --out /absolute/direct-summary.json
```

汇总先计算每个 boot 的各 API 中位数，再等权汇总 boot；VKSO/Raw 是成本比，大于 1 表示 VKSO 较慢。重复 boot_id、漏样本、协议/构建混用、同组镜像或可执行文件变化会被拒绝。启动间比值不强行配对轮次。每侧少于三个 boot 时省略置信区间；其余提供独立 boot 重采样的逐项 percentile 区间，不作等价性证明或多重比较修正。

## 尚需完成的目标验收

本地测试没有运行真实 grafted VKSO，也没有执行本文件中的 root 采集流程。采用正式结果前，仍需在原机器确认 GCC 11.4 构建、四种内核下的新公开 API/路径、实际代码页身份、namespace 与进程生命周期，以及原有内核 reader/publisher 成本。新版本没有修改相关核心，仍然需要将它们的证据与实际使用的 package 身份关联。
