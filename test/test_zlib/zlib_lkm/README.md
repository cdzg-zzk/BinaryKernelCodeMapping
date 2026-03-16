# pigz依赖的libz.so函数以及执行路径

本文档用于回答第一阶段里的核心问题：`pigz` 在“压缩”场景下，真正依赖 `libz.so` 的哪些接口，以及这些接口在 `pigz -> zlib` 里是怎么被走到的。

分析对象固定为：

- `pigz-2.8`
- `zlib-1.2.11`
- 目录位置：
  - `test/test_zlib/pigz_macro/pigz-2.8/`
  - `test/test_zlib/pigz_macro/zlib-1.2.11/`

## 结论先行

`pigz` 的压缩路径并不是调用 `compress()` / `compress2()` 这种一次性接口，而是直接驱动 `deflate` 流接口。

更准确地说：

1. `pigz` 自己负责写 `gzip` / `zlib` / `zip` 的 header 和 trailer。
2. `libz.so` 只负责输出“raw deflate bitstream”以及校验计算。
3. 因为 `pigz` 自己拼接多块压缩流，所以它会用到 `deflateSetDictionary()`、`deflatePending()`、`deflatePrime()` 这类比普通应用更底层的接口。
4. `pigz` 并不依赖 `gzopen()`、`gzwrite()`、`deflateSetHeader()`、`compress()`、`compress2()` 这类接口来完成压缩主流程。

这意味着我们后续要提取的并不是“整个 zlib”，而是一套以 `deflate.c` 为核心的 `compress-only` 子集。

## pigz 直接依赖的 libz.so 导出接口

### 压缩主路径会直接调用的接口

下面这些是 `pigz` 压缩路径里真正会直接碰到的 `libz.so` 导出符号：

| 接口 | 是否必须 | 用途 |
| --- | --- | --- |
| `zlibVersion()` | 是 | 启动时检查版本；同时用于判断是否可走 `deflatePending()`/`deflatePrime()` 优化路径 |
| `get_crc_table()` | 是 | 启动时预热 CRC 表，避免多线程下动态建表问题 |
| `deflateInit2()` | 是 | 初始化 raw deflate 流，`windowBits = -15`，不让 zlib 自己写 wrapper |
| `deflateReset()` | 是 | 每个新输入流/新块开始前复位压缩状态 |
| `deflateParams()` | 是 | 根据 `pigz` 当前 level/strategy 切换压缩参数 |
| `deflate()` | 是 | 真正执行 deflate 压缩 |
| `deflateEnd()` | 是 | 释放 deflate 状态 |
| `deflateSetDictionary()` | 条件依赖 | 多线程且非 `-i` 时，为后续块装载前 32 KiB 历史字典 |
| `deflatePending()` | 条件依赖 | 对齐块边界时查询 pending bits 数量 |
| `deflatePrime()` | 条件依赖 | 为块拼接补空块/补位，保证 byte boundary |
| `crc32()` | 是 | 默认 `gzip`/`zip` 输出使用 CRC32 |
| `adler32()` | 条件依赖 | 只在 `-z` 输出 zlib wrapper 时使用 |

### 条件说明

- `deflateSetDictionary()` 只在并行压缩且没有使用 `-i/--independent` 时需要。
- `deflatePending()` 和 `deflatePrime()` 只在 `zlib >= 1.2.6` 时走到；当前基线 `zlib-1.2.11` 会走到。
- `adler32()` 只在 `pigz -z` 时需要；默认 `gzip` 路径和 `-K zip` 路径只用 `crc32()`。

## 明确不在压缩主路径里的接口

下面这些接口虽然也属于 zlib，但不属于当前 `pigz` 压缩主路径的必需项：

- `compress()` / `compress2()`
- `deflateInit()`
- `deflateSetHeader()`
- `gzopen()` / `gzwrite()` / `gzclose()` 等 `gz*`
- 全部 `inflate*`
- `uncompress()`

原因很简单：

- `pigz` 自己构造 `gzip` / `zlib` / `zip` 外层格式，没有把 wrapper 交给 zlib 管。
- `pigz` 压缩用的是 streaming `deflate`，不是 one-shot `compress()`。
- 本文只关心压缩路径，不关心解压路径。

另外还有一个很关键的点：

- 并行校验合并时，`pigz` 用的是自己内置的 `crc32_comb()` / `adler32_comb()` 实现，而不是从 `libz.so` 导入 `crc32_combine()` / `adler32_combine()`。

