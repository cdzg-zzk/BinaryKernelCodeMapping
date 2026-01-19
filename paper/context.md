你是一个经验丰富、受过严格学术训练的学者，在计算机领域，尤其是Linux操作系统内核拥有深厚的专业知识。您的任务是进行全面系统的研究，来识别研究课题“零拷贝复用内核代码”的内容。您将运用批判性思维、系统方法和综合分析来对研究主题形成整体理解。
0. 本项目的实现方式与机制
我的工作的目的是灵活的让用户态复用内核态代码，创建一个stub动态库，然后将这个动态库文件的i_pages(page cache)修改，是指text段/.rodata指向内核代码/只读数据所对应的物理页面，然后用户进程要使用某个内核函数的时候，链接这个stub动态库，这样由于触发缺页中断，可以直接查page cache发现页缓存中有已加载的物理页面（重定向过的物理页面）然后填充页表PTE，即可在用户态进行访问（只读、无状态、不依赖内核上下文的基础函数），所以并不是所有内核代码都可以被映射，只能是纯函数，不依赖内核上下文等要求的安全函数。
1. 目标/要求：
(1)对“零拷贝复用内核代码”进行全面深入的研究。结合0.本项目的实现方式与机制, 了解其背景与动机，提出相关工作。
(2)要以论文的方式写background和related works。
(3)如果你写的正文中存在引用，直接把引用链接写在这句话后面做标注，即使重复出现过的论文/网址也要再次标注而不省略
(4)要以写顶刊格式要求，内容可以丰富一些，但不能少，后续我会自己裁剪内容
(5)后面的内容你可以学习借鉴，但内容不完整，你需要自己补充
(6)写完之前内容后，请你将我的工作与related works中提到的工作进行比较，尤其是Linux Kernel Library。
2. 标准
研究成果/论文/综述/报告必须
涵盖主题的各个相关方面(例如理论、实践、社会、经济、技术、道德)。
识别并分析关键趋势、驱动力和制约因素。
揭示系统互连和因果链。.
客观地提出和分析替代/竞争观点。
整合相关学科的知识以拓宽背景和理解深度。.
确定不确定的领域、现有知识的差距以及进一步研究的潜在方向。包含有充分根据的结论，如有必要，还包含基于分析的建议。有质量证据支持(定量和定性证据，包括专家共识、概念模型、统计数据(如果与主题相关))。如果有必要，请考虑相关的背景内容，以全面理解该主题。
3. 原则
研究必须严格遵循以下原则:
深度分析:力求进行超越明显结论的多层次分析，识别隐藏内容系统思维:识别各个结构的关系、对完整性的理解、分析的整合。批判性思维:彻底评估证据、识别偏见、考虑替代方案
跨学科性:不同领域知识的整合、观点的协同。
知识诚实:明确区分事实、合理的假设和假说。。
背景性:考虑研究主题所处的历史、文化、经济和其他背景，尤其是制度环境。
实用形:结论的相关性、实施的潜力或对理解的贡献。
相关性:关注重要方面，避免信息过载。
学术严谨性:依赖高质量、方法合理的资料来源，参照Harvardreference style中规定的参考来源。
及时性:分析必须基于截至 2025 年的最新信息。
来源优先排序:分析应主要基于高优先级来源(系统评价、荟萃分。析、基础研究、知名期刊的同行评议文章、官方数据)。如有矛盾，请提出不同观点并评估其有效性，优先考虑方法更严谨、数据更优质的研究。
4. 可选要素
(如果与研究课题相关且为了清晰论证，则应包括):。关键术语表:对基础、方法和跨学科概念进行结构化定义，特别是当术语复杂、不稳定或在不同领域有不同的使用内涵时。可视化:概念图、关系图、比较表或分析框架，用于说明复杂的互连或比较数据/方法。
5.输出格式
- 介绍与背景：介绍和背景:主题的定义、历史观点(如果相关)、相关性和重要性、关键概念/术语。
- 相关工作：特点、应用场景、为了解决什么问题，缺点是什么
- 以Markdown格式输出
6. 要求，一定要有引用参考文献，将参考文献（论文名/网址）置于相关语句之后，重复的话也放

## 介绍与背景

### 1. 研究问题与基本概念

“零拷贝复用内核代码”（zero‑copy kernel‑code reuse）在这里特指：**用户态直接执行内核中已有的、已加载的代码页，而不再复制一份等价实现到用户态**。
与传统“零拷贝 I/O”只关注数据缓冲区不搬运不同，本工作关注的是**代码段（.text/.rodata）的跨保护域共享**——目标是做到：

* 物理页层面零拷贝：内核 `.text` / `.rodata` 与用户态共享同一组物理页；
* 语义层面零复制：用户程序调用的就是内核已经实现并验证过的函数，而不是一套“语义接近但维护独立”的用户态重写版本；
* 安全层面严格受限：只允许**只读、无状态、不依赖内核上下文的“纯函数”**被映射到用户态执行，避免破坏内核不变量或提升权限。

从系统结构上，这一研究试图在“单一实现、多处复用”的逻辑下，打通内核态与用户态之间在**同一段代码上的零拷贝共享**，而不是在两个执行域分别维护两份实现。

#### 本项目的实现思路（概要）
1. **构造 stub 动态库**

   * 为若干目标内核函数构造一个 ELF 共享对象（stub.so），其符号表与函数原型与内核中的目标函数保持一致，但不真正包含实现。
2. **篡改 stub inode 的页缓存映射**

   * 在内核中对 stub.so 对应 inode 的 `i_pages`（page cache）做“重定向”：
     将其中 `.text` / `.rodata` 段对应的页缓存指向内核代码 / 常量数据所在的物理页，而非磁盘上的 stub 映像。
