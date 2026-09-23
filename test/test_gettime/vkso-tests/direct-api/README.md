# Clocktime：公开 API READ 子协议（v2）

当前全量构建与采集命令见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。本文件解释 clean READ 子协议 `clocktime-direct-api-v2` 的调用路径和测量方法；下文 16-boot 独立 READ 命令是旧版操作说明，不应与当前 32-boot 全量 campaign 混用。旧 Redis、v1 sidecar、revision 数据不兼容，不能混入。

## 调用路径

- Raw：应用 → libc 的 `clock_gettime/clock_getres/gettimeofday/time/getcpu` → 原生 vDSO 或 syscall。
- VKSO：应用 → 动态链接的 `libvkso_time.so` 同名公开函数 → `libkernel.so` 的 `__vkso_*` 私有入口/context → grafted 内核驻留计算页；不支持的路径由 carrier 汇编直接 syscall。

没有 LD_PRELOAD、provider selector 或热路径 dlopen/dlsym/dlvsym。`libvkso_time.so` 是部署用的固定公开 API 库，不是多后端实验桥。库只做 ABI/errno 转换；时间计算没有复制进该库。私有 context 注入仍保留。共享库与执行文件反汇编均在构建时检查。

应用需要显式链接这个库，在任何时间 API 调用前调用一次 `vkso_time_init()`；初始化使用 pthread_once，失败后保持失败状态。manager 必须在应用启动前完成注册，所有使用者退出后才能 restore。不是任意未修改应用二进制的透明兼容方案。构造函数中提前调用时间函数的第三方库不在此初始化契约内。

公开函数成功不改 errno；失败转换为 -1/errno。time() 的负秒数不当作通用负错误码。gettimeofday 的过时 timezone 参数与 glibc 公共接口一致忽略，正式测量使用非空 tv、NULL timezone。原始带 timezone 的 carrier 语义仍由 ABI matrix 验证。公开 fallback 不调用同名 libc 函数，所以不会递归。

## 测试内容与单位

16 个 READ 项目：7 种 clock_gettime（realtime、monotonic、raw、boottime、TAI、两种 coarse）；realtime/coarse clock_getres；gettimeofday；time(NULL)、time(&t)；getcpu；process CPU clock 的 gettime/getres；realtime alarm gettime。invalid clock/errno、NULL clock_getres、namespace 与映射权限通过单独功能检查覆盖。目标内核不支持任一正式 API 时失败，不悄悄删项目。

绑定 CPU 2，固定地址布局 setarch -R，初始化、首次访问和预热在计时前。每轮批量 500000 次完整调用，31 轮分布到 7 个新进程。两端使用 LFENCE/RDTSCP/LFENCE 与编译器屏障，检查 TSC_AUX 和运行 CPU。保留全部有效原始批次，发现迁移/错误则整个采集失败。单位是 **TSC ticks/call**，不是核心 cycles。不扣除循环或固定常数；批次分位数不是单次调用 P99。

`--check-fast` 独立进程先预触碰，再用 seccomp 拒绝时间/getcpu syscall，并执行过滤器正向对照；诊断计时不会进入样本。`--fast-only` 仅用于宿主源码测试，正式收集与汇总不允许漏掉 fallback 项目。

## 构建和安装

在仓库根目录先运行源码测试：

```bash
python3 test/test_gettime/vkso-tests/direct-api/tests/test_direct.py
cd test/test_gettime/vkso-tests/baremetal
# 准备原版 Linux 源码；已有同版本压缩包可直接设置 RAW_TARBALL。
curl -fL https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.198.tar.xz -o /tmp/linux-5.15.198.tar.xz
export NORMAL_PACKAGE="$PWD/artifacts/direct-normal"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/direct-no-retpoline"
JOBS=4 RAW_TARBALL=/tmp/linux-5.15.198.tar.xz ./build-all.sh
./verify-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"
sudo env NORMAL_PACKAGE="$NORMAL_PACKAGE" NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" ./install-grub.sh
```

