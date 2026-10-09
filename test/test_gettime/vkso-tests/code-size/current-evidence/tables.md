# 工作 1、2：数值表

所有主表值来自同目录 CSV/JSON；单位和范围见 README.md。

## 同功能源码职责切片

| 职责（非空非注释物理源码行） | Raw | VKSO |
| --- | --- | --- |
| 用户读取计算切片 | 281 | 0 |
| 普通内核读取实现（含原入口） | 163 | 0 |
| 共享读取计算与协议 | 0 | 292 |
| 数据 ABI 与布局断言 | 89 | 182 |
| 用户适配、初始化及用户 provider/fallback | 147 | 384 |
| 内核适配及 syscall 边界 | 103 | 265 |
| 状态发布 | 80 | 85 |
| 映射与 namespace | 335 | 232 |
| provider 接入 | 17 | 13 |
| 其余运行接入声明 | 91 | 22 |
| 构建与链接 | 158 | 87 |
| getcpu 专属实现与适配 | 23 | 62 |
| 时间及共用接入小计（去除 getcpu 专属行） | 1464 | 1562 |
| 功能切片合计 | 1487 | 1624 |
| 保留读取/分派切片（另列） | 91 | 147 |
| 功能 + 上述保留切片 | 1578 | 1771 |
| 共同数学/provider 契约切片（另列） | 31 | 31 |
| 通用构建/注册设施（完整列入的文件，另列） | 336 | 3974 |

普通 Raw 内核函数混合计算与返回 ABI，不能把第一至第三行直接换算成纯算法缩减率。功能合计以共同 Linux/libc 设施为边界；新增公开库、初始化和完整用户头文件均计入 VKSO。最后一行是实际复用设施的文件规模，不按本案例虚构摊销比例；不是整套工具链总量。

## 实际 clean 实验包二进制

| 配置 | 方案 | 项目 | 字节 | 口径 |
| --- | --- | --- | --- | --- |
| normal | Raw | 11 ordinary kernel entry extents | 1456 | kallsyms extents including padding; shared callees separate |
| normal | VKSO | 11 ordinary kernel entry extents | 736 | kallsyms extents including padding; shared callees separate |
| normal | Raw | native time/getcpu vDSO symbols | 1515 | ELF st_size; SGX excluded |
| normal | VKSO | shared time/getcpu function bodies | 1188 | ELF st_size; alignment and general thunk page separate |
| normal | Raw | embedded-vdso .text | 1853 | native DSO including SGX |
| normal | VKSO | direct/libvkso_time.so .text | 760 | user private |
| normal | VKSO | carrier shared backing: count once with kernel executable sections | 8192 | reserved page bytes, not function body bytes |
| normal | VKSO | carrier user private executable sections | 4096 | reserved page bytes, not function body bytes |
| no-retpoline | Raw | 11 ordinary kernel entry extents | 1392 | kallsyms extents including padding; shared callees separate |
| no-retpoline | VKSO | 11 ordinary kernel entry extents | 704 | kallsyms extents including padding; shared callees separate |
| no-retpoline | Raw | native time/getcpu vDSO symbols | 1515 | ELF st_size; SGX excluded |
| no-retpoline | VKSO | shared time/getcpu function bodies | 1149 | ELF st_size; alignment and general thunk page separate |
| no-retpoline | Raw | embedded-vdso .text | 1853 | native DSO including SGX |
| no-retpoline | VKSO | direct/libvkso_time.so .text | 760 | user private |
| no-retpoline | VKSO | carrier shared backing: count once with kernel executable sections | 4096 | reserved page bytes, not function body bytes |
| no-retpoline | VKSO | carrier user private executable sections | 4096 | reserved page bytes, not function body bytes |

这些行是相互重叠的视图，不相加为总体内存：共享函数体属于共享代码页，carrier 的相应页与内核具有相同 backing。内核入口 extent 包含对齐，ELF symbol size 不含函数间对齐。完整段、符号和设施计量分别保存在 binary-sections.csv、binary-symbols.csv。

## 正式裸机机制验证

| 配置 | 独立启动 | 每次 text 共享页 | 每次 data 共享页 | API / 选定快路径 / ABI及namespace / PFN |
| --- | --- | --- | --- | --- |
| normal | 4 | 2 | 1 | 全部通过 |
| no-retpoline | 4 | 1 | 1 | 全部通过 |

## 多进程记录到的唯一物理页

| 配置 | 方案 | 进程数 | 映射类别 | 四次启动 min–max |
| --- | --- | --- | --- | --- |
| no-retpoline | raw | 1 | vdso | 1–1 |
| no-retpoline | raw | 1 | vvar | 0–0 |
| no-retpoline | raw | 8 | vdso | 1–1 |
| no-retpoline | raw | 8 | vvar | 0–0 |
| no-retpoline | raw | 32 | vdso | 1–1 |
| no-retpoline | raw | 32 | vvar | 0–0 |
| no-retpoline | vkso | 1 | carrier | 4–4 |
| no-retpoline | vkso | 1 | mm_data | 1–1 |
| no-retpoline | vkso | 1 | public | 4–4 |
| no-retpoline | vkso | 8 | carrier | 11–11 |
| no-retpoline | vkso | 8 | mm_data | 1–1 |
| no-retpoline | vkso | 8 | public | 18–18 |
| no-retpoline | vkso | 32 | carrier | 35–35 |
| no-retpoline | vkso | 32 | mm_data | 1–1 |
| no-retpoline | vkso | 32 | public | 66–66 |
| normal | raw | 1 | vdso | 1–1 |
| normal | raw | 1 | vvar | 0–0 |
| normal | raw | 8 | vdso | 1–1 |
| normal | raw | 8 | vvar | 0–0 |
| normal | raw | 32 | vdso | 1–1 |
| normal | raw | 32 | vvar | 0–0 |
| normal | vkso | 1 | carrier | 5–5 |
| normal | vkso | 1 | mm_data | 1–1 |
| normal | vkso | 1 | public | 4–4 |
| normal | vkso | 8 | carrier | 12–12 |
| normal | vkso | 8 | mm_data | 1–1 |
| normal | vkso | 8 | public | 18–18 |
| normal | vkso | 32 | carrier | 36–36 |
| normal | vkso | 32 | mm_data | 1–1 |
| normal | vkso | 32 | public | 66–66 |

这是采集器在所列映射中记录到的 PFN，并非总内存。Raw vvar 记录为 0 个 present PFN，不能解释为没有状态页。Raw vDSO 在多进程间本来就共享；VKSO 的物理证据是额外跨用户/内核的页身份一致。
