# zlib_upstream_user

这个目录保存 `D` 方案的用户态动态库构建封装。

源码边界：

- 直接使用 [pigz_macro/zlib-1.2.11](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/zlib-1.2.11) 的 upstream 源码
- 目标产物是：
  - [libzlib_upstream_user.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user/libzlib_upstream_user.so)
  - [pigz_upstream_user](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user)

## 构建

在当前目录执行：

```bash
make clean
make
make pigz-upstream-user
```

构建结果：

- `make` 生成 `libzlib_upstream_user.so`
- `make pigz-upstream-user` 额外生成 `pigz_macro/pigz-2.8/pigz_upstream_user`

## 运行

```bash
../pigz_macro/pigz-2.8/pigz_upstream_user -p 1 -k -f <input-file>
gzip -t <input-file>.gz
```

说明：

- `pigz_upstream_user` 只依赖本地 `libzlib_upstream_user.so`
- 不再依赖系统 `libz.so.1`

## 清理

```bash
make clean
```

