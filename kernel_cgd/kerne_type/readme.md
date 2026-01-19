# vkso-gen-types

**vkso-gen-types** 是一个零 `libbpf` 依赖的命令行小工具，用于从 **内核 BTF** 中仅导出**指定函数所需**的数据类型（`struct/union/enum/typedef`）到一个**可在用户态直接包含**的头文件。它非常适合把“**安全可映射**”的内核函数迁移到用户态执行：只镜像这些函数**真正会用到**的类型布局，而不把整套内核头一股脑拉进来。

---

## 特性

* **只导出必要类型**：以函数原型为根，递归收集形参/返回值引用到的类型闭包。
* **适配老版本 `bpftool`**：自动尝试多种 JSON / `dump id` 语法；不支持按 ID 导出时，回退为“整份 C 导出 + **括号深度**切块解析”，保证嵌套 `union/struct` 也能正确截取。
* **无 libbpf 构建依赖**：仅需能运行的 `bpftool`；路径可通过 `--bpftool` 指定。
* **原生解析 SAFE `.krg`**：`--funcs-file` 可直接指向 `krg` 生成的二进制图，无需先转出文本列表；仍兼容旧的 `out.krg.safe`。
* **可指定 BTF 来源**：优先从 `/sys/kernel/btf/vmlinux` 读取；也可用 `--vmlinux` 指向带 `.BTF` 段的 `vmlinux`。
* **支持模块 BTF**：可通过 `--module/--modules` 指定 LKM BTF（需模块已加载，BTF 位于 `/sys/kernel/btf/<mod>`）。

---

## 工作流程（建议与 `krg` 配合）

1. 用你的 `krg` 工具构建“**安全函数**”子图，生成 SAFE 图 `out.krg`（若已有 `out.krg.safe` 文本清单也可继续使用）。`vkso-gen-types` 现已支持直接读取 `.krg`，会自动解析出函数名。
2. 运行 **vkso-gen-types**，只为这批函数导出它们所需的数据布局声明，生成 `vkso_types.h`。
3. 在用户态工程中 `#include "vkso_types.h"`，按同样布局分配对象，即可把安全函数映射到用户态执行（不影响内核）。

---

## 兼容性说明

* **bpftool**：工具内部优先使用 `btf dump file … -j` / `format json` 读取 JSON；导出时优先 `id <TYPE_ID>` / `type id <TYPE_ID>` 精确导出；若老版本不支持按 ID，则回退为整份导出再切块。
* **BTF 来源**：推荐使用与当前运行内核完全一致的 `vmlinux-$(uname -r)`（debug 版，包含 `.BTF` 段），以避免类型不匹配。
* **模块 BTF**：`.ko` 文件通常无法被 bpftool 直接读取，本工具会优先解析 `/sys/kernel/btf/<mod>`；若该路径不存在，请先加载模块并确保内核开启模块 BTF。

---

## 输出内容

生成的头文件（例如 `vkso_types.h`）包含：

* 目标函数原型**所需**的 `struct/union/enum/typedef` 布局定义（不包含函数声明与实现）
* 必要的基础头：`<stddef.h> / <stdint.h>`
* 每个导出的实体都会以注释标注其 **BTF 类型 ID**（便于对照/溯源）

> 仅按函数**签名**做类型闭包：函数体内部用到的类型不会被导出。只要 ABI 与入参布局正确，这对调用是足够的；若你需要函数内部类型做调试或自建布局，请使用 bpftool 全量导出模块 BTF。

---

## 依赖

* 可运行的 **`bpftool`**（建议使用与当前内核匹配的 `linux-tools-$(uname -r)` 内的版本）：

  * Ubuntu/Debian：`sudo apt-get install -y linux-tools-$(uname -r) linux-tools-common`
  * 或 `sudo apt-get install -y bpftool`（若仓库提供）

---

## 常见问题

* **`bpftool not found`**：用包管理器安装；或用 `--bpftool /full/path/to/bpftool` 指定路径。
* **老版本 `bpftool` 不支持 `id/type id`**：工具会自动回退为“整份导出 + 切块”，并使用**括号深度**计数，避免 `struct` 中嵌套 `union` 被截断。
* **没有 `/sys/kernel/btf/vmlinux`**：改用 `--vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r)`。
* **`--funcs-file` 报 UnicodeDecodeError**：检查你是否误传了 SAFE 的 `.krg`；现在脚本会自动解析，但若文件损坏或格式不同，请重新用 `krg` 生成，或先转成 `out.krg.safe` 再传入。
* **模块类型未输出**：请确认模块已加载且 `/sys/kernel/btf/<mod>` 存在；若函数名不在模块 BTF 中会直接报错；注意该工具只按函数签名导出类型，不包含函数体内部类型。

---

## 目录结构

```
vkso_gen_types.py   # 本工具（Python，无需 libbpf，依赖 bpftool）
vkso_types.h        # 运行后生成的类型镜像头（示例）
```

---

## 参数说明