3. **按需缺页映射**

   * 当用户态进程首次调用 stub 中的某个函数、触发对相应虚拟地址的缺页异常时，内核在 page cache 中发现这些页已经存在（且指向内核物理页），从而建立 PTE，让用户态以 RX 权限执行这些页。
4. **可调用函数的约束**

   * 仅允许**不依赖 `current`、不操作内核全局状态、不访问内核专用地址空间、无副作用或仅依赖参数或只读变量的函数**暴露给用户态。
   * 该限制确保用户进程即便能执行同一段二进制指令，也无法伪造内核态上下文或破坏内核 invariants。

这种方式本质上绕过了“在用户态重写一遍内核函数”的做法：**用户与内核共享同一段机器码**，但在不同特权级、不同页表、不同调用约束下执行。

---

### 2. 历史背景：内核/用户态边界与性能演进

传统操作系统采用单体内核（monolithic kernel）模型：所有设备驱动、文件系统、网络协议栈等都在内核态运行，用户态通过系统调用（syscall）与之交互。为了安全隔离，内核与用户态之间存在若干性能成本：特权级切换、TLB flush、内核栈切换以及用户/内核空间之间的数据拷贝。对于**短小但高频的操作**（如计时、轻量级同步、简单数据结构操作），这些固定成本会主导总延迟。([Packagecloud Blog][1])

