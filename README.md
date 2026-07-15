# BinaryKernelCodeMapping

本项目把 Linux 内核或已加载模块中的函数以普通动态库 API 的形式暴露给用户进程。生成的 `.so` 本身保存 ELF 布局、动态符号和占位页；`page_cache_replace` 再把其中的 `.text` / `.rodata` 文件页替换为对应的内核页，从而完成 page grafting。用户程序最终可以通过正常的链接或 `dlopen(3)` / `dlsym(3)` 路径调用目标函数。

> 这是面向研究和实验的 x86_64 原型。页缓存替换由内核模块执行，必须在与 `vmlinux`、BTF 和目标 `.ko` 完全匹配的测试内核上运行，不应部署到生产环境。

## 项目架构

| 目录 | 职责 | 主要输入/输出 |
| --- | --- | --- |
| `kernel_cgd/src/` | 构建 SAFE/KRG 符号依赖图，解析函数闭包及运行时地址 | `vmlinux`、可选 `.ko` → `out.krg` |
| `kernel_cgd/function_checker/` | 检查每个导出 API 的闭包、特权指令、绝对重定位、Shim 边界和静态数据引用 | API、`vmlinux`、`.ko`、`shim.txt` → PASS/FAIL 报告 |
| `kernel_cgd/kerne_type/` | 从 vmlinux/模块 BTF 提取调用 API 所需的最小类型闭包和函数声明 | `symbols.txt`、BTF → `vkso_types.h` |
| `make_dll/` | 根据 KRG 手工构造稀疏 ELF64 DSO，并按需构建用户态语义替代库 | KRG、`symbols.txt`、`shim.txt` → `lib<owner>.so`、可选 `libshim.so`、地址清单 |
| `page_cache_replace/` | 内核模块与用户态 manager；按 ELF 页布局执行替换和恢复 | DSO、地址清单 → 活跃 page graft |
| `test/` | evaluation 与历史实验，主工作流不依赖这里的固定路径 | 实验数据与基准程序 |
| `paper/` | 论文材料，不参与构建 | 文档 |

更深入的组件说明见 [Function Checker](kernel_cgd/function_checker/Readme.md) 和 [BTF 类型生成器](kernel_cgd/kerne_type/readme.md)。

端到端数据流如下：

```text
vkso/symbols.txt
      │
      ├── functions_checker.py ──> metadata/checks/*.log
      │
      ├── krg + vmlinux + .ko ──> metadata/out.krg
      │                              │
      ├── vkso_gen_types.py ──> include/vkso_types.h
      │                              │
      └── build_PIC_so.py ────> lib/lib<owner>.so
                                     │
                          manager + page_cache_replace.ko
                                     │
                          内核 .text/.rodata 页 graft
                                     │
                              用户程序正常调用 API
```

## 一键工作流

根目录的 `vkso` 脚本统一处理检查、KRG、头文件、DSO、Shim、内核模块、页替换和恢复。每个用户程序拥有独立工作区，不再依赖仓库内实验目录的固定路径。

假设用户程序位于 `/test_work/main.c`，要使用内核的 `xxh32`：

```bash
cd /home/zzk/BinaryKernelCodeMapping
./vkso init /test_work
```

编辑 `/test_work/vkso/symbols.txt`，每行填写一个需要暴露给用户态的 API：

```text
xxh32
```

只生成产物并执行静态验证：

```bash
./vkso build /test_work
```

编译用户程序时使用生成的头文件和 DSO：

```bash
gcc -O2 /test_work/main.c \
  -I/test_work/vkso/include \
  -L/test_work/vkso/lib -lkernel \
  -Wl,-rpath,/test_work/vkso/lib \
  -o /test_work/main
```

一条命令完成重新构建、页替换、运行程序，并在程序退出、失败或收到信号时恢复原始页：

```bash
./vkso exec /test_work -- /test_work/main
```

`vkso` 只对需要读取完整运行时内核地址、加载内核模块和发送替换请求的步骤调用 `sudo`；普通构建产物仍归当前用户所有。

### 模块内 API

如果 API 位于一个 LKM 中，把模块同时传给 KRG、checker 和 BTF 类型生成器。单个 `--module` 会自动作为 owner `.ko`；多个模块时应显式给出导出 API 所属模块：

```bash
./vkso build /test_work \
  --module /path/to/xxhash.ko \
  --owner-ko /path/to/xxhash.ko
```

模块必须与运行内核匹配并保留符号表。为生成 API 头，模块还应带可由 `bpftool` 读取的 BTF；通常应使用当前内核的 Kbuild 自动生成 split BTF。

### 命令

