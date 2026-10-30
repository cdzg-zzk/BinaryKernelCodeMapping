#!/usr/bin/env python3
"""Audit the matched LKL campaign and summarize task/startup/memory evidence."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.run.resolve()
    result, environment, summary = [read(out / name) for name in ['result.json', 'environment.json', 'summary.json']]
    assert result['status'] == 'complete' and result['scope'] == 'native performance'
    assert not environment['functional'] and not summary['functional_only']
    variants = environment['comparison']['variants']
    correctness = read(out / 'correctness.json')
    assert correctness['status'] == 'pass' and len(correctness['cases']) == 7 * len(variants)
    formal = lambda name: [row for line in (out / name).read_text().splitlines()
                            if (row := json.loads(line))['phase'] == 'formal']
    observations, resources = formal('observations.jsonl'), formal('resources.jsonl')
    key = lambda r: (r['image'], r['workload'], r['variant'], r['block'], r['repeat'])
    expected = len(variants) * 4 * environment['blocks'] * environment['repeats']
    assert len(observations) == len(resources) == result['observations'] == expected
    assert len({key(r) for r in observations}) == expected
    resource_by_key = {key(r): r['process'] for r in resources}
    assert len(resource_by_key) == expected and set(resource_by_key) == {key(r) for r in observations}
    groups = {}
    for row in observations:
        groups.setdefault((row['image'], row['workload'], row['variant']), []).append(row)
    table = []
    for (image, workload, variant), rows in sorted(groups.items()):
        assert len(rows) == environment['blocks'] * environment['repeats']
        item = dict(image=image, workload=workload, variant=variant, trials=len(rows),
                    task_ms=1000 * statistics.median(r['wall_seconds'] for r in rows),
                    client_cpu_ms=1000 * statistics.median(r['client_user_seconds'] + r['client_system_seconds'] for r in rows),
                    daemon_cpu_ms=1000 * statistics.median(r['server_cpu_seconds'] for r in rows))
        process = [resource_by_key[key(r)] for r in rows]
        if variant == 'original':
            assert all(p is None for p in process)
        else:
            assert all(p is not None for p in process)
            item['ready_ms'] = 1000 * statistics.median(p['startup_seconds'] for p in process)
            for phase in ('before', 'after'):
                for field in ('Rss', 'Pss', 'VmHWM', 'Threads'):
                    values = [p[phase][field] for p in process]
                    item[f'{phase}_{field}'] = dict(median=statistics.median(values), min=min(values), max=max(values))
            counts = []
            for process_row in process:
                match = re.search(r'iso_lookup_stats calls=(\d+) hits=(\d+) entries=(\d+)',
                                  (out / process_row['log']).read_text(errors='replace'))
                if match: counts.append(tuple(map(int, match.groups())))
            if counts:
                assert len(counts) == len(rows)
                item['lookup_cache'] = dict(calls_median=statistics.median(c[0] for c in counts),
                    hits_median=statistics.median(c[1] for c in counts),
                    entries_median=statistics.median(c[2] for c in counts),
                    hit_fraction_median=statistics.median(c[1]/c[0] for c in counts if c[0]))
        table.append(item)
    for comparison in summary['comparisons']:
        image, workload = comparison['image'], comparison['workload']
        ratios = []
        for block in range(environment['blocks']):
            median = lambda v: statistics.median(r['wall_seconds'] for r in groups[(image, workload, v)] if r['block'] == block)
            ratios.append(median(comparison['treatment']) / median(comparison['baseline']))
        assert ratios == comparison['paired_ratios']
        expected_mean = math.exp(statistics.mean(math.log(r) for r in ratios))
        assert expected_mean == comparison['geometric_mean_time_ratio']
    shared, copied = [read(out / ('pfns-' + name + '.json'))['pages'] for name in ('vkso-fuse', 'copied-fuse')]
    assert shared and all(p['shared'] for p in shared) and all(not p['shared'] for p in copied)
    if 'vkso-uncached' in variants:
        uncached = read(out / 'pfns-vkso-uncached.json')['pages']
        assert len(uncached) == len(shared) and all(p['shared'] for p in uncached)
    record = dict(status='audited', run=str(out), observations=expected,
        correctness_cases=len(correctness['cases']), shared_pages=len(shared),
        table=table, comparisons=summary['comparisons'], environment=environment,
        interpretation=[
            'Tasks use warm backing images, fresh mounts/processes and tmpfs output; startup is separate.',
            'Memory values are KiB except Threads. Rss/Pss come from smaps_rollup snapshots.',
            'VmHWM is the asynchronously accounted status counter, not an exact observed peak.',
            'User RSS/PSS do not measure total deployment memory; kernel module costs are separate.',
            'LKL memory parameters are not measured RSS. Both default and reduced configurations are retained.',
            'Linux 5.15.198 and LKL Linux 6.12 differ; cross-system effects are not page-sharing costs.',
            'Only copied-fuse versus vkso-fuse uses identical core instructions and adapter code.'
        ])
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    for row in table:
        print(row['image'], row['workload'], row['variant'], f"task={row['task_ms']:.2f}ms",
              '' if row['variant'] == 'original' else
              f"ready={row['ready_ms']:.2f}ms RSS={row['before_Rss']['median']/1024:.2f}->{row['after_Rss']['median']/1024:.2f}MiB")
    for comparison in summary['comparisons']:
        lo, hi = comparison['bootstrap_95_percent']
        print(comparison['image'], comparison['workload'], comparison['baseline'], '-> VKSO',
              f"{100*(comparison['geometric_mean_time_ratio']-1):+.2f}% [{100*(lo-1):+.2f}, {100*(hi-1):+.2f}]")


if __name__ == '__main__':
    main()
