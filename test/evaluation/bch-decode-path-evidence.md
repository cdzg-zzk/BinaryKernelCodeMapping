# BCH decode 路径与计时边界核验

本次核验读取原 benchmark 源码、2026-07-17 的结果及保留的构建产物，没有运行 benchmark、guest 或修改核心实现。结论是：`decode-precomputed` 预先计算 ECC 差值，仍然计时 syndrome 计算、错误定位多项式和求根；有效的两错误输入在 t=4、t=8 下均进入二次多项式求根分支。两种 decode 模式使用不同错误向量，现有结果不能相减解释为配对的阶段开销。

## 可直接用于论文的表述

> BCH 使用两种输入接口测量错误定位延迟。`decode-full` 接收 512 B 数据和收到的 ECC，在计时区间内重新计算数据 ECC、与收到的 ECC 异或，并完成 syndrome 计算、错误定位多项式计算及求根。`decode-precomputed` 在计时前完成数据 ECC 计算和异或，将 ECC 差值交给解码器；syndrome 计算及后续错误定位仍包含在计时中。三种后端采用相同调用协议。控制结构初始化、测试缓冲区准备和实际翻转错误位均不包含在这两个 decode 指标内。

> 每个外层轮次在同一参数和模式下为三种后端使用相同错误向量，并轮换后端执行顺序。错误向量的种子包含模式编号，因此 `decode-full` 与 `decode-precomputed` 表示两种输入条件下的测量，其差值不用于分解单次解码的阶段成本。m=13、t=8、两错误时，预计算接口的配对延迟比中位数为 1.209，11 个轮次均慢于 native；full 接口对应为 1.039。两种参数配置下的有效两错误输入均使用二次求根分支，t=8 增加了 syndrome 数量及错误定位多项式的迭代上限。

这里的“配对延迟比”指同一模式、同一轮次的 vkso/native 比值；11 个轮次来自同一进程和部署。上段保持原结果的统计单位，并未增加独立重复或定位性能原因。

## 调用参数与实际工作

`src/bch_bench.c:223–242` 的 `prepare_decode_context` 在两种模式中分配并准备收到的 codeword。只有预计算模式额外调用对应后端的 encode，并将结果与收到的 ECC 逐字节异或。

`src/bch_bench.c:254–263` 的实际调用为：

```c
/* decode-precomputed */
decode(control, NULL, len, NULL, difference, NULL, errloc);
/* decode-full */
decode(control, work, len, work + len, NULL, NULL, errloc);
```

| 工作 | decode-precomputed 计时内 | decode-full 计时内 |
|---|---|---|
| 初始化 BCH 控制结构和查找表 | 否 | 否 |
| 分配缓冲区、复制 codeword、注入错误 | 否 | 否 |
| 从收到的数据重新计算 ECC | 否，在 prepare 中完成 | 是 |
| 将计算出的 ECC 与收到的 ECC 异或 | 否，在 prepare 中完成 | 是 |
| 将提供的 ECC 字节装载为对齐的内部字 | 是，装载预先异或的差值 | 是，装载收到的 ECC |
| syndrome 计算 | 是 | 有错误时是；无错误时提前返回 |
| Berlekamp–Massey 错误定位多项式 | 是 | 有错误时是 |
| 根据多项式次数求根并转换错误位置 | 有错误时是 | 有错误时是 |
| 翻转数据错误位、比较恢复后的 codeword | 否 | 否 |

两种调用的 `syn` 都为 NULL。Linux 实现的 `bch_decode` 只有在调用者提供非空 `syn` 时才跳过 syndrome 计算；benchmark 没有使用这个接口。`recv_ecc=NULL` 在预计算模式中表示异或已完成，并不表示 syndrome 已完成。

author 后端同样使用 `decode_once`，只是函数指针绑定到 `decode_bch`（`src/bch_bench.c:113–121`）。保留的 author 实现 `vendor/parrot-bch/lib/bch.c:987–1033` 也在 `syn=NULL` 时计算 syndrome，再调用错误定位多项式与求根。因此上述边界适用于全部三个后端。

`run_benchmark` 在 prepare 后进行最多 32 次预热，再调用 `measure_context`。计时循环重复使用同一个已损坏的工作缓冲区和已初始化的控制结构，返回错误位置，不在每次迭代中修复数据。`verify_decode` 的实际纠错和比较属于单独的 correctness 路径。无错误时，full 在 ECC 异或结果为零后提前返回；预计算模式不经过这个 `recv_ecc` 分支，仍计算零 syndrome 和零次定位多项式。

## m=13、两错误时的路径

