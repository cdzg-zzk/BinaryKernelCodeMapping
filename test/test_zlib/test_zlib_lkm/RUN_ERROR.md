# `test_zlib_lkm` 最近一次执行记录

## 执行命令

```bash
make -C /home/zzk/BinaryKernelCodeMapping/test/test_zlib/test_zlib_lkm run
```

## 实际输出

```text
LD_LIBRARY_PATH="/home/zzk/BinaryKernelCodeMapping/make_dll:/home/zzk/BinaryKernelCodeMapping/test/test_zlib/so:$LD_LIBRARY_PATH" ./test_zlib_lkm
zlib_lkm runtime is not ready: zlibVersion() would read slot 0x00007fb6f2e6f0f0 -> 0xffffffffc1565d79.
This usually means the page-cache replacement / kernel-page mapping step has not been applied to libzlib_lkm.so yet.
make: *** [Makefile:24: run] Error 3
```

## 结论

当前不是 harness 逻辑错误，而是 `libzlib_lkm.so` 的运行前置条件还没满足。

测试程序在真正调用 `zlibVersion()` 之前做了一个轻量探测：

- 读取 `zlibVersion()` 函数里 `mov disp32(%rip), %rax` 指向的槽位
- 发现该槽位当前值是 `0xffffffffc1565d79`
- 这个值明显还是内核高地址，不是可在用户态直接解引用的有效用户态地址

如果直接继续调用，程序会在首次触达该地址时段错误。之前的段错就是这么来的。

## 我这边的判断

更像是下面两类问题之一：

1. `page_cache_replace` / 你的页替换机制还没对 `libzlib_lkm.so` 完成运行前准备。
2. `zlibVersion()` 依赖的版本串槽位没有被改写成用户态可访问地址，仍然保留了原始内核地址。

仓库里已有线索和这个判断一致：

- `test/test_MACRO/investigate.md` 提到：如果代码页/相关页没被映射到内核页，执行会落到 stub 或错误地址。
- `test/test_zlib/zlib_lkm/README.md` 里也提到 `zlibVersion()` 被改成“从槽位读取版本串指针”，说明这条路径对槽位内容正确性很敏感。

## 你解决后我这边可以继续验证什么

一旦这个运行前置条件解决，我这里的 harness 会继续覆盖这些路径：

- `zlibVersion()` / `get_crc_table()`
- `crc32()` / `adler32()`
- `deflateInit2_()` / `deflate()` / `deflateEnd()`
- `deflateReset()`
- `deflateParams()`
- `deflatePending()`
- `deflatePrime()`
- `deflateSetDictionary()`
- 系统 `libz.so.1` 参考解压校验

## 额外备注

`../so/deflate_types.h` 当前不能直接被 C 编译器当作独立头文件使用，原因是 typedef/结构体定义顺序不满足独立编译条件。为了不改你现有导出物，我在测试目录里放了一个最小兼容头 `zlib_lkm_api.h` 来承接测试编译。
