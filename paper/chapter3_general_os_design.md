# 第三章 面向 General OS 的跨特权级代码复用设计

前两章已经说明，传统跨特权级调用路径往往伴随显式边界切换、重复数据搬运与额外的软件栈开销；一旦复用目标位于 privileged domain 中，这类路径还会进一步放大系统调用、内存拷贝与运行时协调带来的成本。为此，本章将视角转向现代通用操作系统，讨论能否在不削弱隔离边界的前提下，直接复用驻留于 privileged domain 中的既有代码对象，并以零拷贝方式把它们导出为 user space 可承接的标准执行体形态。我们关心的不是把 Linux、Windows、macOS 或 FreeBSD 的实现细节拼接成一个“多系统综述”，而是抽取它们在共享对象、虚拟内存和按需装载路径上的共同结构，并据此提出一套面向 general OS 的跨特权级代码复用方案。

围绕这一目标，本章按三个连续问题展开。首先，`3.1` 检验现代主流 OS 是否共享足以支撑本文机制的 design substrates，从而确认后续设计方向。其次，`3.2` 在这些共有基础之上，从设计目标出发推导透明零拷贝导出所必需的通用机制。最后，`3.3` 在前两节给出的抽象与约束之上，提出一套统一的 carrier-and-export architecture：应用首先经由 *Stub Shared Library* 获得标准 shared-object interface，而真正的执行责任则在 first touch 时被导出到同一份 resident machine code body 上。

![图 3.1：面向 General OS 的跨特权级代码复用总体设计](figures/general_os_overall_design_v2.svg)

图 3.1 给出了本文在 general-OS 视角下的对象关系与运行时语义。图中**编号箭头**表示运行时链路：应用首先以普通共享库方式完成 `link/load`，随后对 *Stub Shared Library* 中目标入口的第一次触达触发一次 *First-Touch / Fault Trigger*；这里的 page fault 只是这一跨系统 first-touch installation 的典型实例，而不是本章唯一依赖的抽象表述。特权域中的 *Object-Backed Mapping* 机制据此为当前进程安装相应的 executable view，使控制流恢复并最终落到同一份 resident machine code body 上。与之相对，图中**未编号箭头**表示持久对象关系：stub 持有 carrier metadata 与 target object identity，*Object-Backed Mapping* 根据这些信息 `resolve/rebind` 到目标 privileged code object / cache-object layer，而该对象层进一步跟踪唯一的 resident reusable code pages。左下角被显式拒绝的 duplicated user implementation pages 则对应本文始终坚持的 *single execution-body invariant*：系统导出的是执行视图，而不是第二份用户态实现副本。

围绕这一链路，本章坚持四个设计目标。第一，系统应避免额外代码副本，使应用最终触达的仍是同一份驻留机器码。第二，系统应在消除显式跨特权边界调用后，使稳态执行尽量接近本地路径。第三，系统应保持对现有用户态 workflow 的透明兼容，使应用仍通过标准 shared library 的链接、装载与调用路径使用复用对象。第四，系统应把宿主操作系统所需的适配压缩到最小范围，而不要求重构其原生逻辑。基于这些目标，本章依次回答三个连续问题：`3.1` 确认现代主流 OS 是否共享支撑本文机制的 design substrates，`3.2` 从这些目标与已有基础共同推导透明零拷贝导出所需的通用机制，`3.3` 则在前两节的抽象与约束之上给出统一的 carrier-and-export architecture。

## 3.1 General OS Design Substrates

在面向 modern general OS 设计跨特权级代码复用机制之前，本文先固定该机制应尽量满足的四个目标。第一，系统应避免额外代码副本，使应用最终触达的仍是同一份驻留机器码。第二，系统应在消除显式跨特权边界调用后，使稳态执行尽量接近本地路径。第三，系统应保持对现有用户态 workflow 的透明兼容，使应用仍沿标准 shared library 的链接、装载与调用路径使用复用对象。第四，系统应把宿主操作系统所需的适配压缩到最小范围，而不要求重构其原生逻辑。对本文而言，这四个目标并不是事后添加的优点陈述，而是对 mechanism shape 的直接约束：若一个方案需要复制执行体，它将违背 Goal 1；若它要求应用绕开现有 loader/linker 或引入新的调用协议，它将破坏 Goal 3；若它要求宿主 OS 重写原生虚拟内存与对象管理逻辑，则又会违背 Goal 4。

