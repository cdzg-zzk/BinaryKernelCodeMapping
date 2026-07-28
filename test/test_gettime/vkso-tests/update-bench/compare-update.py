#!/usr/bin/env python3
"""Summarize VKSO 3.2/3.3 update-side benchmark results."""

import argparse
import csv
import math
import re
import statistics
from pathlib import Path


ROUND_RE = re.compile(r"round-(\d+)-")
LOAD_APIS = {
    "monotonic": "clock_gettime_monotonic",
    "monotonic_raw": "clock_gettime_monotonic_raw",
    "monotonic_coarse": "clock_gettime_monotonic_coarse",
}
SEQ_READERS = {"hres_protocol", "raw_protocol"}
SCENARIOS_BY_SCOPE = {
    "update-side": {"idle"},
    "concurrent": {*LOAD_APIS, "seq_protocol"},
    "all": {"idle", *LOAD_APIS, "seq_protocol"},
}


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


def integer(row, key, path):
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid integer {key} in {path}") from error


def real(row, key, path):
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid number {key} in {path}") from error
    if not math.isfinite(value):
        raise ValueError(f"non-finite number {key} in {path}")
    return value


def validate_reader_rows(path, backend, scenario, rows, metadata):
    if scenario in LOAD_APIS:
        if len(rows) != 1:
            raise ValueError(f"expected one load row in {path}, got {len(rows)}")
        row = rows[0]
        if row.get("backend") != backend:
            raise ValueError(f"reader backend mismatch in {path}")
        if row.get("api") != LOAD_APIS[scenario]:
            raise ValueError(f"reader API mismatch in {path}")
        if integer(row, "seconds", path) != int(metadata["update_seconds"]):
            raise ValueError(f"reader duration mismatch in {path}")
        if integer(row, "cpu_migration", path):
            raise ValueError(f"CPU migration reported in {path}")
        if integer(row, "time_reversal", path):
            raise ValueError(f"time reversal reported in {path}")
        if integer(row, "calls", path) <= 0:
            raise ValueError(f"no reader calls in {path}")
        if integer(row, "wall_ns", path) < int(metadata["update_seconds"]) * 10**9:
            raise ValueError(f"short reader duration in {path}")
        if real(row, "tsc_cycles_per_call", path) <= 0:
            raise ValueError(f"invalid reader cycles in {path}")
        if real(row, "calls_per_second", path) <= 0:
            raise ValueError(f"invalid reader throughput in {path}")
        return

    if scenario != "seq_protocol":
        raise ValueError(f"unexpected reader scenario {scenario} in {path}")
    if len(rows) != len(SEQ_READERS):
        raise ValueError(f"expected two seq rows in {path}, got {len(rows)}")
    if {row.get("reader") for row in rows} != SEQ_READERS:
        raise ValueError(f"seq reader set mismatch in {path}")
    for row in rows:
        if row.get("backend") != backend:
            raise ValueError(f"seq backend mismatch in {path}")
        if integer(row, "completed", path) != int(metadata["seq_iterations"]):
            raise ValueError(f"incomplete seq observation in {path}")
        retries = integer(row, "retries", path)
        odd = integer(row, "odd_seq", path)
        changed = integer(row, "changed_seq", path)
        if retries != odd + changed:
            raise ValueError(f"inconsistent seq retry accounting in {path}")
        if real(row, "retries_per_million", path) < 0:
            raise ValueError(f"invalid seq retry rate in {path}")
        if real(row, "cycles_per_read", path) <= 0:
            raise ValueError(f"invalid seq reader cycles in {path}")


def validate_rounds(rows, expected_scenarios, repeats, description):
    scenarios = {row["scenario"] for row in rows}
    if scenarios != expected_scenarios:
        raise ValueError(
            f"{description} scenario mismatch: expected={sorted(expected_scenarios)}, "
            f"actual={sorted(scenarios)}"
        )
    expected_rounds = list(range(repeats))
    for scenario in sorted(expected_scenarios):
        actual = sorted(row["round"] for row in rows if row["scenario"] == scenario)
        if actual != expected_rounds:
            raise ValueError(
                f"{description} rounds for {scenario}: "
                f"expected={expected_rounds}, actual={actual}"
            )


