# VKSO: Zero-copy Rehosting of Resident Kernel Code as User-space Shared Objects

## Abstract

操作系统内核和用户态经常重复实现 checksum、compression、format parsing 以及只读状态转换等计算。让应用通过 syscall 请求内核执行可以避免代码复制，却为高频短函数保留 privilege-crossing cost；重新维护一份用户态实现则会带来代码重复和 semantic drift。我们提出 VKSO，一种将**当前运行内核中已经驻留的机器码页**零拷贝重宿主为标准 user-space shared object 的机制。VKSO 从最终机器码出发，以 state、control 和 code-shape constraints 界定可复用的 binary closure；standard carrier 保留 ELF/loader 语义，page grafting 复用 resident physical pages，Shim 则显式承接 kernel/user execution environments 之间的依赖。Linux 5.15 原型的 microbenchmarks 表明，page grafting 对装载后的 hot path 没有可测开销，代表性 same-source kernel algorithms 在重宿主后保持相近性能。作为端到端案例，我们重构 Linux clocktime 子系统，使 kernel timekeeping entry 与用户态 fast path 共享同一 resident implementation，并以 VKSO 替换原生 x86-64 vDSO time/getcpu implementation；该改造将完整 product source 减少 13.29%，reader machine-code closure 减少 22.13%，公开 READ 入口总体保持在约 ±1% 范围内，同时降低 UPDATE 的平均与长尾成本。这些结果说明，经过显式状态和环境解耦的内核计算可以由 kernel and user space 共享同一执行体，而不牺牲稳态性能。

# Introduction

内核与用户程序并不总是需要不同的计算语义。Checksum、compression、format parsing 和只读状态转换等功能经常同时出现在 kernel and user space；然而 privilege boundary 使用户程序无法直接使用运行内核中的实现。系统因此通常在“通过 syscall 请求内核执行”和“维护第二份用户态实现”之间选择。前者为每次调用保留边界成本，后者则要求安全修复、优化和边界语义在两个实现中同步演化。

一个看似直接的办法是把内核 `.text` 映射到用户空间，但物理可达性并不等于可执行的程序接口。目标函数还隐含依赖对象布局、relocations、helper targets、动态状态、同步协议和经过启动期改写的最终控制流。若这些依赖没有形成闭包，简单映射只会把错误推迟为用户态非法地址、错误跳转或状态不一致。本文因此围绕三个问题展开：**什么样的 kernel-resident binary closure 可以安全复用，如何在不复制执行体的前提下将其重宿主到用户空间，以及这种复用能否减少重复而不牺牲性能？**

VKSO 的关键洞察是把三个通常耦合的问题分开处理。最终机器码上的 state、control 和 code-shape dependencies 共同决定复用边界；standard shared object 只承载应用可见的对象语义，实际执行体由 resident kernel pages 提供；Shim 则将共享计算与原生执行环境分离，使可等价重建的依赖在各自 domain 内完成绑定。分析、转换和绑定发生在构建或装载边界，首次访问仍走原生 file-backed fault path；稳态调用因此是 ordinary shared-library call，而不是新的跨域 RPC。

本文作出三项贡献：

- 提出一组面向最终机器码的 state、control 和 code-shape constraints，将“可否复用”归结为可审核的 binary-closure eligibility problem；无法满足约束的目标不会进入重宿主流程。
- 设计并实现函数级 resident binary rehosting mechanism：构造可跨地址空间执行的代码闭包，以标准 Stub DSO 保留对象语义，通过 page grafting 复用同一物理执行体，并以 Shim 分离 kernel/user execution environments。
- 用机制级 microbenchmarks、代表性 kernel algorithms 和完整 Linux clocktime case study 验证这一路径：first-touch 实验证明稳态调用不承担页面复用成本，copied closures 和同源算法给出适配开销的边界，clocktime 则检验共享状态与并发 publisher/readers 下的端到端行为。

在 Linux 5.15 原型上，hot call 保持在测量误差内，同源算法大多落在约 ±5% 内；clocktime 改造将完整 product source 和 reader closure 分别减少 13.29% 与 22.13%，而独立 READ 总体保持在约 ±1% 范围内。我们同时报告 first-touch、短入口和并发 coarse path 的边界情况，以明确这些数字适用的 workload 与 build 条件。

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

Builder 为每组开发者选择的 final-binary entries 生成两个耦合产物：描述 source pages、依赖和权限的 closure manifest，以及提供 ELF object semantics 的 Stub DSO。它先在已链接 kernel/LKM ELF 上闭合 code、data and control dependencies，再根据跨布局地址约束构造 carrier；该过程只接受满足 reuse contract 的结果，不尝试从任意 kernel function 自动推断高层语义。

### Fail-Closed Final-Binary Closure Analysis

构建器不从源码中推断可复用性，而是以已链接 ELF 的 symbol、section、relocation 和 disassembly 为输入。它从每个导出入口出发，递归收集 direct calls、tail jumps、可解析的 indirect targets、PC-relative data references 和 relocation targets，并为每项依赖标记为 shared page、domain-local relocation、approved Shim 或 synthetic target。任何未解析符号、指向 privileged state 的重定位、超出可表示范围的分支，以及无法证明目标集合的间接跳转都会使构建失败。

分析结果以 manifest 形式记录每个 reusable region 的原始地址、长度、权限、Stub DSO file offset 和 backing 类型。后续构建和装载两端都检查这份 manifest，因此“分析的对象”与“实际映射的页”不能静默偏离。这一 fail-closed 边界将原本会表现为用户态非法跳转或缺页的问题，提前为可定位的构建或装载错误。

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

Kernel manager 消费 builder 生成的 manifest，并把其中的 logical carrier pages 与当前运行 kernel/LKM instance 对应起来。它先确认 runtime text 仍满足经过分析的 control-flow closure，再验证 source page、权限与生命周期并注册 resident backing。Stub DSO 的 ELF identity 和 loader-visible layout 在这一过程中保持不变。

### Final Runtime Machine-code Validation

Link-time closure 并不自动等于正在运行的 closure。Linux/x86-64 的 compiler instrumentation、static alternatives 和 boot-time rewriting 可能在链接后改变控制目标，因此 manager 在 grafting 前将 manifest 与 final runtime text 再次核对。对不影响 target semantics 的 instrumentation，原型使用局部构建选项关闭；对最终目标稳定且可审核的改写，将实际 target page 显式纳入 closure；对只实现闭包内控制转移的 thunk，则构造语义等价且目标明确的 synthetic direct-jump thunk。任一策略都无法闭合实际控制流时，manager 拒绝建立映射。

Indirect Target Selection（ITS）说明了这项检查的必要性：编译时可见的 retpoline thunk 可能在启动期被改写为 dynamic ITS thunk。若 manifest 只包含原 thunk page，用户路径会到达未导出的目标。原型因此只接受两种显式结果：使用 synthetic direct jump，或将经过验证的 native RX target page 标记为 `reusable_text`。装载端同时校验页类型和最终权限，不允许 runtime rewriting 隐式扩大 executable closure。