* `--funcs-file <path>`：函数名来源。可直接传 `krg` 生成的 **二进制 SAFE 图**（如 `out.krg`，脚本会解出符号）；也可传 UTF-8 文本网（如 `out.krg.safe`），每行一个函数名，可包含 `#` 注释。
* `--funcs name1,name2,...`：直接在命令行指定函数名（逗号分隔）
* `--out <file>`：输出头文件路径（缺省 stdout）
* `--btf <path>`：BTF 二进制路径（默认 `/sys/kernel/btf/vmlinux`）
* `--vmlinux <path>`：带 `.BTF` 段的 `vmlinux` 文件（与 `--btf` 互斥，二选一）
* `--bpftool <path>`：`bpftool` 可执行文件路径；不指定则自动搜索常见位置（`/usr/lib/linux-tools-$(uname -r)/bpftool` 等）
* `--module <mod>`：附加模块 BTF 源（可重复）。可传模块名或 `.ko` 路径，脚本会优先解析 `/sys/kernel/btf/<mod>`。
* `--modules <m1,m2,...>`：逗号分隔的模块 BTF 源，语义同 `--module`。

---

## 实现细节（简述）

* 解析 BTF（JSON）：自动适配多种 `bpftool` 输出风格；得到一个类型对象列表。
* 以函数 **FUNC_PROTO** 为根，对 `ret_type` 和各 `param.type` 做**递归闭包**：
  `typedef/const/volatile/restrict` → 基类型；`ptr` → 指向类型；`array` → 元素类型；`struct/union` → 成员类型；`func_proto/func` → 继续展开原型。
* 导出：

  * 新/旧 `bpftool` 支持**按 ID 导出**时优先逐个导出；
  * 否则回退为**整份导出**并用**括号深度**切块，精准截取 `struct/union/enum/typedef`。

---

## 使用方法

> 下面给出两种最常用的调用方式；实际以你的环境为准替换路径。

### A) 与 `krg` 联动（按安全函数清单导出）

```bash
# 1) 构建安全子图
./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) -o out.krg
```

`krg` 会产生二进制 `out.krg`。如果你更偏好文本版，可用项目内脚本自行转成 `out.krg.safe`；两者均被支持。

```bash
# 2) 生成类型头
sudo ./vkso_gen_types.py \
  --funcs-file out.krg \
  --vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r) \
  --bpftool /usr/lib/linux-hwe-5.15-tools-5.15.0-139/bpftool \
  --out vkso_types.h
```

> 若你提供的是 `out.krg.safe` 或任何 UTF-8 清单，把 `--funcs-file out.krg` 替换为对应路径即可。

### B) 单函数试用（不依赖 `krg`）

```bash
# 仅为某个函数（如 klist_add_head）导出其所需类型
sudo ./vkso_gen_types.py \
  --funcs klist_add_head \
  --vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r) \
  --bpftool /usr/lib/linux-hwe-5.15-tools-5.15.0-139/bpftool \
  --out vkso_types.h
```

> 生成后的 `vkso_types.h` 即可在你的用户态工程中直接包含与使用。

### C) 含模块函数（LKM）

```bash
# 确保模块已加载，BTF 会出现在 /sys/kernel/btf/<mod>
sudo modprobe lz4_compress lz4hc_compress

sudo ./vkso_gen_types.py \
  --funcs-file /home/zzk/workspace/KernelCodeMapping/make_dll/symbols.txt \
  --module lz4_compress \
  --module lz4hc_compress \
  --out vkso_types.h
```

---

## 仅提取模块类型的备选办法（bpftool/pahole）

有时你只想从模块中导出完整类型定义，而不走本脚本的"按函数签名闭包"流程。以下是可用的手工方式。

### 1) 模块已加载：从 /sys/kernel/btf/<mod> 直接导出

```bash
sudo modprobe your_module
ls -l /sys/kernel/btf | grep -E 'your_module'

sudo bpftool -B /sys/kernel/btf/vmlinux \
  btf dump file /sys/kernel/btf/your_module format c \
  > your_module_types.h
```

说明:
- 模块 BTF 常是 split BTF, 建议显式传 `-B /sys/kernel/btf/vmlinux` 作为 base.
- 若 `/sys/kernel/btf/<mod>` 不存在, 说明模块无 BTF 或内核未启用模块 BTF.

### 2) 只有 .ko 文件: 先确认是否包含 BTF

```bash
readelf -S your_module.ko | grep -E '\\.BTF(\\.base|\\.ext)?'

bpftool -B /sys/kernel/btf/vmlinux \
  btf dump file ./your_module.ko format c \
  > your_module_types.h
```

说明:
- 若模块与当前内核不是同一套构建产物, split BTF 引用可能失效, 直接 dump 失败是正常的.
- 最稳的方法仍是加载模块后从 `/sys/kernel/btf/<mod>` 导出.

### 3) 没有 BTF: 退回 DWARF (pahole)

```bash
pahole -C your_struct ./your_module.ko
# 或 debug 文件:
pahole -C your_struct /usr/lib/debug/.../your_module.ko.debug
```
