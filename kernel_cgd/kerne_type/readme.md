# vkso_gen_types

`vkso_gen_types.py` 是一个面向“内核函数用户态映射”场景的小工具。它的目标不是重建函数内部全部实现细节，而是从内核或已加载模块的 BTF 中提取**调用某个 API 所需的最小类型集合**，并自动补出这些 API 的**函数声明**，生成一个可供用户态直接包含的头文件。

这份文档按现在脚本的真实行为来写，重点说明背景、设计动机、实现思路、使用方法，以及和 LKM BTF 相关的注意事项。

## 背景

在“把内核函数映射到用户态执行”的实验里，最容易遇到的第一个问题不是函数地址，而是**类型定义**。

以一个内核导出的 API 为例，用户态如果想像调用动态库一样调用它，至少要满足两件事：

1. 知道函数原型。
2. 知道函数原型中涉及的数据类型布局。

如果直接把整套内核头文件搬到用户态，问题会很多：

- 依赖太大，移植成本高。
- 很多实现细节与用户态无关。
- 宏、内联函数、条件编译会引入大量无关噪音。
- 容易把“为了调用 API 需要的 ABI 信息”和“函数内部实现细节”混在一起。

这个工具的出发点正是把这两件事分开：  
**只为调用 API 提供最小必要的类型和函数声明，不试图复刻整个实现环境。**

## 动机

这个项目现在明确服务于“黑盒 API 调用”而不是“实现级源码还原”。

也就是说，用户态把目标函数当成一个已经映射好的动态库符号来使用时，真正关心的是：

- 这个函数怎么声明。
- 这个函数的入参和返回值里用到了哪些类型。

而通常**不关心**：

- 函数体内部的局部变量类型。
- 内部状态机的全部实现结构。
- 只在函数内部出现、但不影响调用 ABI 的辅助类型。
- 函数执行中访问到的所有只读表、内部枚举、内部函数指针类型。

例如，对 `mz_zlib_deflate(z_streamp strm, int flush)` 这种 API 来说，用户态需要的是：

- `z_streamp`
- `z_stream`
- `z_stream_s`
- `internal_state`
- 函数声明本身

而不是 `deflate_state`、`config`、`block_state` 之类内部实现类型。

因此，本工具当前推荐的输入方式是：

- `--funcs`
- `--funcs-file symbols.txt`

其中 `symbols.txt` 表示“希望暴露给用户态调用的 API 函数列表”，而不是实现调用链上的全部函数集合。

## 实现思路与原理

### 1. 输入是什么

脚本支持两种函数输入方式：

- `--funcs name1,name2,...`
- `--funcs-file <path>`

`--funcs-file` 当前只接受两类内容：

- 纯文本函数名列表，每行一个符号，例如 `symbols.txt`
- SAFE/krg 生成的二进制 `.krg`

它**不再接受** `resolved_symbol_addresses.txt` 作为 `--funcs-file` 输入。原因很简单：那类文件更接近“实现闭包分析输入”，不适合黑盒 API 头生成。

### 2. BTF 从哪里来

脚本优先使用：

- `/sys/kernel/btf/vmlinux`

如果目标函数来自模块，脚本会自动在已加载模块的 BTF 中查找：

- `/sys/kernel/btf/<module>`

也可以手工通过 `--module` 或 `--modules` 指定模块来源，但在多数情况下不需要，因为脚本会自动在已加载模块里搜索。

### 3. 如何决定导出哪些类型

脚本的核心策略是：

1. 在 BTF 中找到目标函数对应的 `FUNC`。
2. 取它关联的 `FUNC_PROTO`。
3. 以该原型为根，递归收集：
   - 返回值类型
   - 参数类型
   - 这些类型继续引用到的 `typedef / ptr / array / struct / union / enum`

这一点非常重要：

> 脚本导出的不是“函数实现过程中出现过的全部类型”，而是“函数原型为调用 ABI 所要求的类型闭包”。

这正是当前黑盒 API 模式想要的行为。

### 4. 为什么模块 BTF 需要特殊处理

模块 BTF 往往不是完整独立的一份类型表，而是 **split BTF**。  
这意味着模块中的很多 type id 会引用 `vmlinux` 里的基础类型。

因此脚本实现里专门做了两件事：

- 读取模块 BTF 时，会带上 base BTF 重试。
- 如果模块类型递归时命中了“本模块里没有、但 base vmlinux 里有”的 type id，会自动回落到 `vmlinux`。

这一步如果不做，常见现象就是：

- 能找到模块函数；
- 但最后导出的类型非常少，甚至几乎空白。

### 5. 为什么输出里既有类型也有函数声明

仅有类型定义还不够。  
如果用户态真的要把这些 API 当动态库接口调用，还需要函数声明本身。

因此当前脚本生成的头文件包含两部分：

