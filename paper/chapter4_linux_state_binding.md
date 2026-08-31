# Linux VKSO 显式状态绑定：Design/Implementation 笔记

本文档整理 clocktime 子功能对通用 VKSO 机制带来的设计增量，供论文 Design 与
Linux Implementation 章节吸收。它记录机制边界和实现证据，不替代最终论文正文，
也不把 clocktime 专用字段表述成通用 ABI。

## 1. 设计问题

早期 VKSO 模型适合只依赖参数与 `.rodata` 的函数。clocktime reader 还需要三类
运行时信息：不断更新的 global time snapshot、随 time namespace 改变的进程视图，
以及只在当前用户地址空间有效的 provider/fallback 地址。如果让共享机器码直接
读取普通内核全局或硬编码用户地址，就会破坏隔离、位置独立性和跨进程共享。

因此，clocktime 实例引入的核心设计不是“允许共享任意状态”，而是：

> 共享 text 的每一项非参数依赖都必须被显式分类、绑定和验证；代码页可以全局
> 共享，状态仍按 global、per-address-space 与 per-loader-instance 分别管理。

## 2. 状态分类

| 类别 | 所有者 | 用户权限 | 更新时机 | clocktime 实例 |
| --- | --- | --- | --- | --- |
| Global snapshot | kernel producer | `R--/NX` | timekeeping publish | `vkso_shared_page` |
| Per-MM context | `mm_struct` | `R--/NX` | exec 初始化、timens commit/setns | `vkso_mm_page` |
| DSO private state | loader/wrapper instance | 普通私有 RW | 启动时绑定 | `vkso_context`、MM_data 指针 |
| Kernel-only state | kernel | 不映射 | 内核原生路径 | private timekeeper、锁/NMI 状态 |

前三类形成受控依赖通道；第四类必须留在内核 fallback。该分类可推广到其他子模块，
但每个子模块都必须重新证明 payload 最小性、只读权限、同步协议和生命周期。

## 3. Linux 实现

### 3.1 Global shared data

`union vkso_shared_page` 占据完整、页对齐的内核页面。timekeeping producer 在 seq
保护下发布 cycle descriptor、七类 global clock base、resolution 和 timezone。
DSO builder 通过 `shared_data.txt` 把该对象加入逐页映射，用户视图只有 `R--`，
并显式去掉执行和写权限。构建器拒绝非整页对象以及与普通可写对象重叠的共享页。

共享 reader 使用同一 global page，因此不需要为每个进程或 time namespace 更新
一份完整 time snapshot。

### 3.2 Per-MM data

`struct vkso_mm_data` 当前包含 ABI version、clock mask、monotonic offset 和 boottime
offset。它由 `arch/x86/kernel/vkso.c` 管理，并在 `mm_context_t` 中记录三个引用：

- `vkso_mm_page`：页面生命周期引用；
- `vkso_mm_kdata`：内核可写别名；
- `vkso_mm_data`：写入 auxv 的用户只读地址。

页面通过 `vm_special_mapping` 暴露为 `[vkso_mm_data]`，权限为
`VM_READ | VM_MAYREAD | VM_DONTDUMP | VM_DONTCOPY`。fault handler 只允许第零页，
`mremap` 被拒绝。内核不把写别名或其他内核指针暴露给用户。

### 3.3 生命周期

```text
new mm / exec
  -> allocate zeroed page
  -> install read-only special mapping
  -> initialize current timens offsets
  -> publish user VA through AT_VKSO_MM_DATA

fork with a new mm
  -> copy payload to a new page
  -> install it at the inherited user VA

thread sharing mm
  -> reuse the same page

timens commit / setns
  -> update offsets through kernel alias
  -> publish clock_mask after the payload

mm destruction / exec replacement
  -> clear context pointers
  -> drop the page reference
```

time namespace offset 不在每次 timekeeping tick 更新。只有进程的 namespace 视图
发生语义变化时才更新 per-MM payload；global clock snapshot 仍由独立 publisher
按正常 timekeeping 频率更新。这避免了“为每个 namespace 执行一次周期性更新”。

### 3.4 Auxv discovery and private wrapper

内核在 x86-64 `ARCH_DLINFO` 中写入 `AT_VKSO_MM_DATA`。用户启动代码读取该值并
检查 MM_data 与 shared-data ABI version，然后调用 `__vkso_bind_context()`。private
wrapper 把 MM_data 指针和 failure callback 写入 DSO 私有状态，并为调用者可提供的
PVClock/Hyper-V 用户别名保留 context 槽位；当前 clocktime 用户启动代码在没有别名时传
`NULL`，共享 provider 随后按受控失败路径回退。共享 text 只通过显式参数读取这些
依赖。