所以如果我们只做 `pigz` 压缩兼容层，这两个 `combine` 导出符号不是必需 ABI。

## pigz 压缩总调用链

### 入口选择

命令行解析完成后，`process()` 会根据线程数决定走哪条压缩路径：

- `g.procs > 1`：`parallel_compress()`
- 否则：`single_compress(0)`

也就是说，后续最重要的是：

1. 单线程压缩路径
2. 多线程压缩路径
3. `-H` / `-U` / `-i` / `-z` 这些选项如何改变 zlib 接口使用方式

## 单线程压缩路径

单线程路径的大致调用链如下：

```text
main
  -> process()
    -> single_compress(0)
      -> put_header()                  # pigz 自己写 gzip/zlib/zip header
      -> deflateInit2(..., -15, ..., strategy)
      -> deflateReset()
      -> deflateParams(level, strategy)
      -> [循环喂入输入块]
           -> deflate(..., Z_NO_FLUSH / Z_BLOCK / Z_SYNC_FLUSH /
                          Z_FULL_FLUSH / Z_FINISH)
           -> [必要时] deflatePending()
           -> [必要时] deflatePrime()
           -> crc32() / adler32()
      -> put_trailer()                # pigz 自己写 trailer
```

这里最关键的事实是：

- `deflateInit2(..., -15, ...)` 明确要求 zlib 输出 raw deflate。
- 所以 `gzip`/`zlib`/`zip` 封装层不在 `libz.so` 里，而在 `pigz.c` 里。

### 单线程下各接口何时出现

- `deflateInit2()`：第一次进入 `single_compress()` 时初始化流
- `deflateReset()`：每次新压缩流开始时调用
- `deflateParams()`：同步压缩级别和策略
- `deflate()`：真正压缩输入
- `deflatePending()` + `deflatePrime()`：为了把块收束到 byte boundary，便于 `pigz` 自己拼接块
- `crc32()` / `adler32()`：`pigz` 自己计算最终 trailer 所需校验

## 多线程压缩路径

并行路径比单线程多了一层“块拆分 + 字典传递 + 写线程串接”：

```text
main
  -> process()
    -> parallel_compress()
      -> 读线程逻辑切分输入块
      -> 为每个 job 准备上一块末尾 32 KiB 字典
      -> compress_thread()
           -> deflateInit2(..., -15, ..., strategy)   # 每个工作线程一次
           -> 对每个 job:
                -> deflateReset()
                -> deflateParams(level, strategy)
                -> [如启用共享历史] deflateSetDictionary()
                -> deflate(..., Z_NO_FLUSH / Z_BLOCK / Z_SYNC_FLUSH /
                               Z_FULL_FLUSH / Z_FINISH)
                -> [必要时] deflatePending()
                -> [必要时] deflatePrime()
                -> crc32() / adler32()
      -> write_thread()
           -> put_header()
           -> 顺序写出各 job 的 raw deflate 数据
           -> 合并校验值（pigz 自带 combine 实现）
           -> put_trailer()
```

### 多线程路径里最关键的依赖点

#### 1. `deflateSetDictionary()`

这是真正把“上一块的 32 KiB 历史”喂给当前压缩 job 的接口。

因此：

- 如果要支持默认多线程压缩，就必须保留它。
- 如果只支持 `-i/--independent`，这个依赖可以不走到。

#### 2. `deflatePending()` + `deflatePrime()`

`pigz` 不是简单地让每个块各压各的再直接拼起来，而是要保证块切分和块尾补位能被后续串接逻辑正确接受。因此会：

- 先 `deflate(..., Z_BLOCK)` 结束当前块
- 再通过 `deflatePending()` 看还剩多少 bit 没落到字节边界
- 必要时调用 `deflatePrime()` 补空块/补位
- 再继续 `Z_SYNC_FLUSH` 或后续输出

这组接口对“多块 raw deflate 可拼接输出”非常关键。

## 选项对接口和路径的影响

### 默认 gzip 压缩

- 外层格式：`pigz` 自己写 gzip header/trailer
- 校验：`crc32()`
- 压缩核心：`deflate*`

### `-z`（输出 zlib wrapper）

- 外层格式：仍然由 `pigz` 自己写
- 校验：改为 `adler32()`
- 压缩核心：仍然是 raw `deflate*`

