# `libzlib_lkm.so` layout 偏移问题分析

这份说明对应本次 `zlib_lkm` stub DSO 的 builder 修复，方便直接和 `make_dll/` 下的脚本一起查看。

## 根因

`zlibVersion()` 在 `zlib_lkm.ko` 中仍然是正确的两级访问链：

```text
.text -> .data slot -> .rodata.str1.1
```

问题不在 `ctx` 方案本身，而在 stub DSO 重建布局时，`compute_core_layout()` 把下面两类 section 也算进了 runtime ro 区：

- `.return_sites`
- `.retpoline_sites`

这会把 `.data` 起点从真实模块需要的 `core+0x9000` 推迟到错误的 `core+0xa000`。

结果就是：

- 真实 LKM 代码里的 RIP-relative 位移仍然按 `core+0x9000` 去取 `.data`
- 但 stub DSO 把 `.data` 摆到了下一页
- 于是访问实际落进 `.rodata`
- 读出的就是已经被内核模块加载器修补过的内核绝对地址

## 证据

修复前复算 layout：

```text
ro_end=0xa000
data_start=0xa000
```

修复后复算 layout：

```text
ro_end=0x9000
data_start=0x9000
```

对 `zlib_lkm.ko` 做最小 section 排除试算时，只有去掉 `.return_sites/.retpoline_sites` 后，`.data_start` 才会从 `0xa000` 回到 `0x9000`；仅去掉 `.note.*` 并不能修复这个 case。

## 本次修改

已在下面两处同步加入非 core section 过滤：

- [build_PIC_so.py](/home/zzk/BinaryKernelCodeMapping/make_dll/build_PIC_so.py)
- [build_LKM_so.py](/home/zzk/BinaryKernelCodeMapping/make_dll/build_LKM_so.py)

过滤项为：

```python
".return_sites",
".retpoline_sites",
```

## 当前验证边界

builder 修复后重新生成的 stub DSO 已经放到：

- [libzlib_lkm.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so/libzlib_lkm.so)

但这份 stub 的 `.text4/.rodata/.data` 文件内容仍然是零页，后续仍需要启动 `page_cache_replace/manager` 做 page cache replace，才能看到真实 mapping 后的运行效果。

所以当前状态可以概括为：

1. layout 主因已经修复。
2. 最终运行效果仍依赖 manager 注入真实页。
