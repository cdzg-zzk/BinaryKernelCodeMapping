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
            variant = row.get("variant") or "scheduled"
            empty_cycles = float(row.get("empty_cycles") or 0.0)
            direct_cycles = float(row["direct_cycles"])
            pgot_cycles = float(row["pgot_cycles"])
            delta_cycles = float(row["delta_cycles"])
            rows.append({
                "experiment": row["experiment"],
                "variant": variant,
                "run_id": int(row["run_id"]),
                "event": event,
                "repeat": int(row["repeat"]),
                "iterations": int(row["iterations"]),
                "empty_cycles": empty_cycles,
                "direct_cycles": direct_cycles,
                "pgot_cycles": pgot_cycles,
                "delta_cycles": delta_cycles,
                "empty_cycles_per_event": empty_cycles / event,
                "direct_cycles_per_event": direct_cycles / event,
                "pgot_cycles_per_event": pgot_cycles / event,
                "delta_cycles_per_event": float(row["delta_cycles_per_event"]),
            })
    return rows


def make_summary_row(variant, event, raw, kept, value_mode):
    raw_empty = stats_for([r["empty_cycles_per_event"] for r in raw])
    raw_direct = stats_for([r["direct_cycles_per_event"] for r in raw])
    raw_pgot = stats_for([r["pgot_cycles_per_event"] for r in raw])
    raw_delta = stats_for([r["delta_cycles_per_event"] for r in raw])
    kept_empty = stats_for([r["empty_cycles_per_event"] for r in kept])
    kept_direct = stats_for([r["direct_cycles_per_event"] for r in kept])
    kept_pgot = stats_for([r["pgot_cycles_per_event"] for r in kept])
    kept_delta = stats_for([r["delta_cycles_per_event"] for r in kept])
    n_raw = len(raw)
    n_kept = len(kept)
    n_dropped = n_raw - n_kept
    drop_rate = n_dropped / n_raw if n_raw else 0.0
    return {
        "variant": variant,
        "event": event,
        "value_mode": value_mode,
        "n_raw": n_raw,
        "n_kept": n_kept,
        "n_dropped": n_dropped,
        "drop_rate": drop_rate,
        "raw_mean_empty_cycles_per_event": raw_empty["mean"],
        "raw_median_empty_cycles_per_event": raw_empty["median"],
        "raw_q1_empty_cycles_per_event": raw_empty["q1"],
        "raw_q3_empty_cycles_per_event": raw_empty["q3"],
        "raw_iqr_empty_cycles_per_event": raw_empty["iqr"],
        "raw_mean_direct_cycles_per_event": raw_direct["mean"],
        "raw_median_direct_cycles_per_event": raw_direct["median"],
        "raw_q1_direct_cycles_per_event": raw_direct["q1"],
        "raw_q3_direct_cycles_per_event": raw_direct["q3"],
        "raw_iqr_direct_cycles_per_event": raw_direct["iqr"],
        "raw_mean_pgot_cycles_per_event": raw_pgot["mean"],
        "raw_median_pgot_cycles_per_event": raw_pgot["median"],
        "raw_q1_pgot_cycles_per_event": raw_pgot["q1"],
        "raw_q3_pgot_cycles_per_event": raw_pgot["q3"],
        "raw_iqr_pgot_cycles_per_event": raw_pgot["iqr"],
        "raw_mean_delta_cycles_per_event": raw_delta["mean"],
        "raw_median_delta_cycles_per_event": raw_delta["median"],
        "raw_q1_delta_cycles_per_event": raw_delta["q1"],
        "raw_q3_delta_cycles_per_event": raw_delta["q3"],
        "raw_iqr_delta_cycles_per_event": raw_delta["iqr"],
        "raw_stddev_delta_cycles_per_event": raw_delta["stddev"],
        "kept_mean_empty_cycles_per_event": kept_empty["mean"],
        "kept_median_empty_cycles_per_event": kept_empty["median"],
        "kept_q1_empty_cycles_per_event": kept_empty["q1"],
        "kept_q3_empty_cycles_per_event": kept_empty["q3"],
        "kept_iqr_empty_cycles_per_event": kept_empty["iqr"],
        "kept_mean_direct_cycles_per_event": kept_direct["mean"],
        "kept_median_direct_cycles_per_event": kept_direct["median"],
        "kept_q1_direct_cycles_per_event": kept_direct["q1"],
        "kept_q3_direct_cycles_per_event": kept_direct["q3"],
        "kept_iqr_direct_cycles_per_event": kept_direct["iqr"],
        "kept_mean_pgot_cycles_per_event": kept_pgot["mean"],
        "kept_median_pgot_cycles_per_event": kept_pgot["median"],
        "kept_q1_pgot_cycles_per_event": kept_pgot["q1"],
        "kept_q3_pgot_cycles_per_event": kept_pgot["q3"],
        "kept_iqr_pgot_cycles_per_event": kept_pgot["iqr"],
        "kept_mean_delta_cycles_per_event": kept_delta["mean"],
        "kept_median_delta_cycles_per_event": kept_delta["median"],
        "kept_q1_delta_cycles_per_event": kept_delta["q1"],
        "kept_q3_delta_cycles_per_event": kept_delta["q3"],
        "kept_iqr_delta_cycles_per_event": kept_delta["iqr"],
        "kept_stddev_delta_cycles_per_event": kept_delta["stddev"],
    }


