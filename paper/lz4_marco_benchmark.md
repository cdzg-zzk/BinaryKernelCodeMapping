用户态基准测试套件适配内核态压缩算法：构建 Shim 层的系统性方法论研究报告1. 摘要本报告旨在深入探讨一种系统性的工程方法，用于在不修改用户态基准测试套件（Specifically Phoronix Test Suite, PTS）源代码的前提下，对其链接的压缩算法库进行透明替换，以实现对 Linux 内核态压缩实现（Kernel-Reuse Code）的性能评估。本研究的核心痛点在于用户态标准库（如 liblz4, libzstd）与内核态对应实现之间存在的应用程序接口（API）及二进制接口（ABI）的显著差异。尽管算法核心逻辑在数学上是等价的，但内核态对于内存管理（显式工作区分配）、符号命名规则以及错误处理机制有着严格且独特的约束，这导致直接链接无法实现。为了解决这一问题，本报告提出了一种基于“接口探查-差异映射-Shim构造-注入集成”的四阶段方法论。首先，我们通过静态源代码分析与动态符号追踪相结合的技术，精确界定了测试套件（Harness）所需的最小功能集（Scope）；其次，详细剖析了 LZ4 与 Zstandard 在用户态与内核态的签名差异，重点阐述了内存模型的映射策略；随后，设计并展示了具体的 Shim 层代码实现，演示了如何通过封装不透明指针来桥接隐式与显式内存管理模型；最后，详细说明了在 PTS 构建流程（install.sh）中注入自定义库的工程实践。本报告论证了该方法的可行性，并指出在构建 Shim 层时必须兼顾正确性与性能损耗的平衡，特别是在处理高频调用的压缩函数时，内存分配策略的选择对基准测试结果的信度具有决定性影响。2. 引言在现代操作系统的性能优化与演进过程中，内核子系统的效率至关重要。Linux 内核广泛采用了 LZ4 和 Zstandard（Zstd）等压缩算法，应用于透明文件系统压缩（Btrfs, F2FS）、内存压缩（ZRAM）、内核镜像解压以及 initramfs 加载等关键路径。为了评估内核中这些算法实现的性能改进或回归，传统的做法是在内核空间编写特定的内核模块（LKM）进行测试。然而，这种方法存在调试困难、测试场景单一以及难以复用成熟的用户态基准测试工具链等缺陷。Phoronix Test Suite（PTS）作为业界广泛认可的开源测试平台，提供了丰富且标准化的测试用例（Test Profiles）。如果能够利用 PTS 现有的测试用例（如 pts/compress-lz4 和 pts/compress-zstd）直接对内核态代码的用户态移植版（Kernel-Reuse）进行测试，将极大地提升评估的标准化程度与便捷性。然而，这一目标的实现面临着巨大的技术鸿沟。Linux 内核为了保证系统的稳定性与可预测性，采用了与用户空间截然不同的编程模型。内核函数通常不支持通过 malloc 进行隐式的动态内存分配，而是要求调用者预先分配并传入工作区（Workspace）；此外，内核符号的命名空间管理（如 zstd_compress_cctx vs ZSTD_compressCCtx）也与标准库存在差异。这就要求我们在测试套件与内核代码之间构建一个适配层——Shim 层。本报告将以“如何确定范围”和“如何构造 Shim”为核心线索，展开详尽的技术论述。3. Phoronix Test Suite 架构与测试套件执行机理分析在着手构建 Shim 层之前，必须对“敌情”进行深入侦察。我们需要透彻理解 PTS 是如何构建、安装以及执行一个测试用例的。这直接决定了我们介入的时机与方式。3.1 测试用例（Test Profile）的解剖学结构PTS 的测试用例并非是一个预编译好的黑盒二进制文件，而是一套完整的构建脚本与元数据集合。一个典型的测试用例（例如 pts/compress-lz4）通常包含以下关键文件，它们位于 ~/.phoronix-test-suite/test-profiles/ 目录下 1：test-definition.xml：这是测试用例的“身份证”。它定义了测试的元数据，包括测试类型（Processor/System）、执行参数的默认值、以及结果解析的规则。对于我们而言，最重要的信息是 <Executable> 标签，它指明了最终被调用的二进制文件名（例如 lz4 或 zstd）以及传递给它的参数（例如 -b1 表示 benchmark level 1） 2。downloads.xml：定义了上游源代码的下载地址和校验和（MD5/SHA256）。这证实了 PTS 确实是从官方源（GitHub Release 或 tarball）下载代码并在本地编译，而非使用系统预装的库 1。install.sh：这是我们需要重点关注的“手术台”。该脚本负责解压源码、配置编译选项（./configure 或 cmake）、执行编译（make）以及安装最终的二进制文件。正是因为存在这个编译环节，我们拥有了在链接阶段替换库文件的黄金机会，而无需诉诸于脆弱的二进制补丁或 LD_PRELOAD 2。3.2 所谓“Harness”的实质在用户提出的问题中，提到了“Harness（测试夹具）”。在 pts/compress-lz4 和 pts/compress-zstd 的语境下，Harness 并不是 PTS 编写的一段独立代码，而是上游项目自带的命令行工具（CLI）。LZ4 Harness：即 LZ4 源码包中的 lz4 可执行文件。当 PTS 运行测试时，它实际上是调用 lz4 -b 命令。该命令会触发 programs/bench.c 中的基准测试逻辑 4。Zstd Harness：即 Zstandard 源码包中的 zstd 可执行文件。同样，PTS 通过调用 zstd -b 来触发其内部集成的基准测试模块 5。深度洞察（Second-Order Insight）：既然 Harness 就是上游的 CLI 工具，那么我们的 Shim 层不仅要骗过链接器，还要在逻辑上完全满足 CLI 工具内部 bench.c 模块对 API 的所有假设。例如，CLI 工具可能会为了性能优化而使用一些非核心的、高级的 API（如上下文复用接口），或者使用一些辅助性的 API（如获取版本号、错误码转换字符串）。如果我们只实现了最基础的 compress 函数，Harness 很可能会在初始化阶段就因为符号缺失（Undefined Symbol）而崩溃，或者在运行过程中因为无法正确复用上下文而导致性能数据失真。因此，“查看 Harness 源码”不仅是应该的，而且是必须的。我们需要查看的正是上游源码包中的 programs/ 目录下的代码。4. 接口探查与范围界定方法论用户最关心的问题之一是：“如何查看，如何明确范围呢？”。这需要结合静态代码分析和动态符号检查两种手段，以确保 Shim 层的覆盖率达到 100%。4.1 策略一：动态二进制符号分析（The "Truth"）这是最直接、最客观的方法。我们让 PTS 按照默认流程编译出一个基于标准库的二进制文件，然后“解剖”它，看它到底需要什么。操作步骤：执行标准安装：在开发环境中运行 phoronix-test-suite install pts/compress-lz4。等待其下载并编译完成。定位二进制文件：编译完成后，PTS 会将结果存放在 ~/.phoronix-test-suite/installed-tests/pts/compress-lz4-<version>/ 目录下。进入该目录，你会找到 lz4 可执行文件。符号表导出：使用 nm 工具查看该二进制文件未定义的符号（Undefined Symbols），这些就是它依赖于外部库的接口。Bashnm -u./lz4 | grep "LZ4_"
预期输出示例（LZ4）：U LZ4_compress_defaultU LZ4_compress_fastU LZ4_compress_HCU LZ4_decompress_safeU LZ4_compressBoundU LZ4_versionNumberU LZ4_createStreamU LZ4_freeStream...关键推论： 这个列表就是你的 Shim 层必须实现的最小功能集（Scope）。任何一个缺失的符号都会导致 ld.so 在运行时报错并终止程序。4.2 策略二：静态源代码审计（The "Context"）仅知道函数名是不够的，我们还需要知道 Harness 是如何调用这些函数的。例如，参数是如何传递的？上下文（Context）的生命周期是怎样的？这需要查看源码。操作步骤：获取源码：可以直接去 GitHub 克隆 LZ4 或 Zstd 的仓库，或者直接查看 PTS 缓存的源码包（位于 ~/.phoronix-test-suite/download-cache/）。定位 Benchmark 逻辑：LZ4：核心逻辑在 programs/bench.c 7。Zstd：核心逻辑同样在 programs/bench.c，但也会引用 programs/zstdcli.c 和 programs/fileio.c 9。分析调用点（Call Sites）：打开 bench.c，搜索你在 4.1 节中找到的符号。案例分析 - LZ4 bench.c 7：通过阅读源码，你会发现一个有趣的现象：即使是进行默认级别的压缩（Level 1），bench.c 往往也不直接调用 LZ4_compress_default，而是调用 LZ4_compress_fast，并将加速参数（acceleration）设置为 1。C// 伪代码示例
int LZ4_compressBlockNoStream(...) {
    int const acceleration = (cLevel < 0)? -cLevel + 1 : 1;
    return LZ4_compress_fast(src, dst, srcSize, dstSize, acceleration);
}
深度洞察： 如果你的 Shim 层只老老实实实现了 LZ4_compress_default 而忽略了 LZ4_compress_fast，即便你的目标只是测试默认压缩比，Harness 也无法运行。因为 Harness 的代码路径写死了去调用 _fast 变体。这就是查看源码的价值所在。案例分析 - Zstd bench.c：Zstd 的 benchmark 极其依赖高级 API。它不会简单地调用 ZSTD_compress（单次调用接口），而是会创建上下文 ZSTD_createCCtx，然后循环调用 ZSTD_compressCCtx 6。这是因为 Zstd 的上下文创建（内存分配与表初始化）开销很大，Benchmark 必须复用上下文才能测出算法本身的吞吐量。深度洞察： 这意味着你的 Shim 层必须能够模拟“上下文”的概念。用户态传给你一个 ZSTD_CCtx* 指针，你的 Shim 必须知道这个指针对应内核态的哪个工作区（Workspace）。4.3 范围界定总结必须实现（Mandatory）： 所有 nm -u 列出的带 LZ4_ 或 ZSTD_ 前缀的符号。不仅是压缩函数： 包括内存分配（createCCtx）、释放（freeCCtx）、错误处理（isError, getErrorName）、参数查询（compressBound）等辅助函数。签名匹配： 函数签名（参数类型、返回值）必须与用户态头文件（lz4.h, zstd.h）完全一致。5. 核心难点：用户态与内核态的架构差异与映射策略确认了“需要做什么”之后，接下来的挑战是“怎么做”。内核态代码的设计哲学与用户态截然不同，这种差异集中体现在内存管理模型上。5.1 内存管理模型的冲突特性用户态标准库 (Baseline)内核态实现 (Kernel-Reuse)内存分配方式隐式 (Implicit)。函数内部自动调用 malloc/stack。显式 (Explicit)。函数不分配内存，只接受调用者传入的指针。上下文管理使用不透明结构体指针（Opaque Pointer），如 ZSTD_CCtx*。使用具体的结构体定义或裸内存指针（void* workspace）。栈使用限制栈空间极大（MB 级），可在栈上分配哈希表。栈空间极小（通常 8KB-16KB），严禁大块内存分配。API 签名简洁，隐藏状态。冗长，暴露状态参数。5.2 LZ4 的接口映射策略5.2.1 签名差异用户态：int LZ4_compress_default(const char* src, char* dst, int srcSize, int dstCapacity); 11内核态：int LZ4_compress_default(const char *source, char *dest, int inputSize, int maxOutputSize, void *wrkmem); 13可以看到，内核态版本多了一个 void *wrkmem 参数。这是因为内核为了避免在压缩路径中发生不可控的内存分配（可能导致 OOM 或死锁），要求调用者预先分配好一块足够大的内存作为“工作区”。5.2.2 Shim 构造方案Shim 层需要拦截用户态调用，分配 wrkmem，然后调用内核函数。关键数据点： 内核态的 LZ4_MEM_COMPRESS 宏定义了工作区的大小。这通常是 LZ4_MEMORY_USAGE 宏导出的一个值（例如 16KB 窗口大小时对应特定的哈希表大小）13。C/* Shim 逻辑伪代码 */
int LZ4_compress_default(const char* src, char* dst, int srcSize, int dstCap) {
    // 1. 获取内核所需的内存大小
    size_t wrkmem_size = LZ4_MEM_COMPRESS; 
    
    // 2. 在堆上分配（用户态可以用 malloc）
    void* wrkmem = malloc(wrkmem_size);
    if (!wrkmem) return 0; // Error

    // 3. 调用重命名后的内核函数
    // 注意：内核源码在编译时需要重命名符号，防止与 Shim 符号冲突
    int ret = kern_LZ4_compress_default(src, dst, srcSize, dstCap, wrkmem);

    // 4. 释放内存
    free(wrkmem);
    return ret;
}
性能陷阱警示：上述实现中，每次调用压缩都会触发 malloc 和 free。在基准测试中，如果压缩包很小，malloc 的开销可能会占据相当比例，导致测试结果反映的是内存分配器的性能而非压缩算法的性能。优化建议： 使用 __thread (Thread-Local Storage) 静态变量来缓存 wrkmem，避免频繁分配。6. 构建与集成：注入 Phoronix 流程完成了 Shim 层的代码编写后，最后一步是将其无缝集成到 PTS 的构建流程中。6.1 解决符号冲突（Symbol Collision）这是一个极易被忽视的技术细节。你的 Shim 层定义了 LZ4_compress_default，而你链接进来的内核源码文件（lz4_compress.c）内部也定义了 LZ4_compress_default（假设内核源码未修改符号前缀）。如果直接链接，链接器会报“Multiple definition”错误。解决方案：预处理重命名（Preprocessor Renaming）在编译内核源码文件时，利用 GCC 的 -D 选项，将内核里的函数名加上前缀。Bash# 编译内核源码，将其符号重命名为 kern_...
gcc -c -O3 -D LZ4_compress_default=kern_LZ4_compress_default \
           -D LZ4_compress_fast=kern_LZ4_compress_fast \
           kernel_source/lz4/lz4_compress.c -o lz4_compress.o