### `-K`（输出 zip 单文件）

- zip local header / central directory / data descriptor 都由 `pigz` 自己写
- 压缩数据部分仍然是 raw `deflate*`
- 校验仍然是 `crc32()`

### `-H`

- `pigz` 把 `g.strategy` 设成 `Z_HUFFMAN_ONLY`
- 这会让 zlib 在 `deflate()` 内部落到 `deflate_huff()`

### `-U`

- `pigz` 把 `g.strategy` 设成 `Z_RLE`
- 这会让 zlib 在 `deflate()` 内部落到 `deflate_rle()`

### `-i`

- `pigz` 把 `g.setdict` 设成 0
- 多线程下不再调用 `deflateSetDictionary()`
- 并且块与块之间会显式做 `Z_FULL_FLUSH`

### `-0` 到 `-9`

- 都走 zlib 的 `deflate` 主体
- `0` 会落到 `deflate_stored()`
- `1` 到 `3` 会落到 `deflate_fast()`
- `4` 到 `9` 会落到 `deflate_slow()`

### `-11`

这是个必须单独标注的例外：

- `pigz -11` 使用的是内置 `zopfli`，不是 `libz.so` 的 deflate 实现
- 所以如果论文目标是“同源 zlib 实现进入内核”，`-11` 不应纳入主实验路径

换句话说，后续我们在 `zlib_lkm/` 中抽取 `compress-only` 子集时，主目标应覆盖 `-0..-9`、`-H`、`-U`、`-i`、默认 gzip/zip/zlib 输出，而不是 `-11`

## zlib 内部执行路径

从 `pigz` 进入 `zlib` 之后，主链路基本可以整理成下面这样：

```text
deflateInit2_
  -> deflateReset
    -> deflateResetKeep
    -> lm_init
    -> _tr_init

deflate
  -> flush_pending                # 如有 pending 输出
  -> 根据 level / strategy 选实现:
       level == 0                -> deflate_stored
       strategy == HUFFMAN_ONLY  -> deflate_huff
       strategy == RLE           -> deflate_rle
       level 1..3                -> deflate_fast
       level 4..9                -> deflate_slow

deflate_fast / deflate_slow / deflate_rle / deflate_huff
  -> fill_window
  -> [fast/slow 路径] longest_match
  -> _tr_tally_lit / _tr_tally_dist
  -> _tr_flush_block
  -> flush_pending
```

### 这条内部链路对应到源码文件

| 文件 | 作用 |
| --- | --- |
| `deflate.c` | 对外导出 `deflate*` 接口，也是压缩主循环所在 |
| `trees.c` | Huffman 树构建、`_tr_init()`、`_tr_tally_*()`、`_tr_flush_block()` |
| `crc32.c` | `crc32()`、`get_crc_table()` |
| `adler32.c` | `adler32()`，仅 `-z` 路径需要 |
| `zutil.c` | `zlibVersion()` 以及通用运行时支持 |

## 对 `compress-only` 提取的直接建议

### 第一版建议保留的源码

如果目标是支撑 `pigz` 的压缩路径，第一版最小保留集建议至少包含：

- `deflate.c`
- `trees.c`
- `crc32.c`
- `zutil.c`
- `adler32.c`

以及对应头文件：

- `zlib.h`
- `zconf.h`
- `zutil.h`
- `deflate.h`
- `trees.h`
- `crc32.h`

说明：

- 即使默认实验是 gzip，`adler32.c` 也建议先保留，因为 `-z` 路径只差这一个校验模块，保留成本低。
- 如果后面确认完全不做 `pigz -z`，那 `adler32.c` 才可以作为第二轮裁剪对象。

### 第一版可以先排除的源码

下面这些可以先不放进 `compress-only` 子集：

- `inflate.c`
- `inffast.c`
- `inftrees.c`
- `infback.c`
- `uncompr.c`
- `compress.c`
- `gzread.c`
- `gzwrite.c`
- `gzclose.c`
- `gzlib.c`

原因分别是：

- `inflate*` / `uncompr.c` 属于解压路径
- `compress.c` 是 one-shot 封装，不是 `pigz` 实际走的接口
- `gz*` 是 zlib 自己管理 gzip 文件格式的高层接口，但 `pigz` 没用它们

## 对后续 ABI 收敛的建议

如果我们的目标是先做一个“足够支撑论文实验”的 `libmz.so` / 内核导出 ABI，那么第一轮最值得优先保证的是下面这组符号：