**Figure 2: Fault-driven page grafting.** The grafting manager changes the backing of a selected file offset, not the process-visible ELF object. The first ordinary file-backed fault installs a user PTE to the resident page already referenced by the kernel mapping; subsequent calls use the existing PTE.

### Registering Resident Backing

`ld.so` 装载 Stub DSO 后，reusable `PT_LOAD` ranges 形成普通 file-backed VMAs。每个 logical page 可由 Stub DSO file offset 转换为 `pgoff_t`，并经 inode 定位到相应 `address_space` entry。Manager 逐项校验 manifest 中的 source address、page alignment、backing class and user permission，再把该 file offset 注册为指向对应 kernel/LKM resident `struct page`。应用可见的 VMA、symbol address and shared-object identity 均不改变。

Registration 同时建立 backing lifetime。对于 LKM pages，manager 持有 module and page references；解除映射、进程退出或注册失败时撤销已建立的关系并释放引用。因而 file-offset binding 不会在 source module/page 已失效后继续存在，部分失败也不会留下可访问的半成品 carrier。

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

VKSO 的目标是让两个 execution domains 复用同一 resident implementation，同时保留普通用户态调用的性能。Evaluation 因此需要同时检验复用机制的成本、依赖适配的成本，以及消除双重实现后的系统收益。我们围绕四个问题组织实验：

- **页面重宿主是否改变调用与缺页成本？** 用字节一致的 Native/Stub DSO，分别测量 hot call、resident minor fault 和 cache eviction 后的 first touch。
- **显式依赖绑定的稳态代价有多大？** 从 Data/Func-PGOT primitives 到完整 copied closures，测量间接访问、依赖链及 retpoline 对适配成本的影响。
- **真实 kernel closures 能否保持同源实现的功能与性能？** 通过 LZ4、BCH 和 XZ 的实际 resident-page export，对照普通同源用户态 DSO，覆盖不同工作粒度、控制流和 helper dependencies。
- **共享动态状态的完整子系统是否值得重构？** 以 clocktime 为案例，同时测量源码与机器码规模、公开 READ 入口、内核 UPDATE 和持续读写并存时双方的成本。

## Experimental Setup and Measurement

实验运行在 Intel Core i7-1165G7（4 physical cores，SMT disabled）上，测量线程固定 CPU 2，使用 GCC 11.4.0。First-touch、PGOT、LZ4、BCH 和 XZ 使用 Linux 5.15.0-119-generic；clocktime 使用 Linux 5.15.198 及相同硬件，并通过 isolcpus、nohz_full 和 rcu_nocbs 隔离 CPU 2。固定执行位置用于降低迁移和 cache locality 变化对短路径的干扰。PGOT 另外比较 retpoline/no-retpoline builds，clocktime 比较 Normal/no-retpoline builds，以观察受保护间接分支相关的构建差异。

PGOT 使用轮内 paired delta；LZ4、BCH 和 XZ 先在相同 outer round 内形成 kernel-backed/native ratio，再汇总跨轮次分布。各算法的这些轮次均在一次 owner module 装载和页面注册内完成。LZ4 为每个 round/block/backend 启动一个 benchmark 进程；BCH 和 XZ 则在单个进程中加载各 backend，再循环执行所有轮次。因此，这些分布描述一次部署内的变化。Clocktime 的 Raw/VKSO 分别启动对应内核镜像，比较各自多轮测量的汇总值，不视作同轮配对实验。其每个 backend/build 的正式批次来自一次启动，31/15 轮重复描述的是该次启动内的变化。表 2 列出各组的重复层次与主指标。

计时前的功能校验用于确认两侧完成相同工作：PGOT copied closures 比较返回值、输出长度和字节；LZ4 交叉验证 compressor/decompressor；BCH 检查错误位置及 codeword recovery；XZ 检查完整输出；clocktime 对各镜像执行相同 ABI matrix。各节说明计时窗口，区分部署准备、目标调用和诊断插桩。表中的 IQR width 为 P75−P25，P25–P75 则列出区间端点；P10–P90 描述跨轮次比值的变化，这些统计量均不作为置信区间。延迟比值大于 1 表示 VKSO 更慢，吞吐比值大于 1 表示更快；百分比变化为相应比值减 1 后乘以 100%。

**Table 2: Evaluation workloads, comparisons, and measurement units.** Algorithm outer rounds repeat measurements within one deployment. LZ4 starts a process per round/block/backend; BCH and XZ retain one process across rounds. Inner calls amortize timing overhead and are not independent trials.


| Experiment       | Primary comparison                                 | Repetitions and statistic                     | Primary metric               |
| ---------------- | -------------------------------------------------- | --------------------------------------------- | ---------------------------- |
| First touch      | Native DSO vs. kernel-backed Stub DSO              | 5 accepted batches × 100 calls; median        | TSC cycles and fault type    |
| Data-PGOT | Independent loads vs. dependent chains; direct/PGOT | 3,100 raw paired samples per configuration | paired cycles/access, IQR |
| Func-PGOT | Stable target; direct/PGOT, two builds | 310 raw paired samples per build | paired cycles/call, IQR |
| Work placement | Before/inside/after target, varied useful work | 3 outer runs × 15 repeats | paired cycles/iteration, IQR |
| Copied closures  | Origin vs. PGOT closure                            | 3 outer runs × 31 repeats                     | paired cycle delta           |
| LZ4              | Kernel-backed vs. same-source/upstream DSO         | 1 deployment, 7 rounds; paired median, P10–P90 | MB/s ratio                   |
| BCH              | Kernel-backed vs. same-source/author DSO           | 1 deployment, 11 rounds; paired median, P10–P90 | latency ratio                |
| XZ Embedded      | Kernel-backed vs. same-source DSO                  | 1 deployment; 3 inputs × 7 rounds × 20 decodes | MiB/s ratio                  |
| Clocktime        | Shared-code design vs. native split implementation | 31 reader rounds; 15 writer/concurrent rounds | cycles/call or cycles/update |


这组实验由机制分解走向完整功能：字节一致的 DSO 控制计算逻辑差异，copied closures 在同一执行域内隔离 PGOT transformation，实际 kernel-backed algorithms 再引入构建域、Shim 和 page rehosting，clocktime 最后检验共享状态及入口适配的组合效果。后一层的端到端结果与前一层的机制解释互补。

## First-touch and Rehosting Cost

Page grafting 改变对象的物理后备，而应用仍通过标准 DSO 调用。因此，我们使用字节一致的 XXH32 function body 构造普通 user-space DSO 和 kernel-backed Stub DSO，使两侧的计算工作和调用形式一致。计时从 dlopen 和 symbol resolution 完成后开始，只包围一次目标调用；它测量执行页的首次触达，不包含 DSO 构造、页面替换或动态链接总时间。

