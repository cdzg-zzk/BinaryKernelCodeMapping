# LKM 到用户态 Stub DSO 的伪 GOT 重建机制说明

## 1. 背景与动机

本项目的目标，不是把 Linux Kernel Module（LKM）重新编译成一个标准的用户态 PIC 共享库，而是在尽量复用已加载 LKM 二进制内容的前提下，为用户态执行补齐必要的重定位和依赖隔离能力。

这件事之所以困难，主要有三个原因。

第一，LKM 的构建和装载模型与普通用户态 DSO 不同。普通共享库默认由 `ld.so` 处理 `.dynsym`、`.rela.dyn`、`.got` 等动态链接元数据；LKM 则依赖内核模块加载器在装载时处理其静态重定位。换句话说，`.ko` 并不是一个可以直接 `dlopen()` 并运行的用户态共享对象。

第二，LKM 内部常常通过函数指针槽位、全局对象指针和只读常量表组织依赖。这些依赖在内核中由模块加载器解释和修补；如果直接把二进制搬到用户态，调用链会失去正确的地址绑定语义。

第三，LKM 往往深度依赖内核 API，例如内存分配、日志输出、时间服务等。如果不人为设置边界，依赖闭包会继续深入内核子系统，导致依赖爆炸，失去可控的用户态复用范围。

基于这些约束，当前方案采用如下整体策略：

| 区域 | 来源 | 是否共页映射 | 是否允许用户态重新绑定 |
| --- | --- | --- | --- |
| `.text` | 尽量复用 LKM 已加载页 | 是 | 否 |
| `.rodata` | 尽量复用 LKM 已加载页 | 是 | 否 |
| `.data` | 从 `.ko` 复制到用户态 DSO | 否 | 是 |

因此，当前方案的关键设计不是“把所有内核重定位原封不动搬进用户态”，而是把原本依赖内核模块加载器修补的**可写数据槽位**，迁移为由用户态动态链接器 `ld.so` 修补的槽位。本文将这组槽位称为**伪 GOT（Pseudo GOT）**。

一句话概括本项目的核心思想：

> 在尽量复用 LKM 的 `.text` 和 `.rodata` 的同时，把必须由用户态重新绑定的地址槽位收敛到用户态私有 `.data` 中，并通过重建 `.rela.dyn` 让 `ld.so` 完成运行期地址填充。

## 2. 整体设计概览

当前 `make_dll` 工具链的核心输入包括：

- `symbols.txt`：用户指定的入口符号集合。
- `out.krg`：依赖图，用于求入口函数的闭包以及识别目标符号的归属模块。
- `shim.txt`：需要被 shim 接管的符号白名单。
- `.ko` 文件：提供原始节区布局、数据内容和静态重定位信息。

生成的结果是一个用户态 stub DSO，其职责不是承载完整的、重新编译后的模块镜像，而是承载三类关键内容：

1. 足够描述外部绑定关系的动态链接元数据，例如 `.dynsym`、`.dynstr`、`.gnu.hash`、`.dynamic`。
2. 一份从 `.ko` 复制来的、可由 `ld.so` 修改的 `.data` 私有副本。
3. 一组从 `.ko` 可写数据重定位重建而来的 `.rela.dyn` 条目。

其中，真正让“跨态复用”成立的，不是标准 GOT 节本身，而是“`.data` 中由 `.rela.dyn` 驱动的可重定位指针槽位”。这些槽位在语义上扮演 GOT 的角色，所以称之为伪 GOT。

## 3. Shim 层隔离与依赖剪枝

### 3.1 为什么需要 Shim

用户态不能直接调用大部分内核 API。即使个别 API 在语义上可以模拟，直接沿着内核依赖图继续展开，也会把整个内核子系统拖入映射边界，既不安全，也不经济。

因此，项目引入了一个轻量级 `libshim.so`，用来承接少量基础依赖，例如：

- 分配/释放接口
- 日志输出接口
- 时间相关接口
- 其他经过明确白名单允许的用户态替代实现

Shim 的目标不是“重写所有内核行为”，而是把最基础、最容易跨态模拟的依赖收束到一个可控边界内。

### 3.2 当前实现如何使用 Shim 作为边界

在 [build_LKM_so.py](/home/zzk/BinaryKernelCodeMapping/make_dll/build_LKM_so.py) 中，`shim.txt` 会先被解析为一个 shim 符号集合。随后，builder 会从 `.ko` 的数据重定位中提取出命中的 shim 目标，并用它们构造 `shim_reloc_targets`。