- `zlibVersion`
- `get_crc_table`
- `crc32`
- `adler32`
- `deflateInit2_`
- `deflateReset`
- `deflateParams`
- `deflate`
- `deflateEnd`
- `deflateSetDictionary`
- `deflatePending`
- `deflatePrime`

这里之所以写 `deflateInit2_`，是因为宏层最终会落到带版本参数的真实导出符号；后续做 ABI 兼容封装时要特别留意这一点。

## 当前阶段的可操作结论

基于上面的梳理，`zlib_lkm/` 下一步最合理的方向不是“从整个 `libz.so` 盲目抠代码”，而是：

1. 先围绕 `deflate.c + trees.c + crc32.c + adler32.c + zutil.c` 建最小可编译子集。
2. 优先保证 `pigz` 默认 gzip 压缩、`-p 1`、`-p 4`、`-H`、`-i` 能走通。
3. 明确排除 `inflate*`、`gz*`、`compress.c` 这类不在真实压缩路径里的代码。
4. 暂时不要把 `-11/zopfli` 混进“同源 zlib 实现”目标里。

如果后续继续往下做，下一份文档最值得整理的是：

- “这些接口分别对应 `zlib-1.2.11` 里哪些源码文件和内部符号”
- “为了把这套代码搬进内核，需要替换哪些 libc/用户态假设”

## 对libz.so中原生代码的修改

这一节只记录“为了把 `zlib-1.2.11` 的 compress-only 子集做成 LKM，我实际做了哪些修改”。

### 当前落地的文件

从 `zlib-1.2.11` 拷入并保留的核心源码：

- `deflate.c`
- `trees.c`
- `crc32.c`
- `adler32.c`
- `zutil.c`
- `zlib.h`
- `zconf.h`
- `zutil.h`
- `deflate.h`
- `trees.h`
- `crc32.h`

新增的 LKM 相关文件：

- `Makefile`
- `zlib_lkm_module.c`

### 尽量保持原样的部分

下面这些压缩核心文件我没有去改 deflate/Huffman/checksum 主逻辑，只是让它们在新的头文件环境下参与 Kbuild：

- `deflate.c`
- `trees.c`
- `crc32.c`
- `adler32.c`

这样做的目的，是尽量保持和上游 `zlib-1.2.11` 的压缩行为一致，把改动集中在“环境适配层”和“导出层”。

### 明确做过修改的文件

#### 1. `zconf.h`

现在 `zconf.h` 已经改成“kernel-only 优先”的结构：

- 文件开头提供一整套 `#ifdef __KERNEL__` 的最小内核版定义
- upstream 原始的 user/跨平台配置内容被放在 `#else` 中，仅作为对照保留

内核分支里的核心改动有：

- 在 `__KERNEL__` 下改为使用内核头文件提供的基础类型
- 直接定义内核编译所需的最小 `zlib` 基础类型和宏：
  - `OF`
  - `Z_ARG`
  - `ZEXTERN`
  - `ZEXPORT`
  - `FAR`
  - `Byte` / `uInt` / `uLong`
  - `z_crc_t`
  - `z_size_t`
  - `z_off_t` / `z_off64_t`
- 其中：
  - `z_crc_t` 在内核分支下固定为 32-bit 的 `u32`，对应 upstream 对 CRC 类型“尽量选 32 位无符号类型”的语义
  - `z_off64_t` 在内核分支下固定为 64-bit 的 `s64`，保证 `*_combine64()` 这类接口在 32-bit kernel 上也不丢 64 位长度语义
- 不再让内核编译路径继续穿过用户态 `sys/types.h`、`unistd.h`、`limits.h`、`stdarg.h` 等历史兼容链
- `#else` 里的参考实现恢复成 upstream `zlib-1.2.11` 的原始多平台配置逻辑，不再混入额外的 `__KERNEL__` 判断

这样做的原因是：

- `zlib_lkm/` 的目标已经明确是内核模块，不再需要同时服务 user 侧编译
- Kbuild 环境不应该依赖 upstream 那套用户态/跨平台配置分支
- 这样可以更清楚地区分“当前可用的 kernel 实现”和“保留下来的 upstream 参考内容”

#### 2. `zutil.h`

现在 `zutil.h` 也已经改成“kernel-only 优先”的结构：