def summarize_backend(backend_dir):
    backend = backend_dir.name
    metadata = read_metadata(backend_dir / "metadata.txt")
    scope = metadata.get("bench_scope", "all")
    if scope not in SCENARIOS_BY_SCOPE:
        raise ValueError(f"unknown benchmark scope in {backend_dir}: {scope}")
    repeats = int(metadata["repeats"])
    expected_scenarios = SCENARIOS_BY_SCOPE[scope]
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
    validate_rounds(writer_rows, expected_scenarios, repeats, "writer")
    if any(row["other_actions"] for row in writer_rows):
        raise ValueError(f"non-periodic writer action below {backend_dir}")
    overheads = {row["tsc_pair_min"] for row in writer_rows}
    if len(overheads) != 1:
        raise ValueError(f"inconsistent TSC measurement overhead below {backend_dir}")
    writer_fields = list(writer_rows[0])
    write_csv(backend_dir / "writer-rounds.csv", writer_fields, writer_rows)

    reader_rows = []
    reader_files = sorted(backend_dir.glob("3.3-concurrent/*/*reader.csv"))
    reader_file_rows = []
    for path in reader_files:
        scenario = scenario_for(path, backend_dir)
        rows = read_csv_rows(path)
        validate_reader_rows(path, backend, scenario, rows, metadata)
        reader_file_rows.append({"scenario": scenario, "round": round_for(path)})
        for row in rows:
            reader_rows.append(
                {
                    "backend": backend,
                    "scenario": scenario,
                    "round": round_for(path),
                    **row,
                }
            )
    expected_reader_scenarios = expected_scenarios - {"idle"}
    if expected_reader_scenarios:
        validate_rounds(
            reader_file_rows, expected_reader_scenarios, repeats, "reader"
        )
    elif reader_files:
        raise ValueError(f"unexpected reader files below {backend_dir}")
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
    for backend in ("raw", "vkso"):
        if not (result_root / backend / "complete").is_file():
            raise ValueError(f"incomplete backend result: {backend}")
    raw_metadata = read_metadata(result_root / "raw" / "metadata.txt")
    vkso_metadata = read_metadata(result_root / "vkso" / "metadata.txt")
    raw_scope = raw_metadata.get("bench_scope", "all")
    vkso_scope = vkso_metadata.get("bench_scope", "all")
    if raw_scope != vkso_scope:
        raise ValueError(
            f"benchmark scope mismatch: raw={raw_scope}, vkso={vkso_scope}"
        )
    for key in (
        "cpu",
        "repeats",
        "update_seconds",
        "warmup",
        "seq_iterations",
        "collection_mode",
        "stabilize_seconds",
        "clocksource",
    ):
        if raw_metadata.get(key) != vkso_metadata.get(key):
            raise ValueError(
                f"metadata mismatch for {key}: "
                f"raw={raw_metadata.get(key)}, vkso={vkso_metadata.get(key)}"
            )
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
        retry = comparison_map.get(("seq", scenario, "retries_per_million"))
        cycles = comparison_map.get(("seq", scenario, "cycles_per_read"))
        if retry and cycles:
            seq_table.append(
                [
                    scenario,
                    f'{float(retry["raw"]):.3f}',
                    f'{float(retry["vkso"]):.3f}',
                    f'{float(retry["delta_percent"]):+.2f}%',
                    f'{float(cycles["raw"]):.3f}',
                    f'{float(cycles["vkso"]):.3f}',
                    f'{float(cycles["delta_percent"]):+.2f}%',
                ]
            )

    title = {
        "update-side": "# VKSO update-side 性能实验结果",
        "concurrent": "# VKSO read/update 并发实验结果",
        "all": "# VKSO update-side 3.2/3.3 实验结果",
    }.get(raw_scope, "# VKSO update-side 实验结果")
    report = [
        title,
        "",
        "主指标均为多轮结果的中位数；`Δ%=(VKSO/Raw-1)×100%`，负值表示VKSO开销更低。",
        (
            f'实验参数：repeats={raw_metadata["repeats"]}，'
            f'每个 load 场景={raw_metadata["update_seconds"]} 秒，'
            f'seq iterations={raw_metadata["seq_iterations"]}，'
            f'稳定等待={raw_metadata.get("stabilize_seconds", "0")} 秒。'
        ),
        "",
        "## 完整 timekeeping_update writer",
        "",
        markdown_table(["场景", "Raw cycles", "VKSO cycles", "差值", "Δ%"], writer_table),
        "",
    ]
    if reader_table:
        report.extend(
            [
                "## 并发条件下公开用户入口 reader",
                "",
                markdown_table(
                    ["场景", "Raw cycles/call", "VKSO cycles/call", "Δ%"],
                    reader_table,
                ),
                "",
            ]
        )
    if seq_table:
        report.extend(
            [
                "## 并发 seq 竞争",
                "",
                markdown_table(
                    [
                        "协议",
                        "Raw retries/百万",
                        "VKSO retries/百万",
                        "retry Δ%",
                        "Raw cycles/read",
                        "VKSO cycles/read",
                        "cycles Δ%",
                    ],
                    seq_table,
                ),
                "",
            ]
        )
    report.extend(
        [
            "完整均值、P95、P99、校正值和每轮数据见 `update-comparison.csv` 及各backend目录。",
            "",
        ]
    )
    summary_name = (
        "CONCURRENT_SUMMARY.md"
        if raw_scope == "concurrent"
        else "UPDATE_SUMMARY.md"
    )
    (result_root / summary_name).write_text("\n".join(report))


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