三种状态分别隔离不同成本。Hot 保留已有 PTE，用于检查稳态调用是否引入额外路径；PTE cold 通过 MADV_DONTNEED 移除 PTE、保留 resident backing，用于比较按需安装页表的成本；Post drop-caches 进一步清理普通 file cache，用于检验内核页面既有 residency 在文件缓存被逐出后是否仍可利用。每个样本记录 minor/major-fault counters，先按预期 fault class 筛选，再执行基准的 IQR filtering，避免将实际不同的缺页状态混入同一组。

**Table 3: First-touch latency and observed fault class.** Latency is measured around one target call after loading and symbol resolution. P25–P75 gives the interquartile interval. Fault counts are per measured call.

| 状态 | Backend | Median cycles | P25–P75 cycles | Minor / major faults |
| --- | --- | --- | --- | --- |
| hot | Native | 71 | 69–71 | 0 / 0 |
| hot | Stub | 71 | 69–71 | 0 / 0 |
| pte-cold | Native | 2662 | 2658–2667 | 1 / 0 |
| pte-cold | Stub | 2637 | 2633–2642 | 1 / 0 |
| post-drop | Native | 701069 | 669200–708383 | 0 / 1 |
| post-drop | Stub | 13094 | 12319–13882 | 1 / 0 |

表 3 中，两种 DSO 的 hot call 均为 71 cycles；PTE cold 时均触发一个 minor fault，延迟差不足 1%。这与 grafting 不增加稳态执行步骤、首次访问继续使用原生 fault path 的设计一致。Post drop-caches 改变的是后备驻留状态：Native 需要 disk-backed major fault，Stub 则仍通过 minor fault 安装 resident kernel page。此时延迟分别为 701,069 和 13,094 cycles，受控 first-touch 延迟比为 53.5×。该收益来自既有 residency，hot call 无需这一步工作。

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

**Takeaway.** Page grafting 对 hot call 和 resident minor fault 不增加可测成本；其启动收益来自 kernel code 的既有 residency，而不是一条特殊的用户态 fast path。

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

## Same-source Kernel Algorithms

本组实验将控制范围从同域 PGOT transformation 扩展到实际 resident-page export。LZ4 覆盖不同 block sizes 下的压缩与解压；BCH 通过纠错强度、错误数及 decode 阶段改变计算工作量；XZ 则覆盖带状态的完整流解析、解码、过滤和校验。三者共同检验不同 closure shapes 下的同源性能，计时对象均为内存中的算法组件。专用 owner modules 承载可导出实现，系统原有算法仍保留，因此本组衡量导出后的执行成本。

主对照采用同一 Linux source 及对应适配代码构建的普通 user-space DSO，使算法版本保持一致；独立 upstream/author implementations 提供用户态性能参照。每次完整 runner 执行加载一次 owner module、解析 runtime addresses、检查闭包、构造 sparse DSO 并注册页面，随后在该部署中完成所有 outer rounds，退出时恢复映射并卸载 owner。输出校验、运行时符号地址和 page-map 记录分别检查功能与部署目标。部署与恢复在计时窗口之外，以下结果衡量一次部署内装载后的算法性能。

### LZ4

LZ4 使用未修改的 upstream 1.9.3 official benchmark core 和 Silesia corpus，测试 4 KiB、64 KiB 和 1 MiB blocks。改变 block size 可以观察固定调用/适配工作在短块与较长计算中的相对影响；同时测量 compression 和 decompression，覆盖两种不同的计算与数据搬运路径。五个 backends 区分 upstream/kernel source 与 native/no-SIMD compilation。主比较是 kernel-backed 与 same-source no-SIMD：两者执行相同 Linux 5.15 algorithm，并使用相同的 test-local REP memory helpers。Native/no-SIMD 同时改变编译限制和 memory helpers，因而这一辅助对照衡量的是构建制度的组合影响。

七个 outer runs 共得到 105 个完整 benchmark cases。官方 harness 在每个 time window 内选择最快完整循环，再对 outer-run 配对吞吐比值取 median 和 P10–P90；该统计量衡量吞吐能力，而非请求尾延迟。五种 compressor × 五种 decompressor × 12 个边界长度以及所有 XXH64 checks 均通过。

**Table 9: LZ4 throughput relative to user-space baselines.** Each cell is median [P10, P90] of seven matched-run throughput ratios. The numerator is kernel-backed throughput. Values above 1 favor VKSO. The geometric mean weights the six operation/block combinations equally.

| Operation | Block size | Same-source no-SIMD | Same-source native | Upstream native |
| --- | --- | --- | --- | --- |
| compress | 4 KiB | 1.0234 [1.0224, 1.0245] | 1.0472 [1.0459, 1.0488] | 1.0357 [1.0351, 1.0369] |
| compress | 64 KiB | 1.0196 [1.0184, 1.0207] | 1.0372 [1.0364, 1.0391] | 1.0087 [1.0082, 1.0104] |
| compress | 1 MiB | 1.0040 [1.0027, 1.0055] | 1.0475 [1.0467, 1.0488] | 1.0075 [1.0059, 1.0144] |
| decompress | 4 KiB | 0.9870 [0.9809, 0.9898] | 1.0379 [1.0373, 1.0400] | 0.9610 [0.9579, 0.9636] |
| decompress | 64 KiB | 0.9817 [0.9787, 0.9837] | 1.0173 [1.0135, 1.0185] | 0.9723 [0.9701, 0.9733] |
| decompress | 1 MiB | 0.9848 [0.9837, 0.9882] | 1.0320 [1.0281, 1.0333] | 0.9228 [0.9207, 0.9257] |
| 等权几何平均 | 六种组合 | 0.9999 | 1.0365 | 0.9840 |

表 9 中，与 kernel-backed 构建约束及 memory helpers 更接近的 same-source no-SIMD 对照得到 0.9999× 的等权几何平均，六个组合落在 0.9817×–1.0234×。Same-source native 对照得到 1.0365×，说明 native compilation 与 glibc helpers 在这些路径上并不必然更快。相对 upstream native，compression 三项略快、decompression 三项较慢，几何平均为 0.9840×。因此，rehosting 后的同源性能接近，而跨构建或跨实现差异需要结合 control flow、copy strategy 和 compiler decisions 解释。

### BCH

BCH 测试 Linux 5.15 scalar implementation，沿用作者 benchmark 的 m=13、t∈{4,8} 和 512-byte data 定义。两种 t 分别提供不同纠错能力，注入 0 到 t 个错误则改变实际 decode 工作量。我们分别计时 encode、包含 syndrome 计算的 full decode，以及输入预计算 ECC difference 的 decode；这种分解能够观察去掉前段工作后，较短剩余路径是否更容易暴露适配成本。