这样，内核源码生成的目标文件中包含的是 kern_LZ4_compress_default，而你的 Shim 层对外暴露的是 LZ4_compress_default，并在内部调用 kern_... 版本。完美解决了冲突。6.2 修改 PTS 的 install.sh我们不能修改 Harness 的源码，但为了链接我们的 Shim，必须修改构建脚本。定位脚本：找到 ~/.phoronix-test-suite/test-profiles/pts/compress-lz4-<version>/install.sh。准备环境：将你的 Shim 源码（shim.c）和提取出的内核源码（lz4_kernel.c 等）放置在 PTS 可以访问的路径下，或者直接拷贝到编译目录中。劫持编译命令：install.sh 通常包含类似 make 的命令。我们需要将其替换为自定义的编译命令，或者修改 Makefile。最稳妥的方式是直接调用 GCC 重新链接 Harness 的对象文件和我们的库。修改后的 install.sh 逻辑片段：Bash#!/bin/sh

# 1. 正常下载解压上游源码
tar -xf lz4-*.tar.gz
cd lz4-*

# 2. 编译 Harness 的必要组件（bench.c, lz4cli.c 等），但不链接
# 注意：我们要使用上游的 programs/ 目录下的代码，这是 Harness 的本体
gcc -c -O3 -Ilib programs/bench.c -o bench.o
gcc -c -O3 -Ilib programs/lz4cli.c -o lz4cli.o
gcc -c -O3 -Ilib programs/lz4io.c -o lz4io.o
#... 其他依赖...