`shim.txt` 只定义依赖闭包的替代边界。如果某个同名符号被 `symbols.txt` 显式列为顶层导出，它仍使用真实内核实现；只有作为非顶层依赖出现时才由 Shim 接管。

这组目标同时承担两个作用：

1. **依赖闭包停止边界**
   在通过 `KrgGraph` 遍历依赖闭包时，遇到 shim 目标就不再继续向内核深处展开。

2. **运行期符号接管目标**
   在构造 stub DSO 时，命中 shim 的目标不会被当成当前对象内部已定义符号，而会被建成外部导入符号，并通过 `DT_NEEDED` 强制依赖 `libshim.so`。

因此，Shim 不是简单的“名字替换表”，而是同时承担：

- 依赖图剪枝边界
- 运行期动态链接目标

### 3.3 Shim 在运行期如何接管调用

一旦某个伪 GOT 槽位的目标符号被认定属于 shim，生成的 DSO 就会：

- 在 `.dynsym` 中为该符号建立一个未定义导入项。
- 在 `.dynamic` 中加入 `DT_NEEDED: libshim.so`。
- 在 `.rela.dyn` 中让对应的数据槽位引用该导入符号。

这样，当 `ld.so` 加载 stub DSO 时，就会从 `libshim.so` 中解析出对应实现，并把实际地址写回 `.data` 中的伪 GOT 槽位。后续 LKM 代码执行间接调用时，跳转目标就自然落入 shim，而不是内核原始 API。

### 3.4 Retpoline thunk 的内置替换

`__x86_indirect_thunk_*` 是特殊的 shim。内核函数中的调用通常已经编码为固定的 `call rel32`，没有可供动态链接器改写的 GOT/PLT 重定位，因此不能只把它声明成 `libshim.so` 导入。

当这类符号出现在 `shim.txt` 并进入依赖闭包时，`build_PIC_so.py` 会在原 thunk 相对虚拟地址生成内置机器码：

```asm
__x86_indirect_thunk_rax:
    jmp *%rax
```

外层 `call thunk` 已经保存了真实返回地址，所以 thunk 使用尾跳转，而不是再增加一层 `call/ret`。构造器同时处理 `__x86_indirect_thunk_array` 到 RAX 的别名，并在同一合成页中把需要的 `__x86_return_thunk` 生成为 `ret`。

合成页会在 `resolved_symbol_addresses.txt` 中标记为 `builtin_thunk,synthetic`。页面替换管理器会保留该文件页，只替换真实 kernel/LKM 页。这样既维持原来的 `rel32` 地址关系，也不需要因为 retpoline thunk 引入 `DT_NEEDED: libshim.so`。

当前支持 RAX、RCX、RDX、RBX、RBP、RSI、RDI 和 R8-R15。RSP thunk 不启用，因为进入 call thunk 后 RSP 已经变化，不能使用相同的直接跳转实现。

## 4. `.ko` 到 stub DSO 的构建流程

当前实现的构建流程可以概括为以下八步。

### 4.1 解析入口符号与依赖闭包

`symbols.txt` 提供待导出的根符号。`out.krg` 提供跨模块、跨函数的闭包解析信息。builder 先根据这些信息确定：

- 哪些符号属于当前 LKM 本体。
- 哪些符号属于 shim。
- 哪些符号需要作为内部定义符号保留下来。

### 4.2 解析 `.ko` 并恢复 core layout

[build_PIC_so.py](/home/zzk/BinaryKernelCodeMapping/make_dll/build_PIC_so.py) 中的 `KoFile.compute_core_layout()` 会把 `.ko` 的 core alloc 区域拆分为：

- `text_secs`
- `ro_secs`
- `data_secs`

其中：

- `text_secs` 是可执行节区。
- `ro_secs` 是只读、非执行节区。
- `data_secs` 是可写节区。

这是后续“哪些区域共页映射，哪些区域复制并重定位”的基础。

### 4.3 仅从可写数据段收集 `R_X86_64_64` 重定位

这是当前伪 GOT 机制最重要的约束之一。

`compute_core_layout()` 只收集 `data_secs` 对应的重定位，也就是：

- 重定位必须挂在可写数据节上。
- 当前实现不收集 `.rela.rodata`。

收集到的结果被编码成 `KoDataReloc`，其核心信息包括：

- 槽位偏移 `offset`
- 目标符号名 `symbol_name`
- 目标符号是否未定义 `is_undef`
- 原始 `addend`
- 重定位类型 `r_type`

