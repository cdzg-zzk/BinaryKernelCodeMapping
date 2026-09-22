# Exported-kernel BCH adaptations

基线是 Ubuntu `linux-source-5.15.0/lib/bch.c`。保留有限域运算、编码/解码流程和错误定位语义；syndrome 循环显式缓存查表基址，
以指针推进输出位置。普通 DSO、owner 与匹配内核参考使用相同改写。完整差分见
[当前源码账本](../evaluation/results/section63/source-ledger/README.md)。

## 必要适配

1. **API namespacing**：四个公共接口改名为 `vkso_bch_init/free/encode/decode`，
   避免 owner LKM 与内核已有 BCH 符号冲突。用户显式导出的仍是这四个真实 LKM
   实现。
2. **闭包内编译器插桩移除**：关闭 fentry/mcount、stack protector、UBSAN、
   jump table、red-zone、retpoline 和 return thunk；BCH 本身没有 SIMD 路径，
   同时显式关闭 SSE/MMX/AVX 与自动向量化。`functions_checker` 对四个导出闭包均
   报告 instrumentation=0。
3. **只读表的 RIP-relative base**：`swap_bits_table` 与默认 primitive-polynomial
   table 标记为 const/used，并先用 `lea table(%rip), reg` 取得 base，再执行索引。
   这是原始 base+index 可能产生绝对地址寻址时的统一两指令改写；表内容不变。
4. **`kzalloc` 等价展开**：内联 `kzalloc` 会把 `kmalloc_caches` 这类内核私有数据
   带入闭包，因此替换成语义等价的 `kmalloc(GFP_KERNEL)` 加 `memset(0)`。
5. **四个 helper 的 owner-private slots**：`__kmalloc`、`kfree`、`memcpy`、
   `memset` 在正常 LKM 中由模块重定位把 slots 指向真实内核 helper；在生成 DSO
   时 slots 成为 private writable data，并重定位到 `libshim.so` 的用户态实现。
   不能使用加载后 text 中的 direct rel32 call，因为其位移已经绑定内核 helper
   地址，页面映射到用户态后无法再修改共享的 immutable machine code。
6. **BTF 与 runtime address**：owner module 经 `pahole -J --btf_base` 添加 BTF，
   并在每次 `insmod` 后重新执行 vkso；`resolved_symbol_addresses.txt` 因此记录本次
   实际加载实例的运行时地址，而非静态 `.ko` 地址。

## 构建警告说明

owner object 使用 `-mfunction-return=keep -mindirect-branch=keep`，所以在启用
RETHUNK/RETPOLINE 的 kernel build 环境中，objtool 会提示 naked return 和
indirect call。这里的机器码目标是在用户态复用：直接 `ret` 以及通过上述 slots
的间接调用是有意生成的；最终闭包检查、DSO 重定位审计和功能测试均会独立验证
这些边界。

## 对照公平性

`kernel-native` 编译同一份 `adapted/bch.c`，因此它包含相同的表寻址和
`kmalloc+memset` 语义，但普通用户态构建直接使用 libc compatibility helpers。
它是实际用户端执行成本的主要对照，包含两种构建及 helper 绑定的差异。`author-standalone` 来自较早的作者
用户态分支，不能假定与 Linux 5.15 source-identical，因此单独作为常用用户态
实现对照，并与同源对照分别报告。
