#!/usr/bin/env python3
import argparse
import csv
import math
import statistics
from collections import defaultdict


VALUE_COLUMNS = [
    "empty_cycles",
    "direct_cycles",
    "cached_indirect_cycles",
    "slot_direct_cycles",
    "pgot_cycles",
]

DELTA_COLUMNS = [
    "delta_cached_direct",
    "delta_slot_direct",
    "delta_pgot_cached",
    "delta_pgot_direct",
]


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


def stats_for(values):
    ordered = sorted(values)
    q1 = quantile(ordered, 0.25)
    median = quantile(ordered, 0.50)
    q3 = quantile(ordered, 0.75)
    return {
        "mean": mean(values),
        "median": median,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def fmt(v):
    if isinstance(v, int):
        return str(v)
    return f"{v:.9f}"


def recompute_deltas(row):
    row["delta_cached_direct"] = row["cached_indirect_cycles"] - row["direct_cycles"]
    row["delta_slot_direct"] = row["slot_direct_cycles"] - row["direct_cycles"]
    row["delta_pgot_cached"] = row["pgot_cycles"] - row["cached_indirect_cycles"]
    row["delta_pgot_direct"] = row["pgot_cycles"] - row["direct_cycles"]
    return row


def add_per_event(row):
    event = row["event"]
    for col in VALUE_COLUMNS + DELTA_COLUMNS:
        row[f"{col}_per_event"] = row[col] / event
    return row


def load_raw(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            event = int(raw["event"])
            row = {
                "experiment": raw["experiment"],
                "build": raw["build"],
                "value_mode": "raw",
                "run_id": int(raw["run_id"]),
                "event": event,
                "repeat": int(raw["repeat"]),
                "iterations": int(raw["iterations"]),
            }
            for col in VALUE_COLUMNS:
                row[col] = float(raw[col])
            for col in DELTA_COLUMNS:
                row[col] = float(raw[col])
            rows.append(add_per_event(recompute_deltas(row)))
    return rows


def as_empty_adjusted(row):
    adjusted = dict(row)
    adjusted["value_mode"] = "empty_adjusted"
    empty = row["empty_cycles"]
    for col in ["direct_cycles", "cached_indirect_cycles",
                "slot_direct_cycles", "pgot_cycles"]:
        adjusted[col] = row[col] - empty
    return add_per_event(recompute_deltas(adjusted))


def make_thresholds(rows):
    by_group = defaultdict(list)
    for row in rows:
        by_group[(row["build"], row["event"])].append(row)
    thresholds = {}
    for group, group_rows in by_group.items():
        # The primary old-style comparison is pgot-direct; use it only to
        # identify gross interruptions, then apply the same mask to all deltas.
        values = [r["delta_pgot_direct"] for r in group_rows]
        s = stats_for(values)
        thresholds[group] = (s["q1"] - 1.5 * s["iqr"],
                             s["q3"] + 1.5 * s["iqr"])
    return thresholds


def make_summary_row(build, value_mode, event, raw, kept):
    n_raw = len(raw)
    n_kept = len(kept)
    row = {
        "build": build,
        "value_mode": value_mode,
        "event": event,
        "n_raw": n_raw,
        "n_kept": n_kept,
        "n_dropped": n_raw - n_kept,
        "drop_rate": (n_raw - n_kept) / n_raw if n_raw else 0.0,
    }

    for col in VALUE_COLUMNS:
        raw_stats = stats_for([r[f"{col}_per_event"] for r in raw])
        kept_stats = stats_for([r[f"{col}_per_event"] for r in kept])
        row[f"raw_median_{col}_per_event"] = raw_stats["median"]
        row[f"kept_median_{col}_per_event"] = kept_stats["median"]

    for col in DELTA_COLUMNS:
        raw_stats = stats_for([r[f"{col}_per_event"] for r in raw])
        kept_stats = stats_for([r[f"{col}_per_event"] for r in kept])
        row[f"raw_mean_{col}_per_event"] = raw_stats["mean"]
        row[f"raw_median_{col}_per_event"] = raw_stats["median"]
        row[f"raw_iqr_{col}_per_event"] = raw_stats["iqr"]
        row[f"raw_stddev_{col}_per_event"] = raw_stats["stddev"]
        row[f"kept_median_{col}_per_event"] = kept_stats["median"]
        row[f"kept_iqr_{col}_per_event"] = kept_stats["iqr"]
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--processed", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--paper-table", required=True)
    parser.add_argument("--paper-main")
    parser.add_argument("--paper-diagnostics")
    args = parser.parse_args()

    rows = load_raw(args.raw)
    thresholds = make_thresholds(rows)

    processed_fields = [
        "experiment", "build", "value_mode", "run_id", "event", "repeat",
        "iterations", "outlier_lower", "outlier_upper", "is_outlier",
    ]
    for col in VALUE_COLUMNS + DELTA_COLUMNS:
        processed_fields += [col, f"{col}_per_event"]

    all_by_group = defaultdict(list)
    kept_by_group = defaultdict(list)
    with open(args.processed, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=processed_fields)
        writer.writeheader()
        for row in rows:
            group = (row["build"], row["event"])
            lower, upper = thresholds[group]
            is_outlier = row["delta_pgot_direct"] < lower or row["delta_pgot_direct"] > upper
            for out in (row, as_empty_adjusted(row)):
                out = dict(out)
                out["outlier_lower"] = lower
                out["outlier_upper"] = upper
                out["is_outlier"] = 1 if is_outlier else 0
                writer.writerow({k: fmt(out[k]) if isinstance(out[k], float) else out[k]
                                 for k in processed_fields})
                out_group = (out["build"], out["value_mode"], out["event"])
                all_by_group[out_group].append(out)
                if not is_outlier:
                    kept_by_group[out_group].append(out)

    summary_fields = [
        "build", "value_mode", "event", "n_raw", "n_kept", "n_dropped",
        "drop_rate",
    ]
    for col in VALUE_COLUMNS:
        summary_fields += [
            f"raw_median_{col}_per_event",
            f"kept_median_{col}_per_event",
        ]
    for col in DELTA_COLUMNS:
        summary_fields += [
            f"raw_mean_{col}_per_event",
            f"raw_median_{col}_per_event",
            f"raw_iqr_{col}_per_event",
            f"raw_stddev_{col}_per_event",
            f"kept_median_{col}_per_event",
            f"kept_iqr_{col}_per_event",
        ]

    build_order = {"no_retpoline": 0, "retpoline": 1}
    mode_order = {"raw": 0, "empty_adjusted": 1}
    summary_rows = []
    for build, mode, event in sorted(all_by_group,
                                     key=lambda x: (build_order.get(x[0], 99),
                                                    mode_order.get(x[1], 99),
                                                    x[2])):
        summary_rows.append(make_summary_row(
            build,
            mode,
            event,
            all_by_group[(build, mode, event)],
            kept_by_group[(build, mode, event)],
        ))

    with open(args.summary, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({k: fmt(row[k]) if isinstance(row[k], float) else row[k]
                             for k in summary_fields})

    paper_fields = [
        "build", "value_mode", "event", "n_raw", "n_kept", "drop_rate",
        "direct_cycles_per_event",
        "cached_indirect_cycles_per_event",
        "slot_direct_cycles_per_event",
        "pgot_cycles_per_event",
        "delta_cached_direct_per_event",
        "delta_slot_direct_per_event",
        "delta_pgot_cached_per_event",
        "delta_pgot_direct_per_event",
        "iqr_delta_cached_direct_per_event",
        "iqr_delta_slot_direct_per_event",
        "iqr_delta_pgot_cached_per_event",
        "iqr_delta_pgot_direct_per_event",
    ]
    with open(args.paper_table, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=paper_fields)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({
                "build": row["build"],
                "value_mode": row["value_mode"],
                "event": row["event"],
                "n_raw": row["n_raw"],
                "n_kept": row["n_kept"],
                "drop_rate": fmt(row["drop_rate"]),
                "direct_cycles_per_event": fmt(row["kept_median_direct_cycles_per_event"]),
                "cached_indirect_cycles_per_event": fmt(row["kept_median_cached_indirect_cycles_per_event"]),
                "slot_direct_cycles_per_event": fmt(row["kept_median_slot_direct_cycles_per_event"]),
                "pgot_cycles_per_event": fmt(row["kept_median_pgot_cycles_per_event"]),
                "delta_cached_direct_per_event": fmt(row["kept_median_delta_cached_direct_per_event"]),
                "delta_slot_direct_per_event": fmt(row["kept_median_delta_slot_direct_per_event"]),
                "delta_pgot_cached_per_event": fmt(row["kept_median_delta_pgot_cached_per_event"]),
                "delta_pgot_direct_per_event": fmt(row["kept_median_delta_pgot_direct_per_event"]),
                "iqr_delta_cached_direct_per_event": fmt(row["kept_iqr_delta_cached_direct_per_event"]),
                "iqr_delta_slot_direct_per_event": fmt(row["kept_iqr_delta_slot_direct_per_event"]),
                "iqr_delta_pgot_cached_per_event": fmt(row["kept_iqr_delta_pgot_cached_per_event"]),
                "iqr_delta_pgot_direct_per_event": fmt(row["kept_iqr_delta_pgot_direct_per_event"]),
            })

    if args.paper_main:
        by_key = {(r["build"], r["value_mode"], r["event"]): r for r in summary_rows}
        events = sorted({r["event"] for r in summary_rows})
        builds = sorted({r["build"] for r in summary_rows},
                        key=lambda b: build_order.get(b, 99))
        main_fields = [
            "build", "event", "n_raw", "n_kept", "drop_rate",
            "raw_direct_cycles_per_event",
            "raw_pgot_cycles_per_event",
            "raw_delta_pgot_direct_per_event",
            "raw_iqr_delta_pgot_direct_per_event",
            "adjusted_direct_cycles_per_event",
            "adjusted_pgot_cycles_per_event",
            "adjusted_delta_pgot_direct_per_event",
            "adjusted_iqr_delta_pgot_direct_per_event",
        ]
        with open(args.paper_main, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=main_fields)
            writer.writeheader()
            for build in builds:
                for event in events:
                    raw_row = by_key[(build, "raw", event)]
                    adj_row = by_key[(build, "empty_adjusted", event)]
                    writer.writerow({
                        "build": build,
                        "event": event,
                        "n_raw": raw_row["n_raw"],
                        "n_kept": raw_row["n_kept"],
                        "drop_rate": fmt(raw_row["drop_rate"]),
                        "raw_direct_cycles_per_event": fmt(raw_row["kept_median_direct_cycles_per_event"]),
                        "raw_pgot_cycles_per_event": fmt(raw_row["kept_median_pgot_cycles_per_event"]),
                        "raw_delta_pgot_direct_per_event": fmt(raw_row["kept_median_delta_pgot_direct_per_event"]),
                        "raw_iqr_delta_pgot_direct_per_event": fmt(raw_row["kept_iqr_delta_pgot_direct_per_event"]),
                        "adjusted_direct_cycles_per_event": fmt(adj_row["kept_median_direct_cycles_per_event"]),
                        "adjusted_pgot_cycles_per_event": fmt(adj_row["kept_median_pgot_cycles_per_event"]),
                        "adjusted_delta_pgot_direct_per_event": fmt(adj_row["kept_median_delta_pgot_direct_per_event"]),
                        "adjusted_iqr_delta_pgot_direct_per_event": fmt(adj_row["kept_iqr_delta_pgot_direct_per_event"]),
                    })

    if args.paper_diagnostics:
        diag_fields = [
            "build", "value_mode", "event", "n_raw", "n_kept", "drop_rate",
            "direct_cycles_per_event",
            "cached_indirect_cycles_per_event",
            "slot_direct_cycles_per_event",
            "pgot_cycles_per_event",
            "delta_cached_direct_per_event",
            "delta_slot_direct_per_event",
            "delta_pgot_cached_per_event",
            "delta_pgot_direct_per_event",
            "iqr_delta_cached_direct_per_event",
            "iqr_delta_slot_direct_per_event",
            "iqr_delta_pgot_cached_per_event",
            "iqr_delta_pgot_direct_per_event",
        ]
        with open(args.paper_diagnostics, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=diag_fields)
            writer.writeheader()
            for row in summary_rows:
                writer.writerow({
                    "build": row["build"],
                    "value_mode": row["value_mode"],
                    "event": row["event"],
                    "n_raw": row["n_raw"],
                    "n_kept": row["n_kept"],
                    "drop_rate": fmt(row["drop_rate"]),
                    "direct_cycles_per_event": fmt(row["kept_median_direct_cycles_per_event"]),
                    "cached_indirect_cycles_per_event": fmt(row["kept_median_cached_indirect_cycles_per_event"]),
                    "slot_direct_cycles_per_event": fmt(row["kept_median_slot_direct_cycles_per_event"]),
                    "pgot_cycles_per_event": fmt(row["kept_median_pgot_cycles_per_event"]),
                    "delta_cached_direct_per_event": fmt(row["kept_median_delta_cached_direct_per_event"]),
                    "delta_slot_direct_per_event": fmt(row["kept_median_delta_slot_direct_per_event"]),
                    "delta_pgot_cached_per_event": fmt(row["kept_median_delta_pgot_cached_per_event"]),
                    "delta_pgot_direct_per_event": fmt(row["kept_median_delta_pgot_direct_per_event"]),
                    "iqr_delta_cached_direct_per_event": fmt(row["kept_iqr_delta_cached_direct_per_event"]),
                    "iqr_delta_slot_direct_per_event": fmt(row["kept_iqr_delta_slot_direct_per_event"]),
                    "iqr_delta_pgot_cached_per_event": fmt(row["kept_iqr_delta_pgot_cached_per_event"]),
                    "iqr_delta_pgot_direct_per_event": fmt(row["kept_iqr_delta_pgot_direct_per_event"]),
                })


if __name__ == "__main__":
    main()