# 3. 编译内核-Reuse 代码（带符号重命名）
gcc -c -O3 -D LZ4_compress_default=kern_LZ4_compress_default \
    /path/to/kernel_reuse/lz4_compress.c -o kernel_lz4.o

# 4. 编译 Shim 层
gcc -c -O3 -I/path/to/kernel_headers /path/to/shim.c -o shim.o

# 5. 最终链接：Harness对象 + Shim对象 + 内核对象
gcc bench.o lz4cli.o lz4io.o shim.o kernel_lz4.o -o lz4

# 6. 生成运行脚本（PTS 要求）
echo "#!/bin/sh
./lz4 -b $@" > lz4-runchmod +x lz4-run```深度洞察（Third-Order Insight）：为什么要手动编译而不是修改 Makefile？因为上游 Makefile 极其复杂，通常会构建动态库并链接。为了确保 Harness 真的用到了我们的内核代码，静态链接（将所有 .o 文件打包进一个可执行文件）是最保险的策略。这样可以完全避免运行时 LD_LIBRARY_PATH 配置错误导致 Harness 意外加载了系统的 /usr/lib/liblz4.so，从而导致实验无效。7. 结论与建议本报告详细阐述了如何在用户态通过 Shim 层技术，利用 Phoronix Test Suite 现有的 Harness 对内核态压缩算法进行基准测试。核心结论：Harness 即 CLI：PTS 的压缩测试 Harness 本质上是上游的命令行工具（lz4 -b, zstd -b），因此 Shim 的接口必须满足 CLI 工具中 bench.c 模块的需求。API 范围：必须通过 nm -u 对标准二进制进行分析，以确定 Shim 需要覆盖的完整符号列表。对于 LZ4，必须包含 LZ4_compress_fast；对于 Zstd，必须支持上下文 API（CCtx）。内存适配是关键：Shim 的核心职责是弥合“隐式内存分配”与“显式工作区传递”之间的鸿沟。



