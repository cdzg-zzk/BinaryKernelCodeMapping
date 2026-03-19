# test_MICRO_pseudo

这个目录现在用于做“函数级”的 PIC 改造 benchmark。当前已经完整跑通并整理好的第一个函数是 `crc32_le`。

当前目标不是再拆成 `data_slot / func_slot` 这类超细粒度实验，而是按函数逐个做：

- 复制一个原生内核函数，形成 `*_micro`
- 用我们的方法把它改造成 PIC 友好的版本
- 直接在 guest kernel 中比较 `native` 和 `pseudo`
- 分别在 `retpoline` 和 `noretpoline` 下运行

当前目录分工：

- [kernel](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel)
  放 benchmark 相关源码。
  当前 `crc32_micro_builtin.c` 是并入 guest kernel 的 `crc32_le_micro` 源码，`micro_pseudo.c` 是比较 `crc32_le` 和 `crc32_le_micro` 的 harness，`micro.c` 保留成宿主机外部分析用的同步副本。

- [qemu](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu)
  放 guest kernel 构建、initramfs 打包、QEMU 运行和串口结果解析脚本。
  当前默认结果路径已经按函数归档到 `results/crc32_le/...`。

- [results](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/results)
  按函数收纳实验结果。
  当前 `results/crc32_le/` 下已经包含 `smoke`、`noinline` 和 `inline` 三组结果。

- [user](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/user)
  放宿主机本地直接驱动 `/proc/micro_pseudo/run` 的脚本。

- [EXPERIMENT_PLAN.md](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/EXPERIMENT_PLAN.md)
  保留早期更细粒度设计记录，当前实现已经不再沿用那套主线。

## 每个函数的MICRO TEST的完整过程

当我们把一个新的内核函数接入到这套 MICRO TEST 里时，通常都会按下面这个顺序做。这个过程的目标很明确：先保证函数改造是对的，再保证汇编形态符合预期，最后再进 guest/QEMU 拿正式结果。

1. 选函数，并确认它适合做函数级 benchmark。
   优先选输入可控、可重复、CPU-bound、依赖不要太重的真实函数。先确认它不是宏或 `inline`，并且能够比较稳定地单独调用。这里的目标不是一上来追求最复杂的路径，而是先找到一个“能被完整复制、能单独驱动、能公平比较 native/pseudo”的函数。

2. 在 [kernel](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel) 下复制原生实现，形成 `*_micro` 版本。
   当前 `crc32_le` 的做法是把源实现复制到 [crc32_micro_builtin.c](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel/crc32_micro_builtin.c)，导出 `crc32_le_micro()`。如果后面换成别的函数，也沿用这个思路：先把原生实现单独复制出来，尽量保持算法和控制流不变，只为后续 PIC 改造留出独立副本。

3. 在 [kernel/micro.c](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel/micro.c) 里保留一个同步副本，用于宿主机外部分析。
   这一份不是最终 guest 里真正运行的版本，它的作用是方便本地编模块、看反汇编、看重定位、快速试验 `_base()` 改造是否生效。这样我们不用每改一点都重新完整启动一次 guest。

4. 在 [kernel/micro_pseudo.c](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel/micro_pseudo.c) 里接入这个新函数的 benchmark harness。
   这里要做的是把“原生函数”和“改造后的 `*_micro` 函数”都纳入同一个测试框架，用同一份输入、同一套循环次数、同一条结果记录逻辑去跑。这个 harness 的责任是：
   比较 `native` 和 `pseudo`；
   做 warmup 和 repeat；
   输出 checksum，保证功能一致；
   输出 cycles/call、cycles/byte 之类的归一化结果。