- API 所需的最小类型定义
- API 函数声明

例如：

```c
typedef struct z_stream_s z_stream;
typedef z_stream *z_streamp;
int mz_zlib_deflate(z_streamp strm, int flush);
```

这就是“黑盒 API 头”的最小闭包。

## 使用方法

### 最推荐的用法：传入 API 列表

假设 API 列表文件是：

- `/home/zzk/BinaryKernelCodeMapping/test/test_zlib/symbols.txt`

生成头文件：

```bash
python3 /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/vkso_gen_types.py \
  --funcs-file /home/zzk/BinaryKernelCodeMapping/test/test_zlib/symbols.txt \
  --out /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/deflate_types.h
```

如果只想直接看 stdout：

```bash
python3 /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/vkso_gen_types.py \
  --funcs-file /home/zzk/BinaryKernelCodeMapping/test/test_zlib/symbols.txt
```

### 直接在命令行写函数名

```bash
python3 /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/vkso_gen_types.py \
  --funcs mz_zlib_deflate \
  --out /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/deflate_types.h
```

### 同时导出多个 API

```bash
python3 /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/vkso_gen_types.py \
  --funcs mz_zlib_deflate,mz_zlib_deflateEnd,mz_zlib_deflateReset \
  --out /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/deflate_types.h
```

### 如果函数来自已加载模块

通常无需额外参数，只要模块已经加载且 `/sys/kernel/btf/<module>` 存在，脚本会自动找到它。

如果需要显式指定，也可以：

```bash
python3 /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/vkso_gen_types.py \
  --funcs mz_zlib_deflate \
  --module mz_zlib_deflate \
  --out /home/zzk/BinaryKernelCodeMapping/kernel_cgd/kerne_type/deflate_types.h
```

## 输出结果应该如何理解

以 `mz_zlib_deflate` 为例，生成的头文件通常只会包含：

- `Byte`
- `uLong`
- `struct z_stream_s`
- `struct internal_state`
- `z_stream`
- `z_streamp`
- `int mz_zlib_deflate(z_streamp strm, int flush);`

这并不表示脚本“漏掉了实现里用到的内部类型”，而是因为这些内部类型并不属于黑盒 API 调用所必需的 ABI 部分。

如果你确实想做“实现级”分析，例如想把 `deflate_state`、`config`、`block_state` 都拉出来，那已经不是这个工具当前的主目标了。

## 需要特别注意的问题

### 1. 这个工具不是“函数实现还原器”

它不会尝试恢复：

- 全调用链
- 全局只读表的完整类型
- 函数体内局部变量所用的全部类型
- 内部状态机的全部定义

它只服务于**黑盒 API 调用所需的最小头文件生成**。

### 2. `resolved_symbol_addresses.txt` 不再作为输入

过去实现分析阶段曾经尝试过把 `resolved_symbol_addresses.txt` 作为输入，这适合做闭包调试，但不适合黑盒 API 头生成。

因此现在如果把这类文件传给 `--funcs-file`，脚本会直接报错并提示改用纯函数名列表。

### 3. 同名函数可能出现在多个 BTF 源

如果某个函数在 `vmlinux` 和某个模块里同名，脚本会认为来源存在歧义并报错，而不是擅自选择。

这是为了避免把错误的 ABI 头导出来。

### 4. 指针类型可以使用不完整类型

例如：

```c
struct internal_state *state;
```

这里 `struct internal_state` 可以在后面再完整定义，因为它在当前上下文里只是一个指针。

但是如果结构体成员是按值嵌入：

```c
struct internal_state state;
```

那就必须在使用前先看到完整定义。

因此，生成头文件里如果出现“先在结构体里用到 `struct X *`，后面再定义 `struct X`”，这是合法且符合 C 语言规则的。

### 5. 只导出一个 API 不代表能完成完整功能流程

例如某个 `.so` 只导出了 `mz_zlib_deflate`，但没有导出 `mz_zlib_deflateInit2`、`mz_zlib_deflateReset`、`mz_zlib_deflateEnd`。

这时用户态虽然可以：

- 成功加载符号
- 成功调用函数
- 验证它不会段错误

但未必能完成一个完整的压缩生命周期，因为初始化入口本身并没有导出。

这是“导出了黑盒 API 的一部分”和“导出了完整功能族 API”之间的区别。

## 给 LKM 加入 BTF section：建议与注意事项

这一部分很关键，因为模块 BTF 如果处理不对，会直接影响两件事：

- `insmod` 是否成功
- `bpftool` / 本脚本是否能正确读取模块 BTF

### 最稳的方式：让 Kbuild 自动生成模块 BTF

如果条件允许，最推荐的做法不是手工给 `.ko` 打 BTF，而是直接使用与当前运行内核匹配的 Kbuild 环境编译模块，并开启相应 BTF 配置。