| 命令 | 行为 |
| --- | --- |
| `./vkso init WORKDIR` | 创建目录和示例 `symbols.txt`，不覆盖已有文件 |
| `./vkso build WORKDIR` | 检查闭包并生成 KRG、header、DSO、按需 Shim 与元数据 |
| `./vkso replace WORKDIR` | 重新构建并应用替换；替换会一直保留到显式 restore |
| `./vkso exec WORKDIR -- CMD...` | 重新构建，受控替换，运行 CMD，并自动恢复；推荐方式 |
| `./vkso restore WORKDIR` | 恢复 `replace` 留下的页面 |
| `./vkso restore WORKDIR --unload-module` | 恢复后卸载 `page_cache_replace` |
| `./vkso status WORKDIR` | 显示当前产物路径和内核模块状态 |

常用选项：

- `--vmlinux PATH`：覆盖默认 `/usr/lib/debug/boot/vmlinux-$(uname -r)`。
- `--btf PATH`：覆盖默认 `/sys/kernel/btf/vmlinux`。
- `--krg PATH`：复用显式指定的 KRG。未指定时，脚本会按 boot ID、vmlinux 和模块元数据安全缓存 KRG。
- `--module PATH`：追加参与闭包分析的模块，可重复。
- `--owner-ko PATH`：向 DSO 构建器提供 owner 模块布局和 `.data` 重定位。
- `--shim-list PATH`：覆盖 `make_dll/shim.txt`；显式导出的顶层 API 始终保留真实内核实现，Shim 只替代其依赖。
- `--skip-check`：跳过静态准入检查，仅用于明确知道风险的调试场景。

完整帮助可运行 `./vkso help` 查看。

## 工作区规范

```text
/test_work/
├── main.c
├── main
└── vkso/
    ├── symbols.txt                 # 用户维护的 API 输入
    ├── include/
    │   └── vkso_types.h            # 最终头文件
    ├── lib/
    │   ├── libkernel.so            # 或 lib<module>.so
    │   └── libshim.so              # 仅在 DSO 包含对应 DT_NEEDED 时存在
    ├── metadata/
    │   ├── outputs.env             # 当前产物的绝对路径
    │   ├── out.krg                 # 当前内核/模块对应的 KRG
    │   ├── out.krg.inputs          # KRG 缓存指纹
    │   ├── resolved_symbol_addresses.txt
    │   ├── module_deps.txt
    │   ├── checks/
    │   └── page_replace.log
```

每次构建只在系统临时目录（通常是 `/tmp`）暂存未完成产物，验证成功后才安装到 `include/`、`lib/` 和 `metadata/`，随后立即删除 staging。应用工作区不保存工具副本：`krg` 使用 `kernel_cgd/src/krg`，manager 和内核模块使用 `page_cache_replace/manager`、`page_cache_replace/page_cache_replace.ko`。KRG 含本次启动和模块集合对应的运行时地址，因此作为应用构建元数据保存在 `metadata/out.krg`。

## 依赖与前置条件

- x86_64 Linux，运行内核与 debug `vmlinux` 匹配。
- 当前内核的 `/lib/modules/$(uname -r)/build`。
- `gcc`、支持 C++20 的 `g++`、`make`、`binutils`、`bpftool`、Capstone 开发库。
- Python 3、`capstone` 和 `pyelftools`。
- 内核开启 BTF，默认可读取 `/sys/kernel/btf/vmlinux`。
- 允许通过 `sudo` 读取内核运行时地址并加载实验内核模块。

Debian/Ubuntu 上的典型依赖为：

```bash
sudo apt install build-essential linux-headers-$(uname -r) \
  binutils bpftool libcapstone-dev python3-pip
python3 -m pip install --user capstone pyelftools
```

## 安全与恢复

- `exec` 是推荐入口：manager 以 `--hold` 运行，并在用户程序退出时恢复；脚本还在退出 trap 中做二次恢复检查。
- `replace` 为手工实验保留替换状态。结束后必须运行 `restore`，不要在替换期间覆盖、截断或删除目标 DSO。
- 如果终端异常退出，可在同一工作区运行 `./vkso restore WORKDIR`。manager 的短期进程状态位于项目级 `page_cache_replace/runtime/`，操作日志位于应用的 `vkso/metadata/page_replace.log`。
- 如果静态 checker 返回 `FAIL` 或 `INCOMPLETE`，构建默认停止。不要把 `--skip-check` 当作通过安全审计的替代品。
- `libshim.so` 只对 `shim.txt` 中明确实现的依赖 API 提供近似用户态语义；`symbols.txt` 显式导出的同名顶层 API 仍使用真实内核实现。新增条目时必须同步实现并验证 ABI/语义。