GCC 11.4.0、Python 3、GNU Make/binutils 与原有内核构建依赖必须可用。没有原版源码压缩包时明确失败；不回用缺少身份元数据的旧包。`build-all.sh` 重新构建四个镜像、carrier、manager、模块、ABI 程序和直接 API 程序。失败构建保留 `.building-*` 与日志，旧完整包不覆盖。要重新构建，显式选择一对新包路径；不要手工补造旧包的 owner/kernel identity。

每个包包含 `direct/`。相对链接 `direct/carrier/libkernel.so -> ../../libkernel.so` 保证运行与 manager 注册同一 inode，包从 staging 移到最终目录后仍有效。外层 SHA256SUMS 覆盖 direct 构建清单、源码和二进制；内层清单绑定构建时的内核清单、carrier、编译器和源码指纹。boot-manifest/source.patch 记录 Git 提交与 dirty patch；不同 variant 的配置、源码与工具身份做交叉检查。

no-retpoline 保留原配置含义：关闭 RETPOLINE、RETHUNK、CPU_UNRET_ENTRY、CPU_SRSO、MITIGATION_ITS 配置族。Normal 至少启用前三项；实际差异可检查包内 raw/vkso.config。不能解释为只替换了一条跳转指令。

## 固定启动/采集流程

`experiment.conf` 默认 4 个 block，每个 block 4 次独立启动，共 16 boot；四种顺序平衡位置。测量参数在 begin 后冻结；内核与测试二进制不变时，采集脚本可通过 refresh-tools 独立升级并记录快照。

```bash
./experiment.sh begin
./experiment.sh status
./experiment.sh boot       # 设置一次性 GRUB 项并立即重启
# 重启后，回到同一 baremetal 目录
./experiment.sh collect    # 自动 sudo、设置并恢复调频/irqbalance，验证后采集
./experiment.sh status
# 重复 boot → 重启后 collect，直到 status=complete
./experiment.sh aggregate
```

第一 block 可显式写四组名称（每个 boot 都会重启）：

```bash
./experiment.sh boot raw-normal
# 重启后
./experiment.sh collect raw-normal
./experiment.sh boot vkso-normal
# 重启后
./experiment.sh collect vkso-normal
./experiment.sh boot raw-no-retpoline
# 重启后
./experiment.sh collect raw-no-retpoline
./experiment.sh boot vkso-no-retpoline
# 重启后
./experiment.sh collect vkso-no-retpoline
```

后续 block 按 status 的顺序使用无参数 boot/collect，不能重复第一块的顺序。只有四种配置，没有 native/bridge/Copy 等额外后端。每个成功样本必须来自新的 boot_id。首次跑通可在**构建前**将 BLOCKS 改为 1，但一组只有一次启动不能支持稳定差异或等价性结论。

目标控制：Linux 5.15.198/x86-64、TSC、SMT 关闭、隔离 1–3、控制 CPU 0、测量 CPU 2、Intel P-state 固定 performance/turbo off。安装器保留既有控制启动参数。collector 核对 UTS、内嵌 config、安装镜像哈希、BOOT_IMAGE、auxv、clocksource、调频和模块占用。Raw 必须有 native vDSO 且无 VKSO MM-data auxv；VKSO 相反。不同实验机器需先明确调整控制协议，不能忽略失败继续运行。debugfs 必须已挂载在 `/sys/kernel/debug`。

## 功能、共享与状态成本

每次收集先执行原 ABI matrix（含动态 clock、namespace 与权限），独立 PFN 观察确认 carrier 的声明代码/只读数据确实映射到内核源 PFN，代码 RX、数据 R--；再跑公开 API syscall-bracket/errno 检查和无时间 syscall 诊断，之后才收 READ。PFN 辅助模块在正式用户态计时前卸载。

