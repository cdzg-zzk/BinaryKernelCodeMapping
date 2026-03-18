# zlib_user

这个目录保存 `B` 方案的用户态动态库源码和构建封装。

源码边界：

- 代码主体来自 [zlib_lkm](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_lkm)
- 只保留用户态必须的最小适配
- 目标产物是：
  - [libzlib_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_user/libzlib_user.so)
  - [pigz_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_user)

## 构建

在当前目录执行：

```bash
make clean
make
make pigz-user
```

构建结果：

- `make` 生成 `libzlib_user.so`
- `make pigz-user` 额外生成 `pigz_macro/pigz-2.8/pigz_user`

## 运行

在当前目录执行一次文件级 smoke test：

```bash
../pigz_macro/pigz-2.8/pigz_user -p 1 -k -f <input-file>
gzip -t <input-file>.gz
```

说明：

- `pigz_user` 在链接时已经写入当前目录的 `rpath`
- 正常情况下不需要额外设置 `LD_LIBRARY_PATH`
- 当前 `pigz_user` 仍会同时链接本地 `libzlib_user.so` 与系统 `libz.so.1`

## 清理

```bash
make clean
```