clock ID 在环境边界分类。CPU/alarm/dynamic/非法 ID 直接进入原生 backend；只有
global hres/coarse clock 进入 shared core。若 cycle provider 在共享路径中失败，
context callback 分别把用户环境送到 syscall、把内核环境送到 private timekeeper，
shared core 本身不包含环境专属策略。

## 4. 构建与映射机制增量

clocktime 使用并验证了三项可推广的构建能力：

1. `shared_data`：将整页内核数据作为 `R--/NX` DSO segment 和 graft mapping；
2. `private-wrapper-object`：合入 ET_REL 用户 wrapper、私有数据及其重定位闭包；
3. `reusable_text`：对启动期可能被 ITS 改写到的 thunk 保留原生 RX 页，避免按
   特例扩展 clocktime 导出列表。

这些能力属于通用项目机制。相对地，`struct vkso_mm_data`、auxv 编号、timens hook、
clock mask 和 provider 字段属于 clocktime 的 Linux 实例。若未来希望把 per-MM
通道产品化为任意子模块注册框架，还需要定义 payload 注册、ABI 命名、更新回调、
资源配额和冲突处理；当前实现尚未提供这些通用注册接口。

## 5. 代码量归属

现有 clocktime 报告把与 vDSO 对称比较的运行时机制记为 363 SLOC：C1
MM/context/namespace 映射 207、C2 用户 context 启动 74、K3 shared ABI/publisher
82。这个数字回答的是“clocktime 产品需要维护多少运行时机制”，不能直接改名为
“通用框架代码量”：

- C1/C2 中的 MM 生命周期、auxv discovery 和 private binding 具有可推广性，但仍
  混有 time namespace 与 clocktime context 细节；
- K3 主要是时间共享状态及 publisher，是 clocktime 功能配套机制；
- builder 的 shared-data/private-wrapper 扩展、ITS/reusable-text、测试和实验脚本
  使用独立口径，不与上述 363 SLOC 相加。

因此，在没有新的逐行语义清单前，只能报告“运行时机制 363 SLOC”和其中三类
组成，不能声称 281 或 363 SLOC 都可被其他子模块原样复用。

## 6. 论文中的归属与表述边界

Design 应强调：

- shared machine code 与 shared execution context 是两个不同命题；
- 可修复函数的状态依赖必须显式化；
- global snapshot、per-process context 和 private wrapper 具有不同所有权与生命周期；
- fallback 是安全边界的一部分，不是共享核心中的临时补丁。

Implementation 应说明 Linux 对应关系：

- page-cache grafting 提供共享 RX/RO execution body；
- `shared_data` 提供 kernel-published global snapshot；
- `mm_context_t`、special mapping 和 auxv 提供 per-MM discovery/lifecycle；
- ET_REL private wrapper 提供 environment-specific binding；
- seq、ABI version、只读权限和 fail-closed builder checks 提供一致性约束。

论文不能声称：

- 任意读取内核状态的函数现在都可导出；
- per-MM ABI 已经是任意子模块可注册的通用框架；
- 旧内核 reader 已全部删除；
- 310 SLOC shared clocktime layer 都是纯时间换算算法。

## 7. 实现证据索引

- 数据与共享入口 ABI：`test/test_gettime/linux-5.15.198-vkso/include/vkso/time.h`
- per-MM 映射和生命周期：`test/test_gettime/linux-5.15.198-vkso/arch/x86/kernel/vkso.c`
- MM hooks：`test/test_gettime/linux-5.15.198-vkso/arch/x86/include/asm/mmu_context.h`
- auxv：`test/test_gettime/linux-5.15.198-vkso/arch/x86/include/asm/elf.h`
- namespace commit：`test/test_gettime/linux-5.15.198-vkso/kernel/time/namespace.c`
- shared reader：`test/test_gettime/linux-5.15.198-vkso/kernel/time/vkso_time_core.c`
- private wrapper：`test/test_gettime/vkso-tests/functional/vkso_user_entry.S`
- 用户启动绑定：`test/test_gettime/vkso-tests/functional/vkso_user_wrapper.c`
- builder：`make_dll/build_PIC_so.py`
- shared-data/private-wrapper tests：`make_dll/tests/test_shared_data.py`、
  `make_dll/tests/test_private_wrapper.py`
