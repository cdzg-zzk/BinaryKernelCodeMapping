#!/usr/bin/env python3
"""Summarize VKSO 3.2/3.3 update-side benchmark results."""

import argparse
import csv
import math
import re
import statistics
from pathlib import Path


ROUND_RE = re.compile(r"round-(\d+)-")


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot summarize an empty sample")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def scenario_for(path, backend_dir):
    relative = path.relative_to(backend_dir)
    if relative.parts[0] == "3.2-idle":
        return "idle"
    return relative.parts[1]


def round_for(path):
    match = ROUND_RE.search(path.name)
    if not match:
        raise ValueError(f"cannot parse round from {path}")
    return int(match.group(1))


def parse_writer(path):
    overhead = None
    dropped = None
    rows = []
    with path.open(newline="") as stream:
        lines = stream.readlines()
    for line in lines:
        if line.startswith("#"):
            match = re.search(r"tsc_pair_min=(\d+)", line)
            if match:
                overhead = int(match.group(1))
            match = re.search(r"dropped=(\d+)", line)
            if match:
                dropped = int(match.group(1))
            continue
        if line.startswith("sample,"):
            reader = csv.DictReader([line] + lines[lines.index(line) + 1 :])
            rows = list(reader)
            break
    if overhead is None or dropped is None or not rows:
        raise ValueError(f"invalid writer sample file: {path}")
    if dropped:
        raise ValueError(f"writer sample capacity overflow in {path}: {dropped}")
    normal = [int(row["cycles"]) for row in rows if int(row["action"]) == 0]
    other = len(rows) - len(normal)
    if not normal:
        raise ValueError(f"no periodic action=0 samples in {path}")
    corrected = [max(0, value - overhead) for value in normal]
    return {
        "count": len(normal),
        "other_actions": other,
        "tsc_pair_min": overhead,
        "mean_cycles": statistics.fmean(normal),
        "median_cycles": statistics.median(normal),
        "p95_cycles": percentile(normal, 0.95),
        "p99_cycles": percentile(normal, 0.99),
        "min_cycles": min(normal),
        "max_cycles": max(normal),
        "mean_corrected_cycles": statistics.fmean(corrected),
        "median_corrected_cycles": statistics.median(corrected),
        "p95_corrected_cycles": percentile(corrected, 0.95),
        "p99_corrected_cycles": percentile(corrected, 0.99),
    }


def read_csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def median_metric(rows, key):
    return statistics.median(float(row[key]) for row in rows)


def read_metadata(path):
    values = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def summarize_backend(backend_dir):
    backend = backend_dir.name
    metadata = read_metadata(backend_dir / "metadata.txt")
    update_seconds = float(metadata["update_seconds"])
    writer_rows = []
    for path in sorted(backend_dir.glob("3.*/*writer.csv")) + sorted(
        backend_dir.glob("3.*/*/*writer.csv")
    ):
        values = parse_writer(path)
        scenario = scenario_for(path, backend_dir)
        row = {
            "backend": backend,
            "scenario": scenario,
            "round": round_for(path),
            **values,
        }
        if scenario != "seq_protocol":
            row["updates_per_second"] = values["count"] / update_seconds
        writer_rows.append(row)
    if not writer_rows:
        raise ValueError(f"no writer samples below {backend_dir}")
    writer_fields = list(writer_rows[0])
    write_csv(backend_dir / "writer-rounds.csv", writer_fields, writer_rows)

    reader_rows = []
    for path in sorted(backend_dir.glob("3.3-concurrent/*/*reader.csv")):
        scenario = scenario_for(path, backend_dir)
        for row in read_csv_rows(path):
            reader_rows.append(
                {
                    "backend": backend,
                    "scenario": scenario,
                    "round": round_for(path),
                    **row,
                }
            )
    if reader_rows:
        fields = []
        for row in reader_rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        write_csv(backend_dir / "reader-rounds.csv", fields, reader_rows)

    summary = []
    scenarios = sorted({row["scenario"] for row in writer_rows})
    for scenario in scenarios:
        rows = [row for row in writer_rows if row["scenario"] == scenario]
        for metric in (
            "count",
            "other_actions",
            "tsc_pair_min",
            "mean_cycles",
            "median_cycles",
            "p95_cycles",
            "p99_cycles",
            "mean_corrected_cycles",
            "median_corrected_cycles",
            "p95_corrected_cycles",
            "p99_corrected_cycles",
            "updates_per_second",
        ):
            metric_rows = [row for row in rows if metric in row]
            if not metric_rows:
                continue
            summary.append(
                {
                    "backend": backend,
                    "category": "writer",
                    "scenario": scenario,
                    "metric": metric,
                    "value": f"{median_metric(metric_rows, metric):.9f}",
                    "rounds": len(metric_rows),
                }
            )

    load_rows = [row for row in reader_rows if row["scenario"] != "seq_protocol"]
    for scenario in sorted({row["scenario"] for row in load_rows}):
        rows = [row for row in load_rows if row["scenario"] == scenario]
        for metric in ("tsc_cycles_per_call", "calls_per_second"):
            summary.append(
                {
                    "backend": backend,
                    "category": "reader",
                    "scenario": scenario,
                    "metric": metric,
                    "value": f"{median_metric(rows, metric):.9f}",
                    "rounds": len(rows),
                }
            )

    seq_rows = [row for row in reader_rows if row["scenario"] == "seq_protocol"]
    for reader in sorted({row.get("reader", "") for row in seq_rows}):
        rows = [row for row in seq_rows if row.get("reader") == reader]
        for metric in ("retries_per_million", "cycles_per_read"):
            summary.append(
                {
                    "backend": backend,
                    "category": "seq",
                    "scenario": reader,
                    "metric": metric,
                    "value": f"{median_metric(rows, metric):.9f}",
                    "rounds": len(rows),
                }
            )

    write_csv(
        backend_dir / "update-summary.csv",
        ["backend", "category", "scenario", "metric", "value", "rounds"],
        summary,
    )
    return summary


