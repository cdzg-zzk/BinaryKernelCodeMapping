# KRG: Linux 内核符号依赖图（SAFE-only）技术说明

> 代码基线：`krg.cpp`（当前版本）。v2 格式新增模块表和 module_id，便于下游按模块拆分依赖并生成多模块 .so（含 shim）。v1 仍可读，模块默认视为 kernel。

## 文件格式（out.krg）

- Header v2（兼容 v1）：
  ```
  struct FileHeader {
      u32 magic;              // 'KRG1' = 0x3147524b
      u32 version;            // 2 (v1 无 n_modules/module_blob_bytes)
      u32 n_nodes;
      u32 n_edges;
      u32 name_blob_bytes;
      u32 arch;               // 0 = x86_64
      u32 is_runtime_address; // 是否已按 KASLR 调整
      u32 reserved1;
      u32 n_modules;          // v2: 模块数（含 kernel=0）
      u32 module_blob_bytes;  // v2: 模块名字符串表大小
  };
  // v2 Node：module=0 -> kernel；v1 仅 {addr,size,kind}
  struct Node { u64 addr; u32 size; u16 module; u8 kind; u8 pad; };
  ```
- 序列化顺序：Header -> Node[n] -> row_ptr[n+1] -> col_idx[m] -> name_off[n] -> name_blob -> module_off[n_modules] -> module_blob（v1 无 module 段）。

## 与下游（build_PIC_so.py）的接口

- 下游期望 v2（含 module），以便按模块拆分 .so；若用 v1，所有节点视为 kernel。
- shim 符号由 `shim.txt` 单独声明，下游映射为 `libshim.so`（外部提供）。
- 多模块依赖通过 module_id 推导，下游生成 `module_deps.txt`、`resolved_symbol_addresses.txt`，并递归生成各模块 .so。

## 1. 背景与目标

我们需要一个**静态、轻量、可复现实验**的工具，从 `vmlinux` 中构建**符号级依赖图**，并在构建阶段**直接裁剪**到“SAFE 子图”（仅包含可在用户态镜像执行且不会影响内核全局状态的函数），查询时仅在该 SAFE 图上做闭包，并输出**运行时地址**（KASLR 对齐）、`size` 与 `kind`（0=code, 1=data）。

核心挑战在于：

* 函数体常被**局部子符号**（如 `.slowpath`）切片；
* 存在多种**间接调用**形式（`CALL IMM` / `CALL [RIP+disp]` / `CALL [ABS]` / `JMP`）；
* 需要合理且**可解释**的“SAFE 判定与裁剪”规则；
* 需要**快速**（大 `vmlinux`）且**干净**（拒绝无用代码、零编译告警）的实现。

## 2. 我们遇到的问题 → 解决方案总览

### P1. 函数边界被子符号“切片”，漏掉尾部调用（如 `.slowpath`）

* **症状**：`__raw_callee_save___pv_queued_spin_unlock` 被切成两段，`call …_slowpath` 落到“.slowpath”子符号，导致主函数视图中**没有**这条 `call`。
* **方案**：**只把“主函数入口”**（非 `.` 开头的函数名）纳入节内函数表，**统一用“下一主入口/节末”重算区间**，将 `.slowpath` 等内部块全部并入主函数区间；所有**owner 与 target**都按**主区间**命中。这样不再被子符号切片。

### P2. 漏识别 `CALL [ABS]`（绝对地址表 + 间接调用）

* **症状**：`klist_add_head` 中 `callq *0xffffffff82e63238` 未被识别，图里只有两个 `call`。
* **方案**：在 MEM 操作数分支中，除 `RIP+disp` 外新增 **ABS 形式**：`op.mem.base==X86_REG_INVALID` 时将 `op.mem.disp` 作为**绝对虚拟地址**，在**可分配节**中读取 8 字节指针，再按**主函数区间**映射为目标函数。日志中标注为 `[CALL ABSMEM]`。

### P3. 指令 owner 归属不稳（跨节小符号干扰）

* **症状**：`klist_add_head` 的某条 `call` 归属到邻近符号，`--dbg-sym=klist_add_head` 看不到。
* **方案**：**owner 命中统一走“主函数区间二分”**：将指令地址在 `fun_ranges_`（全局主函数区间表）中二分命中，不再逐节线性扫描；日志打印 owner 的节名、区间以便核查。

### P4. 仅统计 `CALL` 时容易漏掉**跨函数**的 `JMP`；全量 `JMP` 又会引入噪声