### 4.4 复制 `.data` 镜像

builder 会把 `.ko` 中的可写数据镜像复制出来，作为新 DSO 的 `.data` 内容。注意这里复制的是：

- `.ko` 中的静态初值
- 以及数据布局本身

而不是最终运行期绑定好的用户态地址。

换句话说，这一步得到的是“待修补的数据槽位区”，不是最终 GOT 值。

### 4.5 为每个数据重定位建立目标符号语义

对于每一条数据重定位，builder 会确定它的目标属于哪一类：

- shim 导入符号
- 当前 LKM/当前 stub DSO 内部定义符号
- kernel 闭包中需要保留的其它对象或函数

这一步的结果会被编码成 `ResolvedSymbol`，并进入新 DSO 的 `.dynsym`。

### 4.6 把原始数据重定位重建为 `.rela.dyn`

接下来，每个 `KoDataReloc` 会被转换成一个新的 `DataRelocation`，写入生成 DSO 的 `.rela.dyn`。映射关系如下：

| `.ko` 中信息 | 新 DSO 中对应物 |
| --- | --- |
| `.data` 槽位偏移 | 新 DSO `.data` 内偏移 |
| 目标符号 | `.dynsym` 条目 |
| `R_X86_64_64` | `.rela.dyn` 中的 `R_X86_64_64` |
| `addend` | `.rela.dyn` addend |

生成 `.rela.dyn` 时，真正写入的是：

- `r_offset = dso_.data_base + slot_offset`
- `r_info = dynsym_index | R_X86_64_64`
- `r_addend = original_addend`

### 4.7 生成动态链接元数据

为了让 `ld.so` 能理解这些槽位，builder 还会生成：

- `.dynstr`
- `.dynsym`
- `.gnu.hash`
- `.dynamic`
- `DT_RELA`
- `DT_RELASZ`
- `DT_RELAENT`
- 必要时的 `DT_NEEDED: libshim.so`

这些内容共同定义了：

- 需要修补哪些槽位
- 每个槽位引用哪个符号
- 对哪些外部库有运行期依赖

### 4.8 运行期由 `ld.so` 填充槽位

当 stub DSO 被加载时，真正执行地址回填的是 `ld.so`，而不是内核模块加载器。

最终，stub DSO 中的 `.data` 槽位会被写成：

- shim 函数地址
- 当前 stub DSO 内部定义符号地址
- 其它被允许保留的动态符号地址

此时，这些槽位在语义上就等价于 GOT 项。LKM 代码中的间接调用和间接对象访问，就可以通过这些槽位在用户态继续成立。

## 5. 伪 GOT 的原理

### 5.1 当前项目中的“伪 GOT”是什么

这里的伪 GOT 不是 ELF ABI 中固定命名的 `.got` 节，而是一种工程语义：

- 它位于新 DSO 的 `.data`
- 它由一组指针槽位组成
- 每个槽位在运行期通过 `.rela.dyn` 被 `ld.so` 修补
- 代码通过读取这些槽位，再完成间接调用或对象访问

因此，“伪 GOT”强调的是**行为角色**，不是节名。

### 5.2 为什么输入必须来自可写数据重定位

当前方案的本质要求是：

- 槽位必须属于用户态私有内存
- 槽位必须允许 `ld.so` 在加载时写入真实地址

这与 `.data` 的语义完全一致，却与共页映射的 `.text/.rodata` 相冲突。因此当前实现只从 `.ko` 的可写数据段重定位中构造伪 GOT。

### 5.3 伪 GOT 可以指向哪些对象

当前实现支持两类典型目标。

#### 指向 `libshim.so`

如果目标符号命中 shim 白名单：

- 它会被建成未定义 dynsym 导入项。
- 新 DSO 会带上 `DT_NEEDED: libshim.so`。
- `ld.so` 会从 `libshim.so` 中解析它。

#### 指向 LKM 本地符号

如果目标符号属于当前 LKM 本体或被允许保留在闭包中的内部定义符号：

- 它会被建成当前 stub DSO 的已定义 dynsym 符号。
- `ld.so` 在处理 `.rela.dyn` 时，会把当前对象内该符号的实际地址写回槽位。

因此，伪 GOT 槽位本身并不关心目标来自 shim 还是来自当前对象；它只要求：

- 槽位在 `.data`
- 槽位有一条可被 `ld.so` 解释的动态重定位

## 6. 为什么伪 GOT 不能放进 `.rodata`