为缓解上述成本，Linux 从 `vsyscall` 发展到 **vDSO（virtual Dynamic Shared Object）**：内核在每个进程地址空间中映射一个小型共享库，提供 `__vdso_clock_gettime`、`__vdso_gettimeofday`、`__vdso_time`、`__vdso_getcpu` 等函数，使得这些调用可以在用户态完成，而无需真正陷入内核。vDSO 由内核构建并自动映射，glibc 在探测到可用时会优先调用 vDSO 版本，从而显著降低时间查询等操作的系统调用开销（“vdso(7) – Linux manual page”, [https://man7.org/linux/man-pages/man7/vdso.7.html；“Implementing](https://man7.org/linux/man-pages/man7/vdso.7.html；“Implementing) virtual system calls”, [https://lwn.net/Articles/615809/）。](https://lwn.net/Articles/615809/）。) ([man7.org][2])

然而，vDSO 只是一个**非常狭窄的专用接口**：

* 仅暴露少量经过精挑细选的函数；
* ABI 变化必须极其谨慎，以保持用户空间兼容性；
* 几乎不涉及复杂状态或内核内部数据结构。([LWN.net][3])

它并不是“通用的内核代码复用机制”，而是少数热点系统调用的特化加速路径。

与此同时，硬件性能格局也在发生变化：网络和存储 I/O 带宽在过去十年迅速增长，而 CPU 单核性能增长相对缓慢，内核在数据面上的处理开销逐渐成为瓶颈（“Arrakis: The Operating System is the Control Plane”, [https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter）。](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter）。) ([USENIX][4]) 这推动了 DPDK、netmap、XDP/AF_XDP、io_uring 等一系列绕过或削弱传统系统调用路径的新机制，以降低 I/O 快速路径中的内核参与度。([USENIX][5])

从历史脉络看，“减少用户/内核边界上的开销”和“让用户态更直接地复用底层机制”是过去二十多年操作系统研究中的持续主线。零拷贝复用内核代码可以看作这一趋势在**代码级复用**上的进一步延伸：不仅要绕过拷贝和多余抽象，还要避免重复实现同一算法。

---

### 3. 软件工程与可维护性动机

从工程角度看，目前在内核态与用户态之间普遍存在大量“语义相似但代码不共享”的重复实现，例如：

* 字符串处理、哈希函数、加密/校验和算法；
* 通用数据结构操作（队列、哈希表、红黑树等）；
* 解析、编码、协议处理中的基础工具函数。

像 Linux Kernel Library（LKL）和 NetBSD rump kernel 这类工作，正是出于“复用主线内核源码、避免维护分叉版本”的动机：

* **LKL** 将 Linux 内核作为一个新的“架构端口”集成到用户态，应用可以像链接普通库一样链接一个“内核库”，在其中直接使用主线内核的 TCP/IP 栈、文件系统等实现（“LKL: The Linux kernel library”, [https://www.researchgate.net/publication/224164682_LKL_The_Linux_kernel_library）。](https://www.researchgate.net/publication/224164682_LKL_The_Linux_kernel_library）。) ([ResearchGate][6])
* NetBSD **rump kernel** 和 anykernel 架构则将内核拆分为可组合组件，这些组件既可以在内核中，也可以在用户态或 hypervisor 上以“内核质量”的驱动和协议栈形式运行（“Rump Kernels: No OS? No Problem!”, [https://www.usenix.org/system/files/login/articles/login_1410_03_kantee.pdf；“rumpkernel(7)](https://www.usenix.org/system/files/login/articles/login_1410_03_kantee.pdf；“rumpkernel%287%29) – NetBSD Manual Pages”, [https://man.netbsd.org/rumpkernel.7）。](https://man.netbsd.org/rumpkernel.7）。) ([USENIX][7])

这些工作清晰地表明：**把内核代码“库化”以复用其实现，是可行且工程上非常有价值的**。但它们大多采用“把整个子系统搬到用户态”的路径，而不是像本工作这样，在**宿主内核与用户进程之间共享同一物理代码页**。

在跨内核版本、多发行版环境中维护重复实现不仅增加复杂度，还放大了安全补丁、性能优化在不同实现之间“不同步”的风险。LKL 和 rump kernel 通过“直接复用主线源代码”的方式缓解了这一问题（“Linux Kernel Library – Reusing Monolithic Kernel”, [https://www.slideshare.net/slideshow/linux-kernel-library-reusing-monolithic-kernel/64305411），但仍然需要额外的宿主接口、构建流水线和移植工作。](https://www.slideshare.net/slideshow/linux-kernel-library-reusing-monolithic-kernel/64305411），但仍然需要额外的宿主接口、构建流水线和移植工作。) ([www.slideshare.net][8])

相比之下，本工作的目标之一，是在**不复制源代码、不过度重构内核**的前提下，让用户进程直接调用宿主内核已经加载的机器码。这样一来：

* 内核补丁（包括性能改进与安全修复）可以立即惠及所有复用该函数的用户态应用；
* 不需要维持额外的“用户态内核库”分支；
* 对于被严格限制为“纯函数”的内核例程，语义漂移的可能性也较小。

---

### 4. 性能与资源效率动机

高性能网络与存储系统中，“零拷贝”已被证明可以带来数量级的性能提升：

* **netmap** 在不改动应用的前提下，通过重构内核中网络缓冲区的管理和用户态映射，使通用硬件上的 Linux 能够处理每秒数百万乃至上千百万个数据包（“netmap: A Novel Framework for Fast Packet I/O”, [https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo）。](https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo）。) ([USENIX][5])
* **DPDK** 通过用户态轮询驱动（Poll Mode Driver）、大页内存、批量收发和内核旁路技术，实现 10–40Gbps 链路上的线速转发，成为高性能数据平面的事实标准之一（“DPDK Overview – Intel Ethernet”, [https://edc.intel.com/content/www/us/en/design/products/ethernet/config-guide-e810-dpdk/dpdk-overview/；“Poll](https://edc.intel.com/content/www/us/en/design/products/ethernet/config-guide-e810-dpdk/dpdk-overview/；“Poll) Mode Driver – DPDK Documentation”, [https://doc.dpdk.org/guides-24.03/prog_guide/poll_mode_drv.html）。](https://doc.dpdk.org/guides-24.03/prog_guide/poll_mode_drv.html）。) ([doc.dpdk.org][9])
* **XDP/AF_XDP** 则在 Linux 内核内引入一个可编程的极早期数据路径，并允许将数据帧零拷贝重定向到用户态环形队列，实现单核 40Gbps 级别的包处理能力（“AF_XDP – kernel documentation”, [https://docs.kernel.org/networking/af_xdp.html；“Fast](https://docs.kernel.org/networking/af_xdp.html；“Fast) packet processing in Linux with AF_XDP”, [https://archive.fosdem.org/2018/schedule/event/af_xdp/attachments/slides/2221/export/events/attachments/af_xdp/slides/2221/fosdem_2018_v3.pdf）。](https://archive.fosdem.org/2018/schedule/event/af_xdp/attachments/slides/2221/export/events/attachments/af_xdp/slides/2221/fosdem_2018_v3.pdf）。) ([Kernel Documentation][10])

这些系统证明：**只要减少数据复制与系统调用次数，性能就能获得大幅提升**。

但大多数现有工作聚焦在**数据路径**：数据包缓冲区、I/O 请求、描述符队列等实体的零拷贝传递；而对**代码路径**本身（即内核逻辑实现）仍采用复制或重写的方式。例如，高性能用户态网络栈往往自己实现 TCP/IP 协议栈，而不是直接复用 Linux 内核中的协议代码。

本工作则从另一个维度切入：**如果数据已经做到了零拷贝，能否让“处理这些数据的代码”也实现零拷贝复用？**

* 在许多场景下，用户态只需要调用一些通用的、与内核上下文弱相关的基础函数（如校验和、哈希、简单调度逻辑）；
* 这些函数在内核中已经被验证和优化，如果能够零拷贝地对用户态开放，则既减少代码重复，又避免了为这些函数再包装额外系统调用的开销。

另外，以 **io_uring** 为代表的新型 I/O 接口通过共享提交队列和完成队列，在用户态与内核间建立共享 ring buffer，显著降低了系统调用次数和内核参与度（“An introduction to the io_uring asynchronous I/O framework”, [https://blogs.oracle.com/linux/an-introduction-to-the-io-uring-asynchronous-io-framework；“The](https://blogs.oracle.com/linux/an-introduction-to-the-io-uring-asynchronous-io-framework；“The) rapid growth of io_uring”, [https://lwn.net/Articles/810414/）。](https://lwn.net/Articles/810414/）。) ([Oracle Blogs][11]) 这类机制从接口层面说明：**共享内存+零拷贝+减少陷入内核，是当前 Linux 性能演进的重要方向**。本工作可以看作在“共享代码页”这一维度上与 io_uring 等机制形成互补。

---

### 5. 安全、制度与社会经济考量

从安全和“制度环境”角度，复用内核代码并不是单纯的技术问题：

* **攻击面与特权分离**

  * 近年来 eBPF 和 io_uring 都曾被指出存在安全滥用的潜在风险：eBPF 虽然通过验证器和受限 helper 提供安全扩展能力，但其强大能力也让内核攻击面显著扩大（“What is eBPF?”, [https://ebpf.io/what-is-ebpf/；“A](https://ebpf.io/what-is-ebpf/；“A) thorough introduction to eBPF”, [https://lwn.net/Articles/740157/）。](https://lwn.net/Articles/740157/）。) ([eBPF][12])
  * io_uring 的部分攻击场景甚至可以绕过传统基于系统调用 hook 的安全监测，成为新型 rootkit 的载体（“Linux io_uring PoC Rootkit Bypasses System Call-Based Threat Detection Tools”, [https://thehackernews.com/2025/04/linux-iouring-poc-rootkit-bypasses.html）。](https://thehackernews.com/2025/04/linux-iouring-poc-rootkit-bypasses.html）。) ([The Hacker News][13])
* **本工作中的安全边界设想**

  * 与在内核中执行不受信任的 eBPF 程序不同，本方案是让用户态执行一小部分内核已有代码，而且执行仍然发生在用户态特权级；
  * 通过限制可映射函数为“纯函数”“只读数据”，并维持 W^X、SMEP/SMAP 等硬件防护，本工作在设计上避免了直接获得 ring0 权限的途径。

在社会经济与工程层面：

* 大规模软件栈中，内核代码复用可以减少不同团队、不同产品线维护同一算法多份实现的**人力成本**；
* 但同时会在组织上引入内核与用户态团队之间更紧密的接口约定与兼容性约束；
* 在开源许可（尤其是 GPL）方面，“用户态直接调用内核实现”可能触及法律与合规边界，需要谨慎界定该机制在二进制接口与链接层面的法律含义——这在本研究中属于**制度与伦理**层面的重要不确定因素，需要与法律专家配合进一步评估。

总体上，零拷贝复用内核代码在工程价值与安全/制度风险之间需要精细平衡：**暴露更多能力意味着潜在攻击面扩大，但也能显著降低维护成本与性能开销**。本工作的“纯函数 + 只读映射”设计，是在这一权衡上的一个较为保守的点。

---

### 6. 研究空白与本工作的定位

综合来看，现有工作主要分为几类：

1. **库操作系统 / Exokernel / LibOS：** 将 OS 功能整体“上移”到用户态；
2. **内核代码库化：** 如 LKL、rump kernel，将内核组件打包为库在用户空间运行；
3. **内核旁路与零拷贝 I/O：** 如 DPDK、netmap、XDP/AF_XDP、io_uring，绕过传统系统调用与内核协议栈；
4. **内核内部扩展机制：** 如 eBPF，运行在内核内的受限程序。

这些方案要么复制出一个新的“用户态内核”，要么通过旁路机制绕过宿主内核的数据路径，要么在内核内部执行用户定义的逻辑。**尚缺少一种“在不复制实现的前提下，由宿主内核向用户态以零拷贝方式暴露自身函数”的通用机制。**

本工作正是针对这一空白提出：

* 在共享 page cache 和 PTE 的前提下，**让内核和用户态在不同特权级上共享同一份代码页**；
* 通过静态分析和接口约束，筛选出可安全暴露的纯函数集合；
* 为用户态提供类 vDSO 但更可扩展、可配置的函数复用机制。

由此可以导出一系列研究问题和未来方向（详见后文对比与展望部分）：如何自动识别可暴露函数、如何表达版本与 ABI 约束、如何与调试、性能分析工具集成等。

---

## 相关工作

本节按照“特性 – 应用场景 – 解决的问题 – 局限性”的结构，分主题梳理与本课题密切相关的研究。

### 1. 内核接口特化与库操作系统（Library OS / Exokernel）

#### 1.1 Exokernel 与早期 LibOS

**Exokernel** 将内核缩减为一个只负责安全地多路复用硬件资源的小层（thin veneer），所有高级抽象由用户态库操作系统实现（“Exokernel: An Operating System Architecture for Application-Level Resource Management”, [https://dl.acm.org/doi/10.1145/224057.224076）。](https://dl.acm.org/doi/10.1145/224057.224076）。) ([ACM Digital Library][14])

* **特点：**

  * 内核只提供低层、安全的资源管理接口（物理页、TLB、DMA 等）；
  * 所有传统 OS 抽象（进程、文件、套接字等）由用户态 LibOS 定义。
* **应用场景：**

  * 高度定制化系统；
  * 实验性 OS 结构验证；
  * 需要细粒度控制资源的高性能应用。
* **要解决的问题：**

  * 打破内核提供固定抽象的“黑盒”，让应用能够按需定义策略；
  * 提升性能和灵活性。
* **缺点/局限：**

  * 应用必须链接并信任一整套 LibOS；
  * 移植现有应用代价较高；
  * 与主流 Linux 内核生态存在较大鸿沟。

**Drawbridge** 则在 Windows 世界中提出了一种库操作系统 + picoprocess 的模型：一个用户态的“NT 内核”在受限的 picoprocess 容器中运行，通过极简 ABI 与宿主系统交互（“Rethinking the Library OS from the Top Down”, [https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/asplos2011-drawbridge.pdf）。](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/asplos2011-drawbridge.pdf）。) ([Microsoft][15])

* **特点：**

  * 将完整的 Windows 子系统封装为 Library OS；
  * picoprocess 提供隔离和极窄的内核接口。
* **应用场景：**

  * 应用沙箱；
  * 兼容现有 Windows 应用的同时提升部署灵活性（例如后续 SQL Server on Linux 的技术基础）。
* **局限：**

  * 仍然需要维护一整套库化内核代码；
  * 与 Linux 内核的直接代码共享有限。

**与本工作的关系：**
这些工作将 OS 功能整体“上移”到用户态，而本工作则希望**在不把内核拆成 LibOS 的前提下，复用宿主 Linux 内核中的局部实现**。二者关注粒度不同：前者关注“整个 OS 子系统”，本工作关注“内核函数级别”。

---

### 2. 在用户空间复用内核代码：LKL、rump kernel、NUSE 等

#### 2.1 Linux Kernel Library（LKL）

**Linux Kernel Library (LKL)** 将 Linux 内核作为一个新的“架构”移植到用户态：

* **特点：**

  * 在内核源码树中引入 `arch/lkl` 端口，通过一套“宿主操作”抽象底层硬件（时钟、内存、线程等）；
  * 内核整体以库形式编译，供用户态程序链接使用（“LKL: The Linux kernel library”, [https://www.researchgate.net/publication/224164682_LKL_The_Linux_kernel_library）。](https://www.researchgate.net/publication/224164682_LKL_The_Linux_kernel_library）。) ([ResearchGate][6])
* **应用场景：**

  * 在非 Linux 宿主（如 Windows、BSD、Unikernel）中复用 Linux 文件系统或网络栈；
  * 在用户态环境中进行内核子系统的测试与仿真（例如在 Unikraft 等项目中集成 LKL，用于快速构建 Unikernel 镜像，“Librarizing Linux kernel for Unikernels”, [https://retrage.github.io/2019/06/02/lkl-on-unikraft-en.html）。](https://retrage.github.io/2019/06/02/lkl-on-unikraft-en.html）。) ([retrage.github.io][16])
* **要解决的问题：**

  * 避免从主线内核手工抽取、维护大量分叉代码；
  * 让外部项目能“直接拿来用”成熟的内核实现。
* **缺点/局限：**

  * 每个 LKL 实例实际上是一个“独立内核”，具有自己的调度、地址空间与状态；
  * 无法与宿主 Linux 内核直接共享运行时状态和缓存；
  * 仍然需要与主线内核保持版本同步，否则会出现语义漂移与维护成本；
  * 代码体积大，集成到 Unikernel 等“瘦镜像”环境时会显著放大镜像尺寸（同上博客指出 LKL 集成使镜像趋于“fat”）。([retrage.github.io][16])

#### 2.2 NetBSD rump kernel / anykernel

**rump kernel** 将 NetBSD 内核中的驱动、文件系统、协议栈等组件以“可组合、可移植”的形式在用户空间运行：

* **特点：**

  * 基于 anykernel 架构，同一套 NetBSD 内核组件既可在内核态，也可在用户态运行；
  * 通过轻量的 `rumpuser` 接口适配不同宿主平台（Linux、Hurd、Xen、裸机等）（“Rump Kernels: No OS? No Problem!”, [https://www.usenix.org/system/files/login/articles/login_1410_03_kantee.pdf；“rumpkernel(7)”](https://www.usenix.org/system/files/login/articles/login_1410_03_kantee.pdf；“rumpkernel%287%29”), [https://man.netbsd.org/rumpkernel.7）。](https://man.netbsd.org/rumpkernel.7）。) ([USENIX][7])
* **应用场景：**

  * 在用户空间开发和调试文件系统或驱动；
  * 将 NetBSD 组件迁移到其他内核或裸机环境。
* **局限性：**

  * 与 LKL 类似，每个 rump kernel 实例都是一个“独立内核环境”；
  * 与宿主 Linux 内核的代码与状态并未共享；
  * 需要维护 NetBSD 源码与宿主环境之间的接口层。

#### 2.3 Network Stack in Userspace (NUSE) 与基于 LibOS 的网络栈复用

**NUSE（Network Stack in Userspace）** 通过将 Linux 内核网络栈移植为用户态库，使应用可以直接链接这一网络栈实现：

* **特点：**

  * 通过在内核中增加新的“架构端口”，把 TCP/IP 栈构造成可在用户态运行的库；
  * 利用“LibOS with mainline Linux network stack”的框架，使 NUSE 能作为 LibOS 的一个子项目（“Network Stack in Userspace (NUSE)”, [https://libos-nuse.github.io/；“Library](https://libos-nuse.github.io/；“Library) Operating System with Mainline Linux Network Stack”, [https://netdevconf.org/0.1/papers/Library-Operating-System-with-Mainline-Linux-Network-Stack.pdf）。](https://netdevconf.org/0.1/papers/Library-Operating-System-with-Mainline-Linux-Network-Stack.pdf）。) ([Libos NUSE][17])
* **应用场景：**

  * 在仿真器、网络模拟器（如 ns-3）中直接运行 Linux 网络栈；
  * 实现“每应用一套独立网络栈”的虚拟化环境。
* **局限：**

  * 每个应用拥有独立栈实例，与宿主内核的网络栈仍然是两套系统；
  * 需要维护大规模移植层和 glue code。

**与本工作的关系：**
LKL、rump kernel、NUSE 等方案都明确体现了“把内核代码当库用”的趋势，但它们遵循的是“复制/移植整套子系统到用户态”的路线。相比之下，本工作关注的是：**在保持宿主 Linux 内核不被大量重构的前提下，让用户进程通过页缓存共享直接使用内核已有函数的机器码**，避免创建新的“用户态内核实例”。

---

### 3. vDSO：主流 Linux 中最接近代码复用的机制

如前所述，**vDSO** 是目前 Linux 主线中对“在用户态执行内核提供实现”最接近的通用机制之一。

* **特点：**

  * 内核在每个进程地址空间中映射一个小型 ELF 共享对象，提供少量函数（时间查询、CPU 号等）；
  * 这些函数由内核构建并注入，glibc 自动探测并优先使用（“vdso(7) – Linux manual page”, [https://man7.org/linux/man-pages/man7/vdso.7.html；“On](https://man7.org/linux/man-pages/man7/vdso.7.html；“On) vsyscalls and the vDSO”, [https://lwn.net/Articles/446528/）。](https://lwn.net/Articles/446528/）。) ([man7.org][2])
* **应用场景：**

  * 高频、短小、只读查询型系统调用，例如 `clock_gettime()`。
* **要解决的问题：**

  * 避免在这类操作上每次都进行系统调用陷入，大幅降低延迟。
* **缺点/局限：**

  * 导出接口极少且高度固定，扩展困难；
  * 不适合暴露复杂内核数据结构和状态；
  * ABI 需要保持长期稳定，限制了快速迭代。

**与本工作的关系：**

* vDSO 在理念上与本工作相近：都希望在用户态执行“内核提供的实现”；
* vDSO 的接口是内核硬编码的、固定的小集合；本工作希望建立一个更**可配置、可扩展的“函数目录”**，用于选择性暴露一批纯函数；
* 在机制上，vDSO 倾向于“内核显式构造一个用户态共享对象”，而本工作探索的是“通过页缓存重定向，让普通 stub 库的 text 映射到内核代码页”。

可以将本工作视为对 vDSO 思路的**系统化、泛化和细粒度化**。

---

### 4. 用户态 I/O 旁路与零拷贝框架

#### 4.1 DPDK、netmap、AF_XDP 与 Arrakis

**DPDK** 和 **netmap** 是高性能用户态网络 I/O 的代表：

* **DPDK**

  * 通过用户态 Poll Mode Driver 和大页内存，实现内核旁路和批量 I/O，减少中断和系统调用开销（“Data Plane Development Kit (DPDK)”, [https://developer.nvidia.com/networking/dpdk；“Blazingly](https://developer.nvidia.com/networking/dpdk；“Blazingly) fast packet processing with DPDK”, [https://blog.maowtm.org/dpdk/en.html）。](https://blog.maowtm.org/dpdk/en.html）。) ([NVIDIA Developer][18])
* **netmap**

  * 重构网络驱动缓冲区管理方式，以共享 ring buffer 实现用户态快速收发，性能达到每秒数千万数据包（“netmap: A Novel Framework for Fast Packet I/O”, [https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo；https://dl.acm.org/doi/10.5555/2342821.2342830）。](https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo；https://dl.acm.org/doi/10.5555/2342821.2342830）。) ([USENIX][5])

**AF_XDP** 进一步将 XDP 数据路径与用户态 socket 绑定，使数据帧可以被重定向到用户态内存缓冲区，实现内核网络栈旁路，并在支持的硬件上实现零拷贝（“AF_XDP – kernel documentation”, [https://docs.kernel.org/networking/af_xdp.html；“Accelerating](https://docs.kernel.org/networking/af_xdp.html；“Accelerating) networking with AF_XDP”, [https://lwn.net/Articles/750845/）。](https://lwn.net/Articles/750845/）。) ([Kernel Documentation][10])

**Arrakis** 则从操作系统设计角度系统化了“数据面旁路”的思路：

* 将内核拆分为控制面（负责保护和资源分配）与数据面（大部分 I/O 操作可以直接在用户态进行）；

* 利用 SR-IOV 和 IOMMU 给应用提供直接访问虚拟化 I/O 设备的能力，从而在某些工作负载上获得 2–5× 延迟优化和 9× 吞吐提升（“Arrakis: The Operating System is the Control Plane”, [https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter；https://drkp.net/papers/arrakis-tr.pdf）。](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/peter；https://drkp.net/papers/arrakis-tr.pdf）。) ([USENIX][4])

* **共同特点：**

  * 通过共享缓冲区、内核旁路或极简化数据路径，减少拷贝和系统调用次数；
  * 主要关注数据面，而非代码复用。

* **与本工作关系：**

  * 这些方案解决的是“数据怎么快进快出”；
  * 本工作解决的是“处理数据的代码能否复用宿主内核实现”。
  * 未来可以设想：在零拷贝 I/O 数据路径上，调用零拷贝共享的内核函数实现，形成**数据与代码双零拷贝**的路径。

---

### 5. 内核内部扩展机制：eBPF

**eBPF** 提供了一种在内核中执行受限程序的机制。eBPF 程序运行在内核中的虚拟机上，通过 verifier 保证安全性，并可调用一小组 helper 函数访问内核设施（“What is eBPF?”, [https://ebpf.io/what-is-ebpf/；“Extend](https://ebpf.io/what-is-ebpf/；“Extend) the kernel with eBPF – Android Open Source Project”, [https://source.android.com/docs/core/architecture/kernel/bpf）。](https://source.android.com/docs/core/architecture/kernel/bpf）。) ([eBPF][12])

* **特点：**

  * 允许用户态动态加载程序到内核执行；
  * 在可观测性、安全和网络加速等方面有广泛应用；
  * 提供 helper 函数作为内核代码复用的粒度。
* **应用场景：**

  * 追踪、监控、网络过滤、性能分析等。
* **局限与风险：**

  * 安全验证复杂，历史上曾出现多个 verifier 漏洞；
  * 代码运行在内核态，一旦有缺陷或漏洞将影响整个系统。

**与本工作关系：**

* eBPF 是“在内核中复用用户态逻辑”；本工作是“在用户态复用内核逻辑”；
* eBPF 的 helper 函数本质上也是一种“内核代码复用”，但其调用点在内核内部，而非用户进程直接调用；
* 两者可以互补：本工作暴露的纯函数可以在 eBPF 用户态运行时中也被复用，形成统一的代码库。

---

## 对比分析：本工作与 Linux Kernel Library 等相关方案

在完成背景与相关工作梳理后，可以从多个维度将本工作与典型方案进行系统比较，尤其是 **Linux Kernel Library (LKL)**。

### 1. 架构粒度与复用方式对比

| 方案                      | 架构单元粒度               | 是否共享宿主内核运行时   | 是否零拷贝复用代码页              | 典型应用                 |
| ----------------------- | -------------------- | ------------- | ----------------------- | -------------------- |
| Exokernel / Drawbridge  | 整个 OS 抽象由 LibOS 提供   | 否             | 否                       | 可定制 OS、沙箱            |
| LKL                     | 整个 Linux 内核作为库       | 否（独立内核实例）     | 否（重编译）                  | 非 Linux 宿主复用 Linux 栈 |
| rump kernel / anykernel | 内核组件（驱动、FS、协议栈）      | 否             | 否                       | 组件化复用、测试             |
| NUSE                    | Linux 网络栈作为用户态库      | 否             | 否                       | 网络栈个性化               |
| vDSO                    | 极少数固定辅助函数            | 部分（时间等共享状态）   | 近似（特定路径）                | 加速时间相关 syscall       |
| DPDK/netmap/AF_XDP      | 数据路径（缓冲区、队列）         | 是（设备由宿主管理）    | 仅数据零拷贝                  | 高性能网络 I/O            |
| eBPF                    | 小型内核态程序 + helper 函数  | 是（在内核中执行）     | 否                       | 监控、安全、网络             |
| **本工作（零拷贝复用内核代码）**      | **函数级别（纯函数 / 只读逻辑）** | **是（同一内核实例）** | **是（共享 text/rodata 页）** | **用户态调用内核实现的基础工具函数** |

本工作与 LKL 的关键区别在于：

* **实例 vs. 共享：**

  * LKL 为每个应用或环境创建一个完整的“内核库实例”；
  * 本工作直接与宿主 Linux 内核共享代码页，不再复制实现。([ResearchGate][6])
* **粒度：**

  * LKL 侧重复用整个内核子系统（文件系统、网络栈）；
  * 本工作定位在函数级粒度，专注于那些可安全暴露的纯函数。
* **性能路径：**

  * LKL 的调用路径在用户态内部，虽避免了系统调用，但仍要承担在其“虚拟内核”内部进行线程切换、锁竞争等开销；
  * 本工作在设计上允许用户态像调用普通共享库函数一样直接执行内核实现，对于纯计算型函数几乎没有额外开销。

### 2. 状态管理与一致性

* **LKL / rump / NUSE：**

  * 持有自己的全局状态、锁、对象生命周期；
  * 与宿主内核之间只能通过特定“宿主接口”同步状态（如 I/O 请求）；
  * 补丁和语义更新需要在主线内核和用户态库之间维护一致性。([ResearchGate][6])
* **本工作：**

  * 通过严格限制到“无状态/纯函数”，**刻意规避状态一致性问题**；
  * 不试图在用户态直接操作内核内部复杂状态，而是将其限定在可预测、副作用可控的函数集合内。

这一设计决定减少了可复用函数的数量，但换来了更清晰的安全与一致性边界。

### 3. 安全模型与攻击面

* **LKL / rump / NUSE：**

  * 用户态库实现自身的内核逻辑，一旦库存在漏洞，其影响主要 confined 在该进程或环境内部（除非与宿主内核交互不当）；
  * 与宿主内核之间仍然通过传统 system call 或宿主接口交互。
* **本工作：**

  * 用户态可以执行与宿主内核完全相同的机器码，很容易让人担心“是否打开了通向 ring0 的大门”；
  * 通过以下约束缓解：

    * 仅在用户态特权级运行代码；
    * 保持映射页只读，防止覆盖内核代码；
    * 通过白名单和静态分析筛选“纯函数”；
    * 禁止访问需要内核上下文（如 `current`、内核栈）的函数。

与 eBPF 相比，本工作不在内核中执行不受信任代码，而是在用户态执行受信任代码，因此其攻击面形态不同。eBPF 的风险集中在 verifier 和 helper 功能过强，而本工作的风险集中在“纯函数识别是否可靠、是否存在被绕过的隐含状态依赖”。([eBPF][12])

### 4. 性能与实现复杂度

* **LKL / rump / NUSE：**

  * 需要为“内核库”提供宿主接口（调度、定时、内存分配、I/O 等），实现和维护成本高；
  * 一旦部署，多数调用路径仍然在库内部，与宿主内核之间只有边缘 I/O 流交换。
* **本工作：**

  * 核心复杂度集中在：

    * 如何安全地将 stub.so 的 `i_pages` 指向内核 text/rodata 页；
    * 如何在缺页填充时正确设置 PTE；
    * 如何设计元数据描述、白名单机制以及版本/ABI 检查。
  * 一旦机制建立，对于每个新增函数，边际代价只是在 metadata 中登记，并保证其满足纯函数约束。

在性能上，本工作对于纯计算函数能接近“普通共享库调用”的开销，而 LKL 等方案需要经历一次进入“虚拟内核”的路径（包括锁、调度、潜在上下文切换）。但对于复杂的有状态子系统，本工作则并不打算复用，LKL 等方案在这些场景下更适合。

### 5. 理论与实践上的开放问题

本工作在与这些相关方案对比的同时，也暴露出若干尚待深入研究的问题：

1. **可暴露函数的自动化识别与验证**

   * 如何利用静态分析和形式化方法识别“纯函数”并证明其不依赖隐式内核状态？
   * 是否需要配合内核构建流程，在编译阶段给函数打上可导出/不可导出的标签？

2. **版本与兼容性管理**

   * 如何在内核升级时自动检查 stub 库与内核实现是否仍兼容？
   * 是否需要类似 vDSO 的版本表和符号版本控制机制？（对比 `vdso(7)` 版本管理）。([man7.org][2])

3. **调试与可观测性**

   * 用户态调用内核实现时，如何在 gdb/perf 等工具中呈现调用栈？
   * 是否需要给这些共享代码页提供专门的调试符号路径？

4. **法律与制度环境**

   * 在 GPL 语境下，用户态程序通过这种方式“链接内核代码”是否有额外的合规要求？
   * 这需要与法律界进一步澄清，目前属于不确定领域。

5. **与 I/O 旁路框架的融合**

   * 能否在 DPDK/AF_XDP 等用户态 I/O 框架中，直接调用零拷贝共享的内核函数，例如复用内核中的 checksum、分片算法等，而不再重写？（“Data Plane Development Kit (DPDK)”, [https://developer.nvidia.com/networking/dpdk；“AF_XDP](https://developer.nvidia.com/networking/dpdk；“AF_XDP) – kernel documentation”, [https://docs.kernel.org/networking/af_xdp.html）。](https://docs.kernel.org/networking/af_xdp.html）。) ([NVIDIA Developer][18])

---

## 价值

** 它的价值不在于“我解决了所有 code reuse 问题”而是在于：**
### 1. 证明了一种前所未有的机制
 - 用 page cache + 映射，可以真实做到 kernel/user 二进制级 .text 共享；
 - 这是 concrete 的工程成果。
### 2. 把“能复用的东西范围”具体量化了
 - 通过实验你发现：
   * 真正能导出的多是纯函数 / snapshot 函数；
   * 强状态模块几乎动不了；
 - 你对函数分类、模块结构给出了很清楚的经验边界（我们刚刚一起整理的四类就是这个）。

### 3. 在几个具体场景里给出了“能真实用起来”的 demo
 - io_uring + 导出的协议 core；
 - eBPF/bpftime 共用 helper 的一部分实现；
 - shadow module / fuzz / 仿真；
 - 这些都足以支撑“这不只是玩具”。

### 4. 帮未来的“真库式 OS 设计”踩了一遍坑
 - 你可以在论文结尾很诚实地写：
   * 在现有 Linux 上，我们被这些 global / 设计历史牵制，只能做到某个程度；
   * 如果将来要迁移到更加库化的内核架构（或 LKL / unikernel / 微内核），我们已经有一套成熟的“core + glue + page‑sharing”模型可以直接套用。
 - 换句话说，你给未来 OS 设计者提供了一个informed design point，而不是空想。
---

## 小结

* 从历史上看，Exokernel、Drawbridge、Arrakis、LKL、rump kernel、NUSE、vDSO、DPDK/netmap/AF_XDP、eBPF 等工作共同推动了“内核功能重构与复用”的演进，但各自侧重点不同：有的重构整个 OS，有的库化子系统，有的绕过数据路径，有的在内核中运行用户代码。
* **Linux Kernel Library (LKL)** 与本工作在“复用 Linux 内核实现”这一目标上一脉相承，却采取截然不同的路径：前者通过“复制出独立内核库实例”，后者试图通过页缓存共享在宿主内核和用户态之间实现**零拷贝代码复用**。
* 本工作在理论上提出了一种新的复用维度：在函数级粒度上，让**同一段内核机器码**在不同特权级被多域复用；在实践上，它面临函数筛选、安全验证、版本管理和法律合规等多方面挑战，也因此提供了丰富的研究空间。

如果你接下来希望，我可以在此基础上继续往“方法与系统设计”“形式化安全模型”“实验设计与评估”等章节扩展，把整篇论文骨架搭出来。

[1]: https://blog.packagecloud.io/the-definitive-guide-to-linux-system-calls/?utm_source=chatgpt.com "The Definitive Guide to Linux System Calls"
[2]: https://man7.org/linux/man-pages/man7/vdso.7.html?utm_source=chatgpt.com "vdso(7) - Linux manual page"
[3]: https://lwn.net/Articles/615803/?utm_source=chatgpt.com "Kernel development"
[4]: https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-peter_simon.pdf?utm_source=chatgpt.com "Arrakis: The Operating System is the Control Plane"
[5]: https://www.usenix.org/conference/atc12/technical-sessions/presentation/rizzo?utm_source=chatgpt.com "netmap: A Novel Framework for Fast Packet I/O"
[6]: https://www.researchgate.net/publication/224164682_LKL_The_Linux_kernel_library?utm_source=chatgpt.com "(PDF) LKL: The Linux kernel library"
[7]: https://www.usenix.org/system/files/login/articles/login_1410_03_kantee.pdf?utm_source=chatgpt.com "OPERATING SYSTEMS - Rump Kernels"
[8]: https://www.slideshare.net/slideshow/linux-kernel-library-reusing-monolithic-kernel/64305411?utm_source=chatgpt.com "Linux Kernel Library - Reusing Monolithic Kernel | PDF"
[9]: https://doc.dpdk.org/guides-24.03/prog_guide/poll_mode_drv.html?utm_source=chatgpt.com "15. Poll Mode Driver - Documentation - DPDK"
[10]: https://docs.kernel.org/networking/af_xdp.html?utm_source=chatgpt.com "AF_XDP"
[11]: https://blogs.oracle.com/linux/an-introduction-to-the-io-uring-asynchronous-io-framework?utm_source=chatgpt.com "An Introduction to the io_uring Asynchronous I/O Framework"
[12]: https://ebpf.io/what-is-ebpf/?utm_source=chatgpt.com "What is eBPF? An Introduction and Deep Dive into the ..."
[13]: https://thehackernews.com/2025/04/linux-iouring-poc-rootkit-bypasses.html?utm_source=chatgpt.com "Linux io_uring PoC Rootkit Bypasses System Call-Based ..."
[14]: https://dl.acm.org/doi/10.1145/224057.224076?utm_source=chatgpt.com "Exokernel: an operating system architecture for application ..."
[15]: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/asplos2011-drawbridge.pdf?utm_source=chatgpt.com "Rethinking the Library OS from the Top Down"
[16]: https://retrage.github.io/2019/06/02/lkl-on-unikraft-en.html/?utm_source=chatgpt.com "Librarizing Linux kernel for Unikernels - retrage.github.io"
[17]: https://libos-nuse.github.io/?utm_source=chatgpt.com "Network Stack in Userspace (NUSE)"
[18]: https://developer.nvidia.com/networking/dpdk?utm_source=chatgpt.com "Data Plane Development Kit (DPDK)"



