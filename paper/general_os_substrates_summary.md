# General OS 共性抽象建模总结

## 1. 建模目标与边界

本文档的目标不是罗列 Linux、Windows、macOS、FreeBSD 的实现细节，也不是撰写一个面面俱到的操作系统综述，而是抽取那些与本文机制直接相关、并且跨系统稳定存在的**共性抽象基底**。更具体地说，我们关心的是：现代主流 OS 如何组织 privileged domain、private address space、standard shared object、object-backed mapping、resident page tracking，以及 first-touch 时的 fault-driven installation。这些抽象将直接支撑 Chapter 3 中的 general OS design 叙事，而不是作为 related work 的替代物。

本总结以用户提供的研究报告为线索来源，但所有进入主论证的关键说法都尽量回落到官方文档、系统手册或经典一手论文。Medium、Reddit、Wikipedia、Stack Overflow 一类来源不作为本文主证据链。这样做的目的，是把“多种 OS 的设计共性”收敛成一组可审计、可复述、可为后续设计服务的统一建模结论。

从建模角度看，本文真正需要的不是某个 OS 的局部技巧，而是如下问题的跨系统答案：应用是否总是通过标准共享对象进入既有软件生态；地址空间是否总是通过某种 object-backed 机制与底层对象建立联系；resident pages 是否总是通过某个对象层或缓存层被追踪；以及用户首次触达目标地址时，系统是否通过按需缺页或等价机制完成可见映射的安装。只要这四类关系在不同 OS 中稳定存在，我们就能把“general OS design”写成一种对象关系和运行时语义，而不是某个宿主系统的特化技巧。

## 2. 核心比较表

| OS | privileged / user domain | process-private address space evidence | standard shared-object format | runtime loader / linker | object-backed mapping primitive | cache / object layer tracking resident pages | demand / fault-driven installation evidence | 为什么与本文设计相关 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Linux | 内核态与用户态隔离；用户任务通过 `mm_struct` 拥有各自地址空间。[3][4] | `struct mm_struct` 容纳该进程全部 VMA；每个 VMA 描述一段连续虚拟区间。[4] | ELF shared object。[2] | `ld.so` / dynamic linker。[2] | `mmap(2)` 建立 file-backed mapping；VMA 可指向 `struct file`。[1][4] | `address_space` 统一管理 page cache，并记录 `i_pages`、`i_mmap` 等信息。[5][6] | page tables 与 page faults 按需建立翻译；`MAP_POPULATE` 的存在本身说明默认并非预装全部页表。[1][3][4] | 说明 Linux 中“shared object -> file-backed mapping -> cached resident pages -> first-touch install”是标准路径。 |
| Windows | user space 与 system space 分离；每个 user-mode 进程有自己的 private virtual address space。[7] | Windows 明确把每个进程的 user-space 地址空间视为私有逻辑空间。[7] | PE/EXE 与 DLL image。[8] | load-time linking 与 run-time linking 都由系统 DLL 装载流程支持。[9][10] | section object 与 mapped view；`CreateFileMapping` / `MapViewOfFile` 或 `ZwCreateSection` / `ZwMapViewOfSection`。[11][14] | `SECTION_OBJECT_POINTERS` 把 file stream 连接到 `DataSectionObject`、`SharedCacheMap`、`ImageSectionObject`。[12] | 视图在访问前不分配物理页；首次访问触发 page fault，file-backed section 再把对应页调入内存。[11] | 说明 Windows 也存在“shared object carrier + object-backed mapping + section/cache object + first-touch fault”这一整条链。 |
| macOS | Mach/BSD 混合内核下仍保持受保护执行域与每进程逻辑地址空间。[18][19] | 每个进程的 logical address space 由若干 mapped regions 组成。[18] | Mach-O dynamic library / framework image。[15][16] | `dyld` 负责装载依赖 image 和运行时 `dlopen` 路径。[15][16][17] | VM region 对应 VM object；file-backed 部分由 vnode pager 负责。[18][19] | VM object 跟踪 resident / nonresident pages；UBC 把文件系统缓存和 VM 缓存统一起来。[18][19][20] | 缺页后由 page-fault handler 装页、更新页表并恢复执行。[18] | 说明 macOS 中“image -> dyld -> VM object / vnode pager -> UBC / resident pages -> VM fault”同样成立。 |
| FreeBSD | 内核态与用户态隔离；运行时装载与 VM 继续沿 BSD 路线组织。[21][23][24] | `vm_map_t` / `vm_entry_t` 把进程地址空间组织为映射区间。[24] | ELF shared object。[21] | `rtld` / `ld-elf.so.1`。[21] | `mmap(2)` 把对象映射到虚拟内存；底层用 `vm_object_t` 与 `vm_map_t` 组织。[22][24] | UBC 基于 `vm_object_t` 统一文件缓存；同一页在同一对象中保持统一关联。[23][24] | BSS 首次访问触发 zero-fill fault；不在内存中的页需从磁盘调入；共享库场景还存在 sparse active-mapping 的 fault 讨论。[22][23] | 说明 FreeBSD 也有“runtime linker + mmap/vm_object + unified cache + first-touch fault”这一抽象链，证明这不是 Linux 特例。 |

