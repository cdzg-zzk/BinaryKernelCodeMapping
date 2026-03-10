# 变更记录

本文档按阶段记录 `test_zlib` 目录下的重要修改，重点说明：

- 修改了哪些文件
- 改了哪些符号或数据结构
- 具体做了什么代码调整
- 为什么要这样改

本文档不追求逐行 diff，而是面向开发者说明每一步修改的意图和效果。

---

## Change Log 1

### 本次目标
将内核中的 zlib deflate 相关源码引入到当前测试目录，建立一个可继续裁剪和改造的本地副本。

### 修改文件
- `zlib_deflate/` 下的初始源码文件

### 符号变化
- 无

### 代码调整
- 完成内核 zlib deflate 相关源码的初始导入
- 暂不做功能性修改，以保留上游实现作为基线版本

### 修改原因
这一步的目的不是优化或适配用户态映射，而是先把需要研究和改造的代码完整落地到本地目录。只有先保留一份接近原始实现的版本，后续的符号隔离、依赖裁剪、伪 GOT 改造和用户态映射实验才有清晰的参照基线。

---

## Change Log 2

### 本次目标
把提取出来的 deflate 实现包装成一个可独立构建、可独立装载的内核模块，并隔离全局符号命名空间。

### 修改文件
- `zlib_deflate/deflate.c`
- `zlib_deflate/deftree.c`
- `zlib_deflate/defutil.h`
- `zlib_deflate/zlib.h`
- `zlib_deflate/zutil.h`
- `zlib_deflate/deflate_syms.c`
- `zlib_deflate/Makefile`

### 符号变化
以下全局符号统一增加 `mz_` 前缀，以避免与内核原生 zlib 符号冲突：

- `zlib_deflate_workspacesize -> mz_zlib_deflate_workspacesize`
- `zlib_deflate_dfltcc_enabled -> mz_zlib_deflate_dfltcc_enabled`
- `zlib_deflate -> mz_zlib_deflate`
- `zlib_deflateInit2 -> mz_zlib_deflateInit2`
- `zlib_deflateEnd -> mz_zlib_deflateEnd`
- `zlib_deflateReset -> mz_zlib_deflateReset`
- `zlib_tr_init -> mz_zlib_tr_init`
- `zlib_tr_tally -> mz_zlib_tr_tally`
- `zlib_tr_flush_block -> mz_zlib_tr_flush_block`
- `zlib_tr_align -> mz_zlib_tr_align`
- `zlib_tr_stored_block -> mz_zlib_tr_stored_block`
- `zlib_tr_stored_type_only -> mz_zlib_tr_stored_type_only`

### 代码调整
- 为导出的 deflate 相关符号统一增加模块私有前缀
- 在 `deflate_syms.c` 中补充模块入口/出口和导出包装逻辑
- 调整头文件引用路径，使其使用本目录下的局部头文件
- 在 `Makefile` 中加入 out-of-tree LKM 构建规则

### 修改原因
原始 deflate 代码默认工作在内核 zlib 体系内部，直接编译为独立模块时会遇到两个问题：

1. 全局符号容易与内核已有符号冲突。
2. 缺少独立模块所需的导出与构建组织方式。

因此，这一步的重点是把源码从“内核内部实现片段”变成“可单独装载和分析的模块化实现”。

---

## Change Log 3

### 本次目标
剥离 deflate 模块对内核现成 bit reverse 实现和部分平台钩子的直接依赖，使该模块更适合被单独裁剪和复用。

### 修改文件
- `zlib_deflate/deflate.c`
- `zlib_deflate/deftree.c`
- `zlib_deflate/bitrev.h`

### 符号变化
- 无新的对外符号变化

### 代码调整
- 将 `deflate.c` 中的 DFLTCC 相关 hook 路径整理为本地 no-op 宏形式
- 将 `deftree.c` 中的 `<linux/bitrev.h>` 替换为本地 `bitrev.h`
- 将 `bitrev.h` 中的 `byte_rev_table` 改为模块本地 `static const` 定义

### 修改原因
这一步的核心是减少对外部内核环境的硬依赖。

如果继续直接依赖内核提供的 `byte_rev_table` 或特定平台路径，后续在做模块隔离、二进制映射和用户态复用时，闭包范围会扩大，定位问题也会更加困难。因此需要把这类基础只读数据和辅助逻辑本地化，先把模块变得“自洽”。

---

## Change Log 4

### 本次目标
关闭与本实验无关、且会污染闭包分析结果的内核编译期插桩与消毒器选项。

### 修改文件
- `zlib_deflate/Makefile`

### 符号变化
- 无

### 代码调整
- 添加 `UBSAN_SANITIZE := n`
- 添加 `ccflags-remove-y`
- 添加对应对象文件的 `CFLAGS_REMOVE_*.o`
- 去除以下由全局内核构建配置自动带入的编译选项：
  - `-fsanitize=bounds`
  - `-fsanitize=shift`
  - `-fsanitize=bool`
  - `-fsanitize=enum`
  - `-fstack-protector-strong`

### 修改原因
这些插桩和保护机制虽然对正常内核构建有价值，但会给当前实验带来两个直接问题：

1. 引入额外的 UBSAN / stack protector 依赖，使闭包分析结果偏离真正的 deflate 核心逻辑。
2. 在二进制映射与伪 GOT 研究中制造额外的间接依赖与噪声，干扰对真实问题点的判断。

