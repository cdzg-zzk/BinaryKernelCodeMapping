# VKSO: Zero-copy Rehosting of Resident Kernel Code as User-space Shared Objects

## Abstract

操作系统内核和用户态经常重复实现 checksum、compression、format parsing 以及只读状态转换等计算。让应用通过 syscall 请求内核执行可以避免代码复制，却为高频短函数保留 privilege-crossing cost；重新维护一份用户态实现则会带来代码重复和 semantic drift。我们提出 VKSO，一种将**当前运行内核中已经驻留的机器码页**零拷贝重宿主为标准 user-space shared object 的机制。VKSO 从最终机器码出发，以 state、control 和 code-shape constraints 界定可复用的 binary closure；standard carrier 保留 ELF/loader 语义，page grafting 复用 resident physical pages，Shim 则显式承接 kernel/user execution environments 之间的依赖。Linux 5.15 原型的字节一致 XXH32 对照得到相同的 hot-call 批次中位数均值；真实算法的用户与内核执行成本随依赖适配、构建条件及输入路径变化。作为完整子系统案例，我们重构 Linux clocktime，使内核 reader 与用户态 fast path 共享内核驻留时间计算代码，并以 VKSO 替换原生 x86-64 vDSO time/getcpu 路径。32 次独立启动显示，normal 构建的 13 个非 fallback 公开 READ 路径以完整均值计算的等权几何平均成本降低 3.87%，其中七种 `clock_gettime` fast path 的集合增加 2.57%；UPDATE 成本还随持续读取负载变化。共享代码页保持内核与用户 PFN 一致，而每 MM 支持页增加了所测用户映射的驻留页数。完整 LZ4 应用进一步显示，注册复用后的执行成本与每次建立、释放的成本需要分别评估。经过显式状态和环境解耦的内核计算能够由两域共享同一执行体，其实际代价由适配方式与使用负载共同决定。

# Introduction

内核与用户程序并不总是需要不同的计算语义。Checksum、compression、format parsing 和只读状态转换等功能经常同时出现在 kernel and user space；然而 privilege boundary 使用户程序无法直接使用运行内核中的实现。系统因此通常在“通过 syscall 请求内核执行”和“维护第二份用户态实现”之间选择。前者为每次调用保留边界成本，后者则要求安全修复、优化和边界语义在两个实现中同步演化。

一个看似直接的办法是把内核 `.text` 映射到用户空间，但物理可达性并不等于可执行的程序接口。目标函数还隐含依赖对象布局、relocations、helper targets、动态状态、同步协议和经过启动期改写的最终控制流。若这些依赖没有形成闭包，简单映射只会把错误推迟为用户态非法地址、错误跳转或状态不一致。本文因此围绕三个问题展开：**什么样的 kernel-resident binary closure 可以安全复用，如何在不复制执行体的前提下将其重宿主到用户空间，以及这种复用减少了哪些重复、付出多少部署与执行代价？**

VKSO 的关键洞察是把三个通常耦合的问题分开处理。最终机器码上的 state、control 和 code-shape dependencies 共同决定复用边界；standard shared object 只承载应用可见的对象语义，实际执行体由 resident kernel pages 提供；Shim 则将共享计算与原生执行环境分离，使可等价重建的依赖在各自 domain 内完成绑定。分析、转换和绑定发生在构建或装载边界，首次访问仍走原生 file-backed fault path；稳态调用因此是 ordinary shared-library call，而不是新的跨域 RPC。

本文作出三项贡献：

- 提出一组面向最终机器码的 state、control 和 code-shape constraints，将“可否复用”归结为可审核的 binary-closure eligibility problem，并规定目标需要满足的复用条件。
- 设计并实现函数级 resident binary rehosting mechanism：构造可跨地址空间执行的代码闭包，以标准 Stub DSO 保留对象语义，通过 page grafting 复用同一物理执行体，并以 Shim 分离 kernel/user execution environments。
- 用机制级 microbenchmarks、代表性 kernel algorithms 和完整 Linux clocktime case study 评估这一路径：XXH32 hot-call 基准比较字节一致的两种代码后备，copied closures 和同源算法给出所测配置的适配成本，clocktime 则检验共享状态与并发 publisher/readers 下的端到端行为。

在 Linux 5.15 原型的 XXH32 基准中，两种后备的 hot-call 批次中位数均值均为 71 cycles。BCH 的 t=8、两错误 precomputed decode 相对原始源码用户 DSO 的成本变化为 −10.00%，完整错误数扫描仍保留路径相关的开销。完整 LZ4 CLI 在活动注册下的同源成本接近，包含注册和释放的单遍完整任务则为 native 的 1.717 倍。Clocktime 的 13 个非 fallback 公开路径在 normal 构建下，以完整均值计算的等权几何平均成本降低 3.87%，但七种 `clock_gettime` fast path 的集合增加 2.57%；状态发布及每 MM 支持页也有独立代价。这些结果区分了同一执行体复用、部署摊销和具体调用成本；BCH 的库与专用 owner 账本也没有显示净页节省。

# Background and Motivation



## Privilege Isolation and Cross-boundary Calls

特权隔离要求应用通过 syscall 或 IPC 请求需要内核介入的服务。传统同步 syscall 除目标逻辑外，还会引入用户态与内核态之间的控制转移及相关处理器状态扰动；具体请求路径还可能包含参数检查、数据传递或调度等额外工作。已有研究表明，同步跨界会产生直接的 kernel crossing cost，并可能扰动 pipeline、TLB 和 cache 等处理器状态。[33,35] 这些成本的绝对值及其在完整请求中的占比取决于硬件和具体执行路径，但每次跨界都引入了额外的机制工作。随着操作粒度减小，可用于摊薄这部分工作的有效计算也相应减少，使重复跨界在细粒度、高频调用中更加突出。Linux vDSO 为部分适合在用户态完成的操作提供直接调用入口，也体现了在此类路径中避免重复进入内核的设计价值。[31]

这一优化空间只存在于部分内核计算中。需要访问 privileged state、执行权限检查、修改内核对象或产生特权副作用的操作，仍然需要内核介入。本文关注另一类计算：它们由内核提供，但后续调用本身不再需要特权执行。对于这类计算，重复进入内核带来的 privilege transition 成为了可以避免的调用成本。VKSO 使应用能够在用户地址空间直接执行这部分计算，从而从稳态调用路径中消除重复跨界。对于仍需特权执行的操作，应用继续通过原有系统接口进入内核。

## Cost of Duplicated Implementations

当用户态需要内核已有的计算逻辑，又希望避免反复跨界时，一种直接做法是在用户态重新实现相同或相近的功能，由此形成 kernel/user 双重实现。文件系统提供了典型实例。Rump File Systems 指出，e2fsprogs 和 mtools 等工具在用户态重新实现了内核已有的大量文件系统逻辑，其中 e2fsprogs 还需要持续跟踪 Linux 文件系统特性的演化。[30] 作为独立的定量案例，该工作在 makefs 中直接复用 kernel FFS implementation，使 FFS-specific code 从 1,748 SLOC 降至 247 SLOC，并将报告的实现工作量从至少 100 小时降至约 2 小时。[30] 这说明一旦执行环境迫使软件维护独立的功能实现，代码复制、特性跟进和边界语义同步就会成为持续成本。

VKSO 关注其中能够保持相同计算语义的一部分功能，使用户态直接复用由内核提供的实现，从而避免为消除跨界而维护第二份同语义代码。对于依赖不同权限策略、特权状态、对象所有权或同步语义的功能，仍保留原有实现和执行路径。

## Existing Reuse Mechanisms

- **接口式复用 Service-based Reuse**：系统可以保留 kernel implementation，只向用户态开放受控服务。例如，Linux AF_ALG 允许应用通过 socket 选择 kernel crypto algorithm，并使用 `send`/`write` 和 `read`/`recv` 完成请求。[32] 这类接口保留了原生内核所有权，却要求每次操作经过 syscall、参数传递和边界检查；它适合较粗粒度服务，而不能把短小计算转化为普通用户态函数调用。
- **抽取式复用 Source Extraction**：LKL 和 Rump 的经验表明，从 kernel tree 抽取 VFS 或 file-system code 仍需要手工补充 locks、allocators 与其他关联基础设施，并持续适配内部依赖。[29,30] 这种方法能够得到细粒度用户态实现，但并未消除第二份 executable image 及其维护成本。
- **内核或子系统重宿主 Kernel/Subsystem Rehosting**：LKL 将 Linux kernel 组织为可在用户空间运行的 library，Rump Filesystems 则把 kernel file-system code 与提供所需 kernel interfaces 的 `librump` 一同带入用户环境。[29,30] 它们适合复用大范围 kernel APIs 或完整 subsystem semantics，但会生成新的用户态执行镜像并携带相应 host/adaptation environment；对于只需一个高频函数的场景，复用粒度和环境规模都偏大。
- **专用用户态快速路径 Purpose-built User Fast Paths**：Linux vDSO 证明了内核可以向进程映射标准 ELF image，使部分高频查询通过普通 ABI 函数调用完成。[31] 然而，vDSO 由内核按 architecture and stable ABI 单独选择、实现和构建导出内容；它适合少量长期维护的接口，但不是面向一般、满足约束的 final-binary closure 的通用重宿主机制。

这些方法分别保留了原生内核服务、复用了源码、重宿主了较大的 kernel environment，或为少量接口建立了专用 fast path，但均在至少一个关键维度上与本文目标不同：它们不能同时获得 **function-level rehostable closure**、复用当前运行内核中的同一 **resident execution body**、保持 **ordinary user-space call**，并以统一方式显式承接跨环境依赖。这一组合缺口构成 VKSO 的设计出发点。

这些路径的共同限制是执行体仍属于原来的 domain。异步 syscall 和轻量特权执行可以减少边界成本，但仍围绕服务请求或受限特权环境组织执行，不能把已驻留的 kernel binary 直接变成普通用户态函数。[33,35] RPC、kernel bypass 和用户态重写则把控制权交给另一份用户态实现或专用数据平面，因而需要复制算法、数据格式和更新逻辑。[34] 它们分别优化了调用协议或执行位置，却没有同时解决“复用同一机器码”和“显式承接内核状态依赖”这两个问题。

## General-Purpose Operating-System Substrates

尽管现代 general-purpose OS 在对象格式、内核对象命名和内部实现上彼此不同，它们在代码装载、虚拟内存组织以及按需安装路径上仍共享若干更高层的抽象结构。VKSO 依赖的系统背景可以归纳为四类 common substrate：**shared-object loader、object-backed mapping、cache/object layer，以及 first-touch installation**。

第一类是 **shared-object loader**。现代通用操作系统普遍提供标准化的共享对象承载形式，以及在进程启动或运行时将外部对象纳入地址空间的加载器机制。无论具体格式是 ELF、PE/DLL 还是 Mach-O，这类机制都使代码对象能够以用户态可链接、可装载、可命名的标准形态进入进程视图，而无需在编译阶段将其全部内容固定到最终可执行文件中。

第二类是 **object-backed mapping**。在这些系统中，进程中的可执行或可访问区域通常并不被视为对某份物理实现的直接硬编码，而是通过某种对象化映射关系与底层后备建立联系。换言之，进程所看到的是一个由映射对象承接的执行视图，而非单纯将某个文件字节流整体复制进地址空间。

第三类是 **cache / object layer**。在映射对象与物理页之间，主流操作系统通常都保留了一层抽象的缓存或对象组织结构，用于管理对象后备、页级驻留状态以及对象与页之间的关联关系。该层在不同系统中有不同名称和数据结构，但它们共同体现出同一个事实：执行视图与物理页之间并不是直接、扁平且不可管理的关系，而是通过中间层组织起来的。

第四类是 **first-touch installation**。共享对象或文件后备映射通常并不会在装载时一次性将全部代码页预先安装到进程页表中。相反，页面往往在首次访问时通过 page-fault 等按需路径完成建立、填充或恢复执行。这意味着，代码对象的逻辑承载与其物理页安装时刻在系统中天然是分离的。

Table 1 对 Linux、Windows、macOS 和 FreeBSD 中与上述四类 substrate 对应的典型机制作了并列归纳。[1–24]

**Table 1: Common OS substrates relevant to transparent code reuse.**


| OS      | shared object loader                               | mapping object                                      | cache / object layer                                                                        | first-touch installation                                    |
| ------- | -------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Linux   | ELF `ld.so`。[2]                                    | `mmap(2)`、VMA、file-backed mapping。[1,4]             | `address_space`、`i_pages`、`i_mmap`、page cache。[5,6]                                         | page-fault 路径按需建立页表；默认并非预装全部页，`MAP_POPULATE` 只是显式预取变体。[1,3] |
| Windows | PE/DLL load-time / run-time dynamic linking。[8–10] | section object / mapped view / file mapping。[11,14] | `SECTION_OBJECT_POINTERS`、`DataSectionObject`、`SharedCacheMap`、`ImageSectionObject`。[12,13] | 视图访问前不分配物理页；首次访问触发 page-fault，再把 file-backed 内容调入内存。[11]    |
| macOS   | Mach-O image `dyld`。[15–17]                        | VM object / memory object / vnode pager。[18,19]     | VM object、UBC、vnode-backed caching。[18–20]                                                  | page-fault handler 在首次缺页时装页、更新页表并恢复执行。[18]                  |
| FreeBSD | ELF `rtld` / `ld-elf.so.1`。[21]                    | `mmap(2)`、`vm_object_t`、`vm_map_t`。[22,24]          | UBC、`vm_object_t`、vnode-backed objects。[23,24]                                              | zerofill fault、reactivation fault 与从磁盘调页共同构成按需安装路径。[23,24]  |


这些系统的命名方式和内部实现并不相同，但都提供共享对象承载、对象化映射、缓存/对象层间接组织以及首次触达驱动的按需安装路径。这里的共性只用于说明 VKSO 所依赖的抽象边界，并不把 Linux 原型的 grafting 实现或性能数字外推到其他系统。

# Design for General-Purpose Operating Systems

上述内容提到，高频短函数同时受到 syscall crossing cost 和重复实现的影响。VKSO 的核心思想是：从最终 kernel binary 中构造一个能够跨执行环境保持语义的 machine-code closure，再以标准用户态对象 rehost 当前内核已经驻留的执行页。设计需要同时满足三个相互关联的要求：

- R1：识别真正适合复用的计算
- R2：解除其对原生 kernel environment 的隐式依赖
- R3：让用户进程通过受保护的标准入口访问被复用的代码。

前两个要求由同一个 reuse contract 统一约束。它规定 closure 能观察哪些状态、能够到达哪些控制目标，以及同一机器码在不同地址布局中必须保持哪些关系；environment separation 负责把可重建的地址和语义依赖转化为显式契约。第三个要求则由 standard carrier、page grafting 和 permission-separated mappings 实现，使应用获得 ordinary shared-library call，而不复制 execution body 或引入每次调用的 mediation。

VKSO 只处理由内核开发者明确选择、能够在确定 kernel build 上形成 rehostable closure 的目标，不替代需要特权执行的 syscall 接口。Binary analysis 能检查依赖闭合、地址关系和页面权限，但不能自动证明任意 C 程序的高层语义；需要操作 privileged objects、依赖不可重建同步域或无法解释最终控制流的功能仍位于 reuse boundary 之外。

## Architecture Overview

Figure 1 概括三个设计要求及其关系。**Candidate** 是开发者希望复用的 final-binary entry 及其可达依赖；**rehostable closure** 是满足 reuse contract 的机器码、closure-local data 和显式 environment contract。Reuse contract 给出闭包成立的必要条件，environment separation 则说明哪些原本隐含于 kernel context 的依赖可以转换为跨 domain 的显式接口。不能直接纳入 closure、也不能通过该接口保持语义的依赖位于 reuse boundary 之外。

可复用性首先取决于 closure 是否满足 state、control 和 code-shape constraints。PIC-compatible construction 和 Shim 再解除能够承接的地址与语义依赖，从而扩大可证明的复用范围。三者共同决定了 closure 的组成和环境边界。

访问要求将 rehostable closure 的**对象语义**与**物理后备**分开。Standard carrier 负责应用可见的符号、ABI、布局和装载权限；page grafting 让 carrier 中选定 logical pages 引用 resident kernel code/rodata pages；Shim 则在各 execution domain 中提供 closure 已声明的环境接口。应用最终沿 ordinary shared-library call 进入同一执行体，而不是调用另一个副本。

这一流程保持三项不变式。第一，**single-execution-body invariant** 要求 kernel and user mappings 中的共享计算执行同一组只读机器码页，domain-private entries 负责到达该执行体。第二，**explicit-environment invariant** 要求每项非参数依赖属于 closure 或具有经过审核的 environment contract。第三，**permission-separation invariant** 要求用户映射不能获得内核状态的写权限、privileged virtual alias 或修改共享执行体的能力。VKSO 因而共享的是满足 contract 的计算，而不是 privileged execution context。

**Figure 1: Constructing and rehosting a resident binary closure.** The reuse contract defines a valid closure, while PIC-compatible construction and Shim contracts separate reusable computation from its execution environment. A standard carrier and page grafting then expose the closure through an ordinary user-space function call.

## Constructing a Rehostable Binary Closure



### The Reuse Contract

Reuse contract 直接定义 **rehostable closure**：能够在 kernel/user domains 中执行的同一组机器码页、closure-local data，以及共享计算所需的显式 environment contract。它不是要求未经修改的 kernel function 天然与环境无关，而是规定完成允许的 environment separation 后仍必须成立的 state、control 和 code-shape properties。

第一，**state contract** 要求每项非参数数据具有明确的 owner、writer、consistency protocol、mapping permission 和 lifetime。“用户只读”不等于“数据不可变”：VKSO 允许内核继续更新被发布的状态，只要 kernel 是唯一合法 writer、user mapping 始终只读，并且 reader 能依照声明的 publication protocol 获得 coherent snapshot。数据依赖据此分为四类：