`adapted/bch.c:966–998` 按 `poly->deg` 分派求根，与配置 t 的数值直接分派不同。有效两错误 codeword 的定位多项式次数为 2，因此 t=4 和 t=8 都选择 `find_poly_deg2_roots`。该分支通过 GF 查表、`xi_tab` 和平方校验求两个根；不会因 t=8 自动进入高次多项式分解。Berlekamp Trace 分解位于默认分支，通常处理次数大于 4 的多项式；Chien 搜索仅在 `USE_CHIEN_SEARCH` 条件编译分支中替换入口，保存的实际 owner/native 反汇编均显示低次分派及 BTZ 路径。

下表由源码中的运行时参数公式推导，不是新增运行测得的 helper 次数或时间：

| 工作量或尺寸 | m13/t4 | m13/t8 |
|---|---:|---:|
| `BCH_ECC_WORDS` | 2 | 4 |
| `BCH_ECC_BYTES` | 7 | 13 |
| syndrome 元素数 `2*t` | 8 | 16 |
| syndrome 清零字节数 | 32 | 64 |
| 两个 BM 多项式各自清零的字节数 | 40 | 72 |
| BM 外层迭代上限 | 4 | 8 |
| `load_ecc8` 末尾 memcpy 字节数 | 3 | 1 |
| 有效两错误输入选择的求根次数 | 2 | 2 |

syndrome 内循环还取决于 ECC 差值多项式中置位项；不同错误位置会改变查表、位扫描和条件分支的实际工作。源码中的 t 上限和尺寸变化不能单独解释 vkso 相对 native 的增量，因为同一参数下的 native 也执行这些算法步骤。当前材料没有逐次分支或 helper 指令指针记录；这里的两错误路径是源码与成功解码语义支持的路径推导。

## 构建产物能支持的诊断线索

现存 benchmark、native DSO、author DSO、owner 模块、carrier 和 shim 六个产物均与原 `results/artifacts.sha256` 记录匹配；当前 adapted 源码也与原 metadata 及本次两个完整 BCH guest 的源码快照一致。原 benchmark 的反汇编直接保留两种参数分派、prepare 中的 encode/XOR，以及 `CLOCK_PROCESS_CPUTIME_ID` 包围的重复 decode 循环。

- owner 的 `vkso_bch_decode` 已内联 syndrome 和 BM 主体，`find_poly_roots` 中已内联二次求根逻辑。没有独立符号不代表这些步骤被跳过。
- owner decode 在节内偏移 0x1eff、0x1f10 和 0x2216 通过 slot 间接调用 memset；BM 多项式复制通过同类 memcpy slot。native 对应路径调用 `memset@plt`、`memcpy@plt`，其 `load_ecc8` 的短尾复制使用 `__memcpy_chk@plt`。这证明静态调用形式不同，不证明运行时绑定的最终实现或性能影响。
- 原 carrier 的 decode 符号为 ELF 虚拟地址 0x2e80、长度 1,306 B，跨越 0x2000 与 0x3000 两个页；native 为 0x2720、长度 1,307 B，位于一个页。该静态布局差异同时存在于 t4 和 t8，不构成 I-cache、TLB 或前端停顿的测量证据。

## 原始两错误记录与仍不能推出的结论

从原 `raw.csv` 的整数 `total_ns/iterations` 重新构造每轮延迟，再计算同轮 vkso/native：

| 参数 | 模式 | 11 轮配对比值中位数 | vkso 较慢轮数 |
|---|---|---:|---:|
| m13/t4 | decode-precomputed | 0.968494 | 0/11 |
| m13/t4 | decode-full | 0.971847 | 0/11 |
| m13/t8 | decode-precomputed | 1.209496 | 11/11 |
| m13/t8 | decode-full | 1.038553 | 11/11 |

这些记录支持保留 t8 两错误退化，并将后续诊断范围收敛到实际经过的 ECC 装载、syndrome、BM 与二次求根路径。现有材料不能把 20.9% 归因于某个 helper、跨页布局、cache/TLB、指令数或分支预测，也不能把 1.039 与 1.209 的差异称为新增编码步骤“掩盖”了同一个固定退化。模式改变了错误向量，两个参数的 codeword 种子也不同；它们不是只改一个内部阶段的配对消融。

证据目录为 [results/bch-decode-path-20260912](results/bch-decode-path-20260912/)。其中 `capture.py` 只读取源码、ELF 和既有 CSV；`ledger.json` 保存路径、命令与来源，`artifact-identity.json` 连接原构建产物，`original-two-error-rows.csv` 保留 132 条原记录，`original-two-error-summary.json` 保存逐轮比值。`owner-recorded-compiler-flags.txt` 保留不存在可选 `.GCC.command.line` 节的 readelf 提示，实际保存的 owner 构建命令另见 `owner-build-command.txt`。