def as_empty_adjusted(row):
    adjusted = dict(row)
    adjusted["variant"] = "scheduled_empty_adjusted"
    adjusted["direct_cycles"] = row["direct_cycles"] - row["empty_cycles"]
    adjusted["pgot_cycles"] = row["pgot_cycles"] - row["empty_cycles"]
    adjusted["direct_cycles_per_event"] = adjusted["direct_cycles"] / row["event"]
    adjusted["pgot_cycles_per_event"] = adjusted["pgot_cycles"] / row["event"]
    return adjusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--processed", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--paper-table", required=True)
    args = parser.parse_args()

    rows = load_raw(args.raw)
    by_group = defaultdict(list)
    for row in rows:
        by_group[(row["variant"], row["event"])].append(row)

    thresholds = {}
    for group, group_rows in by_group.items():
        raw_deltas = [r["delta_cycles"] for r in group_rows]
        raw_stats = stats_for(raw_deltas)
        lower = raw_stats["q1"] - 1.5 * raw_stats["iqr"]
        upper = raw_stats["q3"] + 1.5 * raw_stats["iqr"]
        thresholds[group] = (lower, upper)

    processed_fields = [
        "experiment", "variant", "value_mode", "run_id", "event", "repeat",
        "iterations", "empty_cycles", "direct_cycles", "pgot_cycles",
        "delta_cycles", "empty_cycles_per_event", "direct_cycles_per_event",
        "pgot_cycles_per_event", "delta_cycles_per_event", "outlier_lower",
        "outlier_upper", "is_outlier",
    ]
    kept_by_group = defaultdict(list)
    all_by_group = defaultdict(list)
    with open(args.processed, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=processed_fields)
        writer.writeheader()
        for row in rows:
            group = (row["variant"], row["event"])
            lower, upper = thresholds[group]
            is_outlier = row["delta_cycles"] < lower or row["delta_cycles"] > upper
            out = dict(row)
            out["value_mode"] = "raw"
            out["outlier_lower"] = lower
            out["outlier_upper"] = upper
            out["is_outlier"] = 1 if is_outlier else 0
            writer.writerow({k: fmt(out[k]) if isinstance(out[k], float) else out[k]
                             for k in processed_fields})
            all_by_group[group].append(row)
            if not is_outlier:
                kept_by_group[group].append(row)

            if row["variant"] == "scheduled":
                adjusted = as_empty_adjusted(row)
                adjusted_group = (adjusted["variant"], adjusted["event"])
                adjusted_out = dict(adjusted)
                adjusted_out["value_mode"] = "empty_adjusted"
                adjusted_out["outlier_lower"] = lower
                adjusted_out["outlier_upper"] = upper
                adjusted_out["is_outlier"] = 1 if is_outlier else 0
                writer.writerow({k: fmt(adjusted_out[k]) if isinstance(adjusted_out[k], float) else adjusted_out[k]
                                 for k in processed_fields})
                all_by_group[adjusted_group].append(adjusted)
                if not is_outlier:
                    kept_by_group[adjusted_group].append(adjusted)

    summary_fields = [
        "variant", "event", "value_mode", "n_raw", "n_kept", "n_dropped", "drop_rate",
        "raw_mean_empty_cycles_per_event",
        "raw_median_empty_cycles_per_event",
        "raw_q1_empty_cycles_per_event",
        "raw_q3_empty_cycles_per_event",
        "raw_iqr_empty_cycles_per_event",
        "raw_mean_direct_cycles_per_event",
        "raw_median_direct_cycles_per_event",
        "raw_q1_direct_cycles_per_event",
        "raw_q3_direct_cycles_per_event",
        "raw_iqr_direct_cycles_per_event",
        "raw_mean_pgot_cycles_per_event",
        "raw_median_pgot_cycles_per_event",
        "raw_q1_pgot_cycles_per_event",
        "raw_q3_pgot_cycles_per_event",
        "raw_iqr_pgot_cycles_per_event",
        "raw_mean_delta_cycles_per_event",
        "raw_median_delta_cycles_per_event",
        "raw_q1_delta_cycles_per_event",
        "raw_q3_delta_cycles_per_event",
        "raw_iqr_delta_cycles_per_event",
        "raw_stddev_delta_cycles_per_event",
        "kept_mean_empty_cycles_per_event",
        "kept_median_empty_cycles_per_event",
        "kept_q1_empty_cycles_per_event",
        "kept_q3_empty_cycles_per_event",
        "kept_iqr_empty_cycles_per_event",
        "kept_mean_direct_cycles_per_event",
        "kept_median_direct_cycles_per_event",
        "kept_q1_direct_cycles_per_event",
        "kept_q3_direct_cycles_per_event",
        "kept_iqr_direct_cycles_per_event",
        "kept_mean_pgot_cycles_per_event",
        "kept_median_pgot_cycles_per_event",
        "kept_q1_pgot_cycles_per_event",
        "kept_q3_pgot_cycles_per_event",
        "kept_iqr_pgot_cycles_per_event",
        "kept_mean_delta_cycles_per_event",
        "kept_median_delta_cycles_per_event",
        "kept_q1_delta_cycles_per_event",
        "kept_q3_delta_cycles_per_event",
        "kept_iqr_delta_cycles_per_event",
        "kept_stddev_delta_cycles_per_event",
    ]
    summary_rows = []
    order = {"scheduled": 0, "scheduled_empty_adjusted": 1, "barriered": 2}
    for variant, event in sorted(all_by_group, key=lambda x: (order.get(x[0], 99), x[1])):
        raw = all_by_group[(variant, event)]
        kept = kept_by_group[(variant, event)]
        value_mode = "empty_adjusted" if variant == "scheduled_empty_adjusted" else "raw"
        summary_rows.append(make_summary_row(variant, event, raw, kept, value_mode))

    with open(args.summary, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({k: fmt(row[k]) if isinstance(row[k], float) else row[k]
                             for k in summary_fields})

    paper_fields = [
        "variant", "event", "value_mode", "n_raw", "n_kept", "drop_rate",
        "raw_median_empty_cycles_per_event",
        "raw_median_direct_cycles_per_event",
        "raw_median_pgot_cycles_per_event",
        "raw_median_delta_cycles_per_event",
        "raw_iqr_delta_cycles_per_event",
        "raw_mean_direct_cycles_per_event",
        "raw_mean_pgot_cycles_per_event",
        "raw_mean_delta_cycles_per_event",
        "kept_median_direct_cycles_per_event",
        "kept_median_pgot_cycles_per_event",
        "kept_median_delta_cycles_per_event",
        "kept_iqr_delta_cycles_per_event",
    ]
    with open(args.paper_table, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=paper_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({
                "variant": row["variant"],
                "event": row["event"],
                "value_mode": row["value_mode"],
                "n_raw": row["n_raw"],
                "n_kept": row["n_kept"],
                "drop_rate": fmt(row["drop_rate"]),
                "raw_median_empty_cycles_per_event": fmt(row["raw_median_empty_cycles_per_event"]),
                "raw_median_direct_cycles_per_event": fmt(row["raw_median_direct_cycles_per_event"]),
                "raw_median_pgot_cycles_per_event": fmt(row["raw_median_pgot_cycles_per_event"]),
                "raw_median_delta_cycles_per_event": fmt(row["raw_median_delta_cycles_per_event"]),
                "raw_iqr_delta_cycles_per_event": fmt(row["raw_iqr_delta_cycles_per_event"]),
                "raw_mean_direct_cycles_per_event": fmt(row["raw_mean_direct_cycles_per_event"]),
                "raw_mean_pgot_cycles_per_event": fmt(row["raw_mean_pgot_cycles_per_event"]),
                "raw_mean_delta_cycles_per_event": fmt(row["raw_mean_delta_cycles_per_event"]),
                "kept_median_direct_cycles_per_event": fmt(row["kept_median_direct_cycles_per_event"]),
                "kept_median_pgot_cycles_per_event": fmt(row["kept_median_pgot_cycles_per_event"]),
                "kept_median_delta_cycles_per_event": fmt(row["kept_median_delta_cycles_per_event"]),
                "kept_iqr_delta_cycles_per_event": fmt(row["kept_iqr_delta_cycles_per_event"]),
            })


if __name__ == "__main__":
    main()