你这个问题问得非常关键：**路线 A 里“替换”的不是 PTS 的源码**，而是 **PTS 自动下载并编译出来的“被测程序”**（`lz4` / `zstd` 这两个可执行文件）背后所依赖的压缩库实现，让它们在运行时**链接并调用你提供的动态库**，从而走你“映射内核函数”的路径。

下面我把这件事讲清楚，并给你一套**最稳的集成方式**（不靠 LD_PRELOAD，而是“链接替换 + 重编译/替换产物”）。

---

## 1) PTS 里到底是谁在被测？你要改哪里？

### compress-lz4

PTS 的 profile（`compress-lz4-1.10.0`）会做：解压 `lz4-1.10.0.tar.gz` → `make` → 然后生成一个运行脚本，最终跑的是：

* **可执行文件**：`./lz4-1.10.0/lz4`
* **输入数据**：`silesia.tar`

这点在它的 `install.sh` 里写得很明确：`make` 后运行 `./lz4-1.10.0/lz4 $@ silesia.tar`。([OpenBenchmarking][1])

✅ 所以：**你要让 `lz4-1.10.0/lz4` 这个二进制，使用你的动态库实现，而不是它自己带的那套 liblz4 实现。**

---

### compress-zstd

PTS 的 `compress-zstd-1.6.0` profile 类似：解压 `zstd-1.5.4.tar.gz` → `make -j $NUM_CPU_CORES` → 跑：