| State class                    | Required property                                                                 | Contract outcome                  |
| ------------------------------ | --------------------------------------------------------------------------------- | --------------------------------- |
| Immutable closure data         | 构建后不再变化，且全部字节均可向 consumer 暴露                                                      | 与机器码共同构成只读 closure                |
| Kernel-published mutable state | kernel 保留 write ownership；user 只有 read-only view；存在 coherent publication protocol | 作为显式 published input 供 closure 读取 |
| Environment-adaptable state    | 各 domain 可以在不共享 privileged ownership 的情况下重建相同可观察语义                                | 通过 Shim contract 显式提供             |
| Incompatible state             | 依赖 privileged object、不可重建同步域、设备上下文或无法外部化的状态                                       | candidate 不满足 contract            |


Publication protocol 是 design requirement，而不是固定算法。单字原子状态、versioned snapshot 或 reader-verifiable sequence protocol 都可以满足 contract；具体实现必须证明用户不会观察到 torn multi-field state，且更新成本和对象生命周期符合声明。用户态存在同名对象或 API，也不说明它与内核对象属于相同同步域。

第二，**control contract** 要求从导出入口可达的 direct calls、indirect branches、tail jumps、relocations 和 external symbols 全部可解释。目标要么位于 closure 内，要么绑定到语义等价的 Shim endpoint。无法解析目标集合、要求 privileged side effects 或依赖 kernel-only fault/synchronization semantics 的控制转移不满足 contract。

第三，**code-shape contract** 面向系统最终实际执行的机器码，而不是源码或链接前 object。所有 address materialization、relocations and control transfers 必须在 kernel/user virtual layouts 中保持正确；compiler instrumentation、indirect-branch mitigation、tracing、static keys 和 boot-time rewriting 产生的实际目标也必须属于最终 closure。运行时不能修改共享只读执行体来掩盖不兼容。

三项 properties 共同界定“什么是可重宿主 closure”：state contract 规定计算可以观察什么，control contract 规定执行能够到达哪里，code-shape contract 规定同一机器码能否在不同地址空间中保持前两者。Candidate 是否可复用，取决于其依赖能否直接归入 closure，或通过允许的 environment separation 满足这些 properties。

### Satisfying the Contract through Environment Separation

Reuse contract 不把适用范围限制为天然纯净的 kernel functions。一个依赖可以成为 closure-local code/data，也可以在 ownership and observable semantics 保持不变的前提下被表达为 environment contract；只有两种方式都无法承接的依赖才使 candidate 不可复用。因此，实际 reuse boundary 由 contract 与系统能够提供的 environment separation 共同决定，而不是一张静态函数白名单。

环境解耦包含两个维度。**Address-environment separation** 将 closure 内地址关系限制为跨装载布局仍成立的 PIC-compatible form。系统可以保持相对拓扑、施加局部构建约束或修复可验证的地址形成方式，但不声称能把任意 kernel binary 自动转换为 PIC。若地址指向 closure 之外的 privileged object，改变指令形式并不能使其可复用。

**Semantic-environment separation** 由 Shim contract 完成。Shim 定义共享计算可以从 execution domain 获得哪些输入和 helper semantics；kernel and user implementations 可以使用不同地址和局部机制，但对 closure 可观察的结果、副作用、同步和失败语义必须等价。Shim 的作用不是复制整个 kernel environment，而是把原本隐式的环境依赖收敛为一个最小、可审核的 boundary。

### Separating State by Ownership and Lifetime

有状态计算需要同时访问系统持续更新的输入、当前地址空间的语义视图，以及只在当前 execution domain 有效的地址。它们具有不同的 owner、更新频率和生命周期。将这些依赖放入同一个共享对象，会把全局更新与进程管理耦合起来，也使共享指令依赖某个 domain 的地址布局。VKSO 据此将环境依赖组织为 kernel-published state、address-space-local state 和 domain-local context。

Kernel-published state 保存多个 consumer 共用的计算输入。内核保留更新所有权，并通过只读映射与 publication protocol 向 kernel/user readers 提供一致的观察结果。Address-space-local state 保存影响计算语义的局部视图，随所属地址空间建立和释放，只在该视图变化时更新。两者的更新路径相互独立，因此全局 producer 无需为每个进程维护一份相同快照。

Domain-local context 保存当前环境中的 helper、provider aliases 和失败处理入口。它由各 domain 分别构造，通过显式参数交给共享计算。这样，状态值的发布与地址的绑定形成不同接口：内核定义哪些值可读，入口适配层提供在哪里读取以及如何完成环境相关操作。共享执行体只依赖这些接口，具体子系统负责定义数据字段与语义。

### Preserving Public Interfaces through Private Entries

共享计算所需的依赖通常多于应用接口中的显式参数。VKSO 在 carrier 中提供 domain-private entry，将普通 public ABI 转换为 shared-core ABI。入口沿用应用可见的参数和返回约定，补充已绑定的地址空间状态与 context，再通过直接调用或尾跳转进入共享执行体。内核入口执行相同的适配职责，传入内核有效的依赖。共享计算的机器码保持唯一，入口和地址槽位则由各 domain 持有。

入口适配还决定哪些请求可以使用共享计算。能够从请求参数判定的原生操作在入口完成分流；需要执行后才能发现的 provider failure 则通过声明的 context callback 返回所属环境处理。两类出口使 shared core 保持共同的计算语义，同时让权限相关操作、系统调用和失败恢复继续由原生环境完成。回退路径必须能够独立完成请求，避免重新进入刚刚失败的共享计算。

## Rehosting the Rehostable Closure



### Separating Object Semantics from Physical Backing

Rehostable closure 仍然只是一组机器码、数据页和环境契约。应用和 loader 还需要 object identity、exported symbols、ABI、relocations、virtual layout 和 segment permissions。VKSO 因而构造一个 **standard carrier**：它提供完整的 shared-object semantics，但不包含另一份 reusable execution payload。对象语义与执行后备的分离，使应用能够沿现有 software workflow 使用 closure，同时让物理实现继续由运行内核拥有。

该分离还避免把“共享代码”误写成“共享内核虚拟地址”。Kernel and user mappings 可以位于不同 virtual addresses；只要 closure 的内部关系和 environment contract 均已满足，它们就能引用同一物理执行体。Carrier 中属于 loader 或 execution domain 的 writable state 保持本地，不会写入 resident code/rodata pages。

### Resident-page Grafting

General-purpose OSes 已经在 shared object、logical mapping 和 physical backing 之间保留 object/memory layer。Page grafting 利用这一间接关系：carrier 先按普通 shared object 建立 logical executable/readonly regions，系统再把其中声明的 logical pages 绑定到已经驻留的 kernel code/rodata pages。进程看到的符号地址、对象布局和权限不变，改变的只是 selected pages 的 backing identity。

Grafting 必须同时保持 page identity、permission and lifetime。共享代码在 kernel and user mappings 中均不可写；user alias 只能获得声明的 RX or R-- permissions。Kernel-published mutable state 可以由 kernel 持有 writable mapping、由 user 持有 read-only mapping，但它遵循独立的 publication contract，不能因代码页面复用而获得额外权限。只要任一 resident page 或其 owner 的生命周期无法覆盖用户映射，系统就不能建立或继续保留 grafting relationship。

### Transparent and Off-path Execution

Carrier 遵循 standard shared-object ABI，应用通过已有 linker/loader 和 ordinary function symbol 使用共享 closure。无需附加依赖的入口直接导出共享函数；有环境依赖的入口通过 carrier-private wrapper 补充参数。装载建立普通 object-backed virtual mappings，selected pages 由系统的 native first-touch path 按需安装。

Closure construction、初始 environment binding 和 physical-backing setup 均位于 steady-state path 之外。First touch 完成后，共享计算路径只承担普通函数调用、必要的入口分类与参数传递，以及 closure 本身的执行成本；符号解析、代码修补和页面替换不进入每次调用。状态更新沿各自的 publication path 进行，入口继续使用已绑定的地址。这使动态输入可以变化，而共享机器码及其访问方式保持稳定。

# Linux Implementation

我们在 Linux 5.15.198/x86-64 上实现 VKSO。Build-time builder 从 final kernel/LKM ELF 生成 closure manifest 和 Stub DSO，并接入可选的 private wrapper；kernel manager 验证运行实例并注册 resident backing；environment layer 以 `shared_data`、`MM_data`、private context 和 Shim 实现跨域依赖。Builder 负责依赖闭合与对象布局，内核负责发布状态和映射生命周期，入口适配层负责 ABI 转换与环境绑定。下面说明这些项目能力的实现，并以 clocktime 给出具体的数据与接口实例。

## Build-time Closure and Carrier Generation

Builder 为每组开发者选择的 final-binary entries 生成两个耦合产物：描述 source pages、依赖和权限的 closure manifest，以及提供 ELF object semantics 的 Stub DSO。它先分析已链接 kernel/LKM ELF 上的 code、data and control dependencies，再根据跨布局地址约束构造 carrier。Export author 提供入口与环境契约；静态结果和实际绑定需要结合运行验证核对。

### ELF Closure Analysis and Runtime Validation

原型以已链接 ELF 的 symbol、section、relocation 和 disassembly 为输入，从导出入口收集可解析的 code/data dependencies。Checker 分别记录静态引用、Shim 命中、间接控制流和编译插桩；致命指令或地址检查失败产生 FAIL，缺失依赖或无法分析的函数产生 INCOMPLETE。间接控制流与插桩记录本身不必使结果失败，因此 PASS 表示当前检查项通过，不能单独证明所有执行目标已经闭合。

Builder 按依赖分类形成共享 regions、私有数据重定位、Shim imports 和 synthetic targets，并输出 source addresses、file offsets 与 backing 类型。ELF 分析使用镜像中的指令，运行时地址用于确定布局；它没有全面重建装载及启动期改写后的控制流。Evaluation 因而分别核对静态检查、实际 carrier、PFN 和完整调用结果。LZ4 应用验证发现，旧路径会放行没有重绑定位置的直接 Shim 调用。修订后的分析器与 builder 拒绝这类引用；适配 owner 通过显式私有数据 slots 绑定用户 helper。

### PIC-Compatible Code Shape

VKSO 不把任意 non-PIC kernel binary 自动翻译为 PIC。Builder 只接受两类对象：最终机器码本身只依赖 closure-internal relative relationships；或者不兼容的地址生成能够通过局部、可审核的 source/build constraint 修复，而不改变计算语义。Linux/x86-64 中，普通 `%rip`-relative references 可以由 topology-preserving layout 保留；危险情况是源码把函数或对象地址作为值使用，导致 non-PIC code model 在 `.text` 中 materialize original kernel VA。

对此，原型在源码或构建边界将绝对基址生成改为 PC-relative form。典型做法是通过 `%rip`-relative `lea` 取得 closure object 的当前装载基址，再基于该寄存器进行地址传递、比较或动态索引。该 repair 仅改变地址的形成方式；目标仍必须位于已经批准的 closure 内。若地址指向 privileged object 或无法重宿主的数据，builder 不进行二进制猜测，而是拒绝该 target。

函数指针或对象指针等 domain-specific addresses 不能通过保持相对拓扑解决。Analyzer 将这类依赖标记为 private binding，并要求 carrier 为其生成可重定位槽位；Pseudo-GOT 在后文负责完成这类 binding。

### Topology-preserving Stub DSO via Sparse Layout

Stub DSO 是一个合法的 ETDYN carrier：它提供 exported symbols、dynamic metadata、ABI、virtual layout and segment permissions，却不携带另一份 reusable `.text/.rodata` payload。由于 x86-64 closure 中的 `%rip`-relative references 编码了 source and target 之间的位移，builder 按原 kernel/LKM image 的相对拓扑放置 reusable regions，而不把选中的 symbols 紧凑重排。

Builder 将选中的 `.text` 和 `.rodata` ranges 扩展到页边界，合并连续或重叠页面，并分别形成 RX and R-- `PT_LOAD` segments。Segment file offset、virtual address and alignment 同时满足 ELF 与 Linux file mapping 约束；不同 regions 之间只需在 virtual layout 中保留 logical gaps，不为 padding 分配文件内容。

Reusable regions 在 ELF 中保持 `p_filesz = p_memsz`，使 `ld.so` 将其视为普通 file-backed ranges，而不是匿名 `.bss`；builder 随后以 sparse-file holes 保留这些 file offsets，不写入 resident payload。ELF headers、dynamic symbol/hash tables、relocations 以及 Pseudo-GOT 等 carrier-private writable data 则真实物化。结果是一个可由标准 loader 识别的 shared object，其 logical slots 可在 runtime 绑定到 kernel-owned pages。

### Carrier-private Wrapper Construction

为保持 public ABI，同时向 shared core 传入环境依赖，builder 支持将一个 PIC-compatible ET_REL wrapper object 合入 Stub DSO。Wrapper 通过 `.vkso.user.text` 声明私有入口，通过 `.vkso.user.data` 声明 context 与地址槽位。当前布局为两类 section 各保留最多一页，分别使用普通文件后备的 RX text 和进程私有的 RW data；这些页面与 grafted kernel pages 具有独立的 backing identity。

Builder 从 wrapper text 的重定位中提取外部符号，将它们加入 closure 的 dependency roots。依赖根与 public exports 分开管理，因此内部 shared-core helper 可以参与链接而无需成为应用接口。对象布局确定后，builder 将 `R_X86_64_PC32` 和 `R_X86_64_PLT32` 重定位解析为指向 shared core 或 wrapper-local data 的相对位移，并检查 rel32 范围。Wrapper 到 shared core 的转移在构建时直接解析，热路径无需经过 PLT/GOT 查找。

Wrapper text 在 DSO 中保存实际机器码字节，导出符号标记为 `replace_from_kernel=False`，从页面替换计划中排除。可复用算法仍由 resident kernel pages 提供；私有入口只承担参数注入、请求分类和环境相关出口。该构建接口按 section 和 relocation contract 工作，具体 feature 通过自己的 wrapper object 定义 public ABI。

### Segment and Backing Classes

Builder 不按原始 ELF section name 猜测权限，而是在 manifest 中为每个页声明 source、backing class and final user permission。`resident_text` 只能映射为 user RX，`resident_rodata` 和 kernel-published state 只能映射为 user R--/NX；ELF metadata、relocation slots and carrier-private writable sections 使用普通 file/COW backing，绝不指向 kernel PFN。Builder 拒绝 executable/writable overlap、非页对齐 binding，以及只允许暴露部分字节的 resident data page。

这一层只决定对象布局和页面权限，不决定某项环境依赖在语义上能否共享。后者必须先满足 reuse contract，再由 published input、address-space-local context、Shim 或 domain-local binding 承接；section layout 不能替代 state/control eligibility decision。

## Load-time Validation and Resident-page Grafting

Kernel manager 消费 builder 生成的 manifest，并把其中的 logical carrier pages 与当前运行 kernel/LKM instance 对应起来。装载流程核对 runtime text 和页面计划，再请求注册 resident backing。LKM owner 的驻留和清理由部署 runner 管理。Stub DSO 的 ELF identity 和 loader-visible layout 在这一过程中保持不变。

### Final Runtime Machine-code Validation

Link-time closure 并不自动等于正在运行的 closure。Linux/x86-64 的 compiler instrumentation、static alternatives 和 boot-time rewriting 可能在链接后改变控制目标。当前 manager 在 owner 被引用固定后核对 manifest 中的链接产物身份；共享代码的构建配置与实际执行路径另由各 feature 验证。对不影响 target semantics 的 instrumentation，原型使用局部构建选项关闭；对最终目标稳定且可审核的改写，将实际 target page 显式纳入 closure；对只实现闭包内控制转移的 thunk，则构造语义等价且目标明确的 synthetic direct-jump thunk。链接产物身份核对不等于逐指令核验运行时 closure。

Indirect Target Selection（ITS）说明了运行时目标核对的必要性：编译时可见的 retpoline thunk 可能在启动期被改写为 dynamic ITS thunk。若 manifest 只包含原 thunk page，用户路径会到达未导出的目标。所测配置使用 synthetic direct jump，或将经过验证的 native RX target page 标记为 `reusable_text`。这种 feature 级处理显式补齐实际依赖；通用注册接口目前按 owner 范围、声明类型、实际映射权限及页状态准入，尚未提供逐指令的运行时改写验证。

**Figure 2: Fault-driven page grafting.** The grafting manager changes the backing of a selected file offset, not the process-visible ELF object. The first ordinary file-backed fault installs a user PTE to the resident page already referenced by the kernel mapping; subsequent calls use the existing PTE.

### Registering Resident Backing

`ld.so` 装载 Stub DSO 后，reusable `PT_LOAD` ranges 形成普通 file-backed VMAs。每个 logical page 可由 Stub DSO file offset 转换为 `pgoff_t`，并经 inode 定位到相应 `address_space` entry。Manager 检查页面计划的地址对齐、类别标签、重复项和文件范围，再把该 file offset 注册为指向对应 kernel/LKM resident `struct page`。用户映射权限由 carrier segments 和原生 loader 路径决定。应用可见的 VMA、symbol address and shared-object identity 均不改变。

合作的 LKM owner 提供独立页对齐的 descriptor，包含 module pointer、ABI、源码版本和允许复用的 core text/RO 范围。注册模块通过 GPL-exported descriptor symbol 获取 owner 引用，再解析源地址并检查范围；会话还持有 carrier file 和复用页的引用。Builder 在用户私有数据中将管理页对应位置置零，并排除其重定位。Descriptor 的 srcversion 核对源代码版本。Builder 另记录 owner 与 vmlinux 的 GNU build ID；BEGIN 持有 owner 引用后，manager 核对 descriptor 所属模块和 sysfs 中的模块、内核 build ID，匹配后才发送页面计划。具体运行地址和允许的代码重写仍属于部署条件。

Manager 以 transaction ID 提交完整计划，STAGE 每次传输至多 256 个页面，COMMIT 在检查全部源页和目标范围后执行绑定。每个事务独立保存 file/mapping、owner 引用、source page 和页的原始管理字段。不同 carrier 可以使用互不重叠的源页；同一源 PFN 的重复绑定被拒绝。提交失败按逆序撤销已应用页面，恢复遇错仍继续处理其余页面；残留绑定保持引用和恢复状态，供 RELEASE 重试。