5. 先在宿主机做本地 `.ko` 编译验证。
   这一步主要是排最基础的问题，比如声明不全、依赖没带齐、导出符号不对、harness 接口写错。通常先在 [kernel/Makefile](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel/Makefile) 这条链路上把模块编出来，确保源码至少能独立进入 Kbuild。
   这里的编译选项不是我们在这个目录里手工额外指定的，而是直接继承 `KDIR` 指向的那个 kernel build tree 的 Kbuild 选项：
   如果直接执行 `make -C kernel`，默认 `KDIR=/lib/modules/$(uname -r)/build`，那么用的是宿主机当前内核头文件对应的编译配置；
   如果执行 `make -C kernel KDIR=<guest build dir>`，那么用的就是对应 guest kernel 的编译配置。
   所以，这一步默认更像是一个“宿主机 smoke build”，它的作用是快速排基础编译问题，而不是最终证明“代码一定按 guest 的真实选项生成了目标汇编”。
   要做与 QEMU/guest 完全一致的编译选项检查，应该看第 6 步里提到的 [qemu/analyze_guest_modules.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/analyze_guest_modules.sh)，因为它会把 `KDIR` 直接指向 `retpoline / noretpoline` 的 guest build 目录。

6. 在宿主机外部先看一轮汇编和重定位，确认 PIC 改造形态是对的。
   这一步非常关键，因为我们不是只关心“能跑”，还关心“是不是按预期变成了 PIC 风格”。通常要检查：
   有没有出现想要的 `_base()` 取址；
   热路径里是不是通过基址寄存器访问目标对象；
   有没有不希望出现的绝对地址；
   `objdump` 和 `readelf -r` 里的重定位是不是和预期一致。
   当前这一步既可以走本地 `make analyze`，也可以走 [qemu/analyze_guest_modules.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/analyze_guest_modules.sh)，后者更重要，因为它复用了 guest kernel 的编译选项，能避免“宿主机编出来的汇编”和 guest 真正编出来的不一样。
   这一步的“检查是否正确”，不是凭感觉看一眼，而是按下面这几个点去核：
   第一，看 `objdump -drwC` 的热路径入口是不是出现了预期的 PIC 取址方式，例如：
   `_base()` 是 `noinline` 时，是否真的出现了单独的 `_base()` helper，并在函数里先调用它再取基址；
   `_base()` 是 `inline` 时，热路径开头是否直接出现 `lea symbol(%rip), reg` 这种 RIP-relative 取址。
   第二，看后续的数据访问是不是都建立在“基址寄存器 + 偏移”之上，而不是在热路径里继续出现直接引用全局对象的绝对地址。
   第三，看 `readelf -rW` 的重定位类型是否符合预期：
   我们通常希望看到的是与 RIP-relative 取址一致的 `R_X86_64_PC32` 这类 PC-relative 重定位；
   如果在本该被改造成 PIC 的热路径里继续看到 `R_X86_64_32S`、`R_X86_64_64` 之类直接把全局对象地址塞进去的绝对地址重定位，就要提高警惕。
   第四，把 transformed 版本和 native 版本并排看，确认两者的差异确实出现在“我们主动改造的那部分”，而不是编译器把别的代码形态也一起改坏了。
   对 `crc32_le` 这类函数，我们实际就是这样检查的：先看 `crc32_body_micro` 开头是否变成我们想要的 `_base()` / `lea` 取址，再看表访问是否统一变成“基址寄存器 + 常量偏移 + 索引”，最后看重定位里是否还残留不该出现的绝对地址。
   只有这一步也通过了，后面的 guest/QEMU 性能结果才值得解释；否则即使函数能跑，实验形态也还是不干净。

7. 如果本地汇编不符合预期，就先在宿主机把改造收敛好，再进入 guest。
   例如之前 `crc32_le_micro` 的 `_base()` 我们先做过 `noinline` 版，再改成 `__always_inline` 版，然后重新检查汇编，确认 helper call 消失、`lea ...(%rip)` 直接出现在热路径开头。这一步的原则是：先把代码形态搞对，再去跑正式 benchmark，否则进 guest 后看到的性能差异很难解释。

8. 把 `*_micro` 的 builtin 源码并入 guest kernel 源码树。
   当前这一步由 [qemu/build_guest_kernels.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/build_guest_kernels.sh) 自动完成。脚本会把 [kernel/crc32_micro_builtin.c](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/kernel/crc32_micro_builtin.c) 覆盖进 guest 源码树的对应位置，再同步修改 guest 的 `Makefile` 和头文件声明。这样最终进入 `vmlinux` 的，是 guest 内建版本，而不是外部模块版。

