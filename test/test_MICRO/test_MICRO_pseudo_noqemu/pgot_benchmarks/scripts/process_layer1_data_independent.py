#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict


def quantile(sorted_values, q):
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def mean(values):
    return sum(values) / len(values) if values else 0.0


def trimmed_mean(values, trim_ratio=0.10):
    if not values:
        return 0.0
    ordered = sorted(values)
    trim = int(math.floor(len(ordered) * trim_ratio))
    if trim == 0 or (2 * trim) >= len(ordered):
        return mean(ordered)
    return mean(ordered[trim:-trim])


def stats_for(values):
    ordered = sorted(values)
    q1 = quantile(ordered, 0.25)
    median = quantile(ordered, 0.50)
    q3 = quantile(ordered, 0.75)
    iqr = q3 - q1
    stddev = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "mean": mean(values),
        "median": median,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "min": min(values) if values else 0.0,
        "max": max(values) if values else 0.0,
        "stddev": stddev,
        "trimmed_mean": trimmed_mean(values),
    }


def fmt(v):
    if isinstance(v, int):
        return str(v)
    return f"{v:.9f}"


def load_raw(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = int(row["event"])
            rows.append({
                "experiment": row["experiment"],
                "run_id": int(row["run_id"]),
                "event": event,
                "repeat": int(row["repeat"]),
                "iterations": int(row["iterations"]),
                "direct_cycles": float(row["direct_cycles"]),
                "pgot_cycles": float(row["pgot_cycles"]),
                "delta_cycles": float(row["delta_cycles"]),
                "delta_cycles_per_event": float(row["delta_cycles_per_event"]),
            })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--processed", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--paper-table", required=True)
    args = parser.parse_args()

    rows = load_raw(args.raw)
    by_event = defaultdict(list)
    for row in rows:
        by_event[row["event"]].append(row)

    thresholds = {}
    for event, event_rows in by_event.items():
        raw_deltas = [r["delta_cycles"] for r in event_rows]
        raw_stats = stats_for(raw_deltas)
        lower = raw_stats["q1"] - 1.5 * raw_stats["iqr"]
        upper = raw_stats["q3"] + 1.5 * raw_stats["iqr"]
        thresholds[event] = (lower, upper)

    processed_fields = [
        "experiment", "run_id", "event", "repeat", "iterations",
        "direct_cycles", "pgot_cycles", "delta_cycles",
        "delta_cycles_per_event", "outlier_lower", "outlier_upper",
        "is_outlier",
    ]
    kept_by_event = defaultdict(list)
    with open(args.processed, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=processed_fields)
        writer.writeheader()
        for row in rows:
            lower, upper = thresholds[row["event"]]
            is_outlier = row["delta_cycles"] < lower or row["delta_cycles"] > upper
            out = dict(row)
            out["outlier_lower"] = lower
            out["outlier_upper"] = upper
            out["is_outlier"] = 1 if is_outlier else 0
            writer.writerow({k: fmt(out[k]) if isinstance(out[k], float) else out[k]
                             for k in processed_fields})
            if not is_outlier:
                kept_by_event[row["event"]].append(row)

    summary_fields = [
        "event", "n_raw", "n_kept", "n_dropped", "drop_rate",
        "mean_delta", "median_delta", "q1_delta", "q3_delta", "iqr_delta",
        "min_delta", "max_delta", "stddev_delta", "trimmed_mean_delta",
        "median_delta_per_event", "q1_delta_per_event", "q3_delta_per_event",
    ]
    summary_rows = []
    for event in sorted(by_event):
        kept = kept_by_event[event]
        kept_deltas = [r["delta_cycles"] for r in kept]
        s = stats_for(kept_deltas)
        n_raw = len(by_event[event])
        n_kept = len(kept)
        n_dropped = n_raw - n_kept
        drop_rate = n_dropped / n_raw if n_raw else 0.0
        summary_rows.append({
            "event": event,
            "n_raw": n_raw,
            "n_kept": n_kept,
            "n_dropped": n_dropped,
            "drop_rate": drop_rate,
            "mean_delta": s["mean"],
            "median_delta": s["median"],
            "q1_delta": s["q1"],
            "q3_delta": s["q3"],
            "iqr_delta": s["iqr"],
            "min_delta": s["min"],
            "max_delta": s["max"],
            "stddev_delta": s["stddev"],
            "trimmed_mean_delta": s["trimmed_mean"],
            "median_delta_per_event": s["median"] / event,
            "q1_delta_per_event": s["q1"] / event,
            "q3_delta_per_event": s["q3"] / event,
        })

    with open(args.summary, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({k: fmt(row[k]) if isinstance(row[k], float) else row[k]
                             for k in summary_fields})

    paper_fields = [
        "event", "n_raw", "n_kept", "drop_rate",
        "mean_delta_cycles_per_iter",
        "median_delta_cycles_per_iter",
        "trimmed_mean_delta_cycles_per_iter",
        "q1_delta_cycles_per_iter",
        "q3_delta_cycles_per_iter",
        "iqr_delta_cycles_per_iter",
        "stddev_delta_cycles_per_iter",
        "min_delta_cycles_per_iter",
        "max_delta_cycles_per_iter",
        "mean_delta_cycles_per_event",
        "median_delta_cycles_per_event",
        "trimmed_mean_delta_cycles_per_event",
    ]
    with open(args.paper_table, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=paper_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({
                "event": row["event"],
                "n_raw": row["n_raw"],
                "n_kept": row["n_kept"],
                "drop_rate": fmt(row["drop_rate"]),
                "mean_delta_cycles_per_iter": fmt(row["mean_delta"]),
                "median_delta_cycles_per_iter": fmt(row["median_delta"]),
                "trimmed_mean_delta_cycles_per_iter": fmt(row["trimmed_mean_delta"]),
                "q1_delta_cycles_per_iter": fmt(row["q1_delta"]),
                "q3_delta_cycles_per_iter": fmt(row["q3_delta"]),
                "iqr_delta_cycles_per_iter": fmt(row["iqr_delta"]),
                "stddev_delta_cycles_per_iter": fmt(row["stddev_delta"]),
                "min_delta_cycles_per_iter": fmt(row["min_delta"]),
                "max_delta_cycles_per_iter": fmt(row["max_delta"]),
                "mean_delta_cycles_per_event": fmt(row["mean_delta"] / row["event"]),
                "median_delta_cycles_per_event": fmt(row["median_delta_per_event"]),
                "trimmed_mean_delta_cycles_per_event": fmt(row["trimmed_mean_delta"] / row["event"]),
            })


if __name__ == "__main__":
    main()