Kernel-backed 与 same-source native 使用相同 adapted source；author standalone 用于展示跨实现差异。计时使用 CLOCK_PROCESS_CPUTIME_ID，每个样本自适应运行至少约 10 ms，以摊薄定时器读取成本；11 个 outer runs 形成配对 latency ratios。每组参数对 128 个随机 vectors、0 到 t 个注入错误以及 full/precomputed decode paths 验证错误位置和完整 codeword recovery，所有检查及 DSO relocation/page-map audit 均通过。

初始化成本单独计量，表中的 init 包含 BCH 控制结构及查找表的创建与随后释放，不包含 owner module 或 DSO 的部署时间。该行与 encode/decode 分列，以区分算法对象的建立/回收和后续调用成本。

**Table 10: BCH initialization, encoding, and decoding with t=4.** All cases use m=13 and 512-byte data. Absolute times are backend medians. Ratios and P10–P90 are computed from 11 matched outer runs. Ratios above 1 mean VKSO is slower. The native baseline uses the same adapted Linux source; author denotes the standalone implementation.

| Operation | Errors | Native ns/op | VKSO ns/op | VKSO/native median | P10–P90 | VKSO/author median |
| --- | --- | --- | --- | --- | --- | --- |
| init | — | 81969.39 | 81216.15 | 0.995 | 0.977–1.006 | 0.795 |
| encode | 0 | 1090.42 | 1073.41 | 0.984 | 0.984–0.986 | 0.944 |
| decode-full | 0 | 1099.77 | 1090.87 | 0.992 | 0.991–0.992 | 0.978 |
| decode-full | 1 | 1295.70 | 1265.44 | 0.979 | 0.971–0.990 | 0.950 |
| decode-full | 2 | 1363.39 | 1329.69 | 0.972 | 0.966–0.988 | 0.962 |
| decode-full | 3 | 1827.05 | 1813.06 | 0.992 | 0.980–0.997 | 0.987 |
| decode-full | 4 | 1870.59 | 1845.20 | 0.988 | 0.983–0.995 | 0.998 |
| decode-precomputed | 0 | 33.50 | 30.96 | 0.924 | 0.894–0.944 | 0.951 |
| decode-precomputed | 1 | 224.42 | 216.64 | 0.970 | 0.950–0.996 | 0.970 |
| decode-precomputed | 2 | 263.37 | 255.29 | 0.968 | 0.949–0.992 | 0.972 |
| decode-precomputed | 3 | 737.96 | 731.09 | 0.993 | 0.978–1.008 | 1.048 |
| decode-precomputed | 4 | 776.92 | 788.99 | 1.012 | 1.003–1.020 | 1.072 |

**Table 11: BCH initialization, encoding, and decoding with t=8.** Units, baselines, and statistics are identical to Table 10. Full and precomputed paths are reported separately for every injected error count.

| Operation | Errors | Native ns/op | VKSO ns/op | VKSO/native median | P10–P90 | VKSO/author median |
| --- | --- | --- | --- | --- | --- | --- |
| init | — | 116836.84 | 116680.47 | 0.998 | 0.986–1.003 | 0.899 |
| encode | 0 | 1097.07 | 1097.90 | 1.001 | 1.000–1.001 | 0.836 |
| decode-full | 0 | 1112.14 | 1115.94 | 1.003 | 1.001–1.004 | 0.837 |
| decode-full | 1 | 1684.50 | 1771.36 | 1.034 | 1.020–1.057 | 0.909 |
| decode-full | 2 | 1737.17 | 1798.25 | 1.039 | 1.028–1.060 | 0.904 |
| decode-full | 3 | 2259.34 | 2292.19 | 1.025 | 1.013–1.039 | 0.928 |
| decode-full | 4 | 2296.01 | 2352.90 | 1.024 | 1.005–1.037 | 0.927 |
| decode-full | 5 | 2998.13 | 3147.18 | 1.044 | 1.035–1.057 | 0.969 |
| decode-full | 6 | 3638.49 | 3797.26 | 1.050 | 1.040–1.062 | 0.984 |
| decode-full | 7 | 3966.25 | 4197.64 | 1.050 | 1.041–1.061 | 0.997 |
| decode-full | 8 | 4777.83 | 5006.50 | 1.054 | 1.044–1.066 | 1.014 |
| decode-precomputed | 0 | 46.16 | 45.50 | 0.988 | 0.972–1.006 | 0.933 |
| decode-precomputed | 1 | 551.54 | 584.83 | 1.098 | 1.022–1.143 | 1.054 |
| decode-precomputed | 2 | 624.02 | 799.89 | 1.209 | 1.127–1.318 | 1.168 |
| decode-precomputed | 3 | 1121.86 | 1181.21 | 1.055 | 1.034–1.080 | 1.046 |
| decode-precomputed | 4 | 1169.80 | 1228.10 | 1.055 | 1.028–1.079 | 1.065 |
| decode-precomputed | 5 | 1851.09 | 2004.70 | 1.074 | 1.068–1.087 | 1.084 |
| decode-precomputed | 6 | 2513.67 | 2667.90 | 1.078 | 1.049–1.088 | 1.087 |
| decode-precomputed | 7 | 2781.25 | 2953.63 | 1.065 | 1.061–1.078 | 1.095 |
| decode-precomputed | 8 | 3620.21 | 3882.10 | 1.078 | 1.071–1.086 | 1.095 |

表 10–11 将 initialization、encode 和两种 decode 路径分开呈现。Encode 接近同源 native；full decode 在 t=4 时略快，在 t=8 时慢约 0.3%–5.4%。较短的 precomputed path 对 t 更敏感：t=4 大多更快或接近，而 t=8 的 1–8 error cases 均变慢，配对增量约为 5.5%–20.9%，其中 2-error case 最大。该例在 11 轮中均较慢，各轮比值为 1.078–1.519。该变化并非所有 BCH 路径共有，但也不止一个孤立慢点。分阶段结果将需要进一步分析的成本定位到较强纠错配置的 precomputed decode，而不是整个初始化或编码流程。

### XZ Embedded

XZ 使用完整 Linux 5.15 XZ Embedded single-call decoder，闭包覆盖 LZMA2、x86 BCJ 和 CRC32。相比单个 transform，它将 format parsing、range decoding、dictionary、filter 和 integrity check 放在同一调用中。输入选择 bash、libc.so.6 和 python3 三个真实二进制文件，统一预先压缩为启用 x86 BCJ、CRC32 和 1 MiB LZMA2 dictionary 的流，使两侧面对完全相同的字节与解码配置。

Same-source native DSO 与 kernel-backed DSO 各先完成一次不计时解压，再执行 20 次 timed decodes。压缩、decoder allocation 和 CRC-table initialization 均在计时之外；每次 timed iteration 包含 xz_dec_reset 和一次完整 xz_dec_run。七个 outer rounds 轮换 backend 顺序，共形成 21 组 matched pairs。每组均验证 consumed/produced lengths、全部 output bytes 以及两侧 guard regions；DSO audit 确认四个 reusable pages、五个 exports 和 `__kmalloc`、`kfree`、`memcpy`、`memmove` 四类 private helper relocations。后者描述完整导出依赖，性能窗口则聚焦已经初始化的 decoder。

