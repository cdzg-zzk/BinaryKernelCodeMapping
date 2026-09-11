#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    raw = load_rows(args.input)
    groups: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        groups[(row["backend"], row["operation"], int(row["block_size"]))].append(row)

    aggregates: list[dict[str, object]] = []
    for (backend, operation, block_size), rows in sorted(groups.items()):
        throughputs = [float(row["mib_per_second"]) for row in rows]
        official_speeds = [float(row["official_mb_per_second"]) for row in rows]
        ratios = [float(row["compression_ratio"]) for row in rows]
        aggregates.append(
            {
                "backend": backend,
                "operation": operation,
                "block_size": block_size,
                "samples": len(rows),
                "median_mib_s": statistics.median(throughputs),
                "p10_mib_s": percentile(throughputs, 0.10),
                "p90_mib_s": percentile(throughputs, 0.90),
                "median_official_mb_s": statistics.median(official_speeds),
                "compression_ratio": statistics.median(ratios),
            }
        )

    lookup = {
        (str(row["backend"]), str(row["operation"]), int(row["block_size"])): row
        for row in aggregates
    }
    for row in aggregates:
        baseline = lookup[("user-default", str(row["operation"]), int(row["block_size"]))]
        row["speedup_vs_user_default"] = (
            float(row["median_mib_s"]) / float(baseline["median_mib_s"])
        )

    fieldnames = list(aggregates[0])
    with args.csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(aggregates)

    lines = [
        "# LZ4 userspace vs vkso kernel benchmark",
        "",
        "Medians combine outer rounds within one deployment. Each round/block/backend starts a new official-harness process; the owner module and page registration remain active across rounds.",
        "Measurements use the unmodified LZ4 1.9.3 `programs/bench.c` timing core through a thin DSO adapter.",
        "The official harness loads input and allocates state/output buffers before timing, adapts loop counts to approximately one second, and reports the fastest completed loop.",
        "`speedup` is throughput divided by `user-default` throughput, so values above 1 favor the selected backend.",
        "",
    ]
    for operation in ("compress", "decompress"):
        lines += [
            f"## {operation}",
            "",
            "| Block | Backend | Runs | Median MB/s | Median MiB/s | P10–P90 MiB/s | Ratio | Speedup |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        selected = [row for row in aggregates if row["operation"] == operation]
        for row in sorted(selected, key=lambda item: (int(item["block_size"]), str(item["backend"]))):
            lines.append(
                f"| {int(row['block_size']):,} | {row['backend']} | {row['samples']} | "
                f"{float(row['median_official_mb_s']):.2f} | "
                f"{float(row['median_mib_s']):.2f} | "
                f"{float(row['p10_mib_s']):.2f}–{float(row['p90_mib_s']):.2f} | "
                f"{float(row['compression_ratio']):.4f} | "
                f"{float(row['speedup_vs_user_default']):.4f}x |"
            )
        lines.append("")

    backends = sorted({str(row["backend"]) for row in aggregates})
    lines += [
        "## Overall",
        "",
    ]
    for backend in backends:
        speedups = [
            float(row["speedup_vs_user_default"])
            for row in aggregates
            if row["backend"] == backend
        ]
        geomean = math.exp(statistics.fmean(math.log(value) for value in speedups))
        lines.append(f"- `{backend}` geometric-mean speedup vs user-default: {geomean:.4f}x")
    lines.append("")
    args.summary.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
