# BCH 内核内执行对照的来源与构建条件

本记录确认本机已有可读取的 Ubuntu `5.15.0-119-generic` stock BCH 模块，并区分发行构建、匹配条件构建和当前完整 owner。证据采集日期为 2026-09-12；本次仅读取现有文件，没有下载、构建、装载模块或运行实验。

原始记录及可复核脚本位于 [`results/bch-kernel-baselines-20260912/`](results/bch-kernel-baselines-20260912/)。[`result.json`](results/bch-kernel-baselines-20260912/result.json) 的 PASS 仅指二进制配对、公有头和已消费 owner 源文件核对成功。

| 对照 | 源码与构建身份 | 能回答的问题 |
| --- | --- | --- |
| stock-kernel | Ubuntu119 发行版的实际 `bch.ko`，保留发行构建条件 | 适配 owner 相对实际发行实现的整体差异；包含源码适配、编译条件及尚未排除的源版本差异 |
| matched-source-kernel | 单独的测试模块，完整包含未改动的 vendored `lib/bch.c`，使用 owner 的算法编译条件；仅将公有 API 命名为 `matched_bch_*` | 与当前 owner 都在内核内执行时，观察已知源码适配带来的整体差异；包括 helper 调用、分配和表寻址方式 |
| owner-kernel | 现有完整 `adapted/bch.c`、`vkso_bch_*` 四 API 和原 owner 构建条件 | 直接执行当前实际 owner，作为导出同一 owner 的内核侧对照 |

本归档保存 stock 和既有 owner 的来源证据；第三个 matched-source-kernel 的实际新构建命令、二进制及运行结果由独立测试任务保存。本记录没有将其列为已通过的运行结果。三个内核侧对照使用各自创建的 `bch_control`，不交叉传递控制对象。原有普通用户态 `libbch-kernel-native.so` 是 adapted source 的用户态编译，不能标成 stock-kernel。

精确119可用路径：

- stock 模块：`/lib/modules/5.15.0-119-generic/kernel/lib/bch.ko`，包 `linux-modules-5.15.0-119-generic=5.15.0-119.129`，无其他模块依赖，vermagic 为 `5.15.0-119-generic SMP mod_unload modversions`。
- 配对 debug ELF：`/usr/lib/debug/lib/modules/5.15.0-119-generic/kernel/lib/bch.ko`，包 `linux-image-unsigned-5.15.0-119-generic-dbgsym=5.15.0-119.129`。
- 公有头：`/usr/src/linux-headers-5.15.0-119/include/linux/bch.h`。
- 公有符号版本：`/lib/modules/5.15.0-119-generic/build/Module.symvers`，解析到 `/usr/src/linux-headers-5.15.0-119-generic/Module.symvers`。

[`package-owners.txt`](results/bch-kernel-baselines-20260912/package-owners.txt)、[`package-versions.txt`](results/bch-kernel-baselines-20260912/package-versions.txt) 和 [`stock-modinfo.txt`](results/bch-kernel-baselines-20260912/stock-modinfo.txt) 保留原命令输出。stock 和 debug ELF 的 GNU build ID 均为 `225fb9b34102335304f722ae5567ea56ccba70c1`；全部 17 个 SHF_ALLOC section 的名字、类型、flags、大小和内容一致，见 [`allocated-section-comparison.json`](results/bch-kernel-baselines-20260912/allocated-section-comparison.json)。因此下述 DWARF 编译属性来自该实际发行模块的配对调试文件。

119 公有头与 `test/test_BCH/vendor/linux-5.15/include/linux/bch.h` 完全一致，见 [`header-comparison.json`](results/bch-kernel-baselines-20260912/header-comparison.json) 和原头 [`exact119-bch.h`](results/bch-kernel-baselines-20260912/exact119-bch.h)。四个 stock API 均为 `EXPORT_SYMBOL_GPL`：

| API | 119 symbol CRC |
| --- | --- |
| `bch_encode` | `0x0c303f52` |
| `bch_init` | `0x1a267fa8` |
| `bch_decode` | `0x860a2eab` |
| `bch_free` | `0x0d3e3481` |

原始四行分别保存在 [`stock-public-symbols.tsv`](results/bch-kernel-baselines-20260912/stock-public-symbols.tsv) 和 [`owner-public-symbols.tsv`](results/bch-kernel-baselines-20260912/owner-public-symbols.tsv)。比较驱动使用119 Kbuild、公有头、匹配的 `vkso_bch_*` 原型及 GPL module license；通过 `KBUILD_EXTRA_SYMBOLS` 引用本次 owner 构建产生的 `Module.symvers`。本归档的 owner CRC 来自 BCH resource attempt03，作为该既有构建的记录；新构建应使用自身配套文件。驱动对 stock、matched 和 owner API 的普通模块符号依赖会持有正常依赖引用。这仅解释驱动的正常依赖行为，不构成页面注册自动持有 owner 的证据。