- 文件开头提供 `#ifdef __KERNEL__` 的最小内核版 `zutil` 定义
- 原始面向 user/多平台的 `zutil.h` 内容放在 `#else` 中，仅作参考保留

内核分支里的核心改动有：

- 在 `__KERNEL__` 下改为包含：
  - `linux/kernel.h`
  - `linux/mm.h`
  - `linux/string.h`
  - `linux/overflow.h`
  - 以及必要的 bug/errno 头
- 在内核分支里直接定义 deflate 真正需要的最小运行时常量和辅助宏：
  - `ERR_MSG`
  - `ERR_RETURN`
  - `DEF_MEM_LEVEL`
  - `MIN_MATCH` / `MAX_MATCH`
  - `PRESET_DICT`
  - `OS_CODE`
- 强制使用内核提供的 `memcpy/memset/memcmp`
- Trace 宏在内核分支下不再保留 user 侧 `fprintf` 语义，而是直接空实现
- `#else` 里的旧内核兼容分支已经删除，恢复成 upstream `zlib-1.2.11` 原始内容

这部分修改的目的，是把原来依赖 libc 的公共运行时接口切换到内核实现。

这里要单独说明一下：

- 之前 `#else` 里那段旧的内核兼容分支，不是 upstream `libz.so` 原本就有的
- 那是我前一轮为了让 LKM 先编起来，额外塞进去的适配代码
- 现在已经把它移掉，只保留文件开头这一处明确的 `__KERNEL__` 入口，避免和 upstream 参考内容混在一起

#### 3. `zutil.c`

这是这次改动里最明确的一处“重写适配层”：

- 删除了原来与用户态文件 I/O、16-bit 平台、DOS/Windows 分配器兼容相关的大段 target-dependent 代码
- 去掉了对 `gzguts.h` 的依赖
- 保留并继续提供：
  - `zlibVersion()`
  - `zlibCompileFlags()`
  - `zError()`
  - `z_errmsg`
  - `zcalloc()`
  - `zcfree()`
- 目前已开始按“伪 GOT / `.data` 槽位”的方式做第一步收敛：
  - `zlibVersion()` 不再直接在 `.text` 中物化 `ZLIB_VERSION` 的地址
  - 而是改为从 `.data` 中的一个小型上下文槽位读取版本串指针
  - 这一步没有改 `zlibVersion()` 的返回语义，仍然返回同一个版本串，只是把“代码直接拿字符串地址”改成了“代码先读 `.data` 槽位，再由槽位指向字符串”
  - 为了防止编译器再把这个读取折叠回立即数，当前实现把该槽位保留为可写数据对象，并确保它在目标文件里形成 `.rela.data`
  - 这样对应的字符串地址关系会落在数据重定位里，而不是落成 `.text` 里的绝对地址寻址
- 将 `zcalloc()` 改为基于 `kvmalloc()` 的内核分配
- 将 `zcfree()` 改为基于 `kvfree()` 的内核释放
- `zcalloc()` 继续保留乘法溢出检查，同时不再使用 `vzalloc()` 的零填充语义，尽量贴近 upstream 在普通平台上 `malloc(items * size)` 的默认行为
- 在 `ZLIB_DEBUG` 下，把原来的 `fprintf + exit` 改为 `panic()`

这里的原则是：

- 保留 deflate 所需的最小公共运行时
- 删除和 `gz*`、stdio、历史平台兼容相关的无关逻辑
- 让 deflate 状态分配能在内核里稳定工作
- 在“必须换成内核分配器”的前提下，尽量保持和 upstream 默认分配语义接近

#### 3.1 `deflate.c`

- 为了避免 `deflateInit2_()`、`deflateParams()`、`deflate()`、`lm_init()` 直接把只读对象地址物化进 `.text`，这里新增了一个很小的 `deflate_pic_ctx`
- `deflate_pic_ctx` 放在 `.data`，当前只收纳两类普通伪 GOT 槽位：
  - 默认分配器 `zcalloc`
  - 默认释放器 `zcfree`
- `deflateInit2_()` 不再直接把 `zcalloc` / `zcfree` 写入 `strm->zalloc` / `strm->zfree`
- `configuration_table` 没有再塞进 `deflate_pic_ctx`
- 现在的处理方式是：
  - 先把 `configuration_table` 改成非 `const` 的静态数组
  - 再通过一个很小的 `configuration_table_base()`，显式执行 `lea configuration_table(%rip), reg`
  - 后续再用 `&configuration_table_base()[level]` 或 `configuration_table_base()[level].func` 做索引访问

