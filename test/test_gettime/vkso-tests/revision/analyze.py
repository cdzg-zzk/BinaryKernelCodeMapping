#!/usr/bin/env python3
"""Summarize round-level measurements with boots as the independent units."""
import argparse
import csv
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

KEY = ("variant", "role", "scenario", "metric", "unit", "protocol")


def quantile(values, p):
    values = sorted(values)
    point = (len(values) - 1) * p
    low, high = math.floor(point), math.ceil(point)
    return values[low] + (values[high] - values[low]) * (point - low)


def boot_values(rows):
    grouped = defaultdict(list)
    seen = set()
    identities = {}
    for row in rows:
        key = tuple(row[name] for name in KEY)
        identity = (*key, row["method"], row["boot_id"], row["round"])
        if identity in seen:
            raise ValueError(f"duplicate round: {identity}")
        seen.add(identity)
        value = float(row["value"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("non-finite or negative measurement")
        # Backend boot identities must not be pooled across images/configurations.
        image_key = (row["variant"], row["role"], row["image_sha256"])
        previous = identities.setdefault(row["boot_id"], image_key)
        if previous != image_key:
            raise ValueError("one boot_id has inconsistent image/configuration")
        grouped[(*key, row["method"], row["boot_id"])].append(value)
    boots = defaultdict(dict)
    for (*prefix, method, boot), values in grouped.items():
        boots[(*prefix, method)][boot] = statistics.median(values)
    return boots


def compare(left, right, rng, samples):
    """right/left; preserve covariance only when the SAME boots were measured."""
    shared = left.keys() & right.keys()
    if shared and left.keys() != right.keys():
        raise ValueError("incomplete matched-boot comparison")
    paired = bool(shared)
    positive = min(left.values()) > 0 and min(right.values()) > 0
    if paired:
        ids = sorted(left)
        point = statistics.median(right[b] / left[b] for b in ids) if positive else ''
        difference = statistics.median(right[b] - left[b] for b in ids)
    else:
        point = statistics.median(right.values()) / statistics.median(left.values()) if positive else ''
        difference = statistics.median(right.values()) - statistics.median(left.values())
    result = {"ratio": point, "ci_low": "", "ci_high": "",
              "difference": difference, "difference_ci_low": '', "difference_ci_high": '',
              "resampling": "paired boots" if paired else "independent boots"}
    if not positive:
        result['resampling'] += '; zero-valued metric: absolute difference only'
    if min(len(left), len(right)) < 3:
        result["resampling"] += "; fewer than 3 boots: descriptive only"
        return result
    estimates, differences = [], []
    for _ in range(samples):
        if paired:
            chosen = rng.choices(ids, k=len(ids))
            value = statistics.median(right[b] / left[b] for b in chosen) if positive else None
            delta = statistics.median(right[b] - left[b] for b in chosen)
        else:
            a = rng.choices(list(left.values()), k=len(left))
            b = rng.choices(list(right.values()), k=len(right))
            value = statistics.median(b) / statistics.median(a) if positive else None
            delta = statistics.median(b) - statistics.median(a)
        if value is not None:
            estimates.append(value)
        differences.append(delta)
    if estimates:
        result.update(ci_low=quantile(estimates, .025), ci_high=quantile(estimates, .975))
    result.update(difference_ci_low=quantile(differences, .025),
                  difference_ci_high=quantile(differences, .975))
    return result


def summarize(rows, samples=10000, seed=1729):
    boots = boot_values(rows)
    rng = random.Random(seed)
    output = []
    for key in sorted({k[:-1] for k in boots}):
        methods = {k[-1]: values for k, values in boots.items() if k[:-1] == key}
        for baseline, candidate in (("raw", "vkso"), ("raw", "compact-split"),
                                    ("compact-split", "vkso")):
            if baseline not in methods or candidate not in methods:
                continue
            a, b = methods[baseline], methods[candidate]
            output.append({**dict(zip(KEY, key)), "baseline": baseline, "candidate": candidate,
                           "baseline_boots": len(a), "candidate_boots": len(b),
                           "baseline_median": statistics.median(a.values()),
                           "candidate_median": statistics.median(b.values()),
                           **compare(a, b, rng, samples)})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()
    if args.bootstrap_samples < 100:
        parser.error("at least 100 bootstrap samples required")
    rows = []
    for path in args.inputs:
        with path.open(newline="") as stream:
            rows.extend(csv.DictReader(stream))
    output = summarize(rows, args.bootstrap_samples)
    if not output:
        raise SystemExit("no comparable methods; no summary written")
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)


if __name__ == "__main__":
    main()