采集中的 `readelf -n stock` 成功退出，但其自动 debuglink 探测对 `/usr/lib/modules/.../bch.ko` 发出 CRC 不匹配并忽略的提示，原 stderr 保留在 `commands.json`。这里的调试配对使用上文明确指定的 `/usr/lib/debug/lib/modules/.../bch.ko`，由 build ID 和全部分配 section 的独立比较确认，不采用该自动探测结果。

实际发行构建与当前 owner 的差异应保留在结果解释中：

| 条件 | stock119 算法 CU / 二进制 | 既有完整 owner |
| --- | --- | --- |
| 优化与标量条件 | `-O2`，禁用 SSE/MMX/AVX、red-zone 和 jump tables | 同样具备这些条件 |
| stack protector | `-fstack-protector-strong`，有 `__stack_chk_fail` 导入 | `-fno-stack-protector` |
| UBSAN | bounds、shift、bool、enum；实际保留相应 handler 导入 | `-fno-sanitize=all` 和算法对象 `UBSAN_SANITIZE=n` |
| FORTIFY | 119 配置启用，实际有 `fortify_panic` 导入 | `-D__NO_FORTIFY` |
| 间接分支和返回 | `-mindirect-branch=thunk-extern`、`-mfunction-return=thunk-extern` | 最后生效的两个选项为 `keep` |
| 单次调用函数内联策略 | CU producer 含 `-fno-inline-functions-called-once` | 实际 owner 命令不含该选项 |
| GCC 包标记 | `.comment` 为 Ubuntu `11.4.0-1ubuntu1~22.04` | `.comment` 为 Ubuntu `11.4.0-1ubuntu1~22.04.3` |
| profiling | 算法 CU 不含 `-p`/`-pg`/`-mfentry`；实际没有 `__fentry__` 导入 | 构建规则移除 profiling flags；算法命令不含这些选项 |

[`stock-cu.json`](results/bch-kernel-baselines-20260912/stock-cu.json) 只摘录两个 CU 的路径、producer、DWARF 行表字段和四个 API 声明行号；未归档整个 DWARF。`bch.mod.c` 的 producer 含 profiling flags，但 `lib/bch.c` 算法 CU 不含，不能从全局 `CONFIG_FUNCTION_TRACER=y` 或 module metadata CU 推断算法执行了 fentry。stock 与 owner 的实际导入、compiler comments 分别保存在 [`stock-elf.json`](results/bch-kernel-baselines-20260912/stock-elf.json)、[`owner-elf.json`](results/bch-kernel-baselines-20260912/owner-elf.json)。完整 owner 算法命令原样保存在 [`owner-bch_impl-command.txt`](results/bch-kernel-baselines-20260912/owner-bch_impl-command.txt)：前面的 Kbuild thunk 默认值被后面的 `keep` 覆盖。

[`vendor-to-adapted.diff`](results/bch-kernel-baselines-20260912/vendor-to-adapted.diff) 保存完整源差异。适配包括四个 helper 函数指针槽、`kzalloc` 展开为 `kmalloc` 加清零，以及两张表的 const/used 和显式 RIP 相对基址；未修改有限域、编码、解码和错误定位算法循环。原 [`owner-bch_impl.c`](results/bch-kernel-baselines-20260912/owner-bch_impl.c)、[`owner-module_meta.c`](results/bch-kernel-baselines-20260912/owner-module_meta.c) 和 [`owner-Makefile`](results/bch-kernel-baselines-20260912/owner-Makefile) 给出命名与构建适配边界。内核内执行 owner 时，四个 slot 由模块重定位绑定实际内核 helpers；导出用户 DSO 时的 libshim 绑定属于另一执行路径。

上述 owner 证据取自已完成的 `results/bch_resource-qemu-20260912-attempt03/build-source/`。[`owner-source-comparison.json`](results/bch-kernel-baselines-20260912/owner-source-comparison.json) 确认其 Makefile、wrapper、metadata 和完整 adapted source 均与采集时仓库文件一致。每项原输入的路径和内容标识在 [`identity.json`](results/bch-kernel-baselines-20260912/identity.json)，原命令及退出状态在 [`commands.json`](results/bch-kernel-baselines-20260912/commands.json)。

源版本证据的边界：stock119 DWARF 将算法定位到发行构建树的 `lib/bch.c`，四个 API 声明行号与 vendored 文件相符，但行表没有源内容校验字段。现有材料足以证明头文件一致和已知适配 diff，不能证明整份 vendored `bch.c` 与119发行源码逐字一致。本次没有使用本机186源码代替119。stock 对 matched 的差异因此仍包含发行构建条件和未排除的源版本差异；matched 对 adapted owner 才是控制算法编译条件后的已知适配比较。

私有119 guest 的后续运行用于验证完整功能、接口与正常依赖行为。该环境的计时属于诊断记录；正式 C 性能比较仍需隔离裸机测量。本归档本身不新增任何运行或性能结论。