这张表给出的不是四个系统的“功能列表”，而是同一类对象关系在不同实现中的投影。名称不同，并不影响它们在设计上呈现出稳定的一致性：应用经由标准共享对象进入运行时；运行时通过某种 object-backed 机制把地址空间的一段区间绑定到底层对象；resident pages 由对象层或缓存层跟踪；最终由 fault-driven path 把该对象变成当前进程中可见、可执行或可读写的映射。

## 3. 共性抽象 A：Privileged Domain 与 Private Address Space

四个系统都清楚地区分了 privileged domain 和 user domain。Linux 通过每个任务关联的 `mm_struct` 和 VMA 集合描述用户态虚拟地址空间，而页表层次则把虚拟地址翻译为底层物理页。[3][4] Windows 明确区分 user space 与 system space，并强调每个 user-mode process 都拥有自己的 private virtual address space。[7] macOS 把进程的逻辑地址空间表述为一组 mapped regions，每个 region 都有自己的属性、保护位和后备对象。[18][19] FreeBSD 则通过 `vm_map_t` 与 `vm_entry_t` 组织用户地址空间，并由 `vm_object_t` 把虚拟区间与后备对象关联起来。[24]

这一点对本文很关键，因为它意味着“把某些 privileged code 变成 user-visible executable view”并不需要推翻隔离边界。相反，它要求系统在既有的隔离模型之内工作：目标对象仍位于 privileged domain 所维护的对象图中，应用只是在自己的私有地址空间中获得一个受控视图。也正因为每个进程的地址空间天然是独立的，本文后续才可以同时坚持“共享执行体”与“保持进程私有视图”这两个看似矛盾的目标。

同一抽象下还天然包含了一个统一的 demand-paging 框架。Linux 的页表文档明确把 MMU、页表和 page fault 放在同一条链上；Windows 把视图访问前不分配物理页写入 section 文档；macOS 直接说明 page-fault handler 在缺页时装入页面并更新页表；FreeBSD 则把 zero-fill fault、reactivation fault 与从磁盘调页都纳入 VM 设计讨论。[3][11][18][23] 因而，first touch 触发一次按需安装事件，并不是某个 OS 的偶然行为，而是现代虚拟内存系统的通用执行模式。

## 4. 共性抽象 B：标准共享对象与 Runtime Loader / Linker

四个系统在共享代码的用户态入口上也表现出高度一致性。Linux 通过 ELF shared object 与 `ld.so` 组织动态装载。[2] Windows 使用 PE/DLL，并同时提供 load-time 和 run-time dynamic linking 两条路径。[8][9][10] macOS 通过 Mach-O image 与 `dyld` 管理 dependent libraries 以及 `dlopen` 式运行时装载。[15][16][17] FreeBSD 延续 ELF 传统，并由 `rtld`/`ld-elf.so.1` 负责装载和运行时链接。[21]

这一抽象的共同点在于：应用并不直接面向 privileged code object，而是面向一个**标准 shared-object carrier**。不管系统内部如何实现，应用可见的入口始终是某种普通的 shared object、image、DLL、dylib 或 shared library；运行时 loader / linker 负责把对象名、依赖、导出符号和装载动作接入当前进程。这一点对本文中的 *Stub Shared Library* 至关重要，因为它说明“对应用表现为普通共享库”并不是 Linux 特有需求，而是主流 OS 生态的一般约束。

进一步看，四个系统也都允许在“启动时依赖装载”与“运行时显式装载”之间做区分。Linux 和 FreeBSD 的 ELF 生态支持运行时动态装载；Windows 区分 load-time linking 与 `LoadLibrary`/`GetProcAddress` 驱动的 run-time linking；macOS 则区分 dependent libraries 与 `dlopen` 方式打开的 dynamically loaded libraries。[2][10][16][21] 这意味着本文不需要发明新的用户态入口协议，而应复用现成的 loader/linker 工作流，把真正的设计难点放在执行体如何在后续阶段被导出。

## 5. 共性抽象 C：Object-Backed Mapping

四个系统都存在“地址空间中的一个视图被绑定到底层对象”的映射层，只是名称和实现接口不同。Linux 中，`mmap(2)` 建立 file-backed mapping，VMA 记录虚拟区间属性并可关联 `struct file`；VFS/内存管理再通过 `struct address_space` 跟踪该对象的缓存页和映射关系。[1][4][5][6] Windows 中，section object 是这一层的中心：它既可以 file-backed，也可以 anonymous；具体视图通过 `ZwMapViewOfSection` 或用户态文件映射 API 进入当前进程地址空间。[11][14] macOS 明确把 VM system 的对象层表述为 VM object 与 memory object / pager 的组合，并用 vnode pager 处理 memory-mapped file access。[18][19] FreeBSD 则用 `vm_object_t`、`vm_map_t` 和 `mmap(2)` 组织同样的关系。[22][24]