因此，这一步的目标是让模块更接近“无额外工具链插桩污染”的实验对象。

---

## Change Log 5

### 本次目标
解决 `configuration_table[s->level].func` 这一类“函数指针表 + 动态索引”访问在 x86_64 下触发 `.rela.text` 绝对地址重定位的问题，使 `mz_zlib_deflate` 这条调用链更适合映射到用户态执行。

### 修改文件
- `zlib_deflate/deflate.c`

### 涉及位置
主要修改集中在以下三处：

- `configuration_table` 的定义
- `mz_zlib_deflate()` 中对 `configuration_table[s->level].func` 的访问
- `lm_init()` 中对 `configuration_table[s->level].max_lazy/good_length/nice_length/max_chain` 的访问

### 符号变化
- 无新的对外导出符号变化
- 未改动 `mz_zlib_deflate`、`mz_zlib_tr_align` 等函数名

### 代码调整
本次修改采用了与 `test_lkm_locate/lkm_locate.c` 相同的处理思路，但保持了尽量小的改动范围。

#### 1. 将 `configuration_table` 从只读常量表改为可写数据表
原始形式：

```c
static const config configuration_table[10] = { ... };
```

修改后：

```c
static config configuration_table[10] __used = { ... };
```

这样做的直接效果是：

- 表本体不再落入 `.rodata`
- 函数指针槽位不再对应 `.rela.rodata`
- 更符合当前项目“伪 GOT 槽位位于可写数据段”的整体设计

`__used` 的目的是避免编译器在优化过程中把该表过度折叠或删去，从而影响后续对访问路径和重定位形态的控制。

#### 2. 新增显式取基址 helper：`configuration_table_base()`
新增了一个很小的 helper：

```c
static __always_inline config *configuration_table_base(void)
{
    config *base;
    asm volatile(
        "lea configuration_table(%%rip), %0"
        : "=r"(base)
    );
    return base;
}
```

它的作用不是改变功能语义，而是强制编译器先生成一条独立的 RIP-relative 取基址指令。

这是本次修改最关键的工程点。

在 x86_64 架构下，编译器很容易把：

```c
configuration_table[s->level].func
```

折叠成“绝对基址 + 动态变址”的访问形式，最终在 `.rela.text` 中留下对 `.rodata` 或 `.data` 的 `R_X86_64_32S` 绝对地址重定位。这类重定位正是当前用户态映射方案要尽量避免的内容。

通过显式插入：

```asm
lea configuration_table(%rip), reg
```

可以把访问过程强制拆成两步：

1. 先独立获得表基址
2. 再在寄存器上做索引和字段访问

这样更容易得到我们需要的代码形态，而不是被编译器折叠回 `.rela.text` 的绝对地址访问。

#### 3. 在 `mz_zlib_deflate()` 中改为先取表项，再访问 `func`
原始代码：

```c
(*(configuration_table[s->level].func))(s, flush);
```

修改后：

```c
cfg = &configuration_table_base()[s->level];
(*(cfg->func))(s, flush);
```

逻辑没有变化，仍然是按 `s->level` 选择压缩策略函数；变化只在于访问方式被拆成了“先取基址，再索引表项”。

#### 4. 在 `lm_init()` 中统一改造同一张表的其它字段访问
原始代码：

```c
s->max_lazy_match   = configuration_table[s->level].max_lazy;
s->good_match       = configuration_table[s->level].good_length;
s->nice_match       = configuration_table[s->level].nice_length;
s->max_chain_length = configuration_table[s->level].max_chain;
```

修改后：

```c
cfg = &configuration_table_base()[s->level];
s->max_lazy_match   = cfg->max_lazy;
s->good_match       = cfg->good_length;
s->nice_match       = cfg->nice_length;
s->max_chain_length = cfg->max_chain;
```

这样做的目的是保持同一张表的访问方式一致，避免 `func` 走一套取基址逻辑，而其它字段仍然触发编译器的绝对地址折叠。

### 修改原因
这次修改不是普通的代码重构，而是一次面向“用户态映射执行”目标的二进制可重定位性修复。

原始问题点是：

```c
(*(configuration_table[s->level].func))(s, flush);
```

其中 `configuration_table` 是函数指针表。对于当前项目来说，这种访问形式有两个风险：

1. 如果表位于 `.rodata`，其函数指针槽位会变成 `.rela.rodata`，不适合当前“`.rela.data -> .rela.dyn`”的伪 GOT 方案。
2. 即便把表移到 `.data`，如果仍直接写成 `table[index].field`，编译器也可能在 `.rela.text` 中生成绝对地址访问，导致代码段仍然依赖不希望出现的绝对地址重定位。

本次修改的目标，就是同时解决这两个问题：

- 让表进入可写数据段
- 让访问方式变成“先 RIP-relative 取基址，再索引”

### 修改后的效果
针对 `mz_zlib_deflate` 这条调用链，本次修改已经达到了预期效果：

- 原来由 `configuration_table[s->level].func` 引出的 `.rodata` 绝对地址问题被消除
- `checker` 不再把该调用点报为 `HARD FAIL`
- 间接调用来源现在可以追踪到 `.data` 中的表基址加载，再到表项函数指针读取

从当前实验结果看，这说明“把函数指针表改造成可写数据表，并显式控制基址获取方式”的思路是正确的，也为后续继续处理其它存在类似问题的函数提供了可复用的方法。

---