提交前，注册模块取得所有源页引用并准备目标 file-cache pages，随后在持有页锁和 xarray 锁时直接替换已有槽位。槽位始终被一个 page entry 占用，提交无需重新分配 xarray 节点。被替换的普通文件页释放自己的缓存计费与引用；已经驻留的 kernel source 不继承其 memcg charge。

恢复时，页锁覆盖 cache-entry 移除、用户映射撤销和字段恢复，之后才释放引用。Manager 收到成功 COMMIT 的内核确认才通过会话私有 FIFO 发送 READY，释放后发送带退出状态的 DONE；runner 阻塞等待这些事件。响应丢失时，manager 用 QUERY 核对事务的最后操作和序号。事务 ID、carrier inode 和 immutable 标志归属在首次修改文件前持久化，使新的 manager 进程能够接续恢复并保留原有文件标志。应用启动受这一完成边界约束；已有映射在逐页提交和恢复期间仍可能观察到不同页面的过渡状态。

### Fault-Driven PTE Installation and Execution

Grafting 只改变 file-offset backing；用户 PTE 仍由 Linux 原生 file-fault path 按需安装。第一次取指或访问 rodata 时，fault handler 由 VMA 找到 `address_space[pgoff]`，得到已经注册的 resident page，并按 carrier segment permission 安装 user RX or R-- PTE。Carrier `.data` 不参与 grafting，仍使用普通进程私有页面。

首次 fault 后，kernel and user virtual aliases 指向同一 PFN。后续共享计算经现有 PTE 取指，直接导出入口或 private wrapper 将控制流送入 closure，page replacement 和 code copy 不再参与调用。需要原生服务的请求由入口或 failure callback 单独处理。Page grafting 位于 first-touch path，而不进入 closure 的 steady-state execution。

## Cross-domain Environment Provisioning

Page grafting 解决执行体的 physical backing；environment layer 为 closure 提供持续更新的输入、地址空间语义和环境相关操作。Linux 实现以 `shared_data` 发布全局输入，以 `MM_data` 提供每个地址空间的只读视图，并由 private wrapper 注入 domain-local context。Shim 和 Pseudo-GOT 分别承接 helper semantics 与已有代码中的地址绑定。它们共同使共享计算能够使用动态状态，而将更新所有权与地址解析保留在各自环境中。

### Shim and Domain-Local Dependencies

Shim 是共享计算与 kernel/user environments 之间受声明的 helper boundary。Analyzer 检查 helper 对 closure 可观察的输入、输出、副作用、同步域和失败语义；只有这些语义能在另一 execution domain 中完整重建时，该 helper 才进入 whitelist。`libshim.so` 为用户域实现这一有限集合，kernel caller 则保留 domain-equivalent adapter。依赖 kernel-object ownership、privileged synchronization 或 fault-recovery semantics 的 helper 不能由同名 user API 替代。

Builder 将通过审核的 user-side helper 保留为 Stub DSO 的 undefined dynamic symbol，并添加对应 `DT_NEEDED` dependency。`ld.so` 在装载时执行标准 symbol resolution，并把最终地址写入 carrier-private binding slot。依赖解析由此发生在装载期，而不进入每次调用的稳态路径。

### Kernel-published State through shared_data

持续变化的全局输入需要保留内核写权限，同时向多个用户 reader 提供只读访问。VKSO 为此增加 `shared_data` 允许列表，将 feature 显式发布的页对齐数据对象纳入 closure。Builder 检查对象覆盖的完整页与映射权限，在 carrier 中建立 R--/NX region；page-grafting manager 为该 region 绑定相应的 resident data page。内核继续通过原有 writable alias 更新，用户读取相同物理页中的字段。普通 writable kernel objects 不会因所在 section 可映射而自动进入该列表。

数据 schema 和 publication protocol 由 feature 定义。Clocktime 实例以 `vkso_shared_page` 承载 `vkso_shared_data`，其中包括 sequence counter、ABI version 和时间计算所需的 base、cycle conversion parameters 等输入。`tk_publish_read_state()` 先将 seq 置为奇数，直接更新共享页中的 reader state，再通过写屏障和偶数 seq 发布完整一代数据。Shared core 的快照读取在访问字段前后观察 seq，并使用读屏障约束访问顺序；seq 变化时重新读取。

这份共享页也是普通内核 reader 使用的全局快照。Writer 直接在其中发布计算输入，省去中间 staging object 和第二次 payload 搬运；timekeeper 继续维护生产时间所需的内部状态。发布操作不遍历用户进程，进程数增加也不要求为它们复制全局 reader state。通用机制负责页面共享与权限，clocktime 的字段布局和 seq 读写协议构成该机制的一个具体实例。

### Address-space-local State through MM_data

同一共享函数可能需要按调用者的 namespace 或局部配置解释全局输入。VKSO 用 `MM_data` 承载这种地址空间相关的只读状态，并将页面生命周期绑定到 `mm_struct`。内核在 `mm->context` 中分别保存物理页引用 `vkso_mm_page`、内核写地址 `vkso_mm_kdata` 和用户读地址 `vkso_mm_data`。三者指向同一后备对象的不同管理视图，共享机器码通过显式参数取得当前 domain 有效的地址。

`exec` 期间，`arch_setup_additional_pages()` 分配零填充页面，并安装名为 `[vkso_mm_data]` 的 special mapping。VMA 仅允许读取，首次 fault 通过所属 MM 的页引用安装 PTE。映射设置 `VM_DONTCOPY`，由 `vkso_dup_mmap()` 在不共享 MM 的 fork 中复制原页，并在子地址空间相同虚拟地址安装新映射；共享 MM 的线程继续使用同一页。映射拒绝 mremap，MM 销毁时释放页面引用，因此 fork 后继承的已绑定用户指针仍指向各自 MM 的对象。

内核通过 `AT_VKSO_MM_DATA` 将用户读地址写入 ELF auxiliary vector，启动适配代码据此完成发现与绑定。当前 time namespace payload 是 40 B 的 `vkso_mm_data`，包含 `abi_version`、`clock_mask` 以及 monotonic 和 boottime offsets，占据一页 4 KiB 后备。`clock_mask` 标记需要应用非零 namespace offset 的 clock，root namespace 中该值为零。Namespace commit 更新已有页中的 offsets，经写屏障后发布 mask；普通 timekeeping update 不刷新这些字段。

MM_data 的可复用部分是按地址空间组织的只读映射、稳定地址发现和 MM 生命周期管理。当前 payload、auxv tag 与 namespace update hook 实现时间语义；其他 feature 可以沿用这一组织方式，并定义自己的字段与更新时机。它与全局 `shared_data` 分离，使系统级更新和地址空间视图变化各自沿独立路径完成。

### Private Context and Entry Binding

数据页中的值可以跨 domain 共享，但 provider 地址和 failure callback 必须在当前地址空间内解析。Private wrapper 为这些依赖保留本地 context。Clocktime 中，`vkso_context` 保存 PVClock、Hyper-V page aliases 和两个失败回调，另一个私有槽位保存 MM_data 指针。Context 中的地址属于入口提供的环境，不写入 shared text 或 kernel-published data。

用户启动适配代码 `vkso_user_wrapper_init()` 检查 shared/MM ABI version，通过 auxv 取得 MM_data，再调用 `__vkso_bind_context()` 写入私有槽位和用户侧 failure callbacks。随后 `__vkso_clock_gettime()` 在普通 API 参数之外装入 MM_data 与 context 地址，并直接尾跳转到 shared core。内核入口提供 `vkso_kernel_context` 和相应的内核地址。绑定操作发生在首次使用前，后续调用读取已建立的本地槽位。

Provider aliases 由绑定接口显式接收。当前默认用户初始化为 PVClock 和 Hyper-V 传入空指针，TSC 路径直接读取 counter；PV/HV reader 在缺少可用 alias 时返回失败并进入用户 syscall fallback。Shared core 将 TSC 读取内联到热路径，将 PV/HV 读取放入独立冷路径，因此常见 TSC 调用无需访问 context 中的 provider 指针。

Private context 与 Pseudo-GOT 服务于不同的依赖形态。前者把运行时输入与失败出口作为参数传入 shared-core ABI；后者保留代码已有的间接读取形式，在不同 domain 中解析地址槽位。导出 feature 可按依赖形式选择这两种机制，并由 Shim 提供所需的环境语义。

### Request Classification and Environment-local Fallback

入口适配将能够共享的计算与原生请求路径分开。Clocktime 使用共同的 clock classification，将请求区分为 hres、coarse 和 native。用户入口对 native clock 直接执行 syscall；内核 syscall 入口沿 `k_clock` 完成原生分派。支持共享的请求才取得 MM_data 并进入相应 shared entry，避免在必然 fallback 的调用上准备共享状态。

Provider failure 发生在 shared core 读取 counter 时，由 context callback 决定后续操作。用户回调执行原 syscall；内核回调直接读取 private timekeeper state，并在需要时应用 MM_data 中的 namespace offset。内核失败路径绕开会再次调用 shared reader 的 `k_clock` 路径，从而避免回退后重新进入同一个失败 provider。

普通内核 reader 以空 MM_data 指针选择 root namespace 语义，syscall reader 则使用当前 MM 的内核读地址。NMI、early-boot 和 writer-locked reader 保持其原有私有路径，以适配各自的执行上下文。通用入口机制由此提供参数注入、请求分流与失败出口；具体子系统决定共享 core 的请求集合，以及原生环境应如何完成剩余操作。

### Domain-local Binding through Pseudo-GOT

函数指针表、对象指针和回调槽位不能仅靠保持 PC-relative topology 解决：module loader 写入的 absolute kernel VA 在用户域不可用。原型把这类地址所有权从 shared `.text/.rodata` 移入 domain-private slots，并将槽位集中到 `.pseudo-got` 和 `.ro_pseudo-got` sections。共享指令仅以 PC-relative load 读取槽位，因此机器码在两个 domain 中保持相同。

对 kernel/LKM image，module loader 按原重定位解析 kernel target；对 Stub DSO，builder 将对应 slots 物化到 private segment，并把重定位转译为 `ld.so` 可处理的 `.rela.dyn` entries。Pseudo-GOT 不是新的 runtime symbol resolver，而是把 environment-specific address binding 移出共享执行体：两个 loader 分别写入 domain-local target，稳态代码只执行原有的间接读取。

**Figure 3: Environment-specific binding through Pseudo-GOT.** Both domains execute identical resident instructions, but their loaders resolve declared slots to domain-local targets. No runtime patch modifies the shared text or read-only pages.

# Evaluation

我们评估 VKSO 能否在明确的复用条件下，让用户程序正确执行内核已驻留的计算，并量化减少重复实现所付出的代价。实验围绕五个问题展开：

- **是否复用了同一执行体并保持功能？** 用实际 carrier 的 kernel/user PFN、完整算法输出、Clocktime ABI 和应用调用记录联合验证，区分共享成功与计算正确。
- **减少了什么重复，新增了什么资源成本？** 核对 Clocktime 的共享执行页、最终 ELF 段规模和活跃进程中的唯一驻留 PFN；原生 vDSO 已有的进程间共享计入对照。
- **用户端及原有内核使用者付出多少执行代价？** 用字节一致的 DSO 分离 page rehosting 成本，以 PGOT primitives、完整 copied closures 和真实算法检查依赖适配，再由 Clocktime 测量动态状态及并发读写。
- **建立和释放成本在完整工作流中如何体现？** 区分目标调用、一次性部署和复用后的执行，以完整 LZ4 CLI 检查普通 DSO 与 registered carrier 的实际使用路径。
- **哪些依赖形态适用，需要多少改造？** 用固定八个 API 案例及既有集成记录成功、失败、依赖结构和适配量，并以 Clocktime 检验完整状态子系统的复用。

各项比较保留性能退化、额外资源和不确定性。功能、物理共享与性能分别提供证据；一次注册成功不代表执行成本或净资源收益已经成立。

## Experimental Setup and Measurement

实验运行在 Intel Core i7-1165G7（4 physical cores，SMT disabled）上，使用 GCC 11.4.0。PGOT、LZ4、BCH、XZ 的测量线程固定 CPU 2。First-touch、PGOT、LZ4、BCH 和 XZ 使用 Linux 5.15.0-119-generic；clocktime 使用 Linux 5.15.198 及相同硬件，通过 isolcpus、nohz_full 和 rcu_nocbs 隔离 CPU 2，周期性状态发布由内核时钟更新路径驱动。Clocktime 独立用户 READ 使用 CPU 2；持续读取负载也固定在 CPU 2。PGOT 比较 retpoline/no-retpoline builds；clocktime 分别报告 normal 和 no-retpoline 构建的 Raw/VKSO 结果。

PGOT 使用轮内 paired delta。LZ4 和 XZ 各完成三次、BCH 完成十二次完整部署，每次重新装载 owner、构造并注册 carrier、运行工作负载、恢复映射并卸载 owner。这些部署均位于同一次物理机启动中，因此重复单位是部署，不是独立启动。算法与应用先计算同轮配对成本比，取部署内中位数，再对各算法的全部部署等权取中位数；方括号列出部署中位数的最小值与最大值。绝对值同样先取部署内中位数再跨部署汇总，不用两侧已舍入绝对值反推配对比值。LZ4 每个 round/block/backend 启动一个进程，BCH/XZ 则在单个进程中轮换 backend 并完成该部署的各轮。

Clocktime 使用四种实现/构建组合，每种分别运行无插桩 READ 内核和带 UPDATE recorder 的内核；每种镜像独立启动四次，共 32 次。READ、普通内核 reader、UPDATE 与并发公开 reader 均先取每次启动中全部观测的均值，再对四次启动等权平均。READ 观测是批次平均调用成本，UPDATE 观测是逐次发布成本；完整均值保留分布中各耗时区间及其出现比例。Raw/VKSO 比较在同 block 的独立启动之间进行，不把轮次或逐次调用当作独立系统实验。表 2 列出各组重复层次与主指标。

算法和 CLI 的稳态计时位于活动注册期间，不包含 owner 构建、carrier 构造、注册或释放。事务 manager 通过完成通知衔接工作负载与释放；setup 实验另外测量这些生命周期阶段。First-touch 则从装载和符号解析完成后计时，只包围首次目标调用。不同计时窗口对应调用、首次触达和完整任务三个问题。

补充的映射、资源和功能验证使用各节注明的独立 KVM guest，并保留实际构建与 boot identity。Guest 中的计时字段用于验证采集流程，不加入物理机性能比较。

部署成本分为离线 closure/carrier 构造、已有 carrier 的注册与释放，以及活动注册下的新进程装载。完整任务对照使用同源 Linux LZ4 DSO 与实际 carrier，处理全部 12 个 Silesia 文件（211,938,580 B），按 64 KiB 分块完成压缩、解压和逐字节校验。每个进程执行一遍或三遍完整任务，首次有效结果定义为第一遍全部校验完成。无插桩版本从进程启动前计时至退出；插桩版本另外记录装载、计算和释放阶段，并保留观测开销。这一任务用于区分部署与计算成本；LZ4 CLI 的 framing 和输出文件工作由应用实验覆盖。已有 carrier 的命令耗时包含注册和释放，离线构造单独计费，不能从包含整组 benchmark 的 runner 总时长推定 setup。完整测量流程与 guest 原始记录见[setup 对照](../../test/evaluation/setup-comparison-evidence.md)。

计时前的功能校验用于确认两侧完成相同工作：PGOT copied closures 比较返回值、输出长度和字节；LZ4 交叉验证 compressor/decompressor；BCH 检查错误位置及 codeword recovery；XZ 检查完整输出；clocktime 对各镜像执行相同 ABI matrix。表中的 IQR width 为 P75−P25，P25–P75 列出端点。算法、内核端、CLI 和 setup 统一报告成本比，大于 1 表示 VKSO 更慢；吞吐量输入在轮内取 native/VKSO 后再汇总。部署间最小值和最大值描述本次重复的范围，不作为置信区间。

**Table 2: Evaluation workloads, comparisons, and measurement units.** BCH has twelve complete deployments; LZ4 and XZ have three each, all within one host boot. Inner calls amortize timing overhead and are not independent trials. Algorithm cost ratios are summarized first within deployments and then across deployments.


| Experiment       | Primary comparison                                 | Repetitions and statistic                     | Primary metric               |
| ---------------- | -------------------------------------------------- | --------------------------------------------- | ---------------------------- |
| First touch      | Native DSO vs. kernel-backed Stub DSO              | 5 accepted batches; mean of batch medians | TSC cycles and fault type    |
| Data-PGOT | Independent loads vs. dependent chains; direct/PGOT | 3,100 raw paired samples per configuration | paired cycles/access, IQR |
| Func-PGOT | Stable target; direct/PGOT, two builds | 310 raw paired samples per build | paired cycles/call, IQR |
| Work placement | Before/inside/after target, varied useful work | 3 outer runs × 15 repeats | paired cycles/iteration, IQR |
| Copied closures  | Origin vs. PGOT closure                            | 3 outer runs × 31 repeats                     | paired cycle delta           |
| LZ4 | VKSO vs. original Native and Adapted user DSOs | 3 deployments × 7 rounds; median and deployment range | MB/s and cost ratio |
| BCH | VKSO vs. original Native and Adapted user DSOs | 12 deployments × 11 rounds; 10 ms adaptive target | ns/op and cost ratio |
| XZ Embedded | VKSO vs. original Native and Adapted user DSOs | 3 deployments × 3 inputs × 7 rounds × 20 decodes | MiB/s and cost ratio |
| Kernel algorithms | Actual owner vs. compiler-matched and stock kernel implementations | BCH: 12 deployments; LZ4/XZ: 3 each; 11 rounds | ns/op or ms/full input; cost ratio |
| LZ4 CLI | Carrier vs. same-source DSO, upstream DSO and stock CLI | 3 deployments × 4 rounds × 2 block sizes × 12 files × 2 operations | complete command time |
| LZ4 setup | Same-source DSO vs. active/ready carrier | 3 deployments × 3 paired rounds; 1/3 corpus passes, trace on/off | full command and first-valid-result time |
| Clocktime | Raw native vDSO vs. VKSO; normal and no-retpoline | 4 boots per case/image role; equal-weight mean of boot means | TSC ticks/call, TSC ticks/update, selected resident PFNs |


