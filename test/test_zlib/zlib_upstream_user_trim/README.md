# zlib_upstream_user_trim

这个目录保存 `D_trim` 方案的用户态动态库构建封装。

源码边界：

- 基于 [pigz_macro/zlib-1.2.11](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/zlib-1.2.11) 的 upstream 源码
- 只保留 `pigz` 真正需要的最小 upstream 闭包
- 使用 [exports.map](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/exports.map) 控制导出 API
- 目标产物是：
  - [libzlib_upstream_user_trim.so](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/zlib_upstream_user_trim/libzlib_upstream_user_trim.so)
  - [pigz_upstream_user_trim](/home/zzk/BinaryKernelCodeMapping/test/test_zlib/pigz_macro/pigz-2.8/pigz_upstream_user_trim)

## 构建

在当前目录执行：

```bash
make clean
make
make pigz-upstream-user-trim
```

构建结果：

- `make` 生成 `libzlib_upstream_user_trim.so`
- `make pigz-upstream-user-trim` 额外生成 `pigz_macro/pigz-2.8/pigz_upstream_user_trim`

## 运行

```bash
../pigz_macro/pigz-2.8/pigz_upstream_user_trim -p 1 -k -f <input-file>
gzip -t <input-file>.gz
```

说明：

- `pigz_upstream_user_trim` 只依赖本地 `libzlib_upstream_user_trim.so`
- 这套构建用于更公平地和 `B/C` 做对照

## 清理

```bash
make clean
```