**Table 12: XZ Embedded decoding throughput.** Absolute throughput is in MiB/s. Each ratio is the median of seven matched-run ratios. P10–P90 describes their across-run variation. Higher ratios favor VKSO.

| Case | Native median MiB/s | Kernel-vkso median MiB/s | Paired kernel/native median | P10–P90 |
|---|---:|---:|---:|---:|
| bash | 30.40 | 29.94 | 0.985× | 0.984–0.986× |
| libc.so.6 | 33.23 | 32.74 | 0.985× | 0.984–0.988× |
| python3 | 33.25 | 32.64 | 0.982× | 0.980–0.983× |
| 等权几何平均 | — | — | 0.9839× | — |

表 12 的三个输入得到一致的性能趋势：kernel-backed 吞吐量约为 native 的 98%–99%，等权几何平均为 0.9839×，即低 1.61%。各输入的 P10–P90 范围较窄，差异在重复运行中持续存在。这组结果覆盖完整 decoder 的稳态执行，反映 kernel/user build-domain、code layout 和 private helper binding 的组合效果；结合 first-touch 实验，可将它与不进入 steady-state call path 的 page grafting 区分。

## Stateful System Case: Consolidating Kernel and vDSO Time Reads



### Evaluation Goals and Baselines

Clocktime 将 `shared_data`、`MM_data`、private wrapper 与 environment-local fallback 组合到同一子系统中。选择它有两个原因：原生 vDSO 已经提供不经过 syscall 的用户态 fast path，能够作为严格的稳态性能基线；其状态又由内核持续更新，并受 time namespace 和 clock provider 影响，因而能够检验纯算法实验没有覆盖的状态发布、入口语义和并发交互。我们比较 Linux 原生分离的 kernel/vDSO implementation（Raw）与共享 resident calculation core 的实现（VKSO）。

该实例将七类 global clock 的 conversion and normalization 放入 shared core，由全局共享页提供时间输入，由 MM_data 提供 namespace offsets。普通 kernel reader、syscall entry 和 user wrapper 通过入口适配选择各自的状态及 fallback，global writer 发布共同 snapshot。Evaluation 关注这种组合实现的净效果：首先核对等价功能下是否减少代码重复，再分别测量用户 reader、内核 writer，以及二者持续共存时的性能，检查复用是否将成本转移到另一端。

最终实现覆盖 clock_gettime、clock_getres、gettimeofday、time 和 getcpu，支持 realtime、monotonic、monotonic-raw、boottime、TAI 及 coarse clocks，并在 CPU/alarm/dynamic/invalid cases 保持原 Linux errors and fallback semantics。Raw/VKSO 分别构建 Normal 和 no-retpoline 镜像，在相同 mitigation 条件内比较；no-retpoline 用于诊断 build-dependent cost。四种镜像均通过相同 ABI matrix，包括 time namespace、provider cold paths 和 fallback tests；性能测量使用 TSC clocksource。功能矩阵覆盖状态和回退语义，以下计时则报告实际选择的公开入口与工作负载。

### Source and Binary Footprint

源码与机器码分别衡量需要维护的功能实现规模和实际 reader execution body 的规模。我们用人工语义 manifest 选择两侧等价功能，再机械排除空行和纯注释，以免将移动代码产生的 Git churn 当作实现增减。表 13 采用完整产品口径，包含运行时功能、运行时机制和 feature-specific build/link glue；benchmark、通用 VKSO infrastructure、验证代码和生成物在两侧排除。Shared core 只计一次，private wrappers 和 feature-specific state support 仍计入 VKSO。Reader closure 使用最终 ELF symbol sizes，排除页对齐和载体 metadata；它衡量机器码去重，不等同于全系统物理内存节省。

**Table 13: Source and machine-code footprint of the case study.** Shared core code is counted once across the two domains. Tests and project-wide mechanisms are excluded symmetrically.


| Scope                                    | Raw        | Shared-code design | Difference     |
| ---------------------------------------- | ---------- | ------------------ | -------------- |
| Runtime feature and mechanism            | 1,347 SLOC | 1,248 SLOC         | −99 (−7.35%)   |
| Product total with feature build/link    | 1,505 SLOC | 1,305 SLOC         | −200 (−13.29%) |
| Steady-state reader machine-code closure | 2,639 B    | 2,055 B            | −584 (−22.13%) |


**Table 14: Additional footprint accounting.** Rows describe distinct scopes or transformations and are not additive. Source counts are SLOC; reader-closure counts are bytes.

| Accounting scope | Reference | VKSO | Difference |
| --- | --- | --- | --- |
| User-specific source, Raw → VKSO | 359 SLOC | 68 SLOC | −291 SLOC |
| Shared calculation core, Raw → VKSO | 0 SLOC | 310 SLOC | +310 SLOC |
| Narrow intrinsic-function source scope, Raw → VKSO | 1,201 SLOC | 1,102 SLOC | −99 (−8.24%) |
| Narrow reader-closure scope, Raw → VKSO | 2,497 B | 2,401 B | −96 (−3.84%) |
| Product source before → after final fallback refactor | 1,283 SLOC | 1,305 SLOC | +22 SLOC |
| Project-wide ITS/reusable-text support, excluded from case-study totals | — | 84 SLOC | — |

表 13 的完整产品 source 减少 13.29%，reader machine-code closure 减少 22.13%。表 14 进一步区分代码转移与真正消除的重复：用户专属代码缩减后，原先两端重复的计算进入共享 core；总量下降还包括原 vDSO-specific mapping/link path 的简化。Private entry 和 fallback 仍有实现成本，因而不能把用户侧减少的行数全部算作净节省。

表 14 的较窄内在功能口径排除 timekeeper 兼容适配和部分 reader 依赖，所得百分比与完整产品口径回答不同问题。通用 ITS/reusable-text support 属于项目基础机制，单独列示。后续性能分析采用表 13 对应的完整实现，不将这些范围重叠的统计相加。

### Public READ Cost

READ 测量应用可见的完整入口，包括 wrapper、状态准备、shared core 和适用的 fallback，而不是只测共享计算体。20 个 API/参数路径覆盖不同长度的 fast paths、空参数短入口和需要 syscall 的 fallback；分别报告分组和逐项结果，观察固定入口工作在不同调用长度下的影响。基准直接在具体 API 的循环中调用 Raw vDSO 或 VKSO wrapper，每个 sample 预热 10,000 次并计时 500,000 calls，31 rounds 分布于 7 个新进程，并通过 setarch -R 固定用户地址布局。READ 镜像关闭 writer recorder，避免将 UPDATE 的测量插桩带入独立 reader 结果。