这里要把两类场景分开看：

- `zalloc` / `zfree` 这类普通伪 GOT 槽位，直接通过结构体读取就能稳定生成 `.text -> .data` 的 `R_X86_64_PC32`
- `configuration_table` 则不一样：
  - 它是静态数组
  - 里面还带函数指针成员 `func`
  - 这类“数组基址 + 变址访问”的路径，更适合显式先做一次 `lea`

这里要特别说明一下：

- `configuration_table` 的表项内容、布局、顺序都保持和 upstream 一致
- 这里把它从 `const` 改成普通静态数组，不是为了改语义，而是因为表项里含有函数指针 `func`
- 这样链接后这些函数地址关系会落到 `.rela.data`，而不是被压成 `.text` 里的固定地址
- 这里没有把 `configuration_table` 回退到“完全不改”，原因是 `pigz` 的真实压缩路径确实会调用 `deflateParams()`
- 对照 `pigz-2.8/pigz.c` 可以看到：
  - worker 线程初始化压缩任务时会执行 `deflateReset()` 之后立刻调用 `deflateParams()`
  - 单线程压缩路径也会在写头之后调用一次 `deflateParams()`
- 重新查看当前 `deflate.o` 的反汇编后，这一层访问已经是：
  - 先 `lea configuration_table(%rip), reg`
  - 再在寄存器上完成表项索引
- 同时 `readelf -r deflate.o` 里也已经能看到 `configuration_table[].func` 对应的 `.rela.data` 条目
- 因此这块现在更符合“数组不进 ctx、函数指针进 `.rela.data`、访问显式 `lea`”这三个原则

#### 3.2 `trees.c`

- 为了避免 `_tr_init()` 直接把 `&static_l_desc`、`&static_d_desc`、`&static_bl_desc` 写进状态结构，又新增了一个很小的 `trees_pic_ctx`
- `trees_pic_ctx` 也放在 `.data`，里面只保存这三个静态 tree descriptor 的指针
- `_tr_init()` 现在直接从 `trees_pic_ctx` 读取对应 descriptor 指针，再写进 `s->l_desc.stat_desc`、`s->d_desc.stat_desc`、`s->bl_desc.stat_desc`
- 对 `bl_order`、`static_ltree`、`static_dtree`、`extra_lbits`、`extra_dbits`、`base_length`、`base_dist` 这几张只读静态表，没有改成 `.data`
- 这些表都继续保持 upstream 的 `static const` / `const` 定义，继续留在 `.rodata`
- 真正的改动只在“怎么取基址”：
  - 为每张会被索引访问的表新增一个很小的 `*_base()` helper
  - helper 里面显式执行一次 `lea table(%rip), reg`
  - 后续再在寄存器基址上完成 `base[idx]` 或传参
- 这样做的原因和 `crc_table_base()` 一样：
  - 这些对象本身只是只读常量表
  - 不需要像 `configuration_table` 那样引入 `.rela.data`
  - 但如果直接写数组索引，编译器可能把访问折成 `.text` 中的坏绝对地址
- 目前已按这个模式改过的使用点包括：
  - `build_bl_tree()`
  - `send_all_trees()`
  - `_tr_align()`
  - `_tr_flush_block()`
  - `_tr_tally()`
  - `compress_block()`

这里同样遵守了“尽量不改原始只读对象本身”的原则：

- `static_l_desc` / `static_d_desc` / `static_bl_desc` 的定义和内容没有被改写
- 只调整了 `_tr_init()` 获取这些对象地址的方式

#### 3.3 `crc32.c` / `adler32.c`

- 继续往下检查 `deflateInit2_()` 的闭包后，发现真正的热点问题在 `crc32_little()` / `crc32_big()`：
  - 这两个函数会大量执行 `crc_table[k][idx]`
  - 如果直接保留原始写法，编译器会把这些表基址继续固化成 `.text -> .rodata` 的绝对地址引用
- 这里最终采用的是和 `configuration_table` 不同、但和 `trees.c` 那些只读静态表一致的处理方式：
  - `crc_table` 本身继续保持 upstream 的 `static const` 定义
  - 它不再进入任何 `.data` 上下文，也不再额外复制一份指针槽位
  - 整张表继续留在 `.rodata`