同次启动还测三种普通内核 ktime reader，存 `kernel-reader.csv`；旧字段 total_tsc_cycles 的真实单位仍是 TSC ticks。collector 在失败时尝试 restore，restore 失败则保留 backing module 并记录 FAIL，不卸载后伪报成功。捕获不到的断电/SIGKILL 必须人工恢复或重启。

publisher/update 与持续读写交互的插桩和采集工具保留在 `../update-bench/`，它们需要另外构建的 UPDATE 镜像，不能混入无插桩 READ 样本。入口见 [状态成本说明](STATEFUL.md)。此版本不会把历史 writer 结果作为新 READ 包的证据，也不把 Raw/VKSO 所有差异归因于物理页共享。

## 结果与统计

结果在 `baremetal/results/<run>/block-NN/<case>/`：

- `samples.csv` 和 `process-NN.csv`：原始批次的 ticks、调用次数、AUX、进程/轮次。
- `run.json`：case/block/boot_id、源码/包/程序身份、编译器、CPU、控制参数、清理状态。
- `check.log`、`check-fast.log`、`legacy-abi.log`、`sharing.json`（VKSO）：功能和共享证据。
- `kernel-reader.csv`：单独的内核 reader 数据；不会作为用户公开调用结果。

失败留在 `incomplete/`；不覆盖已完成组。全部完成后生成 `.tar.gz` 和 `.sha256`，同时保留原目录。aggregate 生成 `summary.json`，先求每个 boot 内中位数，再等权汇总 boot；VKSO/Raw 大于 1 表示更慢。缺组、重复 boot、缺样本、源码/参数/构建混用均拒绝。少于 3 boot/组不生成区间；区间为逐 API 独立 boot bootstrap，不证明等价性。

也可明确指定结果：

```bash
python3 ../direct-api/results.py results/<run>/block-*/* --out results/<run>/summary.json
```

不要重复输出到同一个 summary 文件。压缩包是汇总前的原始证据包，summary 单独保留。当前实际测试及 NOT_RUN 边界见 [VALIDATION.md](VALIDATION.md)。

## 分层维护：不因脚本修复重编内核

固定入口不变：`build-all.sh` 无参数构建完整四镜像；以下参数是增量维护入口。

**只修改 collect/boot/统计等 Shell、Python 工具：**

```bash
./experiment.sh refresh-tools
./experiment.sh status
# 按 next_case 继续 boot / collect；无需 build、install 或重跑已完成组。
```

工具保存到 `results/<run>/tool-revisions/<hash>/`，每次采集记录工具版本；旧工具快照、
旧样本和不可变 package 校验和保持不变。refresh 会拒绝参数或 C/头文件/Makefile 的变化。
这是为修复采集编排提供的显式入口；若改变测量含义/时序/统计设计，应停止并新建 campaign，
不能将“脚本可升级”理解为不同实验协议可以混合。已有 v2 campaign 可原位接入一次 refresh-tools。

**只修改用户态公开库/benchmark：**

```bash
./build-all.sh bench-normal --out "$PWD/artifacts/direct-normal-bench2"
./build-all.sh bench-no-retpoline --out "$PWD/artifacts/direct-no-retpoline-bench2"
```

保留旧镜像/carrier，重建 direct API 文件和身份清单，输出新包。需要新 campaign；内核镜像相同时无需重新安装。

**只修改一个内核：**

```bash
JOBS=4 ./build-all.sh vkso-normal --out "$PWD/artifacts/direct-normal-kernel2"
# 其他选择：raw-normal、raw-no-retpoline、vkso-no-retpoline
# 可先加 --plan 检查父包并显示构建范围，不编译。
```

默认父包来自 NORMAL_PACKAGE / NO_RETPOLINE_PACKAGE（或 artifacts/direct-*），也可 `--package PATH`。
VKSO 修复只构建 VKSO 内核和依赖它的 carrier/模块，Raw 镜像和对应 reader 模块复用已验证原件。
Raw 修复只构建 Raw 内核及其 reader/动态时钟模块，VKSO/carrier 保留；RAW_SOURCE 或 RAW_TARBALL 提供原版源码。
不修改旧包、不覆盖旧结果。`.work`、`.building` 保留失败日志/产物；重试请选新输出目录。