这一点必须区分“理论上是否存在 rodata 重定位”和“当前方案下是否适合作为伪 GOT”两个层面。

### 6.1 `const` table 在 `.ko` 中会发生什么

如果把函数指针表写成：

```c
static const struct table_entry table[] = {
    { .bias = 0x10, .func = foo },
    { .bias = 0x20, .func = bar },
};
```

那么这个 table 会落入 `.rodata`。对其中函数指针字段，`.ko` 会产生 `.rela.rodata` 条目。也就是说：

- `.ko` 文件里保存的是“静态内容 + rodata 重定位信息”
- 内核模块加载器装载模块时，会先处理这些 `.rela.rodata`
- 模块真正进入内存后，这些 table 槽位中保存的已经是**内核虚拟地址**

### 6.2 当前用户态方案如何使用 `.rodata`

当前方案的设计目标是尽量直接复用 LKM 已加载页。因此：

- `.text` 倾向于共页映射
- `.rodata` 也倾向于共页映射

这意味着，用户态执行时看到的 `.rodata`，不是 `.ko` 文件中的未解析内容，而是**LKM 已加载并完成内核侧重定位后的只读页内容**。

### 6.3 为什么这与伪 GOT 冲突

伪 GOT 的基本要求是：

- 槽位应由用户态 `ld.so` 负责回填
- 槽位必须属于用户态私有、可控、可写的区域

而共页映射的 `.rodata` 恰好相反：

- 它已经被内核模块加载器修补过
- 其中保存的是内核地址，而不是用户态应重新绑定的目标地址
- 它语义上属于共享只读页，不适合作为用户态再次绑定符号的承载区

因此，即使理论上某些 ELF 也可能存在 rodata 上的重定位，在本项目当前方案下，`.rodata` 也不应该承担伪 GOT 槽位职责。

### 6.4 当前实现上的直接限制

除了语义冲突以外，当前代码实现本身也明确把 `.rodata` 排除在伪 GOT 管线之外：

- `compute_core_layout()` 只收集 `data_secs` 的重定位
- `.rela.rodata` 不会进入 `layout.data_relocs`
- 后续 builder 只把这些 `data_relocs` 重建为 `.rela.dyn`

因此，对于当前工程实现：

> 所有希望被用户态 `ld.so` 接管并回填的函数指针或对象指针槽位，都必须位于可写数据段，而不能位于最终共页映射的 `.rodata`。

## 7. `lkm_locate.c` 中 table 问题的根因

[lkm_locate.c](/home/zzk/BinaryKernelCodeMapping/test/test_lkm_locate/lkm_locate.c) 中的 `lkm_locate_config_table` 是一个专门用于说明“数组式函数表访问”问题的最小案例。

问题并不在于 table 语义本身，而在于访问方式和目标架构寻址能力共同作用后，编译器容易生成不适合当前工程的 `.rela.text` 绝对地址访问。

### 7.1 原始访问形式的问题

如果直接写：

```c
entry = &table[index];
return entry->func(selector + entry->bias);
```

编译器往往会把“全局符号基址 + 动态索引 + 字段偏移”压缩成一条或少量几条寻址指令，并在 `.rela.text` 中留下类似：

- `R_X86_64_32S .data + off`
- `R_X86_64_32S .rodata + off`

这意味着：

- 代码段中直接编码了 table 的绝对基址信息
- 访问已经不再是“先通过 RIP 相对拿到基址，再通过索引访问”
- 这与当前工程希望避免 `.rela.text` 绝对地址重定位的目标冲突

### 7.2 根因：x86_64 的寻址表达限制

该问题的根本原因在于 x86_64 的寻址形式有限。

在单条内存操作数中，编译器无法自然表达“先 RIP 相对获取某个全局数组的基址，再在同一条指令中继续做动态变址索引”的理想形式。于是，编译器会倾向于把访问折叠成：

- 绝对基址
- 再叠加变址寄存器

这不是简单的编译器错误，而是：

- 目标架构寻址能力
- 优化器的代码生成策略

共同作用后的结果。

## 8. `lkm_locate.c` 中的工程修复方案

为了避免上述问题，当前实现采用了一个非常明确的工程策略：

1. 不让编译器自己决定“如何同时拿全局符号基址和索引”。
2. 强制把访问拆成两步。

### 8.1 当前实现