* **方案**：**统一处理 `JMP`，但仅保留“跨函数”的跳转**（`v != u`），块内跳转（intra）忽略。软忽略（如 `__x86_return_thunk*`）只过滤不落边，**不**判定 caller 不安全；**硬黑名单**命中 `JMP` 也仅过滤（`JMP` 不代表副作用）。

### P5. SAFE 判定不透明，用户难以定位“谁导致不安全”

* **症状**：只见 `[PRUNE] drop X : callee-unsafe` 之类粗粒度提示。
* **方案**：**深度日志**：

  * 构图时对每条 `CALL/JMP` 打印**命中/过滤/未命中（no-map）**，含 ABS/REL 地址与邻近函数（`near=[below|above]`）；
  * 剪枝时打印 `drop` 的**直接原因**（`CALL-hardBL` / `writable-data` / `callee-unsafe`）——精确到**哪个被调**使其 `callee-unsafe`（配合 `--dbg-sym=<name>` 可以聚焦单函数）。
    -（如需在 `query` 阶段也给用户解释，可额外输出一个 `*.explain.tsv`，文末“可选增强”）。

### P6. 性能与整洁：大 `vmlinux` 下全量线扫过慢，且编译告警多

* **方案**：

  * **全局二分**：`fun_ranges_`（主函数区间）与 `alloc_secs_`（可分配节区间）均采用**二分命中**；
  * 容器 `reserve`、游标复用，避免重复拷贝；
  * 统一花括号/拆行，**零 `-Wmisleading-indentation`**；
  * 仅保留核心数据结构与路径，**拒绝无用代码**。

---

## 3. 设计与算法（简述）

### 3.1 区间构建（主函数入口 → 主函数区间）

1. **主入口筛选**：取 `STT_FUNC && !name.starts_with('.')` 的符号；
2. **节内排序**：每个可执行节内按地址排序；
3. **统一重算**：区间 = `[start, next_start)`，最后一个到节末；
4. **全局合并**：合并为 `fun_ranges_`（全局递增），供**owner/target 二分**。

### 3.2 依赖抽取

* **CALL IMM**：ABS→REL 双尝试；
* **CALL/JMP [RIP+disp]**：从**可分配节**读取 8 字节指针，区间映射；
* **CALL/JMP [ABS]**：`op.mem.base==INVALID`，将 `disp` 当绝对虚拟地址读取 8 字节，区间映射；
* **JMP**：只保留**跨函数**（`v != u`）。
* **名单**：

  * 软忽略（`__x86_return_thunk*` 等）仅**过滤**；
  * 硬黑名单（`schedule*`、`copy_to_user*`、`kmalloc*`、`printk*`、`ioremap*` 等）仅在 **CALL** 命中时：**不过边 + 标记 caller 不安全**。

### 3.3 SAFE 判定与剪枝

* **条件**：

  1. 函数为主符号且已定义；
  2. 所有 `code→data` 仅指向**只读节**（**data 在可写节** → 不安全）；
  3. **未出现**对**硬黑名单**的 **CALL**；
* **传递闭包**：若存在 `u→v` 且 `v` 不安全，则 `u` 标记为 **callee-unsafe** 并被剪除；
* **序列化**：仅写 SAFE 子图（一个文件）。

---

## 4. 日志与可解释性
sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r)  -o out.krg --debug --dbg-sym=zlib_deflate 2>build.log
* `--debug` / `--dbg-sym=<name>`：

  * **RANGE**：打印 `<name>` 所在节的主函数表（验证区间是否覆盖 `.slowpath` 等）；
  * **CALL/JMP**：

    * 命中：`(edge)`；软忽略：`(soft-ignore)`；硬黑名单（仅 CALL）：`(HARD-BL; mark UNSAFE)`；
    * 未命中：`(no-map; abs/rel/ptr_va + near=[below|above])`；
  * **PRUNE**：`keep/drop` 与精确原因：`CALL-hardBL / writable-data / callee-unsafe`。
* 若需要**在 `query` 阶段**给用户直接解释“为什么不安全/元凶是谁”，可选地生成 `out.krg.explain.tsv`（符号 → 状态/原因/元凶/地址），并为 `query` 增加 `--explain` 选项（不影响当前单文件输出）。

---

## 5. 性能优化要点

