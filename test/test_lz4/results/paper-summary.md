# LZ4 论文结果摘要

## 实验有效性

- 正式数据包含 7 个同一部署内的 outer rounds、3 个 block sizes、5 个后端。
- 每个表格比值先在相同 outer round 内配对，再报告 7 个配对比值的中位数与 P10–P90。
- 计时核心是未修改的 LZ4 1.9.3 `programs/bench.c`；薄适配层只负责把 block API 转发到对应 DSO。
- 五个压缩器与五个解压器已在 12 个边界长度上完成全交叉正确性验证；官方 harness 还对每个 Silesia case 执行 XXH64 校验。
- native 版本允许 `-march=native` 和 glibc IFUNC memory helpers；no-SIMD 版本禁用编译器 SIMD，并使用测试内 `rep movsb/rep stosb` helper，机器码审计为 0 个 SIMD/MMX 命中且无外部 memory helper。

## 配对性能比

比值大于 1 表示分子更快。

| Comparison | Operation | Block | Median | P10–P90 |
| --- | --- | ---: | ---: | ---: |
| `vkso_vs_upstream_native` | compress | 4,096 | 1.0357x | 1.0351–1.0369x |
| `vkso_vs_upstream_native` | compress | 65,536 | 1.0087x | 1.0082–1.0104x |
| `vkso_vs_upstream_native` | compress | 1,048,576 | 1.0075x | 1.0059–1.0144x |
| `vkso_vs_upstream_native` | decompress | 4,096 | 0.9610x | 0.9579–0.9636x |
| `vkso_vs_upstream_native` | decompress | 65,536 | 0.9723x | 0.9701–0.9733x |
| `vkso_vs_upstream_native` | decompress | 1,048,576 | 0.9228x | 0.9207–0.9257x |
| `vkso_vs_kernel_user_native` | compress | 4,096 | 1.0472x | 1.0459–1.0488x |
| `vkso_vs_kernel_user_native` | compress | 65,536 | 1.0372x | 1.0364–1.0391x |
| `vkso_vs_kernel_user_native` | compress | 1,048,576 | 1.0475x | 1.0467–1.0488x |
| `vkso_vs_kernel_user_native` | decompress | 4,096 | 1.0379x | 1.0373–1.0400x |
| `vkso_vs_kernel_user_native` | decompress | 65,536 | 1.0173x | 1.0135–1.0185x |
| `vkso_vs_kernel_user_native` | decompress | 1,048,576 | 1.0320x | 1.0281–1.0333x |
| `vkso_vs_kernel_user_nosimd` | compress | 4,096 | 1.0234x | 1.0224–1.0245x |
| `vkso_vs_kernel_user_nosimd` | compress | 65,536 | 1.0196x | 1.0184–1.0207x |
| `vkso_vs_kernel_user_nosimd` | compress | 1,048,576 | 1.0040x | 1.0027–1.0055x |
| `vkso_vs_kernel_user_nosimd` | decompress | 4,096 | 0.9870x | 0.9809–0.9898x |
| `vkso_vs_kernel_user_nosimd` | decompress | 65,536 | 0.9817x | 0.9787–0.9837x |
| `vkso_vs_kernel_user_nosimd` | decompress | 1,048,576 | 0.9848x | 0.9837–0.9882x |
| `kernel_nosimd_vs_kernel_native` | compress | 4,096 | 1.0230x | 1.0222–1.0246x |
| `kernel_nosimd_vs_kernel_native` | compress | 65,536 | 1.0175x | 1.0167–1.0188x |
| `kernel_nosimd_vs_kernel_native` | compress | 1,048,576 | 1.0440x | 1.0416–1.0447x |
| `kernel_nosimd_vs_kernel_native` | decompress | 4,096 | 1.0525x | 1.0497–1.0573x |
| `kernel_nosimd_vs_kernel_native` | decompress | 65,536 | 1.0374x | 1.0336–1.0379x |
| `kernel_nosimd_vs_kernel_native` | decompress | 1,048,576 | 1.0454x | 1.0418–1.0497x |
| `upstream_nosimd_vs_native` | compress | 4,096 | 1.0400x | 1.0386–1.0414x |
| `upstream_nosimd_vs_native` | compress | 65,536 | 1.0339x | 1.0327–1.0355x |
| `upstream_nosimd_vs_native` | compress | 1,048,576 | 1.0430x | 1.0423–1.0497x |
| `upstream_nosimd_vs_native` | decompress | 4,096 | 1.0130x | 1.0120–1.0186x |
| `upstream_nosimd_vs_native` | decompress | 65,536 | 1.0184x | 1.0173–1.0211x |
| `upstream_nosimd_vs_native` | decompress | 1,048,576 | 1.0067x | 1.0049–1.0085x |

## 等权几何平均

- `vkso_vs_upstream_native`: 0.9840x
- `vkso_vs_kernel_user_native`: 1.0365x
- `vkso_vs_kernel_user_nosimd`: 0.9999x
- `kernel_nosimd_vs_kernel_native`: 1.0365x
- `upstream_nosimd_vs_native`: 1.0257x
- `kernel_vs_upstream_native`: 0.9495x
- `kernel_vs_upstream_nosimd`: 0.9593x

## 可用于论文的结论

1. `kernel-vkso` 相对 upstream native 的六个 operation/block 组合等权几何平均为 0.9840x。它在三个压缩 block 上均略快，但在三个解压 block 上均较慢，因此不能概括为 kernel 或 user-space 单方面占优。
2. `kernel-vkso` 相对同源 kernel-userspace native 为 1.0365x，相对同源 kernel-userspace no-SIMD 为 0.9999x。后者接近 1，说明 vkso 路径在本实验中基本保持了同一 kernel 算法的用户态可执行性能量级。
3. kernel 源码的 no-SIMD+REP 版本相对 native+glibc 版本为 1.0365x；upstream 对应比值为 1.0257x。这里 no-SIMD 没有变慢，说明这些 LZ4 路径的性能不能只由 SIMD 可用性解释。
4. 在相同 native 编译制度下，kernel 算法相对 upstream 为 0.9495x；在 no-SIMD+REP 制度下为 0.9593x。剩余差异主要来自算法版本、控制流、内存复制策略和 Kbuild/用户态编译差异。

## 解释限制

- no-SIMD 与 native 的对比同时改变了 memory-helper 实现，这是为了保证完整被测调用路径不借助 glibc SIMD；因此该对比不能被表述为纯粹的单因素 SIMD 消融。
- LZ4 官方 harness 报告每次 time window 内的最快完整循环；本文再对一次部署内各 outer round 的结果取中位数。每个 round/block/backend 启动新进程，owner module 和页面注册在轮次间保留。它适合吞吐比较，但不表示尾延迟。
- 这是内存常驻的 block compression component benchmark，不包含文件系统 I/O、系统调用和分配成本，不应称作完整应用宏基准。
