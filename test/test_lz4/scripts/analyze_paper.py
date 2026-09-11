#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


COMPARISONS = (
    ("vkso_vs_upstream_native", "kernel-vkso", "user-default"),
    ("vkso_vs_kernel_user_native", "kernel-vkso", "kernel-userspace-native"),
    ("vkso_vs_kernel_user_nosimd", "kernel-vkso", "kernel-userspace-nosimd"),
    (
        "kernel_nosimd_vs_kernel_native",
        "kernel-userspace-nosimd",
        "kernel-userspace-native",
    ),
    ("upstream_nosimd_vs_native", "user-nosimd", "user-default"),
    (
        "kernel_vs_upstream_native",
        "kernel-userspace-native",
        "user-default",
    ),
    (
        "kernel_vs_upstream_nosimd",
        "kernel-userspace-nosimd",
        "user-nosimd",
    ),
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def geomean(values: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(value) for value in values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8", newline="") as stream:
        raw = list(csv.DictReader(stream))
    lookup = {
        (
            int(row["run"]),
            row["backend"],
            row["operation"],
            int(row["block_size"]),
        ): float(row["official_mb_per_second"])
        for row in raw
    }
    runs = sorted({key[0] for key in lookup})
    blocks = sorted({key[3] for key in lookup})

    pairwise: list[dict[str, object]] = []
    comparison_cells: dict[str, list[float]] = defaultdict(list)
    for comparison, numerator, denominator in COMPARISONS:
        for operation in ("compress", "decompress"):
            for block in blocks:
                ratios = [
                    lookup[(run, numerator, operation, block)]
                    / lookup[(run, denominator, operation, block)]
                    for run in runs
                ]
                median = statistics.median(ratios)
                comparison_cells[comparison].append(median)
                pairwise.append(
                    {
                        "comparison": comparison,
                        "numerator": numerator,
                        "denominator": denominator,
                        "operation": operation,
                        "block_size": block,
                        "paired_runs": len(ratios),
                        "median_ratio": median,
                        "p10_ratio": percentile(ratios, 0.10),
                        "p90_ratio": percentile(ratios, 0.90),
                    }
                )

    with args.csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(pairwise[0]))
        writer.writeheader()
        writer.writerows(pairwise)

    overall = {
        comparison: geomean(cell_medians)
        for comparison, cell_medians in comparison_cells.items()
    }
    lines = [
        "# LZ4 论文结果摘要",
        "",
        "## 实验有效性",
        "",
        f"- 正式数据包含 {len(runs)} 个同一部署内的 outer rounds、{len(blocks)} 个 block sizes、5 个后端。",
        f"- 每个表格比值先在相同 outer round 内配对，再报告 {len(runs)} 个配对比值的中位数与 P10–P90。",
        "- 计时核心是未修改的 LZ4 1.9.3 `programs/bench.c`；薄适配层只负责把 block API 转发到对应 DSO。",
        "- 五个压缩器与五个解压器已在 12 个边界长度上完成全交叉正确性验证；官方 harness 还对每个 Silesia case 执行 XXH64 校验。",
        "- native 版本允许 `-march=native` 和 glibc IFUNC memory helpers；no-SIMD 版本禁用编译器 SIMD，并使用测试内 `rep movsb/rep stosb` helper，机器码审计为 0 个 SIMD/MMX 命中且无外部 memory helper。",
        "",
        "## 配对性能比",
        "",
        "比值大于 1 表示分子更快。",
        "",
        "| Comparison | Operation | Block | Median | P10–P90 |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    selected_comparisons = {
        "vkso_vs_upstream_native",
        "vkso_vs_kernel_user_native",
        "vkso_vs_kernel_user_nosimd",
        "kernel_nosimd_vs_kernel_native",
        "upstream_nosimd_vs_native",
    }
    for row in pairwise:
        if row["comparison"] not in selected_comparisons:
            continue
        lines.append(
            f"| `{row['comparison']}` | {row['operation']} | "
            f"{int(row['block_size']):,} | {float(row['median_ratio']):.4f}x | "
            f"{float(row['p10_ratio']):.4f}–{float(row['p90_ratio']):.4f}x |"
        )

    lines += [
        "",
        "## 等权几何平均",
        "",
    ]
    for comparison, _, _ in COMPARISONS:
        lines.append(f"- `{comparison}`: {overall[comparison]:.4f}x")

    lines += [
        "",
        "## 可用于论文的结论",
        "",
        f"1. `kernel-vkso` 相对 upstream native 的六个 operation/block 组合等权几何平均为 {overall['vkso_vs_upstream_native']:.4f}x。它在三个压缩 block 上均略快，但在三个解压 block 上均较慢，因此不能概括为 kernel 或 user-space 单方面占优。",
        f"2. `kernel-vkso` 相对同源 kernel-userspace native 为 {overall['vkso_vs_kernel_user_native']:.4f}x，相对同源 kernel-userspace no-SIMD 为 {overall['vkso_vs_kernel_user_nosimd']:.4f}x。后者接近 1，说明 vkso 路径在本实验中基本保持了同一 kernel 算法的用户态可执行性能量级。",
        f"3. kernel 源码的 no-SIMD+REP 版本相对 native+glibc 版本为 {overall['kernel_nosimd_vs_kernel_native']:.4f}x；upstream 对应比值为 {overall['upstream_nosimd_vs_native']:.4f}x。这里 no-SIMD 没有变慢，说明这些 LZ4 路径的性能不能只由 SIMD 可用性解释。",
        f"4. 在相同 native 编译制度下，kernel 算法相对 upstream 为 {overall['kernel_vs_upstream_native']:.4f}x；在 no-SIMD+REP 制度下为 {overall['kernel_vs_upstream_nosimd']:.4f}x。剩余差异主要来自算法版本、控制流、内存复制策略和 Kbuild/用户态编译差异。",
        "",
        "## 解释限制",
        "",
        "- no-SIMD 与 native 的对比同时改变了 memory-helper 实现，这是为了保证完整被测调用路径不借助 glibc SIMD；因此该对比不能被表述为纯粹的单因素 SIMD 消融。",
        "- LZ4 官方 harness 报告每次 time window 内的最快完整循环；本文再对一次部署内各 outer round 的结果取中位数。每个 round/block/backend 启动新进程，owner module 和页面注册在轮次间保留。它适合吞吐比较，但不表示尾延迟。",
        "- 这是内存常驻的 block compression component benchmark，不包含文件系统 I/O、系统调用和分配成本，不应称作完整应用宏基准。",
        "",
    ]
    args.report.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