- 真正需要处理的问题，不是“让 `crc_table` 进 `.data`”，而是“避免数组索引时把 RIP 相对寻址折成坏的绝对地址”
- 现在的办法是新增一个很小的 `crc_table_base()`：
  - 里面显式执行 `lea crc_table(%rip), reg`
  - 然后返回表基址
- `get_crc_table()`、`crc32_z()`、`crc32_little()`、`crc32_big()` 现在都先拿这个 base
- 后续再在寄存器上完成 `table[k][idx]` 的索引访问
- 这一步的关键目标是：
  - `crc_table` 继续只是 `.rodata` 里的常量表
  - `.text` 里对它的引用保持为正常的 `R_X86_64_PC32` RIP-relative 访问
  - 同时数组热路径不再退化成绝对地址寻址
- 从当前 `crc32.o` 的反汇编可以看到，`crc32_little()` 入口已经变成：
  - 先 `lea crc_table(%rip), %rsi`
  - 后续 `t1/t2/t3` 直接用 `0x400/0x800/0xc00` 这样的寄存器偏移来访问
- 这一步没有改 CRC 算法、CRC 表内容、表布局，也没有改对外语义；改的只是“运行时如何获得各张 CRC 表的基址”
- 另外，`zcalloc()` / `zcfree()` 现在也不再直接写死调用 `kvmalloc()` / `kvfree()`
  - 新增了一个很小的 `zutil_pic_ctx`
  - 里面保留两个可改写表项：`kvmalloc`、`kvfree`
  - `zcalloc()` 通过 `zutil_pic_ctx.kvmalloc(...)` 分配
  - `zcfree()` 通过 `zutil_pic_ctx.kvfree(...)` 释放
- 这层改动的目的不是改变 zlib 行为，而是给后续“映射到用户态后由伪 GOT 改写表项地址”留出落点
  - 也就是除了处理 PIC，本地 allocator 内部依赖的 kernel-only 函数也能被替换成用户态 shim

为了更适配 Kbuild 的告警策略，我还顺手把下面几个导出函数从 K&R 风格定义改成了标准 ANSI 原型定义：

- `crc32_combine()`
- `crc32_combine64()`
- `adler32_combine()`
- `adler32_combine64()`

这不是语义修改，只是为了避免内核编译时的 `-Wstrict-prototypes` 报错。

#### 3.3 当前 PIC 检查结果

围绕当前已经改造的伪 GOT 路径，现阶段至少可以确认下面几件事：

- `zlibVersion()`：已通过 `functions_checker.py`
- `get_crc_table()`：已通过 `functions_checker.py`
- `deflateInit2_()`：在把 `deflate_pic_ctx`、`trees_pic_ctx`、`crc_table_base()` 这三层接好之后，也已经通过 `functions_checker.py`
- `deflate()`：在把 `deflate.h` / `trees.c` 中这批只读静态表访问改成 `*_base()` 之后，也已经通过 `functions_checker.py`
- `zcalloc()`：单独检查时能够继续展开到 `kvmalloc` / `kvmalloc_node`，说明 allocator 路径不会再被“默认回调 + 间接调用”完全隐藏

这次 `deflateInit2_()` 的通过，说明此前最集中的几类绝对地址问题已经被压下去了：

- `zcalloc` / `zcfree` 默认函数指针
- `configuration_table`
- `_tr_init()` 中的 `static_*_desc`
- `crc32_little()` 热路径里的 CRC 查表基址

当前 checker 报告里这些点都已经表现为 `.text -> .data` 的可写数据引用，而不再是 `.text -> .rodata` 的绝对地址重定位。

#### 4. `zlib_lkm_module.c`

这是新增的导出层，不属于 upstream zlib 原始文件。它负责：

- 提供 `module_init/module_exit`
- 用 `EXPORT_SYMBOL()` 导出当前这版 compress-only LKM 需要暴露的符号

当前实际导出的符号有：

- `zlibVersion`
- `get_crc_table`
- `deflateInit2_`
- `deflate`
- `deflateEnd`
- `deflateReset`
- `deflateParams`
- `deflatePending`
- `deflatePrime`
- `deflateSetDictionary`
- `crc32`
- `adler32`

### 有意没有导出的内容

以下内容即使在拷入源码里存在，也没有对外 `EXPORT_SYMBOL`：