每个 API 取 31 轮 cycles/call 的中位数；总体和分组结果是逐 API VKSO/Raw ratio 的等权几何平均。这一汇总给予每个接口相同权重，用于描述接口集合的总体变化，不假设真实应用中的调用频率。

**Table 15: Independent public READ latency.** Values are median TSC cycles/call across 31 rounds. Δ = (VKSO/Raw − 1) × 100%; negative values favor VKSO. Raw and VKSO are measured in separately booted kernels within each build regime.

| API | Raw Normal | VKSO Normal | 差异 | Raw No-ret | VKSO No-ret | 差异 |
|---|---:|---:|---:|---:|---:|---:|
| `clock_getres` process CPU fallback | 585.050 | 586.107 | +0.181% | 565.679 | 558.318 | -1.301% |
| `clock_getres` realtime | 8.028 | 6.042 | -24.738% | 8.028 | 6.042 | -24.740% |
| `clock_getres` realtime coarse | 6.022 | 7.064 | +17.302% | 6.106 | 7.063 | +15.681% |
| `clock_gettime` boottime | 53.196 | 53.186 | -0.018% | 53.196 | 53.217 | +0.040% |
| `clock_gettime` monotonic | 53.194 | 53.186 | -0.014% | 53.193 | 54.190 | +1.874% |
| `clock_gettime` monotonic coarse | 10.035 | 11.085 | +10.467% | 10.035 | 10.037 | +0.014% |
| `clock_gettime` monotonic raw | 52.184 | 54.347 | +4.145% | 52.184 | 53.185 | +1.919% |
| `clock_gettime` process CPU fallback | 869.545 | 868.978 | -0.065% | 842.828 | 839.464 | -0.399% |
| `clock_gettime` realtime | 53.193 | 52.184 | -1.897% | 53.192 | 53.987 | +1.495% |
| `clock_gettime` realtime alarm fallback | 679.501 | 677.683 | -0.268% | 665.733 | 659.364 | -0.957% |
| `clock_gettime` realtime coarse | 10.037 | 11.077 | +10.357% | 10.035 | 10.036 | +0.009% |
| `clock_gettime` TAI | 53.194 | 55.192 | +3.755% | 53.196 | 54.190 | +1.868% |
| `getcpu(cpu,node)` | 12.042 | 12.042 | -0.000% | 11.038 | 12.042 | +9.090% |
| `getcpu(NULL,NULL)` | 12.042 | 12.042 | +0.000% | 12.042 | 12.042 | +0.000% |
| `gettimeofday(tv,tz)` | 57.222 | 58.203 | +1.714% | 57.221 | 58.203 | +1.715% |
| `gettimeofday(NULL,NULL)` | 6.021 | 8.028 | +33.327% | 6.021 | 8.028 | +33.324% |
| `gettimeofday(NULL,tz)` | 9.031 | 10.035 | +11.114% | 9.032 | 9.032 | -0.000% |
| `gettimeofday(tv,NULL)` | 55.204 | 57.993 | +5.052% | 55.203 | 58.159 | +5.355% |
| `time(NULL)` | 6.021 | 5.018 | -16.665% | 6.021 | 5.018 | -16.665% |
| `time(&value)` | 5.018 | 4.028 | -19.716% | 5.018 | 4.015 | -19.980% |

**Table 16: Independent READ, grouped by API.** Values are equal-weight geometric-mean latency changes; groups overlap and are not additive. Negative values favor VKSO.

| API group | Normal Δ | No-retpoline Δ |
| --- | --- | --- |
| 全部20项 | +0.941% | -0.275% |
| 17项非fallback | +1.117% | -0.167% |
| 3项fallback | -0.051% | -0.886% |
| 7项主要 `clock_gettime` | +3.726% | +1.027% |
| 4项 `gettimeofday` | +12.168% | +9.330% |
| 2项直接 `clock_getres` | -6.041% | -6.693% |
| 2项 `time` | -18.204% | -18.339% |
| 2项 `getcpu` | 0.000% | +4.446% |

表 15–16 显示，20 项入口的等权几何平均在 Normal 下慢 0.941%，在 no-retpoline 下快 0.275%，但接口间差异明显。Normal 下七个主要 clock_gettime 的分组增量为 3.726%；gettimeofday 是相对开销最大的分组，其中 NULL/NULL 短入口从约 6 cycles 增至约 8 cycles，形成约 33% 的相对变化。Fallback 分组接近 Raw，与进入 shared-state preparation 前分流 native 请求的组织方式一致。因此，整体接口集合接近 Raw，并不意味着每种应用调用组合都具有相同开销。

### Kernel UPDATE Cost

共享 reader snapshot 改变了 writer 发布状态的组织方式。为检查 reader 复用是否增加内核端工作，我们在没有持续 reader load 时记录完整 timekeeping_update，而非只测向 shared_data 写入的局部代码。每个 variant 执行 15 rounds × 15 s，保留系统正常约 250 Hz 更新；Raw/VKSO 使用相同测量插桩，逐样本扣除标定的 33-cycle TSC pair 开销。主指标先计算轮内 Mean corrected，再取 15 轮中位数，用于表示每次 update 的平均 CPU 工作量；Median、P95 和 P99 采用相同的轮内统计、轮间汇总顺序，分别描述典型成本与长尾。

**Table 17: Independent UPDATE cost.** Values are corrected cycles/update. Each statistic is computed within a round, then summarized by its median across 15 rounds. Mean measures average work. Median, P95, and P99 describe the update-latency distribution. Negative differences favor VKSO.

| 变体 | 指标 | Raw | VKSO | 绝对差 | 差异 |
|---|---|---:|---:|---:|---:|
| Normal | Mean | 101.701 | 88.301 | -13.400 | -13.176% |
| Normal | Median | 84.000 | 89.000 | +5.000 | +5.952% |
| Normal | P95 | 156.000 | 131.000 | -25.000 | -16.026% |
| Normal | P99 | 465.060 | 314.040 | -151.020 | -32.473% |
| No-retpoline | Mean | 102.468 | 98.256 | -4.212 | -4.111% |
| No-retpoline | Median | 97.000 | 101.000 | +4.000 | +4.124% |
| No-retpoline | P95 | 143.000 | 145.000 | +2.000 | +1.399% |
| No-retpoline | P99 | 514.020 | 346.550 | -167.470 | -32.580% |

表 17 中，Mean corrected 在 Normal/no-retpoline 下分别下降 13.176% 和 4.111%，P99 均下降约 32.5%；与此同时，Median 分别增加 5 和 4 cycles，no-retpoline 的 P95 也增加 2 cycles。平均值和分位数的方向不同，说明重构改变了 update 成本的分布。对固定周期发布而言，平均工作量和极端长尾降低，但典型单次 update 没有变快。

### Concurrent Readers and Publisher