这组实验由机制分解走向完整功能：字节一致的 DSO 控制计算逻辑差异，copied closures 在同一执行域内隔离 PGOT transformation，实际 kernel-backed algorithms 再引入构建域、Shim 和 page rehosting，clocktime 最后检验共享状态及入口适配的组合效果。后一层的端到端结果与前一层的机制解释互补。

## First-touch and Rehosting Cost

Page grafting 改变对象的物理后备，而应用仍通过标准 DSO 调用。因此，我们使用字节一致的 XXH32 function body 构造普通 user-space DSO 和 kernel-backed Stub DSO，使两侧的计算工作和调用形式一致。计时从 dlopen 和 symbol resolution 完成后开始，只包围一次目标调用；它测量执行页的首次触达，不包含 DSO 构造、页面替换或动态链接总时间。

三种状态分别隔离不同成本。Hot 保留已有 PTE，用于检查稳态调用是否引入额外路径；PTE cold 通过 MADV_DONTNEED 移除 PTE、保留 resident backing，用于比较按需安装页表的成本；Post drop-caches 进一步清理普通 file cache，用于检验内核页面既有 residency 在文件缓存被逐出后是否仍可利用。每个样本记录 minor/major-fault counters，先按预期 fault class 筛选，再执行基准的 IQR filtering，避免将实际不同的缺页状态混入同一组。

**Table 3: First-touch latency and retained fault class.** Latency columns average the within-batch median and P25/P75 order statistics over five accepted batches after fault-class and IQR filtering. Fault counts describe retained calls. Timing covers one target call after loading and symbol resolution.

| 状态 | Backend | Mean batch median (cycles) | Mean batch P25–P75 (cycles) | Minor / major faults |
| --- | --- | --- | --- | --- |
| hot | Native | 71 | 69–71 | 0 / 0 |
| hot | Stub | 71 | 69–71 | 0 / 0 |
| pte-cold | Native | 2662 | 2658–2667 | 1 / 0 |
| pte-cold | Stub | 2637 | 2633–2642 | 1 / 0 |
| post-drop | Native | 701069 | 669200–708383 | 0 / 1 |
| post-drop | Stub | 13094 | 12319–13882 | 1 / 0 |

表 3 中，两种 DSO 的 hot call 批次中位数均值均为 71 cycles；PTE cold 保留的单次 minor-fault 样本对应均值相差不足 1%。这与 grafting 不增加稳态执行步骤、首次访问继续使用原生 fault path 的设计一致。Post drop-caches 下，Native 的 major-fault 样本与 Stub 的 resident-page minor-fault 样本对应均值分别为 701,069 和 13,094 cycles，受控 first-touch 延迟比为 53.5×。该差异反映既有 residency 在所选 fault class 下的收益。

为解释 fault latency，我们另行采集 PMU 和 function-graph trace，避免其插桩影响主要延迟测量。Stub 从 PTE cold 到 Post drop-caches 的 retired instructions 仅由 5,729 增至 5,797，而 L1D/LLC misses 由 1.00/0 增至 62.79/17.61。这支持残余 13K cycles 与更冷的 cache/metadata 状态有关，而非大量新增软件工作；PMU 的 on-CPU cycles 与包含等待时间的 elapsed TSC latency 分开解释。Function-graph tracing 确认两种 PTE-cold case 都进入标准 file-backed minor-fault path，仅用于路径分析。

**Table 4: First-touch PMU diagnostics.** Values are mean event counts from separate instrumented runs, not the uninstrumented latency samples in Table 3.

| 状态 | Backend | Instructions | L1D misses | LLC misses |
| --- | --- | --- | --- | --- |
| hot | Native | 3918.00 | 0.10 | 0.00 |
| hot | Stub | 3918.00 | 0.04 | 0.00 |
| pte-cold | Native | 5828.00 | 2.33 | 0.00 |
| pte-cold | Stub | 5729.00 | 1.00 | 0.00 |
| post-drop | Native | 26725.86 | 774.83 | 96.97 |
| post-drop | Stub | 5797.14 | 62.79 | 17.61 |

**Takeaway.** Hot call 的批次中位数均值相同，resident minor fault 的对应均值接近；受控 first-touch 的差异来自 kernel code 的既有 residency。

