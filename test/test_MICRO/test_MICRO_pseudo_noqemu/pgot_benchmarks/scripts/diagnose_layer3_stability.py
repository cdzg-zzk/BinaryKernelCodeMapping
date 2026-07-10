#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path


BUILD_ORDER = {"no_retpoline": 0, "retpoline": 1}
VARIANT_ORDER = {"data_pgot": 0, "func_pgot": 1, "all_pgot": 2}


def f3(value):
    return f"{float(value):.3f}"


def f2(value):
    return f"{float(value):.2f}"


def read_rows(results_dir):
    rows = []
    for table in sorted(Path(results_dir).glob("*/paper_table.csv")):
        experiment = table.parent.name
        with table.open(newline="") as f:
            for row in csv.DictReader(f):
                row = dict(row)
                row["experiment"] = experiment
                row["iterations"] = int(row.get("iterations", "0"))
                row["n_raw"] = int(row["n_raw"])
                for key in (
                    "origin_cycles", "variant_cycles", "delta_cycles",
                    "delta_iqr", "overhead_percent",
                ):
                    row[key] = float(row.get(key, 0.0))
                if row.get("iqr_to_abs_delta", "") == "":
                    row["iqr_to_abs_delta"] = 0.0
                else:
                    row["iqr_to_abs_delta"] = float(row.get("iqr_to_abs_delta", 0.0))
                if not row["iqr_to_abs_delta"] and row["delta_cycles"]:
                    row["iqr_to_abs_delta"] = row["delta_iqr"] / abs(row["delta_cycles"])
                rows.append(row)
    return rows


def classify(row):
    delta = abs(row["delta_cycles"])
    iqr = row["delta_iqr"]
    ratio = row["iqr_to_abs_delta"]

    if delta < 1.0 and iqr < 5.0:
        return "near_zero"
    if delta < iqr:
        return "indistinguishable"
    if ratio <= 0.25:
        return "strong"
    if ratio <= 0.50:
        return "usable"
    if ratio <= 1.00:
        return "weak"
    return "unstable"


def rank(row):
    ranks = {
        "strong": 0,
        "usable": 1,
        "weak": 2,
        "near_zero": 3,
        "indistinguishable": 4,
        "unstable": 5,
    }
    label = classify(row)
    spread = row["iqr_to_abs_delta"] if abs(row["delta_cycles"]) >= 1.0 else row["delta_iqr"]
    return ranks[label], spread, -row["iterations"]


def group_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["experiment"], row["build"], row["variant"])].append(row)
    for key in groups:
        groups[key].sort(key=lambda r: r["iterations"])
    return groups


def write_report(path, rows):
    groups = group_rows(rows)
    lines = [
        "# Layer3 Stability Diagnosis",
        "",
        "This report is generated from each experiment's `paper_table.csv`.",
        "The key stability metric is `IQR/|Δ|`: lower is better. Rows where `|Δ| < IQR` are not used as strong quantitative evidence.",
        "",
        "Stability labels:",
        "",
        "| label | meaning |",
        "|---|---|",
        "| strong | `IQR/|Δ| <= 0.25`; good paper result |",
        "| usable | `IQR/|Δ| <= 0.50`; acceptable with IQR reported |",
        "| weak | `IQR/|Δ| <= 1.00`; only cautious interpretation |",
        "| near_zero | tiny delta and tiny IQR; report as no visible overhead |",
        "| indistinguishable | `|Δ| < IQR`; signal is smaller than noise |",
        "| unstable | large spread; not suitable as a main quantitative result |",
        "",
    ]

    for key in sorted(groups, key=lambda k: (
        k[0], BUILD_ORDER.get(k[1], 99), VARIANT_ORDER.get(k[2], 99),
    )):
        group = groups[key]
        best = sorted(group, key=rank)[0]
        lines.extend([
            f"## {key[0]} / {key[1]} / {key[2]}",
            "",
            f"Selected row: iterations={best['iterations']}, Δ={f3(best['delta_cycles'])}, IQR={f3(best['delta_iqr'])}, label={classify(best)}.",
            "",
            "| iterations | n | origin cycles | PGOT cycles | Δcycles | IQR(Δ) | IQR/|Δ| | overhead% | label |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for row in group:
            lines.append(
                f"| {row['iterations']} | {row['n_raw']} | "
                f"{f3(row['origin_cycles'])} | {f3(row['variant_cycles'])} | "
                f"{f3(row['delta_cycles'])} | {f3(row['delta_iqr'])} | "
                f"{f2(row['iqr_to_abs_delta'])} | {f2(row['overhead_percent'])} | "
                f"{classify(row)} |"
            )
        lines.append("")

    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    rows = read_rows(args.results_dir)
    write_report(Path(args.out_md), rows)


if __name__ == "__main__":
    main()