正因为如此，`3.1` 的任务不是罗列多种 OS 的实现细节，而是检验这些目标是否能够建立在现代主流系统已经共享的抽象基底之上。若不存在这样的共享 substrate，那么跨态复用就只能退化为某个宿主系统上的局部技巧；反之，如果主流 OS 已经普遍提供标准 shared-object carrier、per-process private address space、对象侧的 cache/object layer，以及 first-touch 时的 fault-driven installation，那么本文后续机制就可以被表述为对这些既有抽象的重组，而不是对某个内核的重新发明。

在这一标准下，尽管 Linux、Windows、macOS 和 FreeBSD 的实现命名、对象类型和 API 入口各不相同，它们在动态库装载、虚拟地址空间组织、对象侧的页跟踪以及按需安装可执行视图这几类关键环节上，表现出高度一致的结构性共性。更具体地说，这些系统都同时提供四类运行时基础：其一，应用总是通过 standard shared-object carrier 与 loader/linker 进入既有软件生态；其二，地址空间中的 process-private view 以某种 file/section/object-backed 形式建立；其三，resident pages 总是由某个 object-centric 的 cache/object layer 跟踪和管理；其四，最终可见映射总是在 first touch 时通过 fault-driven path 被安装。[1]-[24]

| OS | shared object + loader | mapping object | cache / object layer | first-touch installation |
| --- | --- | --- | --- | --- |
| Linux | ELF + `ld.so`。[1][2] | `mmap(2)`、VMA、file-backed mapping。[1][4] | `address_space`、`i_pages`、`i_mmap`、page cache。[5][6] | page fault 路径按需建立页表；默认并非预装全部页，`MAP_POPULATE` 只是显式预取变体。[1][3][4] |
| Windows | PE/DLL + load-time / run-time dynamic linking。[8][9][10] | section object / mapped view / file mapping。[11][14] | `SECTION_OBJECT_POINTERS`、`DataSectionObject`、`SharedCacheMap`、`ImageSectionObject`。[12][13] | 视图访问前不分配物理页；首次访问触发 page fault，再把 file-backed 内容调入内存。[11] |
| macOS | Mach-O image + `dyld`。[15][16][17] | VM object / memory object / vnode pager。[18][19] | VM object + UBC + vnode-backed caching。[18][19][20] | page-fault handler 在首次缺页时装页、更新页表并恢复执行。[18] |
| FreeBSD | ELF + `rtld` / `ld-elf.so.1`。[21] | `mmap(2)`、`vm_object_t`、`vm_map_t`。[22][24] | UBC、`vm_object_t`、vnode-backed objects。[23][24] | zero-fill fault、reactivation fault 与从磁盘调页共同构成按需安装路径。[23][24] |

从这张表可以抽象出三个直接服务于本文设计的结论。第一，**用户态总是通过标准 shared object carrier 进入软件生态，而不是直接面向 privileged code object。** Linux 应用通过 ELF shared objects 和 `ld.so` 工作；Windows 应用通过 DLL 及其 load-time / run-time linking 语义工作；macOS 应用通过 Mach-O images 与 `dyld` 工作；FreeBSD 则沿 ELF 和 `rtld` 路线组织同样的运行时入口。[2][9][10][15][16][17][21] 这意味着，任何 general-OS 代码复用方案若想保持对现有应用透明，就必须首先尊重这一 shared-object-first 的事实：应用只认识普通共享对象、符号和 loader/linker 语义，而不认识 privileged domain 内部的驻留代码对象。这一点直接对应 Goal 3，并为后续的 *Stub Shared Library* 提供了标准承载外壳。

