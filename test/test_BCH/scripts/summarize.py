#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


BACKENDS = ("kernel-vkso", "kernel-native", "author-standalone")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--paired", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit("raw input is empty")

    groups: dict[tuple[int, int, int, str, str], list[dict[str, str]]] = defaultdict(list)
    by_outer: dict[tuple[int, int, int, str, int], dict[str, float]] = defaultdict(dict)
    for row in rows:
        key = (
            int(row["m"]),
            int(row["t"]),
            int(row["errors"]),
            row["operation"],
            row["backend"],
        )
        groups[key].append(row)
        outer_key = key[:4] + (int(row["outer"]),)
        by_outer[outer_key][row["backend"]] = float(row["ns_per_op"])

    aggregates: list[dict[str, object]] = []
    for (m, t, errors, operation, backend), selected in sorted(groups.items()):
        latencies = [float(row["ns_per_op"]) for row in selected]
        throughputs = [float(row["mbit_per_second"]) for row in selected]
        aggregates.append(
            {
                "m": m,
                "t": t,
                "len": int(selected[0]["len"]),
                "errors": errors,
                "operation": operation,
                "backend": backend,
                "samples": len(selected),
                "median_ns_per_op": statistics.median(latencies),
                "p10_ns_per_op": percentile(latencies, 0.10),
                "p90_ns_per_op": percentile(latencies, 0.90),
                "median_mbit_per_second": statistics.median(throughputs),
            }
        )

    with args.aggregate.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(aggregates[0]))
        writer.writeheader()
        writer.writerows(aggregates)

    paired_groups: dict[tuple[int, int, int, str], list[dict[str, float]]] = defaultdict(list)
    for (m, t, errors, operation, _outer), values in sorted(by_outer.items()):
        missing = set(BACKENDS) - set(values)
        if missing:
            raise SystemExit(
                f"incomplete paired sample m={m} t={t} operation={operation} "
                f"errors={errors}: missing {sorted(missing)}"
            )
        paired_groups[(m, t, errors, operation)].append(values)

    paired: list[dict[str, object]] = []
    for (m, t, errors, operation), samples in sorted(paired_groups.items()):
        vkso_native = [
            sample["kernel-vkso"] / sample["kernel-native"] for sample in samples
        ]
        vkso_author = [
            sample["kernel-vkso"] / sample["author-standalone"]
            for sample in samples
        ]
        native_author = [
            sample["kernel-native"] / sample["author-standalone"]
            for sample in samples
        ]
        paired.append(
            {
                "m": m,
                "t": t,
                "errors": errors,
                "operation": operation,
                "samples": len(samples),
                "median_vkso_over_kernel_native": statistics.median(vkso_native),
                "p10_vkso_over_kernel_native": percentile(vkso_native, 0.10),
                "p90_vkso_over_kernel_native": percentile(vkso_native, 0.90),
                "median_vkso_over_author": statistics.median(vkso_author),
                "median_kernel_native_over_author": statistics.median(native_author),
            }
        )

    with args.paired.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paired[0]))
        writer.writeheader()
        writer.writerows(paired)

    aggregate_lookup = {
        (
            int(row["m"]),
            int(row["t"]),
            int(row["errors"]),
            str(row["operation"]),
            str(row["backend"]),
        ): row
        for row in aggregates
    }
    paired_lookup = {
        (int(row["m"]), int(row["t"]), int(row["errors"]), str(row["operation"])): row
        for row in paired
    }

    lines = [
        "# BCH kernel-exported vs user-space results",
        "",
        "Times are medians of CPU-pinned outer rounds within one process and one deployment. The timing clock and random-error method follow the author's `tu_bench.c`; backend order rotates each outer run. `vkso/native` is the matched per-run latency ratio, so values above 1 mean the exported kernel code is slower than the same adapted Linux 5.15 source compiled as a user-space DSO.",
        "",
    ]
    for m, t in ((13, 4), (13, 8)):
        lines += [f"## m={m}, t={t}, data=512 bytes", ""]
        for operation in ("init", "encode", "decode-precomputed", "decode-full"):
            errors_values = [-1] if operation == "init" else ([0] if operation == "encode" else list(range(t + 1)))
            lines += [
                f"### {operation}",
                "",
                "| Errors | kernel-vkso ns | kernel-native ns | author-standalone ns | vkso/native | vkso/author |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
            for errors in errors_values:
                values = [
                    aggregate_lookup[(m, t, errors, operation, backend)]
                    for backend in BACKENDS
                ]
                ratio = paired_lookup[(m, t, errors, operation)]
                label = "-" if errors < 0 else str(errors)
                lines.append(
                    f"| {label} | {float(values[0]['median_ns_per_op']):.2f} | "
                    f"{float(values[1]['median_ns_per_op']):.2f} | "
                    f"{float(values[2]['median_ns_per_op']):.2f} | "
                    f"{float(ratio['median_vkso_over_kernel_native']):.3f}x | "
                    f"{float(ratio['median_vkso_over_author']):.3f}x |"
                )
            lines.append("")

    args.summary.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