* **一次构建、二分命中**

  * fun_ranges_：全局主函数区间表（`vector<Range>`），**owner/target** 查找均为 `O(log N)`；
  * alloc_secs_：所有 `SHF_ALLOC` 节的区间表，指针节定位 `O(log M)`；
* **简化与去冗**

  * 只维护**主函数入口**与其区间，彻底避免 `.slowpath` 子符号带来的切片；
  * 仅 `CALL` 命中硬黑名单才更新 `calls_blacklisted`；`JMP` 不引入副作用；
  * 容器 `reserve`、游标复用；删除所有无用分支与调试残留；
  * 全代码零 `-Wmisleading-indentation` 警告，保持可读性与安全性。

---

## 6. 安全语义（论文复述可直接引用）

> **SAFE（保守）定义**：对任意函数 `f`，若满足：
> (i) `f` 为主函数入口且已定义；
> (ii) `f` 的所有 `code→data` 依赖仅指向只读节；
> (iii) `f` 不存在对**硬黑名单**的 **CALL**；
> (iv) `f` 的**被调闭包**中所有函数也满足 (i)–(iii)；
> 则判定 `f` 为 SAFE。否则 `f` 被剪除并标记为 `CALL-hardBL / writable-data / callee-unsafe` 之一。

该定义保证了**用户态镜像执行**的安全性：参数/局部对象写不是问题（不触达内核全局），但凡涉及调度/用户态拷贝/外设映射/内核日志或告警等**全局效应**的 `CALL` 会**直接**使函数不安全；此外，任何依赖不安全函数的上层函数亦被判为不安全（闭包封闭性）。

---

## 7. 使用方法（复核）

```bash
# 命令行用法（完整）
krg build vmlinux -o out.krg [-m module.ko ...] [--debug] [--dbg-sym=<name>]
  -o <file>           必填：输出图文件（单文件 SAFE 子图，默认示例：./out.krg）
  -m/--module <file>  可重复：追加模块（.ko / .ko.xz / .ko.gz / .ko.zst）
  --module=<file>     同上（等价写法）
  --debug             打印构图日志到 stderr
  --dbg-sym=<name>    仅聚焦某函数名（配合 --debug）
krg query out.krg <symbol>
  输出格式：每行 `<name>\t<addr hex>\t<size>\t<kind>`（kind: 0=code, 1=data），为目标符号的可达闭包

# 构建 SAFE 子图（一个文件 out.krg）
sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) -o out.krg

sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) -o out.krg -m /lib/modules/$(uname -r)/kernel/lib/lz4/lz4_compress.ko -m /lib/modules/$(uname -r)/kernel/lib/lz4/lz4hc_compress.ko
# 调试构图（仅聚焦某函数）
sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) \
  -o out.krg --debug --dbg-sym=klist_add_head 2>build.log

# 查询闭包（运行时地址 KASLR 对齐，size, kind）
sudo ./krg query out.krg klist_add_head

# Makefile 快捷用法（支持变量覆盖）
make
make krg-build VMLINUX=/path/to/vmlinux OUT=mygraph.krg
make krg-build MODULES="a.ko b.ko"
make krg-build DEBUG=1 DBG_SYM=klist_add_head   # DEBUG=1 时 stderr 重定向到 ./build.log
make query OUT=mygraph.krg SYMBOL=klist_add_head
```

---

## 8. 局限与可选增强

* **寄存器间接调用**（如 `mov rax,[…]; call *%rax`）当前默认**不解**；可在未来加一个启发式开关（解析前若干条指令）。
* **错误/告警路径的“非传播”**：如果希望 `printk/__warn_printk` 等仅保留边但**不使 caller 不安全**，可做成**可选 non-prop 前缀**，默认仍采用严格 SAFE 闭包。
* **解释输出**：若希望 `query` 直接返回“为什么不安全/元凶是谁”，可按 4 节所述增加 `*.explain.tsv` 与 `--explain` 选项。

---

## 9. 结论

本实现通过**主函数区间统一重算 + 完整的间接调用解析（含 ABSMEM） + 全局二分命中**，在保证**可解释的 SAFE 语义**前提下，稳定地还原了 `vmlinux` 中函数级依赖关系；构建阶段**直接裁剪**到 SAFE 子图；查询阶段返回**运行时地址**与基本属性，满足论文实验与工程落地双重需求。

> 代码入口与全部实现细节均在 `krg.cpp`，配合 `--debug / --dbg-sym` 可复现实验中的每一条边与每一次判定。