def markdown_table(headers, rows):
    result = ["| " + " | ".join(headers) + " |"]
    result.append("|" + "|".join("---" for _ in headers) + "|")
    result.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(result)


def compare_result_root(result_root):
    raw = summarize_backend(result_root / "raw")
    vkso = summarize_backend(result_root / "vkso")
    raw_map = {
        (row["category"], row["scenario"], row["metric"]): row for row in raw
    }
    vkso_map = {
        (row["category"], row["scenario"], row["metric"]): row for row in vkso
    }
    comparisons = []
    for key in sorted(raw_map.keys() & vkso_map.keys()):
        raw_value = float(raw_map[key]["value"])
        vkso_value = float(vkso_map[key]["value"])
        delta = vkso_value - raw_value
        delta_percent = (vkso_value / raw_value - 1.0) * 100.0 if raw_value else math.nan
        comparisons.append(
            {
                "category": key[0],
                "scenario": key[1],
                "metric": key[2],
                "raw": f"{raw_value:.9f}",
                "vkso": f"{vkso_value:.9f}",
                "delta": f"{delta:.9f}",
                "delta_percent": f"{delta_percent:.6f}",
            }
        )
    write_csv(
        result_root / "update-comparison.csv",
        ["category", "scenario", "metric", "raw", "vkso", "delta", "delta_percent"],
        comparisons,
    )

    comparison_map = {
        (row["category"], row["scenario"], row["metric"]): row
        for row in comparisons
    }
    writer_table = []
    for scenario in ("idle", "monotonic", "monotonic_raw", "monotonic_coarse", "seq_protocol"):
        row = comparison_map.get(("writer", scenario, "median_cycles"))
        if row:
            writer_table.append(
                [scenario, f'{float(row["raw"]):.3f}', f'{float(row["vkso"]):.3f}',
                 f'{float(row["delta"]):+.3f}', f'{float(row["delta_percent"]):+.2f}%']
            )
    reader_table = []
    for scenario in ("monotonic", "monotonic_raw", "monotonic_coarse"):
        row = comparison_map.get(("reader", scenario, "tsc_cycles_per_call"))
        if row:
            reader_table.append(
                [scenario, f'{float(row["raw"]):.3f}', f'{float(row["vkso"]):.3f}',
                 f'{float(row["delta_percent"]):+.2f}%']
            )
    seq_table = []
    for scenario in ("hres_protocol", "raw_protocol"):
        row = comparison_map.get(("seq", scenario, "retries_per_million"))
        if row:
            seq_table.append(
                [scenario, f'{float(row["raw"]):.3f}', f'{float(row["vkso"]):.3f}',
                 f'{float(row["delta_percent"]):+.2f}%']
            )

    report = [
        "# VKSO update-side 3.2/3.3 实验结果",
        "",
        "主指标均为多轮结果的中位数；`Δ%=(VKSO/Raw-1)×100%`，负值表示VKSO开销更低。",
        "",
        "## 3.2及3.3 writer完整timekeeping_update",
        "",
        markdown_table(["场景", "Raw cycles", "VKSO cycles", "差值", "Δ%"], writer_table),
        "",
        "## 3.3公开用户入口reader负载",
        "",
        markdown_table(["场景", "Raw cycles/call", "VKSO cycles/call", "Δ%"], reader_table),
        "",
        "## 3.3 seq竞争",
        "",
        markdown_table(["协议", "Raw retries/百万", "VKSO retries/百万", "Δ%"], seq_table),
        "",
        "完整均值、P95、P99、校正值和每轮数据见 `update-comparison.csv` 及各backend目录。",
        "",
    ]
    (result_root / "UPDATE_SUMMARY.md").write_text("\n".join(report))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backend-dir", type=Path)
    group.add_argument("--result-root", type=Path)
    args = parser.parse_args()
    if args.backend_dir:
        summarize_backend(args.backend_dir)
    else:
        compare_result_root(args.result_root)


if __name__ == "__main__":
    main()
