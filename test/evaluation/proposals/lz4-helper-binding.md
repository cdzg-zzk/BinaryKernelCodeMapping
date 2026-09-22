# LZ4 私有 helper slots 与实际用户绑定方案

状态：**已实施，修改后的完整 guest CLI 功能通过，正式性能待采集**（2026-09-12）。完整 owner、ELF 检查、bridge、builder/vkso 数据绑定集成已由实际导出和全部 24 组 input/block 功能验证覆盖。48 份调用记录核对到选中 carrier、libshim bridge 和 libc provider，四页 text 加一页 rodata 与 kernel PFN 匹配。结果见[应用证据](../lz4-application-evidence.md)。旧编译与故障诊断保留其构建身份，没有将旧性能数字当作新实现结果。

## 为什么采用已有的私有数据路线

`test/test_BCH/adapted/bch.c` 与 `test/test_xz/kmod/xz_private.h` 已将环境相关调用放在 owner 的私有函数指针中。各自 `module_meta.c` 用真实 kernel helper 初始化这些指针；当前 `build_PIC_so.py` 的 owner `.data` 路径能够把 `R_X86_64_64` 初始化转成 DSO 私有数据重定位。LZ4 可以采用这一机制，不需要换算法、换 builder、缩小工作负载或加入历史固定地址页。

但 LZ4 不能直接照搬全局 `#define memcpy`：`lz4defs.h` 的 `LZ4_memcpy`、`LZ4_memmove` 显式调用 `__builtin_*`；解压热路径还依赖 2/4/8/16 字节复制内联。把这些小复制全部改成函数调用，会改变本应保留的优化路径。

本方案分为相互依赖的两部分：完整 owner 用三个私有 slots；生成的用户数据把 slots 明确绑定到能够处理 kernel 栈对齐方式的用户 helper。仅第一部分编译通过，不能宣称完整绑定已经完成。

## Owner 改动：完整算法与现有 API 保持

[未应用补丁](lz4-helper-binding.patch)只改变四个 owner 源文件：

| 文件 | 具体改变 |
|---|---|
| `test/test_lz4/kmod/lz4defs.h` | 声明三个私有 slots；保留已知小常量复制的 builtin 内联；动态/大块复制、移动和清零经对应 slot |
| `test/test_lz4/kmod/lz4_compress.c` | 将 reset 的一次普通 memset、saveDict 的一次普通 memmove 接入相同 helper 宏 |
| `test/test_lz4/kmod/lz4_decompress.c` | 将完整字典路径中的一次普通 memmove 接入相同 helper 宏 |
| `test/test_lz4/kmod/module_meta.c` | 增加三个 8 字节函数指针，以 kernel `memcpy`、`memmove`、`memset` 初始化 |

没有删除 streaming/dictionary/error 路径，没有改变压缩级别、工作内存格式、输入/输出边界检查、选择的两个导出函数或完整 CLI 工作流。原来的小常量复制仍采用 builtin；`LZ4_copy8` 和 `LZ4_wildCopy` 本身不改。

正常内核装载时，模块重定位把三个 slots 初始化为本次内核的原生 helpers。调用者继续使用 `vkso_LZ4_compress_default` 与 `vkso_LZ4_decompress_safe` 的原型；不增加必需的 bind API 或调用参数。直接 helper 调用变成间接调用，成本及布局会改变，不能称为内核端零成本。

生成用户 DSO 时，slots 位于用户私有的 RW/NX 数据，保持相对于共享 text 的正确位置。重定位仅写用户私有数据；kernel slots 不会被用户的绑定修改。同一份**新编译 owner text**在 kernel/user 两端使用，不对已加载共享指令作重写。这不表示新旧 owner 的机器码相同。

## 仅有 slots 仍缺少栈 ABI 的明确绑定

原失败仍然是缺失直接调用目标页。新的编译检查另外揭示：普通 SysV 调用进入 `compress_default` 时 `rsp % 16 = 8`；其两次 push、对 `extState` 的 call，以及后者六次 push 和 `sub $0x48`，使第一次 memory helper 入口的 `rsp % 16 = 0`。普通 SysV helper 预期入口余数为 8。某个 libc leaf 恰好不使用要求对齐的栈访问，不足以建立通用 helper ABI。

现有 `make_dll/shim.c` 使用 `force_align_arg_pointer`，本来就意在处理这种边界。但是把 slot 动态重定位仍命名为 `memset`，不能确保选中该 wrapper：已有全局 libc 符号可能先满足它。attempt06 的 `info address memset` 指向 libc；这与名字叫 Shim 的配置不是同一个事实。

因此完整路线增加**显式的私有数据绑定契约**，不为了恢复旧文中的 REP 一致性增加新算法 API或 helper DSO：