第二，**object-side page tracking 与 process-side executable view 在主流 OS 中始终是分层存在的。** Linux 中，file-backed VMA 提供进程地址空间中的视图，而 `address_space/i_pages` 负责对象侧的 resident page 跟踪；Windows 中，mapped view 与 section / cache structures 分别承担视图和对象职责；macOS 与 FreeBSD 也都把 `vm_map` 一侧的 per-process view 与 `VM object` / `vm_object_t` 一侧的对象语义区分开来。[1][4][5][6][11][12][14][18][19][22][24] 这一分层对本文尤其关键，因为它说明跨态复用并不要求把“对象拥有哪份代码页”和“某个进程如何看到它”混成一层：前者可以稳定锚定在 cache/object layer，后者则可以在 first touch 时被安装为当前进程的 executable view。

第三，**first-touch fault path 为“单份执行体、按需安装视图”提供了天然运行时契机。** Linux 的 page fault、Windows 的 view fault、macOS 的 VM fault，以及 FreeBSD 的 zero-fill/reactivation fault 虽然命名不同，但都遵循同一原则：对象侧先提供内容来源，当前进程的可见映射后安装、按需建立。[3][4][11][18][23] 这意味着，Goal 1 与 Goal 2 并不是彼此冲突的目标组合；系统完全可以一边把 execution body 固定在单一的 resident code pages 上，一边把 per-process executable view 推迟到 first touch 时再安装，从而避免稳态执行路径上持续承受额外的跨边界调用成本。

因此，`3.1` 的结论并不是“不同 OS 恰好都有 `mmap` 或 page fault”，而是：现代主流系统已经共同提供了足以支撑本文设计的 substrate 组合。Goal 3 由 standard shared-object carrier 与既有 loader/linker 生态支撑，Goal 1 由 object-centric 的 cache/object layer 与单份 resident pages 支撑，Goal 2 由 fault-driven installation 与本地 executable view 支撑，而 Goal 4 则来自这些能力本身已是宿主 OS 的原生组成部分，而非需要重新发明的附加机制。于是，后续问题便自然收敛为两个连续层次：首先，在这些共享基础已经存在的前提下，透明零拷贝导出机制还必须依赖哪些更具体的设计条件；随后，如何围绕这些条件把 *eligible object* 组织成统一的 carrier-and-export architecture。

## 3.2 Deriving the Required Design Substrates

在前文已经界定 *eligible object*，并确认 modern general-purpose OS 普遍具备 shared object、对象化映射与按需装载等共有基础之后，下一步问题不再是“系统是否客观上拥有这些机制”，而是：若要把这类对象透明地导出给 user space，同时避免重新物化一份等价实现，设计上究竟必须依赖哪些 substrate。换言之，`3.2` 的任务不是再次比较不同 OS，也不是重复 background 中已经给出的机制事实，而是从本文希望满足的设计目标出发，把后续架构所必需的通用机制严谨地推导出来。

为此，本文先确立该机制希望满足的四个目标：Goal 1，避免额外代码副本，使应用最终触达的仍是同一份驻留机器码，从而消除内存冗余；Goal 2，使稳态执行尽量接近本地路径，在避免显式跨特权边界调用后，将执行开销压缩到最小；Goal 3，保持对现有 user-space workflow 的透明兼容，即对应用而言，复用过程应尽可能表现为加载和使用普通动态库；Goal 4，最小化对 OS 的改动，优先复用现有内存管理与对象装载基础设施，而不重构其原生核心逻辑。这四个 goals 不是对方案优点的事后总结，而是对机制形态的前置约束：后续设计必须同时满足它们，而不是分别对某一目标做局部优化。

这些目标首先排除了两类看似直接、实则不合适的方案。若要满足 Goal 3，复用对象就不能通过专用接口、特制 runtime 或非标准使用路径暴露给应用，而必须借助既有的 *shared-object carrier* 进入 user space，使链接、装载与命名过程保持透明。与此同时，若要同时满足 Goal 1 与 Goal 4，导出过程又不能退化为在 user space 中重新编译、重新链接或重新物化一份等价实现；因此，机制必须建立在 *object-backed mapping* 之上，使用户态承载体所暴露的是对目标实现后备的对象化引用，而非一份被预先物化的等价副本。换言之，transparent interface 与 no-duplicate realization 共同决定了：后续架构既要保留 shared-library form，又必须保留对象身份与底层实现后备之间的对象化联系。