* **可执行文件**：`./zstd-1.5.4/zstd`
* **参数**：`-T$NUM_CPU_CORES $@ silesia.tar`

同样在 `install.sh` 里写得很清楚。([OpenBenchmarking][2])

✅ 所以：你要让 `zstd-1.5.4/zstd` 使用你的库。

---

## 2) 你提供的是“复用内核代码的动态库”，如何让 lz4/zstd 调它？

这里有一个必须先讲清楚的**链接层面事实**：

> **要让现成程序调用你的库，你的库必须“提供它需要的符号”。**

也就是说，`lz4` 程序会调用诸如 `LZ4_compress_default / LZ4_decompress_safe ...` 这类符号；`zstd` 会调用 `ZSTD_compress / ZSTD_decompress ...`（或者内部更复杂）。
如果你现有动态库导出的符号不是这些名字，那就需要一个很薄的 **compat wrapper**（兼容层动态库）把“上游 API”转发到“你的 API”。

这完全符合你论文机制：**用户态不再实现算法，只是提供一个“转发层”去调用映射到用户态的内核函数**。

---

## 3) 路线 A 的推荐做法：不是改大量 C 源码，而是“替换链接依赖”

我给你两个强烈推荐的“路线 A”落地方式（都比改上游 `.c` 文件更干净）：

### 做法 A1：做成“Drop-in 替换库”（论文最漂亮）

让你的动态库成为：

* `liblz4.so.*`（提供 LZ4 API）
* `libzstd.so.*`（提供 ZSTD API）

这样 `lz4` / `zstd` 只要**动态链接到这些库**，跑起来就会走你的实现。

优点：

* 论文叙事非常干净：“我们把用户态实现替换为 kernel-mapped 实现，保持 API 不变”
* 最容易保证“用户态无冗余实现”（至少核心算法代码不再携带）

---

### 做法 A2：保留你的库名，但让程序显式链接它

例如你的库叫 `libkmapcodec.so`，那就让 `lz4` 链接时带上 `-lkmapcodec`，同时确保不再链接/编译原本的 liblz4/libzstd 实现。

优点：

* 你不需要改库名/SONAME
* 你可以把 LZ4/Zstd 都放在一个库里

---

## 4) 具体到 PTS：怎么把你的库“带进”测试程序？

下面是你现在就能照做的**可复跑步骤**（重点是：让 PTS 仍然跑同一个二进制路径，结果解析不变）。

---

# Part A：LZ4（最容易先跑通）

## A.0 安装测试（PTS 生成目录）

```bash
phoronix-test-suite install compress-lz4-1.10.0
```

此测试会 `make` 并生成 `./lz4-1.10.0/lz4` 用于跑 `silesia.tar`。([OpenBenchmarking][1])

进入测试环境目录（典型位置）：

```bash
cd ~/.phoronix-test-suite/installed-tests/pts/compress-lz4-1.10.0/
ls
```

你应该能看到 `lz4-1.10.0/`、`compress-lz4`（运行脚本）等。

---

## A.1 先判断：PTS 编出来的 lz4 是不是“动态链接”的？