1. 在现有 `libshim.so` 增加三个唯一命名的 `vkso_abi_memcpy`、`vkso_abi_memmove`、`vkso_abi_memset`。每个入口都使用 `force_align_arg_pointer`，然后调用真实 libc helper。候选代码见 [user bridge](lz4-helper-binding-user-bridge.c)。它通过显式 `dlopen("libc.so.6")` handle 解析三个函数，避免 bridge 内部再被同名的 legacy Shim 入口截获。handle 随该 shim 的生命周期持有；解析失败终止初始化，不进行未初始化调用。
2. `build_PIC_so.py` 增加可选 `--data-bindings` 输入。示例字段见 [binding contract](lz4-helper-binding-contract.json)。每条记录对应**一个明确的 owner slot 对象**、它在 `.ko` 中的 kernel 初始化符号及用户目标符号；本例用户库仍是现有 `libshim.so`。
3. Builder 检查该 slot 是非 init、可写且非可执行区域中的完整 8 字节对象，恰好对应一个 `R_X86_64_64`、addend 为 0、目标为指定 kernel helper 的初始化；拒绝缺失、重叠或不匹配记录。按 owner layout 得到其私有 data offset，只将这一位置的 DSO relocation 改为唯一用户 helper 名。保留原生 `.ko` 初始化和全部共享指令。
4. 原 helper 名仍参与原来的依赖边界分析；新名字仅是该私有数据 relocation 的用户目标。不能把这个映射应用于 text relocation，不能因此放过其他直接相对调用。[直接调用拒绝方案](export-direct-calls.md)仍需要共同实施，且检查器与 builder 应记录相同的绑定事实。
5. `vkso` 透传并归档 binding contract、最终 slot offset、原始目标、用户目标及输出身份；编译现有 shim 时加入相应 bridge 源及 `-ldl`。不新增全局 preload，不重写用户 libc。实际解析后的 slot 值与 bridge 内的 libc 指针在功能阶段记录，时间测量不混入这一诊断。

上述 builder/vkso/用户 binding 集成已通过合成 contract 测试，并在 binding attempt06 中从新 owner 的实际地址生成 live KRG，完成注册和完整 CLI 执行；旧 guest 的 KRG 未用于新 owner。