单独测量两端无法观察持续读取共享 cache lines 时的 publisher/readers 交互。CONCURRENT 因此让一个 reader 持续调用同一公开 API，同时记录正常约 250 Hz writer 的完整 update function，每个场景执行 15 rounds × 15 s。选择 monotonic、monotonic-raw 和 monotonic-coarse，分别覆盖高精度、raw 和短 coarse 路径；另以 sequence diagnostic 观察 snapshot retry。

公开 reader 沿用独立 READ 的具体 API 调用体，每批计时 500,000 calls；duration-control syscall 放在计时窗口之外，其后执行 10,000 次同路径条件化调用再开始计时。这样可比较相同调用范围，并将负载持续时间控制与 API 本身分开。独立 READ 也会遇到正常周期更新；本实验增加的是持续 reader load 和同步 writer 记录，并没有提高 writer 频率。因此，两组差值不直接等同于新增同步开销。

**Table 18: Public READ under sustained reader load and normal periodic updates.** Values are median TSC cycles/call across 15 rounds. Negative differences favor VKSO.

| Build | Reader | Raw cycles/call | VKSO cycles/call | Δ cycles | Δ |
| --- | --- | --- | --- | --- | --- |
| Normal | monotonic | 52.965 | 53.197 | +0.232 | +0.437% |
| Normal | monotonic_raw | 52.187 | 54.206 | +2.019 | +3.870% |
| Normal | monotonic_coarse | 10.036 | 11.410 | +1.374 | +13.693% |
| No-retpoline | monotonic | 53.197 | 54.463 | +1.266 | +2.380% |
| No-retpoline | monotonic_raw | 52.186 | 53.646 | +1.460 | +2.798% |
| No-retpoline | monotonic_coarse | 10.036 | 10.937 | +0.901 | +8.982% |

**Table 19: Full writer cost under concurrent reader load.** Mean columns are corrected cycles/update; Mean Δ is a percentage, while the remaining deltas are absolute corrected cycles. Each statistic is computed per round and then summarized across 15 rounds. The seq_protocol load is a separate diagnostic workload.

| Build | Reader load | Raw mean | VKSO mean | Mean Δ | Median Δ cycles | P95 Δ cycles | P99 Δ cycles |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Normal | monotonic | 106.013 | 102.662 | -3.160% | +8.0 | -25.0 | -138.35 |
| Normal | monotonic_raw | 114.066 | 102.002 | -10.576% | 0.0 | -29.0 | -159.19 |
| Normal | monotonic_coarse | 113.840 | 101.621 | -10.733% | 0.0 | -29.0 | -200.00 |
| Normal | seq_protocol | 114.138 | 105.849 | -7.262% | 0.0 | -29.1 | -128.16 |
| No-retpoline | monotonic | 100.307 | 98.353 | -1.948% | +20.0 | -8.0 | -81.00 |
| No-retpoline | monotonic_raw | 108.999 | 102.132 | -6.300% | +15.0 | -30.0 | -12.00 |
| No-retpoline | monotonic_coarse | 114.069 | 100.147 | -12.205% | +15.0 | -30.95 | -128.50 |
| No-retpoline | seq_protocol | 116.177 | 103.499 | -10.913% | +14.0 | -26.1 | -133.36 |

表 18 的高精度 reader 保持较小的相对差异，coarse reader 的相对增量更大，但绝对差仍为约 1 cycle。表 19 中 writer Mean 的所有点估计均降低，同时保留了 Median 持平或上升的情况。跨轮次分布显示，raw/coarse 场景两侧的 writer Mean IQR 不重叠，而 monotonic 的 IQR 重叠，后者的改善幅度处于跨轮次变化范围内。读写两端的结果说明，持续读取没有消除 writer 的平均成本收益，但短 reader 仍承担可见的固定开销。

为进一步区分快照协议与公开入口的成本，表 20 列出独立和持续负载下的 sequence diagnostic。Successful snapshot 多约 2 cycles，而 retry 次数减少，表明成功读取的局部工作与竞争重试可能朝不同方向变化。该窗口不包含完整 wrapper、clock classification 和输出处理，公开 API 的性能仍由表 15 与表 18 给出。

**Table 20: Sequence-snapshot diagnostics.** This window covers sequence checks, state/TSC reads, and retry, not a full public API. Cycles are per successful snapshot. Retry counts are per million reads. Independent and sustained-load experiments use distinct workloads.

| Protocol experiment | Build | Snapshot | Raw cycles/read | VKSO cycles/read | Raw retries/百万 | VKSO retries/百万 |
| --- | --- | --- | --- | --- | --- | --- |
| 独立 | Normal | hres | 43.151 | 45.158 | 123.41 | 23.28 |
| 独立 | Normal | raw | 43.151 | 45.157 | 95.81 | 35.33 |
| 独立 | No-retpoline | hres | 43.151 | 45.158 | 154.80 | 29.74 |
| 独立 | No-retpoline | raw | 43.151 | 45.157 | 76.68 | 28.81 |
| 持续负载 | Normal | hres | 43.151 | 45.158 | 82.94 | 34.72 |
| 持续负载 | Normal | raw | 43.151 | 45.157 | 109.94 | 18.98 |
| 持续负载 | No-retpoline | hres | 43.151 | 45.158 | 98.46 | 80.98 |
| 持续负载 | No-retpoline | raw | 43.151 | 45.157 | 106.68 | 65.26 |

**Takeaway.** 该 case study 将一个包含动态发布、地址空间隔离、fallback 和并发更新的双实现路径收敛为 single resident core。它将 product source 减少 13.29%、reader machine code 减少 22.13%，同时使独立 READ 总体保持在 ±1% 左右，并降低 writer average and tail costs。这表明本文机制的适用范围不止于纯算法闭包，但复杂 feature 仍需要按 state ownership 和 environment boundary 做显式重构。

## Reproducibility

First-touch、PGOT、LZ4、BCH 和 XZ 均提供单命令入口，正式参数和数据来源记录于对应 README 与 results directory。结果保留原始 CSV、环境与构建信息、功能校验、disassembly 和 page-map audit，分别支持数值复算与被测执行体核对。Clocktime 的 READ/UPDATE/CONCURRENT 由固定 boot/collect 流程生成，归档中记录内核变体、测量协议和逐轮样本。

表 3–8 来自 first-touch 汇总及 PGOT 各层的 paper tables；表 9–12 来自 LZ4、BCH 的配对结果及 XZ 的正式解码结果；表 13–20 来自 clocktime 的完整代码规模审计和 READ/UPDATE/CONCURRENT 统一报告。配对比值与差值直接沿用对应统计字段，不从已舍入的两侧中位数反推。复现时按各 README 的正式参数重新建立 owner module、Stub DSO 和页面映射，保留 closure checks，再生成相同口径的统计。

# Related Work

