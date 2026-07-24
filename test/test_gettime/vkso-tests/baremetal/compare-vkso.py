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


def read_environment(path):
    values = {}
    with path.open() as stream:
        for line in stream:
            if "=" in line:
                key, value = line.rstrip("\n").split("=", 1)
                values[key] = value
    return values


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[int(math.floor((len(ordered) - 1) * fraction))]


def delta(candidate, baseline):
    return 100.0 * (candidate - baseline) / baseline if baseline else math.nan


def verify_environment(baseline_dir, candidate_dir):
    baseline = read_environment(baseline_dir / "environment.txt")
    candidate = read_environment(candidate_dir / "environment.txt")
    for key in (
        "cpu",
        "iterations",
        "repeats",
        "warmup",
        "pmu",
        "clocksource",
        "smt_active",
        "isolated",
        "kernel_cmdline_common",
    ):
        if baseline.get(key) != candidate.get(key):
            fail(
                f"environment mismatch for {key}: "
                f"{baseline.get(key)!r} != {candidate.get(key)!r}"
            )
    return baseline, candidate


def grouped_values(rows):
    values = defaultdict(lambda: defaultdict(list))
    for row in rows:
        for metric in METRICS:
            values[(row["api"], row["path"])][metric].append(
                float(row[metric])
            )
    return values


def verify_samples(values, expected, label):
    for key, metrics in values.items():
        for metric, samples in metrics.items():
            if len(samples) != expected:
                fail(
                    f"{label} sample count mismatch for "
                    f"{key}/{metric}: {len(samples)}"
                )


def build_rows(baseline_values, candidate_values):
    rows = []
    for key in sorted(set(baseline_values) | set(candidate_values)):
        if key not in baseline_values or key not in candidate_values:
            fail(f"path set changed for {key}")
        for metric in METRICS:
            old = baseline_values[key][metric]
            new = candidate_values[key][metric]
            old_median = statistics.median(old)
            new_median = statistics.median(new)
            rows.append(
                {
                    "api": key[0],
                    "path": key[1],
                    "metric": metric,
                    "baseline_p10": percentile(old, 0.10),
                    "baseline_median": old_median,
                    "baseline_p90": percentile(old, 0.90),
                    "candidate_p10": percentile(new, 0.10),
                    "candidate_median": new_median,
                    "candidate_p90": percentile(new, 0.90),
                    "delta_percent": delta(new_median, old_median),
                }
            )
    return rows


def write_csv(path, rows):
    fields = tuple(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{value:.6f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def write_summary(path, baseline, candidate, rows):
    selected = [
        row
        for row in rows
        if row["metric"] in ("tsc_cycles_per_call", "instructions_per_call")
        and row["path"] in ("vkso_core", "vkso_wrapper")
    ]
    with path.open("w") as stream:
        stream.write("# VKSO optimization result\n\n")
        stream.write(
            f"- CPU: `{candidate['cpu']}`\n"
            f"- iterations/repeat: `{candidate['iterations']}`\n"
            f"- repeats: `{candidate['repeats']}`\n"
            f"- baseline package: `{baseline.get('package_manifest_sha256', 'unknown')}`\n"
            f"- candidate package: `{candidate.get('package_manifest_sha256', 'unknown')}`\n\n"
        )
        stream.write(
            "Negative delta means the optimized VKSO is faster or uses "
            "fewer instructions.\n\n"
        )
        stream.write(
            "| API | Path | Metric | Before | After | Delta % |\n"
            "|---|---|---|---:|---:|---:|\n"
        )
        for row in selected:
            stream.write(
                f"| {row['api']} | {row['path']} | {row['metric']} | "
                f"{row['baseline_median']:.6f} | "
                f"{row['candidate_median']:.6f} | "
                f"{row['delta_percent']:.6f} |\n"
            )


def main():
    if len(sys.argv) != 4:
        fail(
            f"usage: {sys.argv[0]} "
            "baseline-vkso-dir candidate-vkso-dir output-dir"
        )
    baseline_dir = pathlib.Path(sys.argv[1]).resolve()
    candidate_dir = pathlib.Path(sys.argv[2]).resolve()
    output_dir = pathlib.Path(sys.argv[3]).resolve()
    baseline_env, candidate_env = verify_environment(
        baseline_dir, candidate_dir
    )
    if (
        (baseline_dir / "functional.matrix").read_bytes()
        != (candidate_dir / "functional.matrix").read_bytes()
    ):
        fail("VKSO functional/path matrices changed after optimization")
    baseline_values = grouped_values(read_csv(baseline_dir / "perf.csv"))
    candidate_values = grouped_values(read_csv(candidate_dir / "perf.csv"))
    expected = int(candidate_env["repeats"])
    verify_samples(baseline_values, expected, "baseline")
    verify_samples(candidate_values, expected, "candidate")
    rows = build_rows(baseline_values, candidate_values)
    write_csv(output_dir / "vkso-optimization.csv", rows)
    write_summary(
        output_dir / "VKSO-OPT-SUMMARY.md",
        baseline_env,
        candidate_env,
        rows,
    )
    print(f"comparison={output_dir / 'vkso-optimization.csv'}")
    print(f"summary={output_dir / 'VKSO-OPT-SUMMARY.md'}")


if __name__ == "__main__":
    main()