栈契约依据是 [x86-64 psABI 的 Stack Frame 规定](https://gitlab.com/x86-psABIs/x86-64-ABI/-/raw/master/x86-64-ABI/low-level-sys-info.tex)：普通调用在 call 前按 16 字节对齐，进入函数后 `(rsp + 8)` 对齐。[GCC 11.4 的 x86 function attributes 文档](https://gcc.gnu.org/onlinedocs/gcc-11.4.0/gcc/x86-Function-Attributes.html)说明 `force_align_arg_pointer` 可生成运行时栈重对齐的序言和尾声。这里的具体余数与实际 `and rsp, -16` 指令来自归档反汇编；属性名称本身不能替代最终指令和绑定目标核对。

## 编译证据及仍保留的限制

[验证脚本](lz4-helper-binding-validate.py)在 `lz4-helper-binding-validation/` 下分别编译完整原始/拟修改 owner，使用精确 `5.15.0-119-generic` headers、gcc-11 和原 Makefile；没有改变 flags。结果见 [validation JSON](lz4-helper-binding-validation.json)。

| 检查 | 原始 | 拟修改 |
|---|---:|---:|
| 完整 owner 中有函数体的符号 | 21 | 21，名称集合相同 |
| 对三个 memory helpers 的 text 直接重定位 | 34 | 0 |
| 三个 slots 的 RIP-relative 引用 | 0 | 34 |
| helper 的私有 `.data` R_X86_64_64 初始化 | 0 | 3 |
| `.text` 字节数 | 21,266 | 21,426 |
| 三个已知选中函数体覆盖的 `.text` 相对页 | 1、2、3 | 0、1、2、3 |

GCC 在此构建中使用 `mov slot(%rip), %rax` 然后 `call *%rax`。检查逐项追踪到间接调用，允许同函数内无条件跳转，并拒绝到达调用前覆盖该寄存器或遇到其他控制转移。初版检查错误地只接受直接内存操作数形式，后按实际完整 owner 指令修正并重查原编译输出；并非 owner 编译失败或换成更小程序。

常量内联仍可直接核查：拟修改 `decompress_safe` 的 `.text+0x3037/0x303b` 两个 8 字节 load 与 `0x3046/0x304c` 两个 store 完成 16 字节复制；`0x306c–0x3084` 保留 8+8+2 字节路径。`0x309d–0x30af` 与 `0x311c–0x312e` 保留 8 字节循环，未变成每次循环调用 helper。

完整 owner 仍有三个 `__ubsan_handle_out_of_bounds` 直接调用，全部位于 `vkso_LZ4_compress_fast_continue`；原始 owner 也有这三项。没有通过新关掉 sanitizer 或删除该函数来隐藏它们。选择的独立 block API 不走该 streaming API，但完整声明仍需由新 KRG/实际调用链确认。原有 `-mfunction-return=keep`、`-mindirect-branch=keep` 继续使用；Kbuild 的 naked-return/indirect-call 警告完整保留，不能把此 owner 称为发行版默认缓解配置。

最初的离线编译将候选 bridge 与当时完整的 shim.c 一起链接，仅作反汇编：三个唯一入口均在间接 libc 调用前 `and rsp, -16`。该离线步骤没有运行构造函数、wrappers 或修改后的 LZ4；后续 binding attempt06 才提供实际绑定、页面共享及完整输出证据。

上述四页是三个函数体的静态覆盖范围，不是最终 page map 或净内存数字。新增 slots 有 24 字节 payload，但会连同布局、私有数据、桥接库及元数据按真实驻留页计费，不能只报 24 字节而复用旧三页结论。[attempt03](../results/lz4-binding-qemu-20260912-attempt03/result.json) 当时受执行环境限制，无法访问 `/dev/kvm`。限制解除并补齐 owner BTF 与 guest `libdl.a` 后，[attempt06](../results/lz4-binding-qemu-20260912-attempt06/result.json) 完成运行，实际 page map 为四页 text 和一页 rodata；净内存仍需完整计费。

## 联动文件、owner descriptor 与实验重测

实施时除了四个 owner 文件，还要共同处理 `make_dll/build_PIC_so.py`、`make_dll/shim.c`、`vkso`、LZ4 的 binding config、`run.sh`/`run_under_replacement.sh` 的配置与身份记录，以及 `test/evaluation/lz4_guest.py`、`lz4_qemu.py` 的输入归档和运行观察。原有 API、官方 benchmark、完整 CLI 的 framing/I/O/校验行为不改变；adapter 只增加功能阶段的绑定身份记录。若新 shim 全局增加初始化工作，BCH/XZ 使用该 shim 的新部署也要记录版本和初始化成本。

[注册事务方案](registration-transactions.md)已在 `module_meta.c` 增加 owner descriptor。两项应共同形成最终构建：descriptor 是独立对齐的管理页，包含 `THIS_MODULE`，必须从用户导出排除；三个 helper slots 则属于应当被私有化、重定位的算法数据，不能随 descriptor 一并误删，也不能注册成共享源数据页。逐批次完成确认与错误传播已通过新 guest；cooperative owner pin 及正常释放又已通过 LZ4 验证；后续 [v3 事务](../registration-transaction-evidence.md)已通过 300 页回滚、QUERY 和恢复重试；槽位内替换和启动中断恢复已通过，其余生命周期仍待完成，本方案不替代它们。

在正式性能采集前，原计划要求的下列证据必须由最终实现重新获得：

- 新 owner 的内核装载、真实 native slot 目标和原选中 API 功能；同 flags 下原 owner/新 owner 的实际内核执行成本，另列与发行版默认构建的差别。现有原生 CryptoAPI/内核调用者不会自动改为调用改名 owner。
- 新 live KRG、完整静态分析、最终 DSO/数据重定位与实际调用点；确认所有 helper slot 私有、内核目标未被改变、用户目标进入唯一 ABI bridge、其后为所记录的 libc 实现。真实共享 text/rodata PFN、权限和原计划的恢复边界需要重测。
- 全 12 个 Silesia 文件 × 64 KiB/1 MiB × 压缩/解压的 24 对功能组合，保留完整输出校验、stock 交叉解码、算法与 helper 的实际入口身份。通过后再按 C 的三次独立部署和 E 的完整 CLI 计时矩阵执行。
- 重算 B 的 source-page union、私有 PGOT/DSO/页表、owner 新增驻留、shim 初始化与 setup-to-first-valid-result。新布局不能沿用旧 PFN 页数或旧脚本运行时间。
- 保留五个原算法后端和全部应用对照。新 kernel-backed 路线采用所记录的 libc helper；同源 no-SIMD 原对照使用自己的 REP helpers，二者 helper policy 不同，不能再将比值解释为仅 PGOT/放置成本，也不能称整个新路径没有 SIMD。单纯机制成本继续由原计划的 PGOT/copy-closure 对照及实际内核对照提供，不能改写旧 REP 身份来制造公平性。

旧 Table 9 和历史原始数据保留为旧构建观察。上述最终实现通过且重新采集后，再更新对应 C/E/B 结果与适配表；冻结的 Clocktime 实验不因本 proposal 重新执行。