9. 编译两套 guest kernel：`retpoline` 和 `noretpoline`。
   这一步同样由 [qemu/build_guest_kernels.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/build_guest_kernels.sh) 负责。我们保留两套 guest，是为了隔离 retpoline 对调用路径的影响，后续每个函数都用同样的二分法来跑。

10. 打包 initramfs，并把 benchmark 模块放进去。
    当前由 [qemu/build_guest_initramfs.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/build_guest_initramfs.sh) 完成。这里通常只把 benchmark 必需的模块和工具打进去，避免 guest 太重。当前 `crc32_le` 这条链路里，guest 会加载 `micro_pseudo.ko`，然后直接调用 guest 内建的 `crc32_le_micro`。

11. 启动 QEMU，分别运行 `retpoline` 和 `noretpoline` 两个 guest。
    当前主入口是 [qemu/run_micro_qemu.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/run_micro_qemu.sh)。它会自动做这些事：
    编译 guest kernel；
    打包 initramfs；
    启动两套 guest；
    把 benchmark 参数通过 kernel cmdline 传进去；
    把串口日志抓出来；
    最后解析成结构化结果文件。
    如果宿主机有 `/dev/kvm`，脚本会走 KVM；否则就退回 TCG。当前环境里如果退回 TCG，就要接受 guest `perf` 硬件 PMU 不可用这个现实，这时主要看 guest 内部的 `rdtsc` 周期结果。

12. 在 guest 里实际跑 `native` 和 `pseudo` 两个版本。
    这一层由 [qemu/guest_runner.sh](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/qemu/guest_runner.sh) 驱动。它会在同一套 guest 环境里依次跑：
    原生函数；
    PIC 改造后的函数；
    并把每轮的 result/perf 输出落盘。这里最重要的是保证两边输入一致、循环次数一致、校验值一致。

13. 先做结果正确性检查，再做性能分析。
    第一件事永远不是看快慢，而是看 checksum 是否一致。只有功能完全一致，这次 benchmark 才有意义。之后再看：
    `cycles/call`；
    `cycles/byte`；
    `retpoline` 和 `noretpoline` 的差异；
    `noinline` 和 `inline` 等不同改造形态的差异。

14. 把结果归档到 `results/<function>/`，并写 `SUMMARY.md`。
    这是最后一步，但很重要。每个函数都应该有自己的结果目录和总结文件，至少说明：
    跑的是哪两个版本；
    guest 环境是什么；
    主要结果是多少；
    checksum 是否一致；
    汇编和重定位上观察到了什么；
    如果出现“pseudo 反而更快/更慢”，解释是什么。
    当前 `crc32_le` 的结果就是这样整理在 [results/crc32_le](/home/zzk/BinaryKernelCodeMapping/test/test_MICRO/test_MICRO_pseudo/results/crc32_le) 下面的。

15. 如果结果不干净，就回到前面的某一步继续收敛，而不是硬写结论。
    比如：
    checksum 不一致，就回到 harness 或函数实现；
    汇编形态不对，就回到 PIC 改造；
    guest 编译选项和本地验证不一致，就回到 `analyze_guest_modules.sh`；
    性能结果解释不清，就补对照版，例如 `noinline` 和 `inline` 两版都保留。
    这一步的核心原则是：先把“功能、代码形态、运行环境”三件事都说清楚，再把结果写进论文。

如果压缩成一句话，这套流程其实就是：

先复制函数，再做 PIC 改造，再在宿主机确认汇编形态，之后并入 guest kernel，跑 `retpoline / noretpoline` 两套 QEMU，最后检查 checksum 和 cycles，并把结果按函数归档。

## 当前 example：crc32_le
`crc32_le` 当前状态：

- `noinline _base()` 版本已经完成并保留为诊断结果
- `inline _base()` 版本是当前接受的主结果
- 结论是：`crc32_le_micro` 在当前函数级 benchmark 中与原生 `crc32_le` 基本性能等效，少量“更快”的现象来自代码生成更紧凑，而不是 PIC 本身带来的算法性优势

后续新增函数时，建议沿用同一结构：

- 源码放进 `kernel/`
- 结果放进 `results/<function>/`
- 每个函数至少保留一个自己的 `README.md` 或 `SUMMARY.md`