内核变化后把对应的 PACKAGE 环境变量指向新包，执行 verify-packages.sh、install-grub.sh，再开始新 campaign。
两种 mitigation 包仍要求相同内核源码、配置只差既定选项、用户态二进制相同；若改了两种配置共用的 VKSO 源码，
须分别重建 vkso-normal 和 vkso-no-retpoline，两份 Raw 不需重建。
Git 提交/dirty patch/构建时间可不同，源码树、镜像、carrier、依赖和工具链身份仍严格核验。

```bash
# 仅在更换内核/测量二进制或协议时结束旧 campaign；原数据保留。
./experiment.sh stop "kernel or benchmark revision"
export NORMAL_PACKAGE="$PWD/artifacts/direct-normal-kernel2"
# NO_RETPOLINE_PACKAGE 指向配套包
./verify-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"
sudo env NORMAL_PACKAGE="$NORMAL_PACKAGE" NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" ./install-grub.sh
./experiment.sh begin
```

构建/验证不会自动安装或重启。`rebuild.json` 与 parent-package-* 保存旧包身份及选择性构建来源。
选择性构建的真实目标内核运行仍须在对应启动下由 collect 验证，构建成功不等于运行通过。

## 公共入口优化候选（2026-09-23）

`time` 使用 ELF IFUNC，在链接器解析阶段返回 `__vkso_time` 地址。解析器不执行
carrier、不分配状态；应用仍必须在注册成功后先调用 `vkso_time_init`。两者在
x86-64 LP64 下签名相同，负时间值和 errno 语义不变。正式 benchmark 使用
`-z now`，解析发生在计时前。其他公开 API 保留 errno/参数适配，以 `-fno-plt`
编译公共库，使用已解析 GOT 直接调用 carrier，省去 PLT 中转。没有复制共享计算。

现有内核、carrier、映射和上下文不变。与原 direct-normal 包相比，候选公共库
size 的 text 为 3106（原 3282）字节，data 696、BSS 16 字节均不变；PT_LOAD
的页覆盖范围不变。此为静态布局证据，不等于实测 RSS 或性能收益。
单元测试核对 public time 与 carrier 函数地址一致、负秒值/errno/TLS/初始化语义，
并检查其他公共入口的 GOT 调用。真实共享页上的候选性能及完整功能仍为 NOT_RUN。

已生成的候选包为 baremetal/artifacts/direct-{normal,no-retpoline}-entry-opt2。
无需重建或重装内核。完成旧实验后，在 baremetal 目录运行：

```bash
export NORMAL_PACKAGE="$PWD/artifacts/direct-normal-entry-opt2"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/direct-no-retpoline-entry-opt2"
./verify-packages.sh "$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE"
./experiment.sh begin
./experiment.sh boot
# 自动重启后回到 baremetal 目录
./experiment.sh collect
# 按 status 重复 boot/collect，complete 后 aggregate
```

新 campaign 在 begin 时保存包路径，重启后不需要重新 export。旧结果保持原位；
不要对旧 campaign 使用 refresh-tools 来混入新公共库。

进一步回退排查及冷路径候选 entry-opt4：见 [ENTRY_DIAGNOSIS.md](ENTRY_DIAGNOSIS.md)。

公共 namespace/错误路径专项及 kernel READ 汇总：见 [SUPPLEMENTAL.md](SUPPLEMENTAL.md)。

UPDATE／并发的新执行流程和完整命令：见 [RUN_STATEFUL.md](../update-bench/RUN_STATEFUL.md)。历史迁移审查见 [UPDATE_AUDIT.md](UPDATE_AUDIT.md)。
