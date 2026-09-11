#!/usr/bin/env python3
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def exact_throughput(row: dict[str, str]) -> float:
    byte_count = int(row["bytes"])
    repeats = int(row["repeats"])
    elapsed_ns = int(row["elapsed_ns"])
    if byte_count <= 0 or repeats <= 0 or elapsed_ns <= 0:
        raise ValueError("bytes, repeats, and elapsed_ns must be positive")
    return (
        byte_count * repeats / (1024.0 * 1024.0)
    ) / (elapsed_ns / 1.0e9)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--aggregate", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    with args.input.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit("raw CSV is empty")

    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    paired: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in rows:
        backend = row["backend"]
        case = row["case"]
        run = int(row["outer_run"])
        # Derive the statistic from lossless counters.  The human-readable
        # throughput column is rounded and must not feed paired ratios.
        throughput = exact_throughput(row)
        grouped[(case, backend)].append(throughput)
        paired[(case, run)][backend] = throughput

    args.aggregate.parent.mkdir(parents=True, exist_ok=True)
    with args.aggregate.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("case", "backend", "runs", "median_mib_s",
                         "p10_mib_s", "p90_mib_s"))
        for (case, backend), values in sorted(grouped.items()):
            writer.writerow((
                case, backend, len(values),
                f"{statistics.median(values):.3f}",
                f"{percentile(values, 0.10):.3f}",
                f"{percentile(values, 0.90):.3f}",
            ))

    ratios: dict[str, list[float]] = defaultdict(list)
    for (case, _run), values in paired.items():
        if set(values) != {"native", "kernel-vkso"}:
            raise SystemExit(f"incomplete backend pair for {case}")
        ratios[case].append(values["kernel-vkso"] / values["native"])

    lines = [
        "# XZ Embedded evaluation summary",
        "",
        "| Case | Native median MiB/s | Kernel-vkso median MiB/s "
        "| Paired kernel/native median | P10–P90 |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in sorted(ratios):
        native = statistics.median(grouped[(case, "native")])
        kernel = statistics.median(grouped[(case, "kernel-vkso")])
        ratio = statistics.median(ratios[case])
        lines.append(
            f"| {case} | {native:.2f} | {kernel:.2f} | {ratio:.3f}× "
            f"| {percentile(ratios[case], 0.10):.3f}–"
            f"{percentile(ratios[case], 0.90):.3f}× |"
        )
    lines += [
        "",
        "Ratios are formed within the same outer run before aggregation. "
        "The two-backend execution order rotates between outer rounds within one process and one deployment.",
    ]
    args.summary.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
