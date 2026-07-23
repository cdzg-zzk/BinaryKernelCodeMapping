#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import csv
import math
import pathlib
import statistics
import sys
from collections import defaultdict


METRICS = (
    "tsc_cycles_per_call",
    "pmu_cycles_per_call",
    "instructions_per_call",
    "branches_per_call",
    "branch_misses_per_call",
    "cache_references_per_call",
    "cache_misses_per_call",
    "l1d_load_misses_per_call",
    "llc_load_misses_per_call",
)


def fail(message):
    raise SystemExit(message)


def read_csv(path):
    if not path.is_file():
        fail(f"missing result: {path}")
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def percentile(values, fraction):
    ordered = sorted(values)
    index = int(math.floor((len(ordered) - 1) * fraction))
    return ordered[index]


def median_map(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row["api"], row["path"])
        for metric in METRICS:
            grouped[(key, metric)].append(float(row[metric]))
    result = {}
    for (key, metric), values in grouped.items():
        result[(key[0], key[1], metric)] = statistics.median(values)
    return result


def delta(new, baseline):
    if baseline == 0:
        return None
    return 100.0 * (new - baseline) / baseline


def fmt(value):
    return "NA" if value is None else f"{value:.6f}"


def read_environment(path):
    values = {}
    with path.open() as stream:
        for line in stream:
            line = line.rstrip("\n")
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    return values


def compare_environments(root):
    raw = read_environment(root / "raw" / "environment.txt")
    vkso = read_environment(root / "vkso" / "environment.txt")
    keys = (
        "cpu",
        "iterations",
        "repeats",
        "warmup",
        "pmu",
        "seq_iterations",
        "layout_iterations",
        "clocksource",
        "smt_active",
        "isolated",
        "kernel_cmdline_common",
    )
    for key in keys:
        if raw.get(key) != vkso.get(key):
            fail(
                f"environment mismatch for {key}: "
                f"{raw.get(key)!r} != {vkso.get(key)!r}"
            )
    return raw


def write_path_summary(path, rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = (row["backend"], row["api"], row["path"])
        for metric in METRICS:
            grouped[key][metric].append(float(row[metric]))
    with path.open("w", newline="") as stream:
        fields = ["backend", "api", "path", "samples"]
        for metric in METRICS:
            fields.extend(
                (f"{metric}_p10", f"{metric}_median", f"{metric}_p90",
                 f"{metric}_p99")
            )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for key in sorted(grouped):
            output = {
                "backend": key[0],
                "api": key[1],
                "path": key[2],
                "samples": len(grouped[key][METRICS[0]]),
            }
            for metric in METRICS:
                values = grouped[key][metric]
                output[f"{metric}_p10"] = fmt(percentile(values, 0.10))
                output[f"{metric}_median"] = fmt(statistics.median(values))
                output[f"{metric}_p90"] = fmt(percentile(values, 0.90))
                output[f"{metric}_p99"] = fmt(percentile(values, 0.99))
            writer.writerow(output)


def write_question_rows(path, raw_rows, vkso_rows, seq_rows, layout_rows):
    values = median_map(raw_rows + vkso_rows)
    rows = []

    def add(question, api, metric, baseline_path, candidate_path):
        baseline = values.get((api, baseline_path, metric))
        candidate = values.get((api, candidate_path, metric))
        if baseline is None or candidate is None:
            return
        rows.append(
            {
                "question": question,
                "api": api,
                "metric": metric,
                "baseline_path": baseline_path,
                "baseline_median": fmt(baseline),
                "candidate_path": candidate_path,
                "candidate_median": fmt(candidate),
                "delta_percent": fmt(delta(candidate, baseline)),
            }
        )

    apis = sorted({row["api"] for row in raw_rows + vkso_rows})
    for api in apis:
        add(
            "kernel_syscall_shared_core_effect",
            api,
            "tsc_cycles_per_call",
            "raw:syscall",
            "vkso:syscall",
        )
        add(
            "wrapper_over_shared_core",
            api,
            "tsc_cycles_per_call",
            "vkso:vkso_core",
            "vkso:vkso_wrapper",
        )
        add(
            "raw_vdso_vs_vkso_wrapper",
            api,
            "tsc_cycles_per_call",
            "raw:raw_vdso",
            "vkso:vkso_wrapper",
        )
        add(
            "raw_vdso_vs_vkso_core",
            api,
            "tsc_cycles_per_call",
            "raw:raw_vdso",
            "vkso:vkso_core",
        )

    raw_api = "clock_gettime_monotonic_raw"
    for metric in (
        "tsc_cycles_per_call",
        "pmu_cycles_per_call",
        "instructions_per_call",
        "l1d_load_misses_per_call",
        "llc_load_misses_per_call",
    ):
        add(
            "monotonic_raw_cacheline_end_to_end",
            raw_api,
            metric,
            "raw:raw_vdso",
            "vkso:vkso_wrapper",
        )
        add(
            "monotonic_raw_cacheline_core",
            raw_api,
            metric,
            "raw:raw_vdso",
            "vkso:vkso_core",
        )

    seq_by_key = {
        (row["backend"], row["reader"]): row for row in seq_rows
    }
    for reader in ("hres_protocol", "raw_protocol"):
        raw = seq_by_key.get(("raw", reader))
        vkso = seq_by_key.get(("vkso", reader))
        if not raw or not vkso:
            fail(f"missing seq result for {reader}")
        raw_value = float(raw["retries_per_million"])
        vkso_value = float(vkso["retries_per_million"])
        rows.append(
            {
                "question": "seq_protocol_retry_rate",
                "api": reader,
                "metric": "retries_per_million",
                "baseline_path": "raw:seq_observer",
                "baseline_median": fmt(raw_value),
                "candidate_path": "vkso:seq_observer",
                "candidate_median": fmt(vkso_value),
                "delta_percent": fmt(delta(vkso_value, raw_value)),
            }
        )

    layout = defaultdict(list)
    for row in layout_rows:
        layout[row["layout"]].append(float(row["cold_cycles_per_read"]))
    old = statistics.median(layout["old_straddled_raw"])
    new = statistics.median(layout["new_aligned_raw"])
    rows.append(
        {
            "question": "isolated_raw_cacheline_layout",
            "api": "synthetic_cold_raw_snapshot",
            "metric": "cold_cycles_per_read",
            "baseline_path": "old_straddled_raw",
            "baseline_median": fmt(old),
            "candidate_path": "new_aligned_raw",
            "candidate_median": fmt(new),
            "delta_percent": fmt(delta(new, old)),
        }
    )

    fields = (
        "question",
        "api",
        "metric",
        "baseline_path",
        "baseline_median",
        "candidate_path",
        "candidate_median",
        "delta_percent",
    )
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: tuple(row.values())))
    return rows