然而，仅有 *shared-object carrier* 与 *object-backed mapping* 仍然不足。若对象一旦形成便静态绑定到某个固定文件副本或固定页集合，系统仍无法在保持对象身份不变的前提下调整其实际后备，也就无法在不引入重复实现页的情况下管理执行体的真实驻留来源。为此，设计还需要在对象身份与其实际驻留后备之间保留 *cache/object-layer indirection*，使底层驻留关系围绕对象而非固定副本来组织。进一步地，若要在满足 Goal 2 的同时不破坏 Goal 3 与 Goal 4，机制就不应把全部绑定与装载决定前移到链接时或初始化时完成；相反，它必须依赖原生 *first-touch installation*，使对象的实际执行后备在首次真正触达时才被确定并安装，从而既保留标准 shared-library workflow，又避免为后续 steady-state execution 引入额外的持续 crossing overhead。

因此，本文所依赖的并不是若干彼此孤立的 OS 机制，而是四类相互配合的 substrate：作为透明用户态外壳的 *shared-object carrier*，作为对象化联系的 *object-backed mapping*，作为后备可管理性的 *cache/object-layer indirection*，以及作为安装时机的 *first-touch installation*。它们并非来自对接口名称的机械对照，而是由透明接口、非复制后备、对象化可管理性与按需安装这四类目标共同收缩出来的设计结果。`3.3` 将在此基础上进一步说明，如何围绕这四类 substrate 组织统一的 carrier-and-export architecture，使 *eligible object* 能够以 zero-copy 方式进入既有 user-space workflow。

## 3.3 Unified Carrier-and-Export Architecture

在前文已经界定 *eligible object*，并在 `3.2` 中推导出 transparent no-copy export 所需的通用 substrate 之后，系统接下来要解决的就不再是“如何再做一份用户态实现”，而是“如何让应用通过标准 shared object 触达这份既有 execution body”。因此，本文在 `3.3` 中给出的并不是两个并列机制，而是一套统一的 *carrier-and-export architecture*：应用首先看到的是一个遵守既有 loader/linker 语义的用户态承载体，而真正的执行责任则在 first touch 时被兑现到目标 *eligible object* 所对应的 resident machine code body 上。主流 OS 中共享库之所以能成为稳定承载体，也正是因为它把 file mapping、动态绑定和位置无关代码组织成了一种对应用透明的标准对象形态。[2][9][10][15][16][17][21][26]

在这一统一架构中，四类组件各自承担不同而连续的职责。*Stub Shared Library* 是应用可见的 *shared-object carrier*；它首先以普通 shared library 的方式被链接、装载和命名，使现有 runtime loader-linker 能够完成符号解析与入口接入。*Cache-Object Layer* 则位于对象一侧，用于锚定目标 privileged code object 的 resident code pages，并保存后续运行时重绑定所依赖的对象身份与页来源关系。*Object-Backed Mapping* 并不是对象层本身，而是 first touch 时的 lookup、binding 与 installation 机制；它根据 stub 所携带的符号、入口与布局元数据，把当前进程中的访问请求解析到目标对象上。最后，*Process View* 表示当前进程最终承接安装结果的 executable view，它在地址空间层面接收被导出的执行体，却不拥有第二份实现代码。[26][27][28]

从这一意义上看，stub 更像一个**代理式共享库对象**。它在外部行为上遵守标准 DSO 的链接与装载语义，在内部职责上却并不自行承担最终执行责任，而是把这一责任延后到运行时的 export 过程中去完成。于是，stub 的三类职责也都成为这套统一架构的前提部分：其一，它必须为应用提供标准 shared library 形态，使现有 runtime loader-linker 无需改变即可完成链接、装载与符号解析；其二，它必须保存后续运行时重定向所需的符号、入口与布局元数据，使系统能够把用户态对象中的入口解释为特权域中目标对象的 executable view；其三，它必须为 first touch 建立一个受控的用户态入口，使应用能够沿 ordinary shared-library path 进入后续运行时阶段。[26][27][28]

