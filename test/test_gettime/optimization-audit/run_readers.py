#!/usr/bin/env python3
"""Paired process diagnostics, not a replacement for boot-based performance."""
import argparse
import collections
import csv
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('carriers', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--cpu', type=int, default=2)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    binary = out / 'reader-probe'
    subprocess.run(['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-omit-frame-pointer',
                    str(HERE / 'reader_probe.c'), '-ldl', '-o', str(binary)], check=True)
    methods = ['baseline', 'entry-null', 'coarse-late-offset']
    rows, identities = [], []
    for process in range(9):
        order = methods[process % 3:] + methods[:process % 3]
        for method in order:
            command = ['setarch', 'x86_64', '-R', str(binary), str(args.carriers.resolve() / f'{method}.so'),
                       str(args.cpu), '31', '500000']
            with (out / f'{process:02}-{method}.csv').open('w') as stdout, (out / f'{process:02}-{method}.log').open('w') as stderr:
                subprocess.run(command, check=True, stdout=stdout, stderr=stderr)
            identity = (out / f'{process:02}-{method}.log').read_text().strip()
            assert identity.startswith('checks=60002 ')
            identities.append(identity)
            records = list(csv.DictReader((out / f'{process:02}-{method}.csv').open()))
            assert len(records) == 31 * 7
            for row in records:
                row.update(method=method, process=process, ticks_per_call=int(row['tsc_ticks']) / int(row['iterations']))
                rows.append(row)
    assert len(set(identities)) == 1, 'method or process layouts differ'
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row['method'], row['process'], row['scenario']].append(row['ticks_per_call'])
    medians = {key: statistics.median(value) for key, value in grouped.items()}
    summary = []
    for scenario in sorted({r['scenario'] for r in rows}):
        baseline = [medians['baseline', i, scenario] for i in range(9)]
        for method in methods:
            values = [medians[method, i, scenario] for i in range(9)]
            ratios = [v / b for v, b in zip(values, baseline)]
            summary.append(dict(scenario=scenario, method=method, median_ticks=statistics.median(values),
                median_paired_ratio=statistics.median(ratios), minimum_paired_ratio=min(ratios), maximum_paired_ratio=max(ratios)))
    (out / 'summary.json').write_text(json.dumps(dict(scope='same host boot, stable synthetic shared state, copied complete code; not formal application or concurrent performance',
        kernel=os.uname().release, layout=identities[0], processes_per_method=9, rounds=31, iterations=500000,
        warmup=10000, rows=len(rows), summary=summary), indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