这样通常由内核构建流程自动处理：

- `.BTF`
- 模块与 `vmlinux` 的 base 关系
- 需要时的模块 split BTF 元数据

这是最不容易出错的方案。

### 手工对 `.ko` 加 BTF 时要注意什么

如果你是对现有 `.ko` 手工处理，常见做法是：

```bash
pahole -J your_module.ko
```

但这里有几个容易踩坑的点。

#### 1. `.ko` 上有 `.BTF`，不等于 `bpftool` 一定能直接读

你可能会看到：

```bash
readelf -S your_module.ko | grep BTF
```

确认模块里已经有 `.BTF` section。

但这并不自动意味着下面这条一定成功：

```bash
bpftool btf dump file your_module.ko format c
```

原因是模块 BTF 很可能是 split BTF，它依赖 base `vmlinux`。

更稳的读取方式通常是：

```bash
bpftool btf dump file your_module.ko --base-btf /sys/kernel/btf/vmlinux format c
```

或者更推荐：

```bash
modprobe your_module
bpftool btf dump file /sys/kernel/btf/your_module format c
```

后者一般比直接读 `.ko` 更稳定。

#### 2. 模块 BTF 和当前内核必须匹配

模块 BTF 中引用的 base 类型必须和当前运行内核的 `vmlinux` BTF 保持一致。

如果模块不是针对当前运行内核编译的，就可能出现：

- `insmod` 失败
- `bpftool` 读取失败
- 模块加载了，但 BTF 无法正确关联

因此在处理模块 BTF 时，务必保证：

- 模块对应的源码、配置、内核版本与当前运行内核一致
- `pahole` 使用的调试信息和当前 `vmlinux` 匹配

#### 3. split BTF 场景下，base 信息不能缺

你们之前遇到过“`insmod` 失败，后来补了 `btf_base` 等内容”的问题，本质上就是这个点：

- 模块 BTF 不只是“一段孤立的 `.BTF` 数据”
- 它还需要和 base `vmlinux` 的类型体系建立一致关系
- 在不少实践里，这会体现为与 `.BTF.base` 或等价 base-BTF 元数据相关的要求

如果只是把一段 `.BTF` 生硬塞进模块，而没有正确处理 base 关联信息，那么：

- 内核装载器可能拒绝它
- `bpftool` 也可能无法正确解释它

从实践角度说，遇到这种问题时，最合理的处理顺序是：

1. 先确认模块是针对当前运行内核构建的。
2. 确认 `vmlinux` BTF 可用：
   - `/sys/kernel/btf/vmlinux`
3. 用 `readelf -S your_module.ko` 检查是否存在 `.BTF`，必要时也检查是否有与 base 相关的 section。
4. 尽量通过内核原生构建流程重新生成模块 BTF，而不是事后手工修补二进制。
5. 如果要调试读取问题，优先使用：
   - `/sys/kernel/btf/<module>`
   - 或 `bpftool ... --base-btf /sys/kernel/btf/vmlinux`

#### 4. 优先信任 `/sys/kernel/btf/<module>`，而不是磁盘上的 `.ko`

对于已经加载的模块，最实用的经验是：

> 如果 `/sys/kernel/btf/<module>` 已经存在，优先读它，不要优先读磁盘上的 `.ko`。

原因是：

- 它已经通过了内核装载校验
- base 关联关系已经由内核处理过
- 对 `bpftool` 和本工具来说更稳定

### 建议的排查顺序

如果你怀疑 LKM 的 BTF 有问题，建议按下面顺序排查：

1. 看模块是否已经成功加载。
2. 看 `/sys/kernel/btf/<module>` 是否存在。
3. 看 `/sys/kernel/btf/vmlinux` 是否存在。
4. 用 `bpftool btf dump file /sys/kernel/btf/<module> format raw` 验证函数和类型是否存在。
5. 如果只能拿到 `.ko`，再尝试：

```bash
bpftool btf dump file your_module.ko --base-btf /sys/kernel/btf/vmlinux format raw
```

6. 如果仍然失败，优先重新构建模块 BTF，不要继续手工修补已有二进制。

## 小结

`vkso_gen_types.py` 当前的定位可以概括为一句话：

> 它是一个“面向黑盒 API 调用”的最小 ABI 头生成器，而不是一个“把内核实现完整翻译到用户态”的工具。

如果你的目标是：

- 像调用动态库一样调用映射后的内核函数
- 只关心函数声明和参数/返回值涉及的类型
- 不关心内部实现细节

那么当前这套工作流就是合适的：

1. 准备 `symbols.txt`
2. 用本工具生成头文件
3. 在用户态包含该头文件并调用动态库中的目标符号

如果以后目标变成“分析完整实现闭包”，那应当另开一条工具链，而不是让当前这个脚本同时承担两种互相冲突的职责。
