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


LIBC_COMPARISONS = (
    ("vkso_vs_kernel_user_libc", "kernel-vkso", "kernel-userspace-libc"),
    ("kernel_libc_vs_kernel_rep", "kernel-userspace-libc", "kernel-userspace-nosimd"),
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
    backend_names = {row['backend'] for row in raw}
    comparisons = COMPARISONS + (LIBC_COMPARISONS if 'kernel-userspace-libc' in backend_names else ())
    lookup = {
        (
            int(row["run"]),
            row["backend"],
            row["operation"],
            int(row["block_size"]),
        ): float(row["official_mb_per_second"])
        for row in raw
    }
    if len(lookup) != len(raw):
        raise ValueError('duplicate round/backend/operation/block observation')
    runs = sorted({key[0] for key in lookup})
    blocks = sorted({key[3] for key in lookup})

    expected = {(r, b, op, block) for r in runs for b in backend_names
                for op in ('compress', 'decompress') for block in blocks}
    if set(lookup) != expected or not all(math.isfinite(v) and v > 0 for v in lookup.values()):
        raise ValueError('incomplete or invalid throughput matrix')
    pairwise: list[dict[str, object]] = []
    comparison_cells: dict[str, list[float]] = defaultdict(list)
    for comparison, numerator, denominator in comparisons:
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
        f"- 数据包含 {len(runs)} 个同一部署内的 outer rounds、{len(blocks)} 个 block sizes、{len(backend_names)} 个后端。",
        f"- 每个表格比值先在相同 outer round 内配对，再报告 {len(runs)} 个配对比值的中位数与 P10–P90。",
        "- 计时核心是未修改的 LZ4 1.9.3 `programs/bench.c`；薄适配层只负责把 block API 转发到对应 DSO。",
        "- 全交叉正确性结果见同部署 correctness.log；官方 harness 的校验记录保留在逐进程原始日志中。",
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
    selected_comparisons.update(c[0] for c in LIBC_COMPARISONS)
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
    for comparison, _, _ in comparisons:
        lines.append(f"- `{comparison}`: {overall[comparison]:.4f}x")

    lines += [
        "",
        "## 各项比较的观察范围",
        "",
    ]
    for comparison, _, _ in comparisons:
        selected = [r for r in pairwise if r['comparison'] == comparison]
        medians = [r['median_ratio'] for r in selected]
        lines.append(f"- `{comparison}`：{len(medians)} 项 operation/block 的配对中位数范围 "
                     f"{min(medians):.4f}–{max(medians):.4f}x；等权几何平均 {overall[comparison]:.4f}x。")
    if 'kernel-userspace-libc' in backend_names:
        lines += ["", "新增 libc 对照与 REP 同源 DSO 使用相同算法编译选项，只改变外部 memory-helper 的解析。",
                  "它的算法体无 SIMD，libc helper 可以使用 SIMD；实际目标地址的匹配见 helper-targets.json。",
                  "VKSO owner 使用 Kbuild，用户 DSO 使用 -O3/PIC；相同 helper 不等于相同机器码或单因素 PGOT 消融。"]
    lines += [
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