- 所有 `static`/`local` 内部函数
- Huffman/距离表等内部实现细节
- `crc32_combine*` / `adler32_combine*`
- `deflateInit_`、`deflateResetKeep`、`deflateGetDictionary`、`deflateBound`
- `crc32_z`、`adler32_z`
- `zlibCompileFlags()`、`zError()`
- `deflateCopy()`、`deflateTune()`、`deflateSetHeader()` 等当前 `pigz` 压缩路径不需要的接口

原因是：

- 当前目标是“支撑 `pigz` compress-only 路径”
- 不希望把和当前实验无关的 ABI 面暴露得过宽
- 像 `zlibCompileFlags()`、`zError()` 这类函数目前仍保留在源码里，是为了尽量少动 `zutil.c` 的原始结构；但既然 `pigz` 压缩路径不会用到，就不再导出给模块外部

#### 5. `Makefile` / gcc 编译参数

为了让后续 `.ko` 中真正要映射出去的压缩代码更适合做二进制分析和用户态执行侧复用，我在 `Makefile` 里额外加了一层编译参数约束。

这部分不是改 zlib 算法语义，而是约束 Kbuild 不要给这批对象额外塞进内核侧 instrumentation。

当前显式处理的内容包括：

- 通过 `UBSAN_SANITIZE := n` 关闭本目录对象的 UBSAN
  - 这一步是必须的，因为当前内核配置里开启了 `CONFIG_UBSAN_SANITIZE_ALL=y`
  - 如果不显式关掉，Kbuild 仍会把 `-fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum` 自动加回编译命令里
  - 结果就是 `.ko` 中会留下 `__ubsan_handle_out_of_bounds`、`__ubsan_handle_shift_out_of_bounds` 这类外部依赖，不利于后续映射到用户态执行
- 通过 `ccflags-remove-y` / `CFLAGS_REMOVE_*.o` 去掉：
  - `-fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum`
  - `-fstack-protector-strong`
  - `-pg -mrecord-mcount -mfentry`
  - `-fpatchable-function-entry=16,16`
- 通过 `ccflags-y` 增加：
  - `-fno-stack-protector`
  - `-fno-sanitize=all`
  - `-fno-omit-frame-pointer`
  - `-fno-inline`
  - `-fno-optimize-sibling-calls`
  - `-fno-ipa-cp`
  - `-fno-ipa-sra`
  - `-fno-tree-ccp`

这里的目标是：

- 去掉 UBSAN、ftrace/fentry、stack protector、patchable function entry 这些会改变控制流或引入额外外部符号的内容
- 保留更稳定、可读的控制流形态，方便后续 `objdump`、符号分析和映射验证

这轮调整之后，重新构建得到的最终 `zlib_lkm.ko` 已经不再包含 `__ubsan_handle_out_of_bounds` / `__ubsan_handle_shift_out_of_bounds` 这类外部依赖。

需要注意的是：

- 这类编译参数修改的是“代码生成方式”，不是 zlib 算法语义
- 当前我们重点强制去掉的是 `__ubsan*`
- x86 的 retpoline / return thunk 仍然保留在当前产物里；这一轮没有继续处理它

### 关于 user 兼容的当前态度

现在这份 `zlib_lkm/` 代码的目标已经明确是：

- 以 `__KERNEL__` 分支为实际生效实现
- 以 LKM 构建、导出和后续映射为唯一目标

也就是说：

- 这里不再把“同时兼容 user/kernel 编译”当作目标
- `#else` 里的 upstream 内容只是参考，不是当前要维护的构建路径

### 头文件层保留但代码层未实现/未导出的部分

我保留了原版 `zlib.h`，主要是为了：

- 保留 `z_stream`、常量、宏、类型定义
- 尽量维持和 upstream 接近的 public interface 形状

但要注意：

- 这不代表 `zlib.h` 里所有声明都已经在当前 LKM 中实现
- 当前模块只覆盖了 `pigz` 压缩路径真正需要的那部分 deflate/checksum ABI

### 当前构建结果

在当前目录执行 `make`，已经可以生成：

- `zlib_lkm.ko`
- `Module.symvers`

这说明这版最小 `compress-only` 子集已经能以 LKM 形式成功编译。

当前还没有做的事情包括：

- 实际 `insmod`/`rmmod` 装载验证
- 通过 page cache replace 导出成用户态 DSO
- 用 `pigz` 端到端跑 `LD_PRELOAD` 回归