```bash
ldd ./lz4-1.10.0/lz4 | grep lz4 || true
readelf -d ./lz4-1.10.0/lz4 | grep NEEDED || true
```

* 如果你看到 `liblz4.so` / `liblz4.so.1` 之类的依赖 → 很好，你可以做“库替换”。
* 如果完全没有（说明静态链接或把对象编进去了）→ 那就需要你改 Makefile 让它动态链接（但 LZ4 这边一般比 zstd 好处理）。

---

## A.2（推荐）用 RPATH + 本地库目录实现“强制加载你的库”

目的：让 `./lz4-1.10.0/lz4` **无论系统里装了什么 liblz4**，都优先加载你放在它旁边的 `.so`。

1. 准备一个目录放你的库：

```bash
mkdir -p ./lz4-1.10.0/kmaplib
```

2. 把你的库放进去（两种选择）：

**选择 1：Drop-in（建议）**
把你的库命名为 `liblz4.so.1`（以及可选的 `liblz4.so` 软链接）：

```bash
cp /path/to/your/liblz4.so.1 ./lz4-1.10.0/kmaplib/
ln -sf liblz4.so.1 ./lz4-1.10.0/kmaplib/liblz4.so
```

**选择 2：你库名不叫 liblz4**
比如你的库叫 `libkmapcodec.so`，那你后面需要 `patchelf --replace-needed`（见下一步）把依赖改过去。

3. 给 `lz4` 二进制设置 RUNPATH/RPATH 指向 `$ORIGIN/kmaplib`
   （需要 `patchelf`）

```bash
sudo apt install -y patchelf
patchelf --set-rpath '$ORIGIN/kmaplib' ./lz4-1.10.0/lz4
```

4. 如果你的库名不是 `liblz4.so.1`，就把依赖替换掉：

```bash
# 例：把原来需要的 liblz4.so.1 替换为 libkmapcodec.so
patchelf --replace-needed liblz4.so.1 libkmapcodec.so ./lz4-1.10.0/lz4
cp /path/to/libkmapcodec.so ./lz4-1.10.0/kmaplib/
```

5. 验证它确实会加载你这份库：

```bash
LD_DEBUG=libs ./lz4-1.10.0/lz4 -V 2>&1 | head
ldd ./lz4-1.10.0/lz4 | grep -E 'lz4|kmap' || true
```

✅ 到这里，你已经实现了：**PTS 仍然运行同一个 `./lz4-1.10.0/lz4` 路径，但它加载的是你的库。**

接下来直接跑：

```bash
phoronix-test-suite benchmark compress-lz4-1.10.0
```

---


## 5) 你问的“替换什么源码？”——一句话总结

* **不是替换 PTS 源码**
* 也不一定要改 LZ4/Zstd 的核心 `.c` 文件
* 你真正要做的是：**让 PTS 构建出的被测可执行文件（`lz4` / `zstd`）在链接层面依赖你的动态库，从而调用你的实现**（而不是它自带/系统自带的用户态算法实现）。([OpenBenchmarking][1])

---

如果你下一步愿意继续推进，我建议你先把 **LZ4 跑通**，并把下面两条信息发我（不用长）：

1. 你的动态库目前导出的符号名（`nm -D libXXX.so | head`）
2. 你希望对齐上游 API（`LZ4_*`/`ZSTD_*`）还是自定义 API

我就可以把“如何做最小 wrapper、如何证明程序确实走你的库（而不是偷跑系统库/静态对象）”这部分，细化成你可以直接写进论文 Artifact 的脚本化步骤。

[1]: https://openbenchmarking.org/innhold/ab6c39a4e83590abe241c9d276621c0215b16e31?utm_source=chatgpt.com "LZ4 Compression v1.10.0 Test [compress-lz4]"
[2]: https://openbenchmarking.org/innhold/8a321b74f5a88fc2e6fa0f9d04430ac555313bb0 "Zstd Compression v1.6.0 Test [compress-zstd] - OpenBenchmarking.org"
[3]: https://github.com/facebook/zstd/issues/2976?utm_source=chatgpt.com "consider linking the CLI tool against the shared library ..."
[4]: https://chromium.googlesource.com/external/github.com/facebook/zstd/?utm_source=chatgpt.com "external/github.com/facebook/zstd"
[5]: https://github.com/facebook/zstd/issues/2261 "make / cmake inconsistencies · Issue #2261 · facebook/zstd · GitHub"