def prefixed_rows(rows):
    output = []
    for row in rows:
        converted = dict(row)
        converted["path"] = f'{row["backend"]}:{row["path"]}'
        output.append(converted)
    return output


def write_markdown(path, environment, question_rows):
    selected = [
        row
        for row in question_rows
        if row["question"]
        in {
            "wrapper_over_shared_core",
            "kernel_syscall_shared_core_effect",
            "raw_vdso_vs_vkso_wrapper",
            "seq_protocol_retry_rate",
            "monotonic_raw_cacheline_end_to_end",
            "isolated_raw_cacheline_layout",
        }
    ]
    with path.open("w") as stream:
        stream.write("# Raw vDSO / VKSO bare-metal result\n\n")
        stream.write(
            f"- CPU: `{environment['cpu']}`\n"
            f"- iterations/repeat: `{environment['iterations']}`\n"
            f"- repeats: `{environment['repeats']}`\n"
            f"- PMU: `{environment['pmu']}`\n"
            f"- clocksource: `{environment['clocksource']}`\n\n"
        )
        stream.write(
            "Negative delta means the VKSO/new candidate is faster or "
            "uses fewer events. QEMU data is not included.\n\n"
        )
        stream.write(
            "| Question | API | Metric | Baseline | Candidate | Delta % |\n"
        )
        stream.write("|---|---|---|---:|---:|---:|\n")
        for row in selected:
            stream.write(
                f"| {row['question']} | {row['api']} | {row['metric']} | "
                f"{row['baseline_median']} | {row['candidate_median']} | "
                f"{row['delta_percent']} |\n"
            )
        stream.write(
            "\nThe seq rows are protocol observers using the same seq "
            "window; production functions remain uninstrumented. The "
            "isolated layout row is a synthetic cold-cache A/B test. "
            "Use the MONOTONIC_RAW PMU rows for end-to-end evidence.\n"
        )


def verify_function_matrices(root):
    raw_path = root / "raw" / "functional.matrix"
    vkso_path = root / "vkso" / "functional.matrix"
    if raw_path.read_bytes() != vkso_path.read_bytes():
        fail("raw and VKSO functional/path matrices differ")


def main():
    if len(sys.argv) != 2:
        fail(f"usage: {sys.argv[0]} result-root")
    root = pathlib.Path(sys.argv[1]).resolve()
    environment = compare_environments(root)
    verify_function_matrices(root)

    raw_rows = read_csv(root / "raw" / "perf.csv")
    vkso_rows = read_csv(root / "vkso" / "perf.csv")
    seq_rows = read_csv(root / "raw" / "seq.csv")
    seq_rows += read_csv(root / "vkso" / "seq.csv")
    layout_rows = read_csv(root / "vkso" / "layout.csv")

    expected_repeats = int(environment["repeats"])
    for backend, rows in (("raw", raw_rows), ("vkso", vkso_rows)):
        grouped = defaultdict(int)
        for row in rows:
            if row["backend"] != backend:
                fail(f"backend label mismatch in {backend}/perf.csv")
            grouped[(row["api"], row["path"])] += 1
        for key, count in grouped.items():
            if count != expected_repeats:
                fail(f"sample count mismatch for {backend}/{key}: {count}")

    combined = prefixed_rows(raw_rows) + prefixed_rows(vkso_rows)
    write_path_summary(root / "path-summary.csv", combined)
    questions = write_question_rows(
        root / "research-questions.csv",
        prefixed_rows(raw_rows),
        prefixed_rows(vkso_rows),
        seq_rows,
        layout_rows,
    )
    write_markdown(root / "SUMMARY.md", environment, questions)
    print(f"comparison={root / 'research-questions.csv'}")
    print(f"summary={root / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()