另一次 exact119 guest 采集保留筛选前的全部 first-touch 调用和每批决策。六个 Native/Stub 条件组均达到五个合格批次，共尝试 38 批、记录 3,800 次调用；其中 Native/post-drop 的八个拒绝批次仍计入未筛选分布。IQR 视图保留 3,564 次调用，合格批次内的筛选视图保留 2,859 次。功能校验使用独立进程并在采样前退出，使其普通 DSO 映射不影响驱逐条件。实际载入的两端 XXH32 函数具有相同的 338 字节指令，并通过 247 个独立参考向量；采集后仍观测到注册页与源 PFN 相同，随后正常释放。这些 guest 记录验证完整采集和筛选口径，表 3 的物理机数值保持其原构建身份。见[原始调用与批次记录](../../test/evaluation/first-touch-evidence.md#registered-raw-protocol-run--2026-09-12)。

为区分显式缓存驱逐和后台回收，我们在同一注册流程下增加 baseline、pressure 和 recovery 三阶段观察，每阶段执行十对 Native/Stub 调用。4 GiB、无 swap 的 exact119 guest 中，后台进程持有约 2.70 GiB 匿名内存，并在每对调用前完整读取两遍 1 GiB 文件；两侧先执行完整 XXH32，再移除函数 PTE，所有调用均保留。十个压力窗口都发生实际回收，合计回收 5,238,600 个页事件，但两侧代码页在全部观察中仍驻留，60 次调用均为一次 minor fault、零 major fault。30 次 Stub 调用的 PFN 均与内核源页一致，压力前后各 247 个完整参考向量通过，随后恢复与卸载正常。这说明后台回收本身并不保证普通代码页被逐出；表 3 的 post-drop 优势取决于实际驻留状态，不能外推为一般压力下的加速。该 guest 诊断的原始调用见[压力与恢复记录](../../test/evaluation/first-touch-evidence.md#reclaim-pressure-scenario--2026-09-12)，其插桩延迟与物理机表分开。

完整建立成本使用另一组生命周期边界：当前导出命令到首个有效结果、已构造 carrier 的注册到首个有效结果，以及活动注册中的新进程装载。三个独立 5.15.0-119 guest 分别执行 LZ4、BCH 和 XZ，每个 guest 包含两次注册及 12 个任务进程；这些导出命令从 owner 和注册模块已装载的状态开始。LZ4 完成全部 12 个 Silesia 文件的压缩、解压和字节比较；BCH 完成两个原始参数组的初始化、编码、完整纠错及 codeword 恢复；XZ 解码三个完整输入并检查输出和边界。每进程执行一次或三次完整任务，首个有效结果的边界包含结果校验。

各层时间戳使用同一启动内的 CLOCK_MONOTONIC_RAW。进程内记录先缓存在内存中，任务结束后输出；外部控制程序记录启动和返回，shell 标记区分构造、注册、应用和释放。dlopen 与符号解析属于装载阶段，内核 prepare/apply 属于 COMMIT，不能与其外层时间重复相加。Shell 标记包含时钟 helper 的启动开销，因此这些 guest 记录用于验证阶段和完整任务的对应关系，不计入物理机性能表。完整任务、原始时间戳及释放记录见[装载采集证据](../../test/evaluation/setup-evidence.md)。

## Dependency Adaptation Overhead



### Primitive Pseudo-GOT Costs

Data-PGOT 将环境相关地址放入 private slot；Func-PGOT 再通过该 slot 调用 helper。单次 slot load 的延迟并不能直接预测整个函数的开销：独立访问可能重叠执行，依赖链则必须等待前次读取，间接调用还受 retpoline 影响。我们据此构造可并行数据读取、串行 dependent chain 和稳定单目标调用，分别观察吞吐成本、关键路径延迟和固定绑定下的调用成本。随后在 target body 内或相邻指令流中增加 useful work，检验额外指令在完整调用中的可见程度。计时循环包含等价 empty-loop control；objdump 检查确认 compiler 没有 hoist slot load 或把 indirect call 重新直接化。

Work-placement 实验的每个 work unit 是一段作用于同一 64-bit 值的乘加、rotate、异或和移位依赖链。Before 和 after 将其置于空 target 调用之前或之后，inside 将同样的工作置于 target 内；工作量为零时只保留调用。三种位置使用相同工作定义，并逐步增加重复次数，以观察有用计算如何影响间接调用的可见成本。

**Table 5: Data-PGOT cost under independent and dependent accesses.** Values are raw paired median deltas and delta-IQR widths in cycles/access, with 3,100 paired samples per configuration.

| 每轮访问数 | Independent Δ cycles/access | IQR width | Dependent Δ cycles/access | IQR width |
| --- | --- | --- | --- | --- |
| 1 | 0.100 | 0.001 | 5.017 | 0.001 |
| 2 | 0.334 | 0.001 | 5.017 | 0.001 |
| 4 | 0.501 | 0.002 | 5.017 | 0.018 |
| 6 | 0.502 | 0.002 | 5.028 | 0.023 |
| 8 | 0.502 | 0.001 | 5.025 | 0.013 |
| 10 | 0.502 | 0.001 | 5.020 | 0.010 |

**Table 6: Stable-target Func-PGOT cost.** One call event per loop iteration. There are 310 raw paired samples per build. Direct and PGOT columns are marginal medians; Δ is the median of paired differences.

| Build | Direct cycles/call | PGOT cycles/call | Paired Δ | IQR width |
| --- | --- | --- | --- | --- |
| No-retpoline | 3.010 | 4.013 | +1.003 | 0.002 |
| Retpoline | 3.010 | 42.161 | +39.150 | 0.003 |

**Table 7: Visible retpoline overhead as useful work increases.** Each cell is paired median Δ [IQR width] in cycles/iteration, from 3 outer runs × 15 repeats. Before, inside, and after place the same work before the call, in its target, or after the call; the instruction stream is unfenced.

| Work units | Before Δ [IQR width] | Inside Δ [IQR width] | After Δ [IQR width] |
| --- | --- | --- | --- |
| 0 | +39.135 [0.074] | +39.200 [4.013] | +39.135 [0.072] |
| 1 | +30.770 [1.458] | +30.954 [0.071] | +36.457 [0.073] |
| 2 | +19.951 [0.197] | +22.089 [0.430] | +25.087 [0.091] |
| 3 | +17.948 [0.144] | +11.202 [2.503] | +16.260 [0.736] |
| 4 | +8.887 [0.227] | +3.272 [1.465] | +4.713 [0.224] |
| 5 | +1.682 [1.877] | −0.047 [0.158] | −0.191 [0.141] |
| 6 | −0.249 [0.297] | −0.053 [0.136] | −0.219 [0.137] |
| 8 | −0.015 [0.108] | +0.014 [0.089] | −0.042 [0.072] |

表 5 中，当每轮包含至少四次独立访问时，增量稳定在约 0.50 cycles/access；dependent chain 的增量约为 5.02 cycles/access。前者允许额外读取与其他 load overlap，后者将 slot load 放入必须逐步完成的依赖链。这两个构造分别给出所测指令流中偏向吞吐和偏向延迟的成本边界。

稳定 target 的 Func-PGOT 在 no-retpoline build 中增加约 1.00 cycle/call；retpoline build 中增加约 39.15 cycles/call（表 6）。表 7 的工作量扫描进一步显示，同一间接调用在不同指令流中的可见开销并不固定：增加到约 5–6 个 work units 后，三种放置方式的 paired delta 均接近零。该结果衡量未加 fence 的完整指令流，说明有效工作与调用路径的组合会改变开销的可见程度；它不意味着 retpoline thunk 的串行延迟消失。

### End-to-end Copied Closures

为检验 primitive cost 在真实控制流中的表现，我们从 Linux 源码复制完整 SHA-256 transform、BCH encode、zlib deflate 和 Zstd decompress closures，在 LKM 内分别构建 origin 与 PGOT variants。两侧在同一 kernel execution domain 中完成同一计算，不引入用户态 rehosting；差异来自显式 data slots、address repair 和适用的 closure-external helper calls。SHA-256 覆盖只需 data adaptation 的闭包，其余目标覆盖数据与 helper 绑定的组合。每个配置执行 3 个 outer runs、每轮 31 次配对测量。表 8 同时列出每个 sample 内的调用次数、按调用归一化的 cycles 和 paired delta，以区分批内工作量与独立重复次数。

**Table 8: PGOT overhead on complete copied closures.** SHA-256 uses Data-PGOT; the other closures use the complete applicable Data/Func-PGOT transformation. Each row contains 93 paired samples. Δ is the paired median, not PGOT median minus Origin median. The percentage normalizes Δ by Origin cycles. IQR is the width of the paired-delta distribution.

| Closure | Build | Calls/sample | Origin cycles | PGOT cycles | Paired Δ cycles | IQR width | Δ / Origin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SHA-256 | No-retpoline | 16384 | 1314.389 | 1314.855 | +0.526 | 3.815 | +0.04% |
| SHA-256 | Retpoline | 16384 | 1314.575 | 1313.522 | −0.978 | 4.451 | −0.07% |
| BCH | No-retpoline | 128 | 5502.159 | 5604.730 | +108.746 | 33.086 | +1.98% |
| BCH | Retpoline | 64 | 5492.913 | 5660.585 | +178.609 | 47.134 | +3.25% |
| zlib | No-retpoline | 16 | 27599.375 | 27988.312 | +375.094 | 166.376 | +1.36% |
| zlib | Retpoline | 32 | 27405.921 | 27248.218 | −180.234 | 192.156 | −0.66% |
| Zstd | No-retpoline | 32 | 6296.984 | 6379.843 | +87.109 | 39.844 | +1.38% |
| Zstd | Retpoline | 128 | 6276.851 | 6666.569 | +391.059 | 24.304 | +6.23% |

表 8 显示，no-retpoline 下四个闭包的增量均不超过约 2%。Retpoline 对不同闭包的影响取决于依赖类型：只有 data adaptation 的 SHA-256 仍接近零，BCH 的开销增至 3.25%，helper-call-heavy 的 Zstd 达到 6.23%。zlib 的 −0.66% 伴随较大的 paired-delta IQR，不据此主张稳定加速。Primitive 与 closure 两层结果共同表明，适配成本应结合实际依赖链和 helper 调用结构评估，不能将单次间接调用成本线性叠加到整个算法。

## Exported Kernel Algorithms

We evaluate LZ4, BCH, and XZ through their actual VKSO carriers, then invoke the same export owners from kernel benchmarks. The user comparison includes an ordinary port of the original Linux algorithm (`Native`), a user DSO containing the owner's algorithm rewrites and feature configuration (`Adapted`), and `VKSO`. Native and Adapted use the same `-O2` user compiler options. In the kernel, we compare the distribution implementation (`Stock`), the original source and dependencies under the owner's code-generation options (`Matched`), and the exported `Owner`. VKSO/Native and Owner/Stock measure the complete execution cost of adopting the export. The intermediate versions help explain that cost.

LZ4 processes all twelve Silesia files at three user block sizes (4 KiB, 64 KiB, and 1 MiB); the kernel uses the latter two. BCH uses 512-byte inputs with $m=13$, $t\in\{4,8\}$, and zero through $t$ errors. XZ decodes three complete streams. On a pinned core of an i7-1165G7 running Linux 5.15.0-119, we use 12 BCH module loads and three loads each for LZ4 and XZ, summarizing paired costs by their median within and then across loads. Timing includes algorithm reset and helper calls, with loading and binding completed beforehand.

![Execution overhead of actual user-space exports](figures/exported_algorithms.svg)

**Figure: Execution overhead of actual user-space exports.** Points show medians of paired load results; whiskers span load medians (twelve for BCH, three for LZ4/XZ). LZ4 C/D denote compression/decompression. BCH Full/Pre use two errors; the full error-count sweep and initialization costs are in the [complete results](../../test/section63/results/paper-material/tables.md).

**User execution.** The user results figure shows that LZ4 compression costs 0.5–1.4% less than Native, while decompression costs 1.5–2.0% more. The decompression difference is already present in the Adapted DSO: VKSO differs from Adapted by approximately $-0.1$% to $+0.1$%. XZ's complete-stream cost is 0.8–0.9% above Native and 1.1–1.2% above Adapted. These comparisons include the domain-local helper calls and their ABI bridges.

BCH's response depends on the decode path. Precomputed decode receives an ECC difference and measures syndrome computation and error-location search. With two errors, VKSO reduces this cost by 8.6% for $t=4$ and 10.0% for $t=8$ relative to Native. The reduction does not extend across the error-count sweep: with eight errors at $t=8$, precomputed and full decode cost 3.7% and 2.3% more, respectively. The full sweep is retained with the experiment results.

**Kernel consumers.** Table 9 reports the costs of the dedicated export owners. LZ4 is within 0.4% of Stock for compression and 2.6–3.1% faster for decompression. BCH includes both reductions in decode cost and a 3.2% increase for $t=4$ encoding. XZ adds 4.3–5.2% relative to Stock, although Matched is approximately 2.5–2.6% below Stock. The XZ increase therefore appears when applying the export's source and dependency adaptations to the matched build.

**Table 9: Kernel execution costs of the actual export owners.** Stock is the distribution implementation; Matched retains original source and dependencies with owner code-generation options. Brackets span load medians (twelve for BCH, three for LZ4/XZ). BCH decode rows use two errors.

| Algorithm | Operation/input | Owner / Stock | Owner / Matched |
| --- | --- | --- | --- |
| LZ4 | compress, 64 KiB | 1.003 [1.003, 1.003] | 1.005 [1.005, 1.005] |
| LZ4 | compress, 1024 KiB | 0.998 [0.998, 0.998] | 1.000 [1.000, 1.000] |
| LZ4 | decompress, 64 KiB | 0.974 [0.971, 0.974] | 0.995 [0.995, 0.997] |
| LZ4 | decompress, 1024 KiB | 0.969 [0.966, 0.971] | 0.999 [0.998, 0.999] |
| BCH | t=4, encode | 1.032 [1.026, 1.039] | 1.000 [0.997, 1.009] |
| BCH | t=4, decode-full | 1.000 [0.996, 1.016] | 1.003 [0.989, 1.005] |
| BCH | t=4, decode-precomputed | 0.897 [0.875, 0.926] | 0.962 [0.917, 0.982] |
| BCH | t=8, encode | 0.989 [0.986, 0.995] | 1.000 [0.996, 1.004] |
| BCH | t=8, decode-full | 0.929 [0.914, 0.945] | 0.946 [0.933, 0.962] |
| BCH | t=8, decode-precomputed | 0.851 [0.834, 0.888] | 0.869 [0.842, 0.901] |
| XZ | bash | 1.043 [1.036, 1.052] | 1.069 [1.065, 1.069] |
| XZ | libc.so.6 | 1.052 [1.049, 1.054] | 1.082 [1.072, 1.083] |
| XZ | python3 | 1.051 [1.048, 1.053] | 1.081 [1.072, 1.084] |

**BCH execution paths.** The adopted syndrome loop caches its table pointer explicitly. The original kernel build reloads this pointer inside the loop, whereas the ordinary user build hoists the load. Disabling strict-alias analysis in the original user build reproduces the reload. The loop-only kernel control reduces two-error precomputed cost by 2.4% at $t=4$ and 4.1% at $t=8$. Independent user-space PMU measurements show that the complete VKSO operation retires 2,614 rather than 2,854 instructions at $t=4$, and 6,723 rather than 7,346 at $t=8$. The reduction in executed work accompanies the gains in both two-error configurations.

At higher error counts, root finding changes the balance of work. Linux BCH uses specialized solvers through degree four and polynomial factorization above that degree. With eight errors, VKSO retires 38,218 instructions versus 37,242 for Native, while branch misses rise from 6.95 to 9.85 per operation. The kernel comparison has the opposite instruction-count direction: Owner retires approximately 38,038 instructions versus 40,577 for Stock. The two domains compare different generated implementations, explaining why the user-side increase coexists with a kernel-side reduction.

**Variation across loads.** The $t=4$ zero-error path varies across loads: Owner/Matched ranges from -7.3% to +3.4% across twelve loads. Its diagnostic instruction count, branch-miss count, L1D misses, and cycle/reference-cycle ratio remain nearly constant despite latency variation. The two-error reductions persist when all three kernel implementations rotate through the same allocated contexts within each diagnostic load. The user results figure and Table 9 retain the full load ranges.

**XZ dependency cost.** The XZ difference is dominated by its CRC dependency. Stock and Matched call the kernel CRC32 implementation, whereas the export contains XZ's compact internal CRC32 routine. In a separate kernel control, we retain the owner's decoder, feature configuration, and helper slots, and replace the CRC body with a call to kernel CRC32. The original owner costs 7.1–7.8% more than this control. The control is 2.3–3.2% below Stock. Replacing this dependency thus removes the observed kernel-side regression. Both user DSOs use the portable internal CRC32 routine, explaining why the user comparison has a much smaller gap. We next examine shared state and concurrency using Linux clocktime.

The [experiment report](../../test/section63/results/report.md) provides the six version definitions, complete paired results, source and compiler records, and separate causal controls.

## Stateful System Case: Consolidating Kernel and vDSO Time Reads

### Evaluation Goals and Baselines

Linux vDSO 将常用时间查询放在用户态执行，已经消除了这些调用的 syscall 开销。[31] 内核 reader 与 vDSO reader 却分别实现了时钟状态读取和时间换算。Clocktime 用这一有状态子系统检验 VKSO 能否将两端的计算收敛到同一驻留执行体，并量化为共享代码而引入的入口、状态发布和映射成本。相较于前述算法案例，它还要求共享计算与持续更新、time namespace 和原生 fallback 协同工作。

我们在 Linux 5.15.198 中抽出共享时间核心，由内核发布只读状态快照，并通过 MM context 提供 namespace 偏移等局部输入。用户程序链接 `libvkso_time.so`，以常规 API 签名调用 `clock_gettime`、`clock_getres`、`gettimeofday`、`time` 和 `getcpu`；公开入口经 `libkernel.so` 的私有 ABI 适配进入内核驻留页。初始化、符号绑定和 context 准备在计时前完成。Raw 基线使用 libc 的原生 vDSO 路径。两端都保留原生不支持的 clock 的 syscall fallback，稳态路径均不经过实验性 provider bridge、预加载库或逐次动态符号查找。

比较包含 normal 与 no-retpoline 两种构建条件。后者关闭 RETPOLINE、RETHUNK 和 CPU_UNRET_ENTRY，以及由 Kconfig 联动关闭的依赖选项。每个 block 轮换四种 Raw/VKSO 构建的执行顺序，每种构建分别启动无插桩 READ 镜像和带 UPDATE recorder 的镜像；四个 block 共 32 次启动。READ、普通内核 reader、UPDATE 与并发公开 reader 分别统计。性能主指标均先取每次启动的完整观测均值，再对四次启动等权平均；差值 Δ 为 VKSO 减 Raw，负值表示成本下降。单位为 TSC ticks。

### Code Adaptation and Mapping Footprint

共享核心承担时间换算、归一化和 namespace 偏移计算，两个执行域的入口负责提供各自的状态与失败处理。表 10(a) 以原版 Linux 5.15.198 为基线，统计非空、非注释源码行，包含头文件、汇编和编译期 ABI 断言。共享计算与 ABI 为 494 行，内核 reader、状态发布及 MM/namespace 接入需要相应改造。所列部分共新增 1,494 行、删除 340 行，净增 1,154 行；这项重构合并了计算实现，同时增加了跨域适配代码。

**Table 10(a): Clocktime integration changes against Linux 5.15.198.** Counts include nonblank, noncomment source lines, declarations and ABI assertions. Replacements contribute to both columns; platform-wide vDSO withdrawal and diagnostic instrumentation are excluded.

| Adaptation category | Added | Deleted |
| --- | ---: | ---: |
| Shared computation and ABI | 494 | 0 |
| Kernel readers and syscall boundaries | 238 | 182 |
| Shared-state publication | 102 | 14 |
| Per-MM mapping and time namespace | 173 | 57 |
| Clock-provider integration | 10 | 22 |
| Build, linking and platform integration | 84 | 65 |
| User ABI and initialization | 393 | 0 |
| **Total** | **1,494** | **340** |

用户交付层共 393 行，包括 112 行 carrier 私有汇编入口、143 行公开 API 与初始化 C 代码，以及 138 行头文件。这些代码完成 ABI、errno、fallback 与 context 适配，时间计算由共享核心执行。原生 x86-64 vDSO 的时间读取、架构 shim 与入口实现切片为 406 行，但该切片不包含其数据 ABI 和初始化支持，两者不能用于计算同口径代码缩减率。表 10(a) 衡量的是重构规模，复用的直接效果是消除独立的用户计算副本。

原型的 no-vDSO 平台基线还裁剪了部分 32 位、UML 和 SGX 支持；这些删除与另计的 1,213 行验证及诊断代码均不进入上述改造量。通用 exporter 和 page-grafting 机制由各案例共用。分类边界及逐文件计数见[源码改造账本](../../test/test_gettime/vkso-tests/code-size/CHANGE_AUDIT.md)。

表 10(b) 给出被测无插桩镜像的静态规模。两种构建的最终 kernel `.text` 规模分别保持不变，原生 vDSO 的 1,853 字节 `.text` 由 carrier 映射与 760 字节公开库入口替代。Carrier 的共享页与内核源页具有相同 PFN，其 `.text` 大小描述用户可见代码映射，不能作为第二份物理代码相加。压缩镜像的文件大小另外反映链接布局与压缩效果。

**Table 10(b): Clocktime static artifacts.** Sizes are bytes. Kernel text, carrier mappings and compressed image sizes have different accounting scopes and are not additive.

| Artifact | Normal Raw | Normal VKSO | No-retpoline Raw | No-retpoline VKSO |
| --- | ---: | ---: | ---: | ---: |
| Kernel `.text` | 14,683,442 | 14,683,442 | 14,681,453 | 14,681,453 |
| Native vDSO `.text` | 1,853 | — | 1,853 | — |
| Carrier `.text` | — | 12,288 | — | 8,192 |
| VKSO public library `.text` | — | 760 | — | 760 |
| Compressed `bzImage` | 8,422,432 | 8,414,368 | 7,982,208 | 7,975,712 |

表 11 清点指定时间接口用户映射中观测到的唯一驻留 PFN。Raw 的 vDSO 代码页在进程间共享；VKSO 在共享执行页之外还需要 MM 映射和入口支持页。Normal 下，所选映射从单进程的 10 个 PFN 增至 32 进程的 103 个，而 Raw 均为 1 个。代码页共享因而没有转化为这一映射范围的净页数下降。该清点不包含完整内核、页表及其他进程内存。

**Table 11: Observed resident unique PFNs in named time-related user mappings.** One PFN is 4 KiB. Counts are medians across four independent READ boots per case and do not represent total system RAM.

| Build | Processes | Raw PFNs | VKSO PFNs | Additional VKSO PFNs |
| --- | ---: | ---: | ---: | ---: |
| Normal | 1 | 1 | 10 | 9 |
| Normal | 8 | 1 | 31 | 30 |
| Normal | 32 | 1 | 103 | 102 |
| No-retpoline | 1 | 1 | 9 | 8 |
| No-retpoline | 8 | 1 | 30 | 29 |
| No-retpoline | 32 | 1 | 102 | 101 |

### Public and Kernel READ Cost

用户 READ 覆盖 16 个 API/参数路径，包括七种 `clock_gettime` fast path 和三种 native fallback。每条路径在每次启动中由七个新进程合计执行 31 个批次，每批次包含 500,000 次完整公开调用。初始化与预热在计时前完成，有序 TSC 读取覆盖调用批次，CPU 与 TSC_AUX 检查用于检测迁移。表 12 对启动内批次成本取均值，再跨启动等权平均；这些数值是批次平均调用成本，不是逐次调用尾延迟。

**Table 12: Complete public READ cost.** R/V denotes Raw/VKSO TSC ticks per call, averaged within each boot and then equally across four boots. Δ is VKSO minus Raw.

| Public path | Normal R/V | Normal Δ | No-retpoline R/V | No-retpoline Δ |
| --- | ---: | ---: | ---: | ---: |
| `clock_gettime` realtime | 54.191 / 54.016 | −0.175 | 54.190 / 54.463 | +0.273 |
| `clock_gettime` monotonic | 54.198 / 54.647 | +0.449 | 54.198 / 53.473 | −0.726 |
| `clock_gettime` monotonic raw | 54.193 / 54.673 | +0.480 | 54.206 / 53.609 | −0.597 |
| `clock_gettime` boottime | 54.202 / 54.950 | +0.748 | 54.192 / 53.570 | −0.622 |
| `clock_gettime` TAI | 54.193 / 55.115 | +0.922 | 54.194 / 55.046 | +0.851 |
| `clock_gettime` realtime coarse | 15.097 / 16.102 | +1.004 | 15.097 / 15.095 | −0.002 |
| `clock_gettime` monotonic coarse | 15.099 / 16.172 | +1.073 | 15.097 / 15.237 | +0.140 |
| `clock_getres` realtime | 15.094 / 13.045 | −2.049 | 15.093 / 13.045 | −2.047 |
| `clock_getres` realtime coarse | 14.052 / 13.078 | −0.973 | 14.052 / 13.079 | −0.973 |
| `gettimeofday(tv, NULL)` | 56.211 / 55.203 | −1.008 | 56.210 / 55.201 | −1.008 |
| `time(NULL)` | 7.024 / 6.022 | −1.002 | 7.025 / 6.023 | −1.002 |
| `time(&t)` | 7.024 / 5.918 | −1.107 | 7.025 / 7.303 | +0.279 |
| `getcpu(&cpu, &node)` | 14.600 / 12.825 | −1.774 | 14.609 / 12.906 | −1.703 |
| `clock_gettime` process CPU fallback | 870.070 / 867.993 | −2.078 | 843.772 / 842.718 | −1.054 |
| `clock_getres` process CPU fallback | 592.303 / 585.086 | −7.217 | 575.675 / 563.165 | −12.510 |
| `clock_gettime` realtime alarm fallback | 684.827 / 671.805 | −13.022 | 670.648 / 662.287 | −8.361 |

成本变化依赖具体入口。两种构建的 `clock_getres` realtime 均降低约 2.05 ticks，`gettimeofday` 和 `time(NULL)` 各降低约一 tick。Normal 下，monotonic、monotonic-raw、boottime 和 TAI 增加 0.45–0.92 ticks，两种 coarse 查询各增加约一 tick；no-retpoline 下前三者降低 0.60–0.73 ticks，TAI 仍增加 0.85 ticks。原生 fallback 单列，以区分共享 fast path 与需要进入内核的查询。

完整分布还会改变单纯使用中位数时的判断。No-retpoline 的 `time(&t)` 中，111/124 个 VKSO 批次约为 5.03 ticks/call，另外 13 个约为 26–27 ticks/call，分布在全部四次启动中。Raw 均值为 7.025 ticks/call。VKSO 的批次中位数较低，完整均值却为 7.303 ticks/call，差值 +0.279 ticks；同 block 启动均值差的 bootstrap 95% 区间为 [−0.407, +1.140]。这些高成本批次保留在主结果中。

表 13 对各路径的 VKSO/Raw 均值比取等权几何平均。Normal 的 13 个非 fallback 路径总体成本下降 3.87%，七种 `clock_gettime` fast path 的集合则增加 2.57%。No-retpoline 对应变化为 −3.63% 和 −0.09%。这一汇总描述所测接口集合，不按应用调用频率加权。

**Table 13: Equal-weight geometric mean of VKSO/Raw ratios of boot-averaged mean costs.** Negative changes favor VKSO; path groups overlap.

| Path group | Number of paths | Normal change | No-retpoline change |
| --- | ---: | ---: | ---: |
| All public paths | 16 | −3.36% | −3.18% |
| Non-fallback paths | 13 | −3.87% | −3.63% |
| `clock_gettime` fast paths | 7 | +2.57% | −0.09% |
| Native fallback paths | 3 | −1.12% | −1.19% |

普通内核 reader 使用共享核心而不经过用户公开库。表 14 显示，normal 下 monotonic 与 monotonic-raw 分别降低 0.993 和 1.439 ticks，coarse 增加 1.843 ticks；no-retpoline 下三条路径均降低。这些方向在各配置的四个 block 中一致。两种构建同时改变一组 mitigation 配置，因此配置间差异不归因于单条指令。

**Table 14: Ordinary kernel READ cost.** R/V denotes Raw/VKSO boot-averaged mean TSC ticks per call; Δ is VKSO minus Raw.

| Kernel reader | Normal R/V | Normal Δ | No-retpoline R/V | No-retpoline Δ |
| --- | ---: | ---: | ---: | ---: |
| Monotonic | 56.194 / 55.202 | −0.993 | 58.567 / 55.484 | −3.083 |
| Monotonic raw | 55.718 / 54.279 | −1.439 | 54.656 / 53.353 | −1.303 |
| Monotonic coarse | 9.197 / 11.039 | +1.843 | 11.023 / 8.753 | −2.270 |

### Publisher and Concurrent Readers

UPDATE recorder 在持有 timekeeper 锁后测量 `timekeeping_update()` 的发布区间，不包含锁等待或完整定时器中断。每次启动分别在 idle 和三种持续公开读取负载下采集 15 个窗口，每个窗口为 15 秒。主结果纳入全部 `action=0` 更新的原始 TSC 差，不扣除固定计时开销。逐次记录呈现低、高耗时集中区，高侧还包含子峰；完整均值同时保留各区间的位置和出现比例。

表 15 给出启动均值的等权平均。区间通过同 block 的 Raw/VKSO 启动均值差进行 percentile bootstrap，四个 block 枚举 256 种重采样序列。它描述启动间不确定性，不把窗口或逐次调用当成独立实验。该区间基于四个 block，逐项报告且未作多重比较校正。

**Table 15: Complete UPDATE cost under idle and sustained public readers.** Costs are boot-averaged means in TSC ticks/update. The pointwise 95% interval resamples block-level Raw/VKSO differences.

| Build and reader load | Raw | VKSO | Δ ticks/update | 95% interval for Δ |
| --- | ---: | ---: | ---: | --- |
| Normal, idle | 123.27 | 126.32 | +3.05 | [+2.22, +3.87] |
| Normal, monotonic | 129.96 | 128.00 | −1.95 | [−4.00, +0.23] |
| Normal, monotonic raw | 136.56 | 128.61 | −7.95 | [−10.71, −6.33] |
| Normal, monotonic coarse | 134.03 | 128.05 | −5.98 | [−8.33, −3.63] |
| No-retpoline, idle | 120.78 | 118.19 | −2.59 | [−4.19, −0.86] |
| No-retpoline, monotonic | 128.33 | 118.68 | −9.65 | [−12.58, −7.22] |
| No-retpoline, monotonic raw | 135.03 | 118.69 | −16.34 | [−18.23, −14.91] |
| No-retpoline, monotonic coarse | 135.50 | 120.53 | −14.97 | [−18.70, −12.74] |

Normal 的 idle publisher 增加 3.05 ticks/update；monotonic-raw 和 coarse 负载下分别降低 7.95 和 5.98 ticks。Monotonic 负载的均值差为 −1.95 ticks，但四个 block 中有一个为正，区间也跨零。No-retpoline 的四种负载均降低，范围为 2.59–16.34 ticks/update，方向在各自四个 block 中一致。

分布解释了为何单个峰或中位数不足以概括发布成本。Normal idle 中，以 Raw 120、VKSO 110 ticks 的历史谷值划分低、高侧，VKSO 的低侧均值为 84.10 ticks，低于 Raw 的 97.91 ticks；高侧占比却从 47.84% 增至 60.56%，最终完整均值增加 3.05 ticks。Normal monotonic-raw 的中位数汇总差为 +6 ticks，完整均值差则为 −7.95 ticks。阈值改变会影响分层描述，但不会改变完整均值。Raw normal 的独立诊断中，同一进位状态及倍率调整路径内部仍有低、高耗时样本，尚不能将这些集中区对应为已识别的业务状态。

长尾敏感性检查中，将 UPDATE 成本截顶到 300 ticks 后，八项均值差均保持原有符号，变化不超过 0.93 ticks。完整样本仍用于表 15。[分布报告](../../test/test_gettime/vkso-tests/direct-api/DISTRIBUTION_ANALYSIS.md)给出每次启动的直方图、全范围 CDF 和阈值敏感性；诊断追踪数据与正式性能样本分别分析。

持续 reader 在 writer 窗口开始前进入稳态，并在其结束后退出。表 16 测量包围该窗口的完整公开调用批次，采用相同的启动均值统计。Normal 的三种 reader 分别增加 0.806、0.523 和 1.014 ticks/call；no-retpoline 的 monotonic 与 monotonic-raw 各降低约一 tick，coarse 增加 0.064 ticks。这说明 publisher 与 reader 的收益需要分别衡量。

**Table 16: Public reader cost during periodic UPDATE.** R/V denotes Raw/VKSO boot-averaged mean TSC ticks per call over the enclosing load interval; Δ is VKSO minus Raw.

| Reader load | Normal R/V | Normal Δ | No-retpoline R/V | No-retpoline Δ |
| --- | ---: | ---: | ---: | ---: |
| Monotonic | 54.192 / 54.998 | +0.806 | 54.192 / 53.201 | −0.991 |
| Monotonic raw | 54.199 / 54.722 | +0.523 | 54.197 / 53.210 | −0.987 |
| Monotonic coarse | 16.056 / 17.070 | +1.014 | 16.056 / 16.121 | +0.064 |

### Functional and Sharing Evidence

每次启动在计时前检查公开 API 返回值与 errno、namespace 偏移、本地 context、fallback 及初始化语义。Fast-path 验证禁用时间与 getcpu syscall，确认受支持调用在用户态完成；VKSO 另外检查共享映射与内核源页的 PFN 一致性及 RX/R-- 权限。表 17 汇总各启动中的功能与共享证据，映射恢复在采集结束时检查。

**Table 17: Functional and sharing evidence across the Clocktime campaign.** Denominators count applicable boots; VKSO sharing checks cover both READ and UPDATE images.

| Check | Completed / applicable boots |
| --- | ---: |
| Correct kernel, package and completed collection | 32 / 32 |
| ABI and fallback matrix | 32 / 32 |
| Fast-path syscall-denial check | 32 / 32 |
| VKSO physical-page sharing and permissions | 16 / 16 |

Clocktime 将内核与用户态的时间计算合并到同一驻留执行体，用户侧通过 393 行 ABI 与初始化代码接入，并保留所测时间、namespace 和 fallback 语义。其成本由接口和负载共同决定：公开库中的若干短入口降低了调用成本，normal 的 coarse reader 与 idle publisher 则付出额外开销。共享执行页消除了独立用户计算副本，MM 与入口支持页增加了所测映射的驻留规模。该案例量化的是共享计算、状态重组及入口适配组成的完整子系统改造。

## Registration and Mapping Behavior

物理共享及释放行为在独立 KVM guest 中验证，API 性能使用前述物理机记录。实际 LZ4、BCH 和 XZ carrier 分别有五、四、四张声明页与源 kernel PFN 相同，同一注册会话中的完整算法工作负载通过。正常释放后，新映射恢复文件后备，owner 引用归零并可卸载。表 18 汇总与复用契约直接相关的结果；完整恢复矩阵见[附录 A](#appendix-a-registration-and-recovery-evidence)。

**Table 18: Evidence for the registration and mapping contract.** These observations use the transaction implementation on Linux 5.15.0-119; they are functional checks rather than deployment-performance measurements.

| 需要验证的性质 | 关键观察 |
| --- | --- |
| 实际共享执行页 | 三算法的十三张声明页与 kernel PFN 匹配；完整用户及内核工作负载通过 |
| 源内容与私有写隔离 | MAP_PRIVATE 写入产生 COW；共享写升级被拒绝，源内容及 PFN 保持 |
| 源页存活及正常释放 | 活跃注册持有 owner 引用；绑定释放后恢复文件内容，模块可卸载 |
| 失败结果可见且可恢复 | 源页预检失败不应用绑定；跨批提交失败回滚，释放残留可重试，manager 反映内核结果 |
| 声明类型符合实际权限 | 正常只读 text/rodata 可注册；相同 owner 在关闭只读保护后，其可写源页被拒绝 |

原注册实现没有持有 owner 引用，部分失败还会留下绑定并被 manager 误报成功。表 9–12 及内核端、应用和 setup 结果使用事务实现；旧实验和原始失败在独立归档及附录 A 中保留。源页权限检查发生在注册时，既不自动判定整页内容的公开性，也不验证其后发生的运行时代码改写。当前完整两端功能记录见[源页准入实验](../../test/evaluation/registration-typed-evidence.md)。

## Resident Pages and Per-process Support

共享执行页之外，VKSO 还需要注册对象、carrier/Shim 支持页和域内工作状态。注册模块为每个活动事务请求 688 B 的固定对象和每页 64 B 的 binding array；RELEASE 释放数组及 owner/page 引用，FORGET 回收终态对象。四十八次会话均在完成通知后查不到该事务，见[回收实验](../../test/evaluation/registration-retirement-evidence.md)。688+64N B 是分配请求量，不包含 allocator 元数据和未使用容量；对象释放也不等于所在 slab 页立即归还。下面分别计量库与 owner 的实际物理页，以及算法活动对象的请求量。

我们在同一 5.15.0-119 guest 中比较 BCH 普通同源 DSO 与完整 registered carrier 的页面占用，分别启动 1、4、16 个独立 loader。每组 loader 同时存活，在装载后触达目标及所需 shim 的全部可读 PT_LOAD 页，再从原始 pagemap 按 PFN 求并集。三个场景分别为装载专用 owner 前的普通 DSO、owner 已装载时的普通 DSO，以及保持注册的 VKSO。完整 BCH 功能矩阵由同一注册会话中的另一进程执行；这里的 loader 观测不包含 BCH control objects 和算法工作堆。

**Table 19: Observed BCH library and owner page unions after touching all readable PT_LOAD pages.** Counts are distinct 4 KiB PFNs across simultaneous loaders. Library scope includes code, read-only content, relocated private data and metadata. The table excludes manager, page tables and allocations outside the module core and selected libraries.

| 观测范围 | 1 loader | 4 loaders | 16 loaders |
| --- | ---: | ---: | ---: |
| 普通 DSO，owner 装载前 | 7 | 13 | 37 |
| 普通 DSO ∪ 已装载的完整 owner core | 13 | 19 | 43 |
| Registered carrier ∪ 所需 shim | 11 | 23 | 71 |
| Registered carrier ∪ shim ∪ 完整 owner core | 13 | 25 | 73 |

全部 registered loader 的三个 text 页和一个 rodata 页均匹配源 PFN，kernel/user 并集始终为四页。普通 DSO 的三个 executable PFN 也在进程间共享。普通 DSO 有五个组内共享 PFN，加上每 loader 两个不同 PFN；registered carrier 与 shim 合计有七个组内共享 PFN，加上每 loader 四个不同 PFN。计入相同的六页 owner core 后，两者在单 loader 时均为 13 页，VKSO 在 4 和 16 loaders 时分别多六页和三十页。该结果表明，所测小闭包的支持页成本抵消了目标页共享的空间收益。这里的专用 owner 与发行版 BCH 模块分别构建，普通 DSO 并不需要它；若与未装载 owner 的普通 DSO 比较，VKSO 的库、Shim 与 owner 合计分别多六、十二和三十六页。

完整 owner core 为 24 KiB，其中四页用于共享、两页用于其他 core 内容；page-cache 模块 core 为 48 KiB，PFN observer 为 16 KiB。活动 manager 的 VmRSS 为 1,216 KiB、PSS 为 1,212 KiB、VmPTE 为 28 KiB。Loader 的 VmPTE 为 88–100 KiB，本次布局中装载前后的增量为零，反映已有页表分配粒度。这些进程指标与库的 PFN 并集可能重叠，故分别呈现。表 19 计量选定库和完整 owner core，表 20 补充 BCH 工作对象；模块外分配及 allocator/slab 的完整物理占用在这一账本之外。原始记录与重建步骤见[BCH 资源证据](../../test/evaluation/results/bch_resource-qemu-20260912-attempt03/README.md)。

我们在另一 exact119 guest 中补充观测 BCH 的活动对象。每个进程使用一个后端，同时保留 m=13、t=4/8 的两个 control 和对应的 512 B payload 加 parity；依次建立、验证并释放一个 full-decode context。观测复用原 benchmark 的 C 分配和校验函数，原有完整三后端正确性矩阵在同一注册会话中另行通过。普通 DSO 与 registered carrier 的分配请求量相同：两个 control 及其持久表分别请求 41,448 B 和 49,896 B，表 20 给出同时存活的对象总量。

**Table 20: Live BCH allocation requests per process, identical for the native DSO and registered carrier.** Both parameter cases remain initialized; at most one decode context is live. Bytes exclude allocator metadata and initialization temporaries already freed before observation.

| 活动状态 | 分配对象数 | Control 及持久表 (B) | Codeword 与工作缓冲区 (B) | 合计 (B) |
| --- | ---: | ---: | ---: | ---: |
| 两个参数组初始化完成 | 30 | 91,344 | 1,044 | 92,388 |
| t=4 full-decode context 存活 | 33 | 91,344 | 1,586 | 92,930 |
| t=8 full-decode context 存活 | 33 | 91,344 | 1,614 | 92,958 |

三个角色下的 1/4/16 个同时存活进程均得到相同的每进程请求量。由对象地址区间重建的 PFN 集合显示，control 覆盖页在同组进程之间没有共享，而 control 与工作缓冲区可能共页。因此，共享执行页没有消除这些随进程数增加的活动对象；物理覆盖需按 PFN 求并集。覆盖页也可能包含其他分配，不能作为 BCH 独占成本，本账本不包含 allocator/slab 的完整成本及短暂分配峰值。原始快照、分配清单和重建结果见[BCH 活动对象证据](../../test/evaluation/bch-heap-evidence.md)。

## Applicability across Dependency Shapes

我们在尝试导出前固定八个 Linux API，覆盖显式输入、只读表、局部工作状态、格式化、回调以及内核私有状态。该分层案例集与已有 LZ4、BCH、XZ、clocktime 集成分别统计，用于检验依赖形态和当前构建的导出条件。它不是 Linux API 的随机样本。所有静态检查使用同一个 Ubuntu 5.15.0-119-generic final image；表 21 分别列出 checker 结果和实际运行证据。

**Table 21: Prospective API cases on the default exact119 kernel build.** Visited functions count the static checker traversal. Source-backed and generated executable pages are separate; neither count includes loader metadata or registration support. The revised checker batch has terminal records for all eight cases.

| API | Checker | Visited functions | Source-backed / generated text pages | 实际运行结果或当前构建障碍 |
| --- | --- | ---: | --- | --- |
| `xxh32` | PASS | 1 | 2 / 0 | 247 个向量在内核及用户入口均匹配独立参考 |
| `crc32_le` | FAIL | 2 | — | 一处绝对地址表引用；未构造 carrier |
| `sha256` | FAIL | 5 | — | 18 处绝对地址引用；另有 14 处插桩记录 |
| `hex_dump_to_buffer` | FAIL | 1,834 | — | 6,405 条静态引用、408 个间接点、2,230 处插桩、3,542 条硬失败及 716 条未解析记录；未构造 carrier |
| `string_escape_mem` | FAIL | 2 | — | 四处绝对地址表引用；未构造 carrier |
| `sort` | PASS | 3 | 2 / 1 | 1,152 个组合在内核及用户入口均匹配独立参考 |
| `rhashtable_insert_slow` | FAIL | 1,844 | — | 6,398 条静态引用、411 个间接点、2,232 处插桩、3,530 条硬失败及 721 条未解析记录；容器、RCU、锁与分配语义未重构 |
| `get_random_bytes` | FAIL | 28 | — | 94 条静态引用、36 处插桩、36 条硬失败及 4 条未解析记录；kernel-private RNG state，未构造 carrier |

静态结果揭示了语义适用性与二进制形态的区别。`crc32_le` 和 `string_escape_mem` 的主要障碍是当前机器码中的绝对地址表引用，不能据此把只读查表归为内核私有状态。`hex_dump_to_buffer` 的通用格式化依赖沿警告和错误处理路径扩展，修订批次记录 6,405 条静态引用、408 个间接点、2,230 处插桩、3,542 条硬失败，以及涉及 347 个函数的 716 条未解析记录。这些计数描述静态展开，不代表一次格式化调用实际执行了这些分支。

对两个 PASS 入口，我们在匹配该 image 的独立 KVM guest 中使用原有完整导出流程，直接复用 built-in implementation。独立 GPL 观测模块通过公开内核符号调用原入口，用户 driver 通过实际 carrier 的公开符号调用导出入口；两侧分别与独立参考核对。XXH32 的 247 个向量包含七个已知答案、四种 seed、三种对齐和算法块及页边界附近的长度，同时检查输入不变。Sort 的 1,152 个组合覆盖六种数组长度、六种元素宽度、两种对齐、四种输入分布、正反比较方向，以及默认和自定义 swap；校验完整输出、元素多重集和缓冲区边界。

Sort 的五个间接调用点通过显式用户回调完成绑定。两侧各记录 95,384 次 comparator 调用和 35,252 次自定义 swap 调用，逐例输出及调用次数一致。观测 driver 的回调使用显式栈对齐入口，swap 的长度参数保持原 API 的 `int` 类型。现有 exporter 将同页的四个 indirect thunks 和 return thunk 生成为用户侧跳转页，保留其相对位置；算法所在的两个页继续复用内核 backing。相比之下，XXH32 的第二个共享页包含原 return thunk。因此，checker 的 visited-function 数、最终依赖和共享页数具有不同口径。

两个 carrier 的全部声明页均在活动注册期间由独立 loader 观测到 kernel/user PFN 一致；功能 driver 使用同一注册 inode，其 API 地址另与实际 ELF symbol 和 built-in root 对齐。恢复后的新映射不再使用原 source PFN。这组结果支持显式输入计算及所测回调配置的完整功能，并保留生成支持页的成本；它不改变前述物理机性能结果或 BCH 资源账本。这两个入口在加入类型和实际权限检查的 v4 注册流程下再次通过相同完整矩阵，manager 在发送页面计划前确认运行内核身份。原始 PFN 记录覆盖 4 KiB 与 2 MiB 内核映射，见[源页准入实验](../../test/evaluation/registration-typed-evidence.md)。完整输入、独立重放和构建记录见[适用范围证据](../../test/evaluation/applicability-evidence.md)。

将两个新导出入口与四个既有集成放在同一结构口径下，可以区分无需算法修改的入口、依赖绑定改造和状态重构。表 22 从实际 carrier 的符号、重定位、page-map 与 PFN 记录提取数据。函数数仅包含声明的源代码闭包，按入口地址去重，并将 thunk 单列；它不等于整份 owner 的函数数，也不包含同页相邻代码。私有支持页只统计 carrier，外部 Shim 与其他运行资源另行计费。

**Table 22: Structure of the six deployed cases.** Source functions and resident thunk bodies are separate. Source pages are text/read-only data/shared state; generated pages belong to the carrier. Helper slots count stored external function pointers, while callback parameters and context fields are listed explicitly.

| Case | Source functions / thunks | Source pages T / RO / state | Generated text pages | Dependency binding |
| --- | ---: | --- | ---: | --- |
| xxh32 | 1 / 1 | 2 / 0 / 0 | 0 | 0 helper slots；显式 input/seed |
| sort | 3 / 0 | 2 / 0 / 0 | 1 | 0 helper slots；comparator 与 optional swap 参数 |
| LZ4 | 3 / 0 | 4 / 1 / 0 | 0 | 3 memory-helper slots |
| BCH | 11 / 0 | 3 / 1 / 0 | 0 | 4 allocator/memory-helper slots |
| XZ | 20 / 0 | 3 / 1 / 0 | 0 | 4 allocator/memory-helper slots；私有 CRC table |
| Clocktime | 9 / 4 | 2 / 0 / 1 | 1 | 40 B context：2 个 failure callbacks、3 个数据地址 |

三算法共十一处 helper slots 均为八字节对象，其内核与用户目标可分别从 owner 和 carrier 重定位重建。LZ4 的用户目标为三个唯一命名的 Shim bridge；XZ 的 memcpy 也通过显式 bridge 绑定到默认 libc 实现，其余槽位和 BCH 使用域内分配与内存 helper。Clocktime 不使用动态 helper 重定位，私有 binder 将 context 写入五个地址槽。不同归档中的二十个声明源页均有 PFN 匹配记录，这一跨案例总数不表示单次部署的资源占用。

**Table 23: Source changes for algorithm adaptation.** Counts compare full C/header files with the retained Ubuntu 5.15.0-119.129 source baseline using the same lexical policy. Owner support and Kbuild are separate; common exporter/Shim code and tests are excluded.

| Algorithm | Compared files | Added / deleted code lines | Owner support SLOC | Kbuild noncomment lines |
| --- | ---: | ---: | ---: | ---: |
| LZ4 | 3 | 45 / 7 | 18 | 25 |
| BCH | 1 | 41 / 11 | 19 | 17 |
| XZ | 8 | 64 / 19 | 27 | 26 |

这些修改包括显式 helper 绑定、API/头文件适配、BCH syndrome 与 XZ 字典循环的局部缓存，以及支持可复用代码的构建设置。两项循环改写应用于 Adapted DSO 和内核 owner，Native DSO 与内核 Matched 保留原始循环。三个 owner 的合作 descriptor 与初始化调用计入各自 support；通用 owner 实现单列。源基线为保留的 Ubuntu 5.15.0-119.129 源码包，与新 Matched 使用的发行版版本一致。Clocktime 的改造还涉及共享 reader/state、publication、MM/namespace 和两个域的入口；表 10(a) 按职责给出源码改造量，表 10(b) 分别给出内核、carrier 和公开库的最终机器码规模。源码行数与 ELF 段字节数属于不同指标，均不换算为人工工时。

构建条件也是适用范围的一部分。LZ4 的算法对象移除 ftrace 入口，BCH/XZ 还关闭所用算法对象的 stack protector、sanitizer 与 jump-table 生成；XZ 使用完整的 XZ_SINGLE/x86-BCJ/internal-CRC 配置。表中 LZ4/BCH/XZ 实际请求导出的 API 数分别为 2/4/5。六个成功案例均有两域功能记录，三算法的内核与用户工作负载使用同一次注册的 owner。XZ 的 support 包含五个公开模块导出，算法源码差分为新增 64 行、删除 19 行。源码、完整补丁重放、构建限制和逐案例记录见[跨案例适配账本](../../test/evaluation/applicability-ledger-evidence.md)。

## Application Integration and Deployment Cost

本节保留独立应用/setup 采集的同源标量构建与 libc helper 对照；6.3 的 Native/Adapted 使用新普通 O2 构建。两组各自使用其记录的基线，不合并成本比。

### Complete LZ4 CLI

我们将 Linux LZ4 接入完整 upstream 1.9.3 CLI，保留 frame processing、checksum、内存分配和文件 I/O。工作负载为全部十二个 Silesia 文件、64 KiB 与 1 MiB independent blocks，分别执行压缩和解压。对照包含同源 libc DSO、upstream DSO 和 stock CLI；前三种可选择 backend 的 CLI 使用相同前端，stock 保留原始命令实现。

每次部署执行四轮，共 768 次完整命令，压缩输出由 stock CLI 交叉解码，解压结果逐文件核对。额外十二份诊断调用记录覆盖两种 block sizes、两种操作和三个可选 DSO，确认命令调用选中的 API；诊断插桩不进入性能样本。每轮先累加十二个文件的完整命令时间，再计算 backend 成本比。

**Table 24: Complete LZ4 CLI file workflows.** Times sum twelve file commands, in ms. Commands include process startup, framing and buffered file I/O; output is closed without fsync. Inputs are pre-read. Cost ratios retain matching rounds; brackets span deployment medians.

| Operation | Block size | Same-source ms | VKSO ms | Cost / same-source | Cost / stock CLI |
| --- | --- | --- | --- | --- | --- |
| compress | 64 KiB | 694.95 | 683.82 | 0.984 [0.984, 0.986] | 1.008 [1.008, 1.009] |
| compress | 1024 KiB | 670.15 | 657.74 | 0.982 [0.981, 0.983] | 1.008 [1.007, 1.009] |
| decompress | 64 KiB | 325.77 | 330.92 | 1.014 [1.012, 1.018] | 1.024 [1.024, 1.028] |
| decompress | 1024 KiB | 325.67 | 327.05 | 1.006 [1.005, 1.010] | 1.034 [1.032, 1.036] |

相对同源 DSO，完整命令的压缩成本变化为 -1.8%–-1.6%，解压为 0.6%–1.4%。Stock CLI 的结果同时列出，体现应用实际可选路径。这些命令在注册已经活动时运行，因此体现复用后的工作流成本；建立和释放由下一组对照计费。

独立 guest 中，carrier 的四个 RX text 页及一个只读 rodata 页均与 source PFN 一致；释放后的新映射恢复文件后备。完整 CLI 也揭示了静态闭包检查遗漏：旧构建虽通过检查并共享四页，却因未重绑定的直接 memset 调用在首个 dickens/64 KiB 压缩中触发 SIGSEGV。三个显式私有 slots 和 ABI bridge 修复实际绑定，checker 随之拒绝缺少可重定位位置的直接 Shim 引用。原失败、修复及完整调用证据见[应用记录](../../test/evaluation/lz4-application-evidence.md)。

### Full-task Setup and Release

部署成本使用同源 Linux LZ4 DSO 与相同实际 carrier，按 64 KiB blocks 完成全部十二个文件的压缩、解压及逐字节比较。每个新进程执行一遍或三遍完整语料任务。Active 模式复用已有注册，只计新进程及完整任务；ready 模式复用已构造 carrier，将注册、任务和释放一并纳入命令时间。每种模式/backend/任务遍数保留三轮配对测量及 trace on/off 两种观察条件。表 25 使用无插桩的完整命令耗时。

**Table 25: Complete LZ4 task cost with and without registration in the command.** Trace-off elapsed times are in ms and include full input, compression, decompression and validation. Active starts a new process under an existing registration; ready additionally registers and releases a constructed carrier. Offline construction is separate.

| Registration scope | Corpus passes | Native ms | VKSO ms | Cost / native |
| --- | --- | --- | --- | --- |
| active | 1 | 839.35 | 836.05 | 0.997 [0.996, 0.998] |
| active | 3 | 2090.82 | 2084.01 | 0.996 [0.996, 0.998] |
| ready | 1 | 837.51 | 1438.17 | 1.717 [1.715, 1.721] |
| ready | 3 | 2091.53 | 2689.03 | 1.287 [1.285, 1.287] |

已有 carrier 的单遍命令从 native 的 837.51 ms 增至 VKSO 的 1438.17 ms，成本比为 1.717；三遍任务的比值降至 1.287。活动注册下的成本接近同源 DSO，但每次建立和释放的命令仍有可见额外成本。这组结果说明复用注册能摊薄生命周期成本，所测一遍和三遍任务均未证明包含注册的整体加速。

首次有效结果定义为第一遍完整语料校验完成。插桩记录另行报告该时刻、DSO 装载、输入读取、计算及释放；阶段存在嵌套，不相加为总耗时，也不从无插桩主结果中扣除固定校准值。阶段结果见附录 B，完整协议及原始时间戳见[setup 对照](../../test/evaluation/setup-comparison-evidence.md)。

**Table 26: Offline LZ4 export stages.** Seconds are medians and ranges across complete deployments. Timings retain shell observer overhead and exclude owner compilation/loading. The benchmark application interval is excluded.

| Stage | Median seconds | Deployment range |
| --- | --- | --- |
| krg | 3.870 | [3.855, 3.884] |
| checker | 11.995 | [11.965, 12.277] |
| header | 2.708 | [2.651, 2.716] |
| carrier | 0.330 | [0.325, 0.356] |
| install | 0.103 | [0.101, 0.120] |

离线分析、闭包检查和 carrier 生成按阶段单列于表 26，每次完整算法部署构造一次。该表不包含 owner 编译及装载；ready 命令从可用 carrier 和已装载 owner 开始。离线成本与表 25 的注册后任务属于不同复用层次，不能用整组 benchmark runner 的耗时替代其中任一阶段。

## Reproducibility

First-touch、PGOT、LZ4、BCH 和 XZ 均提供单命令入口，正式参数和数据来源记录于对应 README 与 results directory。结果保留原始 CSV、环境与构建信息、功能校验、disassembly 和 page-map audit，分别支持数值复算与被测执行体核对。Clocktime 的 READ/UPDATE/CONCURRENT 由固定 boot/collect 流程生成，归档中记录内核变体、测量协议和逐轮样本。

表 3–8 来自 first-touch 汇总及 PGOT 各层的 paper tables；表 9 和用户端主图来自[新三算法六版本采集](../../test/section63/README.md)，BCH 有十二次、LZ4/XZ 各三次完整物理机部署；完整结果及独立原因诊断见[实验报告](../../test/section63/results/report.md)；表 24–26 及附录 B 使用[独立 LZ4 应用与 setup 记录](../../test/evaluation/results/application-setup/README.md)。两组分别从原始记录重建配对轮次、部署统计和表格。Clocktime 的表 10(a) 来自[源码改造账本](../../test/test_gettime/vkso-tests/code-size/CHANGE_AUDIT.md)，表 10(b)、11、17 取自[32 次启动的完整 Raw/VKSO 采集](../../test/test_gettime/vkso-tests/baremetal/results/20260924T065535Z-clocktime-full-summary.json)及其原始记录；表 12–16 依据同轮原始数据的[完整均值与分布重算](../../test/test_gettime/vkso-tests/baremetal/results/clocktime-distribution-analysis/20260924T065535Z-clocktime-full/report.json)，表 13 对表 12 对应的未舍入均值比取几何平均。双峰路径的单独诊断不混入正式采集。算法性能采用当前完整采集。

表 18 汇总[事务与恢复](../../test/evaluation/registration-transaction-evidence.md)、[文件/VMA 检查](../../test/evaluation/registration-notification-evidence.md)和[源页准入](../../test/evaluation/registration-typed-evidence.md)；原版本及完整事务观察分别列于附录表 A1–A2。表 19 来自[BCH 多进程资源记录](../../test/evaluation/results/bch_resource-qemu-20260912-attempt03/README.md)，表 20 来自[BCH 活动对象记录](../../test/evaluation/bch-heap-evidence.md)。Guest 提供独立的功能和 PFN 证据，其计时字段不加入物理机性能样本。

表 21 来自固定八例的修订静态记录及[xxh32/sort 实际导出记录](../../test/evaluation/applicability-evidence.md)。原始 CSV 保留完整输入和输出，独立重放使用 libxxhash 0.8.1 与按元素字节排序的参考，并核对 API 地址、生成 thunk、page map 和 PFN。两个已通过入口各在同一 guest 内完成一次注册会话；功能组合数不作为性能重复次数。六个静态失败项不构造 carrier，也不计入运行时成功率。

# Related Work

**Shared objects, loaders, and binary transformation.** 传统 shared-library systems 通过位置无关代码、动态符号解析和 copy-on-demand mappings 在进程间共享文件后备代码；SunOS shared libraries 和后续 safe dynamic linking 工作奠定了这一对象语义与保护边界。[26,27] Luci 将普通 shared objects 用于 off-the-shelf 软件的动态更新，iFed 则把 dynamic loader 组织为可组合的 transformation passes，并在用户态 library 上优化 hugepage 和 relocation cost。[28,36] 这些工作改变的是用户态对象的版本或装载过程，仍以一份用户态 payload 为执行体。VKSO 沿用 loader-visible object semantics，却把 selected logical pages 重绑定到当前运行内核已经驻留的页；其核心问题因此不是设计另一种动态链接器，而是验证跨 privilege domain 的 backing、state 与 control-flow closure。

**Kernel-code rehosting and isolation.** LKL 与 Rump Kernels 将重新构建的 kernel or subsystem image 连同 host adaptation layer 带入新的执行环境，适合需要大范围 kernel APIs 或完整 subsystem semantics 的场景。[29,30] KSplit 从另一个角度分析未修改的 kernel/driver source，显式识别共享 state 和同步需求，以支持隔离而不是复用同一执行体。[37] VKSO 面向更细粒度、已驻留的 final binary closure：它不携带第二个 kernel instance，也不重新编译一份 user-owned execution body。相应代价是适用边界更窄；依赖 kernel objects、privileged locking domain 或无法发布状态的路径仍位于 reuse boundary 之外。内核锁设计本身依赖 privileged object ownership and execution context，也说明仅让指令可达并不足以重宿主其同步语义。[25]

**Binary sharing and kernel/user fast paths.** ORC 通过扩展 ELF 和 capability-based relocation，在隔离域之间显式共享 immutable binary objects，并为每个域保留私有状态；它解决的是跨 tenant 的对象复用与隔离，而不是从运行内核中复用 resident pages。[38] vDSO 与 VKSO 都让用户程序通过普通 ELF symbols 读取内核发布的只读状态，避免高频查询的 syscall entry。[31] FlexSC、Privbox 和 Userspace Bypass 则分别通过 exception-less scheduling、sandboxed privileged execution 或将用户指令透明移入内核来降低跨界成本。[33,35,39] 这些系统改变调用协议或执行位置；VKSO 的方向相反，从 final kernel/LKM binary 出发，以 closure analysis、page grafting 和 explicit dependency adaptation 构造标准用户态 carrier。大型 clocktime case study 检验的正是这种通用机制能否收敛原本分离的 kernel/vDSO execution bodies，而非提出另一组专用 vDSO API。

# Discussion



## Applicability and Limitations

VKSO 不是自动的 arbitrary-kernel-function exporter。当前 Analyzer 提供 ELF 依赖与引用检查，page identity 则由独立的运行时 PFN 观测验证。静态 PASS 不保证完整控制流或 helper 绑定，高层语义等价、数据可公开性和 helper 副作用也需要 export author 给出明确契约及相应验证。因而 VKSO 最适合计算密集或调用频繁、状态依赖能够收敛为少量显式输入的目标，不适合直接操作 kernel objects、devices、per-CPU state 或 privileged synchronization domains 的功能。

Carrier 的部署依赖指定的内核和 owner 构建及其运行地址。Kernel update、module relink、compiler mitigation 或 boot-time rewriting 改变代码、布局或调用目标后，需要重新分析和构建。当前 `vkso replace/exec` 从给定输入重新生成 carrier；manager 在 owner 被引用固定后核对模块所属关系及 owner/vmlinux 的 GNU build ID，不匹配时拒绝发送页面计划。Build ID 标识链接产物，不能检测保留该 note 的后续文件修改或运行时代码重写。面向应用的 exported symbol version 可由新 carrier 保持，但 kernel internal ABI 及其运行地址仍是每次部署需要核实的输入。

本文在 Linux/x86-64 上实现并评估完整原型。Design 所需的 shared-object carrier、object-backed mapping 和 first-touch installation 在主流 general-purpose OS 中普遍存在，但将 grafting hook、page lifetime 与 loader metadata 移植到其他内核仍需要系统特定实现；本文不把 Linux 原型的代码量或性能数字外推到其他 OS。类似地，当前数据只覆盖一台 x86-64 微架构，retpoline/ITS 的成本和不同 cache hierarchy 下的 first-touch 行为需要在更多硬件上复核。

## Threat Model and Security Boundary

本文信任 kernel、export builder、page-grafting manager、目标 kernel/LKM image 和 manifest。攻击者是能够装载已授权 Stub DSO 的普通非特权进程：它可以选择任意 API 参数、以任意顺序并发调用导出入口，并尝试通过 `mmap`、`mprotect` 或文件操作改变映射。保护目标是导出映射不赋予应用修改 kernel backing 或读取未授权 kernel pages 的能力。Closure 分析检查声明入口及其依赖的控制目标，page grafting 本身不限制进程执行其地址空间中的其他代码。已显式导出的机器码和只读常量按设计对该进程可见。

**Write integrity.** Reusable text、rodata 和 shared state 在 Stub DSO 中分别以 user RX、R/NX 和 R/NX 权限映射，user-writable data 使用不指向 kernel PFN 的私有页面。管理器在 BEGIN 前设置 carrier 文件的 immutable 标志；内核在持有文件后拒绝已有写访问和 writable shared mappings，恢复全部绑定后才释放这些限制，manager 再撤销自身添加的标志。附录表 A1 给出原实现 ready 之后的权限观察；附录表 A2 检查事务实现对已有写访问的拒绝，以及并发 fault、持久只读映射和私有 COW 的恢复行为。

**Page granularity.** Page grafting 以物理页为最小单位，因此导出一个符号也会使同一页内的其他字节可见。Shared-state builder 因此只接受占据完整、对齐页的显式允许列表对象。对 executable pages，安全部署应用专用 section/page 隔离 export closure，或证明页内所有 colocated symbols 均可向用户态暴露。当前原型能严格检查 synthetic thunk page 和 shared-data page；若普通 text page 上还共存未分析函数，则必须依靠 linker layout 隔离，否则该 page 不应导出。

**Side channels and code disclosure.** 共享物理代码页会产生与 shared libraries 类似的 cache 和 access-pattern channels，且 kernel/user 共享使攻击者可能观察目标页的内核活动。消除这类 microarchitectural side channels 不在本文范围内。系统因此不应导出其访问模式或指令字节本身具有机密性要求的对象，并应把扩大 code-reuse gadgets 与 KASLR 攻击面纳入部署策略评估。

# Conclusion

VKSO 将跨 privilege domain 的代码复用转化为一个有明确边界的 binary-closure problem：state、control 和 code-shape constraints 决定什么可以复用，PIC-compatible construction、standard carrier、page grafting 和 Shim 决定如何复用。字节一致的 XXH32 对照得到相同的 hot-call 批次中位数均值，真实算法的两端成本则随适配和构建条件变化。Clocktime 使内核与用户共享驻留时间计算页；相对原生 vDSO，normal 构建的 13 个非 fallback 公开路径以完整均值计算的等权几何平均成本降低 3.87%，七种 `clock_gettime` fast path 的集合增加 2.57%，每 MM 支持页也增加了所选映射的驻留 PFN。LZ4 的完整应用和 setup 对照说明，复用后的执行成本接近同源 DSO，并不意味着每次建立和释放均能回本。BCH 所测库与专用 owner 范围没有净页节省，纠错路径也存在退化；共享执行体的价值需要结合实现重复、支持资源和实际使用方式判断。

# References

1 `mmap(2)`: Linux manual page. [https://man7.org/linux/man-pages/man2/mmap.2.html](https://man7.org/linux/man-pages/man2/mmap.2.html)

2 `ld.so(8)`: Linux manual page. [https://man7.org/linux/man-pages/man8/ld.so.8.html](https://man7.org/linux/man-pages/man8/ld.so.8.html)

3 *Page Tables*: The Linux Kernel Documentation. [https://docs.kernel.org/mm/page_tables.html](https://docs.kernel.org/mm/page_tables.html)

4 *Process Addresses*: The Linux Kernel Documentation. [https://docs.kernel.org/mm/process_addrs.html](https://docs.kernel.org/mm/process_addrs.html)

5 *Overview of the Linux Virtual File System*: The Linux Kernel Documentation. [https://docs.kernel.org/filesystems/vfs.html](https://docs.kernel.org/filesystems/vfs.html)

6 *Linux Filesystems API summary*: The Linux Kernel Documentation. [https://docs.kernel.org/filesystems/api-summary.html](https://docs.kernel.org/filesystems/api-summary.html)

7 *Virtual Address Spaces*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/virtual-address-spaces](https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/virtual-address-spaces)

8 *About Dynamic-Link Libraries*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows/win32/dlls/about-dynamic-link-libraries](https://learn.microsoft.com/en-us/windows/win32/dlls/about-dynamic-link-libraries)

9 *Load-Time Dynamic Linking*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows/win32/dlls/load-time-dynamic-linking](https://learn.microsoft.com/en-us/windows/win32/dlls/load-time-dynamic-linking)

10 *Run-Time Dynamic Linking*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows/win32/dlls/run-time-dynamic-linking](https://learn.microsoft.com/en-us/windows/win32/dlls/run-time-dynamic-linking)

11 *Managing Memory Sections*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-sections](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-sections)

12 `SECTION_OBJECT_POINTERS` structure: Microsoft Learn. [https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_section_object_pointers](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_section_object_pointers)

13 *File Caching*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows/win32/fileio/file-caching](https://learn.microsoft.com/en-us/windows/win32/fileio/file-caching)

14 *Creating a File Mapping Object*: Microsoft Learn. [https://learn.microsoft.com/en-us/windows/win32/memory/creating-a-file-mapping-object](https://learn.microsoft.com/en-us/windows/win32/memory/creating-a-file-mapping-object)

15 *Overview of Dynamic Libraries*: Apple Developer Documentation. [https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/OverviewOfDynamicLibraries.html](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/OverviewOfDynamicLibraries.html)

16 *Dynamic Library Usage Guidelines*: Apple Developer Documentation. [https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html)

17 `dyld(1)`: Apple Developer Documentation. [https://leopard-adc.pepas.com/documentation/Darwin/Reference/ManPages/man1/dyld.1.html](https://leopard-adc.pepas.com/documentation/Darwin/Reference/ManPages/man1/dyld.1.html)

18 *About the Virtual Memory System*: Apple Developer Documentation. [https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/AboutMemory.html](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/AboutMemory.html)

19 *Memory and Virtual Memory*: Apple Kernel Programming Guide. [https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html)

20 *Managing Data*: Apple IOKit Fundamentals. [https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/DataMgmt/DataMgmt.html](https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/DataMgmt/DataMgmt.html)

21 `rtld(1)`: FreeBSD Manual Pages. [https://man.freebsd.org/cgi/man.cgi?query=rtld&sektion=1](https://man.freebsd.org/cgi/man.cgi?query=rtld&sektion=1)

22 `mmap(2)`: FreeBSD Manual Pages. [https://man.freebsd.org/cgi/man.cgi?query=mmap&sektion=2](https://man.freebsd.org/cgi/man.cgi?query=mmap&sektion=2)

23 *Design elements of the FreeBSD VM system*: FreeBSD Documentation Portal. [https://docs.freebsd.org/en/articles/vm-design/](https://docs.freebsd.org/en/articles/vm-design/)

24 *FreeBSD Architecture Handbook*: FreeBSD Documentation Portal. [https://docs.freebsd.org/en/books/arch-handbook/book/](https://docs.freebsd.org/en/books/arch-handbook/book/)

25 John H. Baldwin. *Locking in the Multithreaded FreeBSD Kernel*. BSDCon 2002.

26 Robert A. Gingell, Meng Lee, Xuong T. Dang, and Mary S. Weeks. *Shared Libraries in SunOS*. USENIX Summer 1987.

27 Michael Hicks, Stephanie Weirich, and Karl Crary. *Safe and Flexible Dynamic Linking of Native Code*. Types in Compilation, 2001.

28 Bernhard Heinloth, Peter Wägemann, and Wolfgang Schröder-Preikschat. *Luci: Loader-based Dynamic Software Updates for Off-the-shelf Shared Objects*. USENIX ATC 2023.

29 Octavian Purdila, Lucian Adrian Grijincu, and Nicolae Tapus. *LKL: The Linux Kernel Library*. 9th RoEduNet IEEE International Conference, 2010, pp. 328–333. [https://ieeexplore.ieee.org/document/5541547](https://ieeexplore.ieee.org/document/5541547)

30 Antti Kantee. *Rump File Systems: Kernel Code Reborn*. USENIX ATC 2009. [https://www.usenix.org/conference/usenix-09/rump-file-systems-kernel-code-reborn](https://www.usenix.org/conference/usenix-09/rump-file-systems-kernel-code-reborn)

31 Michael Kerrisk. `vdso(7)`: Linux manual page. [https://man7.org/linux/man-pages/man7/vdso.7.html](https://man7.org/linux/man-pages/man7/vdso.7.html)

32 *User Space Interface: Kernel Crypto API*. The Linux Kernel Documentation. [https://docs.kernel.org/crypto/userspace-if.html](https://docs.kernel.org/crypto/userspace-if.html)

33 Livio Soares and Michael Stumm. *FlexSC: Flexible System Call Scheduling with Exception-Less System Calls*. 9th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2010). [https://www.usenix.org/conference/osdi10/flexsc-flexible-system-call-scheduling-exception-less-system-calls](https://www.usenix.org/conference/osdi10/flexsc-flexible-system-call-scheduling-exception-less-system-calls)

34 Simon Peter, Jialin Li, Irene Zhang, Dan R. K. Ports, Doug Woos, Arvind Krishnamurthy, Thomas Anderson, and Timothy Roscoe. *Arrakis: The Operating System is the Control Plane*. 11th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2014), pp. 1–16. [https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter)

35 Dmitry Kuznetsov and Adam Morrison. *Privbox: Faster System Calls Through Sandboxed Privileged Execution*. 2022 USENIX Annual Technical Conference (USENIX ATC 22). [https://www.usenix.org/conference/atc22/presentation/kuznetsov](https://www.usenix.org/conference/atc22/presentation/kuznetsov)

36 Yuxin Ren, Kang Zhou, Jianhai Luan, Yunfeng Ye, Shiyuan Hu, Xu Wu, Wenqin Zheng, Wenfeng Zhang, and Xinwei Hu. *From Dynamic Loading to Extensible Transformation: An Infrastructure for Dynamic Library Transformation*. 16th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2022), pp. 649–666. [https://www.usenix.org/conference/osdi22/presentation/ren](https://www.usenix.org/conference/osdi22/presentation/ren)

37 Yongzhe Huang, Vikram Narayanan, David Detweiler, Kaiming Huang, Gang Tan, Trent Jaeger, and Anton Burtsev. *KSplit: Automating Device Driver Isolation*. 16th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2022), pp. 613–631. [https://www.usenix.org/conference/osdi22/presentation/huang-yongzhe](https://www.usenix.org/conference/osdi22/presentation/huang-yongzhe)

38 Vasily A. Sartakov, Lluís Vilanova, Munir Geden, David Eyers, Takahiro Shinagawa, and Peter Pietzuch. *ORC: Increasing Cloud Memory Density via Object Reuse with Capabilities*. 17th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2023), pp. 573–587. [https://www.usenix.org/conference/osdi23/presentation/sartakov](https://www.usenix.org/conference/osdi23/presentation/sartakov)

39 Zhe Zhou, Yanxiang Bi, Junpeng Wan, Yangfan Zhou, and Zhou Li. *Userspace Bypass: Accelerating Syscall-intensive Applications*. 17th USENIX Symposium on Operating Systems Design and Implementation (OSDI 2023), pp. 33–49. [https://www.usenix.org/conference/osdi23/presentation/zhou-zhe](https://www.usenix.org/conference/osdi23/presentation/zhou-zhe)

# Appendix A: Registration and Recovery Evidence

本附录区分原注册实现、后续事务实现及类型检查的观测。合成文件用于检查映射与失败行为，真实算法会话用于验证完整调用；这些 guest 记录不替代物理机性能结果。

## Registration, Mapping and Recovery Details

我们在独立 KVM guest 中使用同一套 5.15.198 kernel、owner module 和页面管理器检查注册到释放的行为。测试把 owner 的一张 text page 注册到合成文件的指定页偏移，直接比较 kernel/user PFN；这里测量映射行为，不采集 API 性能。扩展会话包含四个独立 reader 进程，其中一个以 UID/GID 65534、无 effective capabilities 运行。文件属于该用户且权限为 0666，文件操作测试从 manager 建立 ready 文件后开始。

**Table A1: Registration, mapping and ordered-release observations of the original implementation.** The fixture uses a controlled file offset. PFN equality is checked after faulting each mapping; the completion-protocol revision is evaluated separately below.

| 检查对象 | 实际路径 | 观察结果 |
| --- | --- | --- |
| 物理页共享 | 四个进程读取注册页 | 四个 user PFN 均等于 kernel PFN |
| 只读映射 | 对只读 PTE 执行用户态 store | SIGSEGV |
| 私有写入 | 特权与非特权进程分别对 MAP_PRIVATE 执行 mprotect(RW) 和 store | 均产生独立 COW PFN；源页内容不变 |
| 共享写权限 | 非特权进程以只读 fd 建立 MAP_SHARED，再请求 mprotect(RW) | EACCES |
| 新文件操作 | 非特权 owner 对已注册文件执行 open(RDWR) 和 truncate | 均为 EPERM |
| 正常释放 | 关闭全部 reader，恢复绑定，再卸载 owner | 原文件内容恢复，manager 正常退出，owner 卸载成功 |
| Owner 引用 | 注册前、ready 后、活跃 reader 期间及恢复后读取 module refcnt | 七个观察点均为 0 |
| 部分注册失败 | 同批次先注册有效页，再提交无 PTE 的源地址 | 内核返回 ENOMEM；manager 仍报告成功并进入 ready，首个绑定仍可访问 |
| 恢复结果传递 | 恢复上述两页计划 | 内核恢复首个绑定，在第二页报告 ENOENT；manager 仍报告成功并退出 0 |

这些结果表明，所测私有写入通过 COW 保持源页内容，正常退出顺序能够恢复文件后备。该原版本没有增加 owner 的 module refcount，因此表 A1 的生命周期结果依赖 runner 保持 owner 驻留并按顺序清理。首次会话中的三个 reader 也观察到相同的共享、COW 和正常释放行为。

部分失败检查使用另一独立会话：提交前确认第二个源地址没有 present PTE，再观察 kernel 日志、manager ready 状态和两个用户映射。失败后首个绑定仍可访问，说明该批次操作不具备事务式回滚；旧 manager 的成功状态也未反映内核结果。显式恢复后，这两个文件页均恢复原内容，owner 可按顺序卸载。

事务实现将完整计划的完成状态与单次传输分开。我们在 5.15.0-119 guest 中使用完整 manager 和注册模块，以提供 300 张独立 resident pages 的 owner 检查两批计划的提交和恢复。测试页不作为算法执行，用于跨越 256 页传输边界。对三页计划逐项注入错误，并在 300 页计划的首、中、批次边界及末页注入错误；每次都读取全部文件内容并检查剩余绑定与模块引用。

**Table A2: Full-plan transaction and recovery observations on Linux 5.15.0-119.** Failure indices are zero-based. Fault injection is disabled in the separate application workflow.

| 检查对象 | 观察结果 |
| --- | --- |
| 300 页计划，分两批 STAGE | STAGE 后文件保持原内容；COMMIT 返回 300 个绑定，RELEASE 恢复全部内容 |
| 三页计划的各位置源页检查失败 | 首次绑定前拒绝，applied 为 0 |
| 300 页计划在第 0、150、255、256、299 项提交失败 | 均返回 EIO，已应用绑定全部回滚，300 页恢复原内容 |
| 三页恢复在中间页失败 | 其余两页仍恢复；保留一页及 owner 引用，重试后全部释放 |
| 已有可写 fd 或 shared writable VMA | BEGIN 返回 ETXTBSY，文件未替换 |
| 已有只读映射和私有 COW | 恢复后只读映射读回原内容，COW 保留修改 |
| 三进程持续 fault 与恢复并发 | 均正常退出，完成恢复后读到完整原文件页 |
| 提交和释放响应丢失 | 实际 manager 分别通过 QUERY 恢复结果，正常启动和退出 |
| Manager 在启动过程五个阶段被终止或恢复失败 | 新 manager 根据保存的事务 ID 和 carrier inode 完成恢复 |
| 文件已有 immutable 标志 | 正常注册与释放后保留该标志 |
| 稀疏文件索引 1、64、4096、262144 | 不同 xarray 层次的四个槽位均完成替换和原内容恢复 |
| 同源码不同构建、错误模块或错误内核身份 | Manager 在 BEGIN 后、STAGE 前拒绝，释放引用并清理状态 |
| Root 与普通用户经 sudo 启动 | 均收到注册与释放通知；普通应用保持 UID 65534，manager 为 UID 0 |
| 活跃会话的竞争启动及遗留恢复状态 | 新 wrapper 被拒绝，原状态保留；原会话继续运行或由显式恢复完成释放 |
| 普通用户操作 carrier 及既有 hardlink | 七种操作的普通文件对照成功，两个注册名称上的 14 次操作均为 EPERM |
| 共享写升级、私有写/fork 及 cache hints | 共享写升级为 EACCES；私有修改相互隔离，cache hints 后源内容及 PFN 保持 |

构建身份对照使用同一目录内、相同源码以不同编译选项生成的两个真实 owner ELF；两者 srcversion 相同，GNU build ID 和初始化代码不同。实际 manager 拒绝另一构建的 ID，错误模块名与错误内核 ID 同样被拒绝。这三项检查均在持有 owner 引用后、发送任何页面计划之前完成，随后正常释放。

会话通知测试运行实际 wrapper 的启动和清理函数，并分别使用 root 与普通 UID 65534 经 sudo 启动 manager。竞争 wrapper 不修改原会话状态；wrapper 在 START 后退出时，manager 无法发送 READY，随后释放绑定，应用没有启动。普通用户拥有 ext4 carrier 及可写父目录，预先建立 hardlink；测试写打开、truncate、rename、unlink、创建 hardlink、chmod 和 utime。相同用户在普通文件上完成对应操作后，再检查活动 carrier 的限制。MAP_PRIVATE 写入及 fork 后的修改保持隔离，msync、madvise 和 posix_fadvise 后共享内容与源 PFN 相同。详见[通知及文件操作记录](../../test/evaluation/registration-notification-evidence.md)。

五个进程终止点分别位于持久化恢复记录、设置 immutable、BEGIN、STAGE 和 COMMIT 之后，均在发布 ready 之前。对被拒绝的 BEGIN，我们另外丢弃其响应；QUERY 返回原 ETXTBSY，manager 随后清除本次状态和文件标志。

活跃事务为 source owner 增加一个引用，恢复仍有残留时卸载请求被拒绝。使用不相交源 PFN 的两个 carrier 可以同时注册；重复源 PFN 的第二次提交返回 EBUSY，并保留第一项事务。所有绑定撤销且 Netlink socket 关闭后，owner 和注册模块的引用均归零并成功卸载。并发 reader 检查过渡期间每个字节来自源页或原文件，并在恢复完成后要求原文件内容，不将一次跨页面读取视为原子快照。

独立的完整 LZ4 CLI 会话使用相同注册实现，通过全部 24 组 Silesia 文件/块配置的压缩、解压及 stock 交叉校验。48 份操作记录确认调用选中的 carrier 和实际 helper；四张 text 页及一张 RO 页与内核 PFN 匹配，释放后的新映射不再使用这些源 PFN。相同注册构建下，BCH 和 XZ 的 cooperative owner 也分别通过完整功能矩阵，活跃引用均为 1，各自四页与 kernel PFN 匹配并正常释放。BCH 覆盖 10,752 个 decode checks；XZ 的 42 行记录覆盖 882 次完整解码和 84 次完整输出比较。三个算法会话均没有 kernel panic、BUG 或 WARNING。完整记录见[当前注册与算法会话](../../test/evaluation/registration-notification-evidence.md)。

页面规模检查使用同一完整注册机制，选择 1、2、4、8、16、32 张独立 resident pages，并比较目标文件页已驻留与逐文件驱逐后的状态。计时前通过 mincore 核对所有选定页的缓存驻留情况。每种规模、缓存条件和控制路径各执行四次，完整 manager 与直接 v4 传输共 96 次注册；后者用于观察内核机制，不包含 manager 的身份核对、文件标志和持久化。1,008 个活动映射均匹配源 PFN，释放后的 1,008 个映射均恢复原字节并使用不同 PFN。该合成 fixture 不执行算法，其原始计时及验证记录见[规模实验](../../test/evaluation/registration-scale-evidence.md)。

源页类型检查使用实际 LZ4 owner 的 text、rodata 和管理页，每页分别声明为三种类型。在正常内核保护下，text 与 rodata 的匹配声明可注册，用户映射与源 PFN 一致。以相同内核及模块二进制关闭只读保护后，独立页表观测确认这两类源页可写；其匹配声明也在 COMMIT 应用任何页面前返回 EACCES。两次启动的 18 个直接协议组合中，两个匹配只读页被接受，其余 16 个被拒绝；实际 manager 对这 16 个组合同样返回失败并清理状态。该对照验证注册时对实际权限的要求，运行期间的代码改写不在这一检查范围内。见[源页准入实验](../../test/evaluation/registration-typed-evidence.md)。

# Appendix B: Setup Stage Measurements

**Table B1: Instrumented one-pass setup stages, in milliseconds.** Cells are medians of deployment medians. First-valid-result time includes nested stages; wrapper measurements are separate intervals, not an additive breakdown of the full command.

| Stage | Active native | Active VKSO | Ready native | Ready VKSO |
| --- | ---: | ---: | ---: | ---: |
| Start to first valid result | 814.058 | 812.363 | 812.573 | 1392.592 |
| DSO load and symbol resolution | 0.063 | 0.108 | 0.063 | 0.108 |
| Input read | 87.994 | 88.498 | 87.950 | 88.038 |
| One complete corpus task | 725.375 | 722.986 | 723.686 | 722.640 |
| DSO unload | 0.021 | 0.032 | 0.020 | 0.031 |
| Registration wrapper | n/a | n/a | n/a | 188.327 |
| Release wrapper | n/a | n/a | n/a | 22.586 |

Trace-on/trace-off 的部署汇总比值在所测模式、backend 和任务遍数组合中为 0.9999–1.0027。独立时钟 helper 每部署测量三十次，部署中位数的中位数为 0.390 ms，范围为 0.389–0.390 ms。原始阶段记录保留部署间范围；主结果使用 trace-off 命令时间，不减去这些诊断值。