**Shared objects, loaders, and binary transformation.** 传统 shared-library systems 通过位置无关代码、动态符号解析和 copy-on-demand mappings 在进程间共享文件后备代码；SunOS shared libraries 和后续 safe dynamic linking 工作奠定了这一对象语义与保护边界。[26,27] Luci 将普通 shared objects 用于 off-the-shelf 软件的动态更新，iFed 则把 dynamic loader 组织为可组合的 transformation passes，并在用户态 library 上优化 hugepage 和 relocation cost。[28,36] 这些工作改变的是用户态对象的版本或装载过程，仍以一份用户态 payload 为执行体。VKSO 沿用 loader-visible object semantics，却把 selected logical pages 重绑定到当前运行内核已经驻留的页；其核心问题因此不是设计另一种动态链接器，而是验证跨 privilege domain 的 backing、state 与 control-flow closure。

**Kernel-code rehosting and isolation.** LKL 与 Rump Kernels 将重新构建的 kernel or subsystem image 连同 host adaptation layer 带入新的执行环境，适合需要大范围 kernel APIs 或完整 subsystem semantics 的场景。[29,30] KSplit 从另一个角度分析未修改的 kernel/driver source，显式识别共享 state 和同步需求，以支持隔离而不是复用同一执行体。[37] VKSO 面向更细粒度、已驻留的 final binary closure：它不携带第二个 kernel instance，也不重新编译一份 user-owned execution body。相应代价是适用边界更窄；依赖 kernel objects、privileged locking domain 或无法发布状态的路径仍位于 reuse boundary 之外。内核锁设计本身依赖 privileged object ownership and execution context，也说明仅让指令可达并不足以重宿主其同步语义。[25]

**Binary sharing and kernel/user fast paths.** ORC 通过扩展 ELF 和 capability-based relocation，在隔离域之间显式共享 immutable binary objects，并为每个域保留私有状态；它解决的是跨 tenant 的对象复用与隔离，而不是从运行内核中复用 resident pages。[38] vDSO 与 VKSO 都让用户程序通过普通 ELF symbols 读取内核发布的只读状态，避免高频查询的 syscall entry。[31] FlexSC、Privbox 和 Userspace Bypass 则分别通过 exception-less scheduling、sandboxed privileged execution 或将用户指令透明移入内核来降低跨界成本。[33,35,39] 这些系统改变调用协议或执行位置；VKSO 的方向相反，从 final kernel/LKM binary 出发，以 closure analysis、page grafting 和 explicit dependency adaptation 构造标准用户态 carrier。大型 clocktime case study 检验的正是这种通用机制能否收敛原本分离的 kernel/vDSO execution bodies，而非提出另一组专用 vDSO API。

# Discussion



## Applicability and Limitations

VKSO 不是自动的 arbitrary-kernel-function exporter。Analyzer 能证明 binary closure、relocation range、page identity 和 declared binding 是否完整，但不能从机器码自动证明高层语义等价、数据是否可公开或一个 user helper 是否与 kernel helper 具有相同副作用。Export author 仍需声明允许的数据与 helper contract，系统再对声明执行 fail-closed validation。因而 VKSO 最适合计算密集或调用频繁、状态依赖能够收敛为少量显式输入的目标，不适合直接操作 kernel objects、devices、per-CPU state 或 privileged synchronization domains 的功能。

Manifest 与 Stub DSO 绑定到一个确定的 final kernel build。Kernel update、module relink、compiler mitigation 或 boot-time rewriting 只要改变 closure hash、symbol layout 或 executable targets，都需要重新分析和构建；运行端拒绝 build identity 不匹配的 carrier。这一限制牺牲了“一份 DSO 跨任意内核版本”的可移植性，但避免了把 kernel internal ABI 假装成稳定接口。面向应用的 exported symbol version 仍可独立保持稳定，并由新 carrier 适配新的 kernel build。

本文在 Linux/x86-64 上实现并评估完整原型。Design 所需的 shared-object carrier、object-backed mapping 和 first-touch installation 在主流 general-purpose OS 中普遍存在，但将 grafting hook、page lifetime 与 loader metadata 移植到其他内核仍需要系统特定实现；本文不把 Linux 原型的代码量或性能数字外推到其他 OS。类似地，当前数据只覆盖一台 x86-64 微架构，retpoline/ITS 的成本和不同 cache hierarchy 下的 first-touch 行为需要在更多硬件上复核。

## Threat Model and Security Boundary

本文信任 kernel、export builder、page-grafting manager、目标 kernel/LKM image 和 manifest。攻击者是能够装载已授权 Stub DSO 的普通非特权进程：它可以选择任意 API 参数、以任意顺序并发调用导出入口，并尝试通过 `mmap`、`mprotect` 或文件操作改变映射。阻止该进程写入 kernel memory、读取未授权 kernel data 或跳转到 export closure 之外属于本文的安全目标；隐藏已显式导出的机器码和只读常量则不属于目标，因为这些字节已按设计向该进程可见。

**Write integrity.** Reusable text、rodata 和 shared state 在 Stub DSO 中分别以 user RX、R/NX 和 R/NX 权限映射，所有 user-writable data 都位于不指向 kernel PFN 的 DSO-private pages。活跃 grafting session 还将 Stub DSO backing file 标记为 immutable，防止文件内容在 kernel pages 占据 page cache 时被修改，并在恢复 grafting 关系后撤销由 manager 添加的标记。当前原型的权限测试覆盖正常 loader 路径；对 adversarial `mprotect` 或 `MAP_SHARED` 组合的完整 VM/file boundary 证明不在本文范围内。

**Page granularity.** Page grafting 以物理页为最小单位，因此导出一个符号也会使同一页内的其他字节可见。Shared-state builder 因此只接受占据完整、对齐页的显式允许列表对象。对 executable pages，安全部署应用专用 section/page 隔离 export closure，或证明页内所有 colocated symbols 均可向用户态暴露。当前原型能严格检查 synthetic thunk page 和 shared-data page；若普通 text page 上还共存未分析函数，则必须依靠 linker layout 隔离，否则该 page 不应导出。

**Side channels and code disclosure.** 共享物理代码页会产生与 shared libraries 类似的 cache 和 access-pattern channels，且 kernel/user 共享使攻击者可能观察目标页的内核活动。消除这类 microarchitectural side channels 不在本文范围内。系统因此不应导出其访问模式或指令字节本身具有机密性要求的对象，并应把扩大 code-reuse gadgets 与 KASLR 攻击面纳入部署策略评估。

# Conclusion

VKSO 将跨 privilege domain 的代码复用转化为一个有明确边界的 binary-closure problem：state、control 和 code-shape constraints 决定什么可以复用，PIC-compatible construction、standard carrier、page grafting 和 Shim 决定如何复用。Linux 原型表明，经过这种解耦后，稳态调用不承担可测的页面复用开销；完整 clocktime 改造进一步说明，有状态子系统可以在保持 reader performance 的同时减少 source and machine-code duplication 并改善 publisher cost。无法隔离状态、闭合控制流或验证最终机器码的目标仍位于 reuse boundary 之外，这一边界是系统可部署性的组成部分。

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