在这套架构中，真正需要被解决的不是 linking problem，而是 execution-body export problem。应用已经能够像使用普通共享库那样看见并调用这个 carrier，但这并不自动意味着它最终执行到的是 privileged domain 中那份已经驻留的机器码。关键在于，*Cache-Object Layer* 与 *Object-Backed Mapping* 在这里承担的是两层不同职责：前者负责 object-to-pages 的 binding / rebinding，也即目标对象最终关联到哪一份 resident code pages；后者则在 first touch 时 lookup 这一对象层结果，并把它安装成当前进程可承接的 executable view。动态链接与 loader-based indirection 的相关系统文献长期表明，对外可见的 shared-object interface、对内实际承担执行责任的代码实体，以及运行时的绑定/重定向过程，本来就是可以在对象语义上解耦而又在执行语义上重新收敛的。[27][28]

因此，图 3.1 所示的运行时链路应被理解为这一统一架构的展开，而不是两个阶段性机制的机械拼接。应用首先按普通共享库语义完成对 *Stub Shared Library* 的 `link/load`；当它第一次真正访问 stub 中相应入口时，系统触发一次 first-touch installation event，图中用 page fault 表示这一典型契机，因为它最直观地体现了“访问一个尚未被安装为可执行页的对象视图”这一情形。[1][3][4][11][18][23] 随后，特权域中的 *Object-Backed Mapping* 机制根据这次访问 lookup 相应的 *Cache-Object Layer*，解析目标 *eligible object* 当前绑定的 resident code pages，并把结果安装为当前进程的 *Process View*；控制流恢复之后，应用在地址空间层面仍沿 ordinary shared-library path 调用，但执行体层面已经落到同一份 privileged code pages 上。[2][16][17][21]

这里需要强调的是，整个机制从头到尾维护的都是同一个不变量：系统导出的是**执行视图**，而不是第二份代码实体。图中被划掉的 duplicate user implementation pages 并不是一个工程优化选项，而是本章明确拒绝的对象关系；不同用户进程可以各自拥有面向自身地址空间的 carrier、入口和 *Process View*，但这些视图在执行体层面必须收敛到同一份 resident machine code body，而不应在物理页层面分化为多份实现副本。这正是本文所说 *single execution-body invariant* 的实质内容。[26][28]

同样地，这一设计共享的是**machine code body**，而不是 privileged execution context。应用之所以能够透明地沿 standard shared-library path 进入该执行体，是因为 stub 提供了兼容既有软件生态的标准对象形态；应用之所以最终执行到同一份 resident pages，则是因为统一的 carrier-and-export architecture 在首次触达时完成了 object-side rebinding 与 process-side installation。于是，系统导出的不是完整的 privileged runtime，而只是一个受控的、可执行的代码对象视图；共享的不是内核上下文，而是已经驻留的机器码主体。第四章将在这一 general-OS 语义之上，进一步说明 Linux 如何以 page cache、fault path 与 PTE 安装来实例化这里的 *Cache-Object Layer*、*Object-Backed Mapping* 与 *Process View*。

至此，本章形成了完整闭环。`3.1` 说明现代主流 OS 已经提供了 standard shared object、cache/object layer、process-side executable view 与 fault-driven installation 这些 general-OS substrates；`3.2` 在这些共有基础之上，从设计目标推导出 transparent no-copy export 所必需的通用机制；`3.3` 则给出统一的 carrier-and-export architecture，说明 *eligible object* 如何被嵌入这些既有抽象，并在不复制执行体的前提下完成跨特权级复用。第四章将进一步回答，这些 general-OS roles 在 Linux 上分别落到哪些具体对象与运行路径上。

## 参考文献

[1] `mmap(2)` — Linux manual page. <https://man7.org/linux/man-pages/man2/mmap.2.html>

