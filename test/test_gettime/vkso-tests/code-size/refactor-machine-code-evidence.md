# VKSO源码去重机器码等价证据

日期：2026-07-28
基线提交：`9ad92a19598c52b7c28bc5bfc3f999d68edd2de2`
编译器：GCC 11.4.0
配置：`baremetal/artifacts/final-normal/vkso.config`

## Reader

重构前源码由基线提交取得，重构后源码使用相同Kbuild命令编译。比较目标为
`kernel/time/vkso_time_core.o`的`.vkso.text`：

```text
before sha256 317925e9b0d4d5ef819311f40613b1e9cc5814be52e30e86a17db944235fd1d2
after  sha256 317925e9b0d4d5ef819311f40613b1e9cc5814be52e30e86a17db944235fd1d2
relocation entries before/after: 30 / 30
relocation contents: identical
```

逐函数尺寸也完全相同：

| symbol | before | after |
|---|---:|---:|
| `vkso_clock_gettime_realtime` | 209 B | 209 B |
| `vkso_clock_gettime_monotonic` | 297 B | 297 B |
| `vkso_clock_gettime_realtime_coarse` | 46 B | 46 B |
| `vkso_clock_gettime_monotonic_coarse` | 103 B | 103 B |
| `vkso_clock_gettime_monotonic_raw` | 315 B | 315 B |
| `vkso_clock_gettime_boottime` | 300 B | 300 B |
| `vkso_clock_gettime_tai` | 212 B | 212 B |
| `vkso_clock_gettime_core` | 94 B | 94 B |

这证明宏重构只消除了手写源码重复，没有引入通用运行时分派，也没有改变reader
指令、布局或重定位。

## Update

将timekeeper转换移动到`vkso_time_compat.h`后，仍以`__always_inline`方式编入
原发布函数。`kernel/time/vkso_time.o`的`.text`比较结果：

```text
before sha256 a76e9a296c22fdcc4c05e53250eff69efbcc6987cf25a6d73f1f7ad95c999105
after  sha256 a76e9a296c22fdcc4c05e53250eff69efbcc6987cf25a6d73f1f7ad95c999105
```

| symbol | before | after |
|---|---:|---:|
| `vkso_time_publish` | 430 B | 430 B |
| `vkso_time_update_timezone` | 29 B | 29 B |
| `vkso_time_set_pvclock_page` | 12 B | 12 B |
| `vkso_time_set_hvclock_page` | 12 B | 12 B |

因此兼容层的物理拆分没有增加函数调用，也没有扩大reader可见的odd-seq区间。

## 完整导出与功能回归

使用生产normal配置重新构建内核、生成`libkernel.so`后，与提交`9ad92a1`裸机
性能基线中的DSO逐字节比较：

```text
baseline libkernel.so sha256 3faf6d3c8884a9dfafb49f0217b3f24167c1977d8f69c9700bf4f435f0cea13b
refactor libkernel.so sha256 3faf6d3c8884a9dfafb49f0217b3f24167c1977d8f69c9700bf4f435f0cea13b
cmp result: identical
```

QEMU使用Raw/VKSO两个完整kernel和同一ABI矩阵回归：

```text
qemu_backend=raw status=pass matrix_rows=76
qemu_backend=vkso status=pass matrix_rows=76
raw-vkso-matrix.diff: empty
qemu_preflight=pass
```

因此这次修改不需要用裸机噪声重新估计reader性能：性能实验实际执行的VKSO DSO
与重构后DSO是同一个字节序列。update侧也由前述发布对象`.text`完全相同覆盖。

no-retpoline实验配置也使用各自相同Kbuild命令比较了重构前后对象：

```text
reader .vkso.text before/after:
1b925e0c792f673cf14b86d44563dce0ce9636e3e734797b4f6d5e033033f034
update .text before/after:
d2fe46f250c775afaefb7a0a3c80d7fb57bec4f74a0781cc0303f59d1f9698cd
```

两个配置的reader和update比较结果均为逐字节相同。