这里最重要的共性不是“文件能被 mmap”，而是**地址空间视图与后备对象之间存在一个显式中介层**。也就是说，当前进程里看到的 mapped region 并不是凭空存在的，它总是某个 object-backed abstraction 的投影。这个中介层正是本文 general-OS 叙事中 *Object-Backed Mapping* 的基础。本文不是要凭空创造新的地址空间原语，而是要利用这一跨系统已经存在的中介层，把某个 user-visible carrier 的执行视图重绑定到目标 privileged object 所驻留的 resident pages 上。

## 6. 共性抽象 D：缓存层与目标对象关系

要把执行视图最终落到同一份 resident pages 上，仅有 object-backed mapping 还不够；系统还必须存在一个对象层或缓存层，用来持续追踪某个 backing object 当前有哪些 resident pages，以及它们如何与映射视图发生关系。在这方面，四个系统再次呈现了结构上的一致性。

Linux 中最清晰的对象就是 `address_space`。官方文档直接说明，它用于分组和管理 page cache 中的页，同时也追踪“文件片段到进程地址空间映射”的关系；`struct address_space` 中的 `i_pages` 与 `i_mmap` 正是这一对象层的核心成员。[5][6] Windows 中，同样的角色由 `SECTION_OBJECT_POINTERS` 及其连接的 `DataSectionObject`、`SharedCacheMap` 和 `ImageSectionObject` 承担：它把 file stream 与 memory manager / cache manager 的控制结构连接起来，分别对应数据流、缓存视图和可执行 image section 的驻留状态。[12][13] macOS 中，VM object 负责管理 resident / nonresident pages，而 UBC 又把文件系统缓存与 VM 缓存统一起来；file-backed region 通过 vnode pager 把文件对象与 VM object 联系起来。[18][19][20] FreeBSD 中，UBC 以 `vm_object_t` 为中心统一文件缓存，同一物理页在同一对象中的关联关系保持一致。[23][24]

从 general-OS 角度看，这一层的共同含义是：resident pages 并不是孤立的页集合，而是经由某个**backing-object-centric cache / object layer** 被追踪和管理。也正因为如此，本文才能把“执行体不复制”描述为一种对象关系上的不变量，而不是某种偶然的内存布局现象。

## 7. 共性抽象 E：Fault-Driven Installation

四个系统都把 first touch 视为建立可见映射的关键时刻。Linux 的页表文档把 page fault 放在 MMU/page table 工作链条中，而 `mmap(2)` 文档中 `MAP_POPULATE` 的语义则反向证明默认映射并不会预先安装所有页表；缺页处理因此构成 file-backed region 的标准 first-touch path。[1][3][4] Windows 在 memory section 文档中说得更直接：mapped view 在访问前不分配物理内存，首次访问触发 page fault，file-backed section 再把对应文件内容读入内存。[11] macOS 的 virtual memory 文档明确指出 page-fault handler 会定位物理页、把需要的数据从磁盘装入、更新页表并恢复程序执行。[18] FreeBSD 的 VM 设计既讨论了 zero-fill faults，也讨论了 reactivation faults 和从磁盘装页的路径。[22][23]

因此，本文后续要写的 `first access -> install mapping -> execute` 并不是为了贴合 Linux 的 page cache trick 而强行抽象出来的顺序，而是跨系统都成立的运行时语义：用户先得到一个地址空间中的逻辑视图；真正的物理页和页表绑定延后到首次访问时完成；而 file-backed 或 object-backed 对象则在这个时刻提供内容来源与控制关系。

## 8. 对本文设计的直接启示

基于上述四类共性抽象，可以把本文 general-OS 设计真正依赖的不变量收敛为六条。

第一，现代主流 OS 都有受保护的 privileged domain 与 per-process private address space，这意味着“共享执行体”不等于“共享执行上下文”。第二，应用总是通过 standard shared-object carrier 接入现有软件生态，因此任何跨态复用方案都必须尊重 shared library / image / DLL / dylib 这一对象形态。第三，地址空间中的视图总是通过某种 object-backed mapping primitive 与底层对象建立联系，这为执行视图的 *rebinding* 提供了抽象支点。第四，resident pages 总是由某个 cache/object layer 跟踪，而不是孤立存在，这为“single execution-body invariant”提供了对象层语义。第五，first touch 总是通过 page fault 或等价 fault-driven path 触发映射安装，这为“首次访问时导出执行体”提供了通用运行时契机。第六，上述机制是共性；Linux 的 `address_space/i_pages/xarray/page_cache_replace`、Windows 的 `SECTION_OBJECT_POINTERS`、macOS 的 VM object / vnode pager、FreeBSD 的 `vm_object_t` / UBC 则只是这些共性的不同实例化。

这也意味着，Chapter 3 的 general-OS 设计不应该被写成“如何在 Linux 上利用 page cache 做一个 clever trick”，而应该被写成：在这些已存在的共享抽象之上，系统如何先筛选可独立承接的 privileged code object，再把它包装为标准 shared-object carrier，并在 first touch 时把其 executable view 重绑定到同一份 resident machine code body 上。

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