[lkm_locate.c](/home/zzk/BinaryKernelCodeMapping/test/test_lkm_locate/lkm_locate.c#L131) 到 [lkm_locate.c](/home/zzk/BinaryKernelCodeMapping/test/test_lkm_locate/lkm_locate.c#L146) 采用了如下写法：

```c
asm volatile(
    "lea lkm_locate_config_table(%%rip), %0"
    : "=r"(base)
);

entry = &base[index];
return entry->func(selector + entry->bias);
```

### 8.2 这个写法为什么有效

这段代码强制生成了两个阶段。

第一阶段：

- 先显式用 `lea symbol(%rip), reg` 取得 table 基址
- 这一步会在 `.rela.text` 中留下 `R_X86_64_PC32`，而不是 `R_X86_64_32S` 的绝对地址字段访问

第二阶段：

- 再在寄存器基址上做索引和成员访问
- 也就是先得到 `base`，再通过 `entry = &base[index]` 访问表项

这样就避免了编译器把“全局符号 + 索引 + 字段偏移”重新折叠成绝对地址寻址。

### 8.3 这个案例说明了什么

这个案例说明：

- 单纯把 table 从 `.rodata` 挪到 `.data` 并不够
- 如果访问写法不受控，编译器仍然可能在 `.rela.text` 中生成不希望出现的绝对地址重定位
- 对于数组式函数表，除了保证槽位位于可写数据段，还必须控制取基址方式

## 9. 为什么当前工程更推荐结构体，而不是数组式伪 GOT

这里的结论需要限定在“当前工程实现”这一前提下理解。

### 9.1 结构体字段是更稳定的伪 GOT 载体

像 `lkm_locate_ctx_default` 这种结构体中的显式指针字段，具备几个优势：

- 每个字段都是语义清晰的独立槽位
- 更容易稳定地产生 `.data` 上的 `R_X86_64_64`
- 更容易被 builder 收集并重建为 `.rela.dyn`
- 更容易在调试和分析时对应到具体功能含义

这正是当前 builder 所偏好的输入形态。

### 9.2 数组不是绝对不能用，但属于特殊场景

数组式函数表并不是语义上绝对错误，但在当前方案里会面临两个额外风险：

1. 如果使用 `const`，容易落入 `.rodata`，从而脱离当前伪 GOT 管线。
2. 如果直接以 `table[index].field` 访问，容易触发 `.rela.text` 绝对地址优化。

因此，对当前工程来说，更准确的结论是：

- **普通伪 GOT 槽位，优先使用 `.data` 中的结构体字段表示。**
- **数组式函数表只适合特殊场景，并且必须显式控制基址获取方式。**

### 9.3 `lkm_locate.c` 中两个案例的角色

[lkm_locate.c](/home/zzk/BinaryKernelCodeMapping/test/test_lkm_locate/lkm_locate.c) 中实际上提供了两类示例：

- `lkm_locate_ctx_default`
  这是推荐模式。它展示了如何通过结构体字段稳定构造伪 GOT 输入。

- `lkm_locate_config_table`
  这是特殊模式。它展示了“数组式函数表 + 动态索引”场景下，如何通过显式 `lea` 避免 `.rela.text` 绝对地址问题。

因此，文中的“结构体优先”不是语言层面的硬性规定，而是当前工程下最稳妥、最符合 builder 机制的设计建议。

## 10. 总结

当前项目中的伪 GOT 机制，可以概括为以下几个工程事实：

1. 伪 GOT 的本体不是标准 `.got` 节，而是新 DSO `.data` 中的一组可重定位指针槽位。
2. 这些槽位来自 `.ko` 的可写数据重定位，而不是来自 `.rodata`。
3. shim 既是依赖剪枝边界，也是运行期的动态链接目标。
4. `.text` 和 `.rodata` 的目标是尽量共页映射，而 `.data` 的目标是由用户态私有持有并允许 `ld.so` 改写。
5. 因为共页映射的 `.rodata` 会携带内核加载器已经修补过的值，所以它不能承担当前方案中的伪 GOT 槽位职责。
6. 对于数组式函数表，除了保证其位于可写数据段，还必须显式控制取基址方式，避免 x86_64 编译器在 `.rela.text` 中生成绝对地址访问。

在这一约束下，当前工程中最推荐的模式仍然是：

- 用结构体中的显式指针字段构造伪 GOT 槽位
- 用 `.rela.data -> .rela.dyn` 的方式把这些槽位交给 `ld.so` 回填
- 用 Shim 保持依赖边界可控

这也是当前 `build_LKM_so.py`、`build_PIC_so.py` 与 `lkm_locate.c` 共同体现出的设计收敛点。