[2] `ld.so(8)` — Linux manual page. <https://man7.org/linux/man-pages/man8/ld.so.8.html>

[3] *Page Tables* — The Linux Kernel Documentation. <https://docs.kernel.org/mm/page_tables.html>

[4] *Process Addresses* — The Linux Kernel Documentation. <https://docs.kernel.org/mm/process_addrs.html>

[5] *Overview of the Linux Virtual File System* — The Linux Kernel Documentation. <https://docs.kernel.org/filesystems/vfs.html>

[6] *Linux Filesystems API summary* — The Linux Kernel Documentation. <https://docs.kernel.org/filesystems/api-summary.html>

[7] *Virtual Address Spaces* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/virtual-address-spaces>

[8] *About Dynamic-Link Libraries* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows/win32/dlls/about-dynamic-link-libraries>

[9] *Load-Time Dynamic Linking* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows/win32/dlls/load-time-dynamic-linking>

[10] *Run-Time Dynamic Linking* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows/win32/dlls/run-time-dynamic-linking>

[11] *Managing Memory Sections* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-sections>

[12] `SECTION_OBJECT_POINTERS` structure — Microsoft Learn. <https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_section_object_pointers>

[13] *File Caching* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows/win32/fileio/file-caching>

[14] *Creating a File Mapping Object* — Microsoft Learn. <https://learn.microsoft.com/en-us/windows/win32/memory/creating-a-file-mapping-object>

[15] *Overview of Dynamic Libraries* — Apple Developer Documentation. <https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/OverviewOfDynamicLibraries.html>

[16] *Dynamic Library Usage Guidelines* — Apple Developer Documentation. <https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryUsageGuidelines.html>

[17] `dyld(1)` — Apple Developer Documentation. <https://leopard-adc.pepas.com/documentation/Darwin/Reference/ManPages/man1/dyld.1.html>

[18] *About the Virtual Memory System* — Apple Developer Documentation. <https://developer.apple.com/library/archive/documentation/Performance/Conceptual/ManagingMemory/Articles/AboutMemory.html>

[19] *Memory and Virtual Memory* — Apple Kernel Programming Guide. <https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/vm/vm.html>

[20] *Managing Data* — Apple IOKit Fundamentals. <https://developer.apple.com/library/archive/documentation/DeviceDrivers/Conceptual/IOKitFundamentals/DataMgmt/DataMgmt.html>

[21] `rtld(1)` — FreeBSD Manual Pages. <https://man.freebsd.org/cgi/man.cgi?query=rtld&sektion=1>

[22] `mmap(2)` — FreeBSD Manual Pages. <https://man.freebsd.org/cgi/man.cgi?query=mmap&sektion=2>

[23] *Design elements of the FreeBSD VM system* — FreeBSD Documentation Portal. <https://docs.freebsd.org/en/articles/vm-design/>

[24] *FreeBSD Architecture Handbook* — FreeBSD Documentation Portal. <https://docs.freebsd.org/en/books/arch-handbook/book/>

[25] John H. Baldwin. *Locking in the Multithreaded FreeBSD Kernel*. BSDCon 2002.

[26] Robert A. Gingell, Meng Lee, Xuong T. Dang, Mary S. Weeks. *Shared Libraries in SunOS*. USENIX Summer 1987. <https://www.cs.cornell.edu/courses/cs414/2004fa/sharedlib.pdf>

[27] Michael Hicks, Stephanie Weirich, Karl Crary. *Safe and Flexible Dynamic Linking of Native Code*. In Robert Harper (ed.), *Types in Compilation (TIC 2000)*, LNCS 2071, pp. 147-176, Springer, 2001. <https://www.cs.cmu.edu/~crary/papers/2000/taldynlink/taldynlink.pdf>

[28] Bernhard Heinloth, Peter Wägemann, Wolfgang Schröder-Preikschat. *Luci: Loader-based Dynamic Software Updates for Off-the-shelf Shared Objects*. 2023 USENIX Annual Technical Conference (USENIX ATC 23), pp. 241-256. <https://www.usenix.org/conference/atc23/presentation/heinloth>
