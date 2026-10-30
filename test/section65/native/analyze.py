#!/usr/bin/env python3
"""Audit completed native campaigns and retain within-campaign comparisons."""
import argparse
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_text())


def campaign(label, path):
    result = read(path / 'result.json')
    environment = read(path / 'environment.json')
    summary = read(path / 'summary.json')
    assert result['status'] == 'complete' and result['scope'] == 'native performance'
    assert not environment['functional'] and not summary['functional_only']
    correctness = read(path / 'correctness.json')
    assert correctness['status'] == 'pass' and len(correctness['cases']) == 35
    rows = [json.loads(line) for line in (path / 'observations.jsonl').read_text().splitlines()]
    formal = [r for r in rows if r['phase'] == 'formal']
    expected = 2 * 2 * 5 * environment['blocks'] * environment['repeats']
    assert len(formal) == result['observations'] == expected
    keys = {(r['image'], r['workload'], r['variant'], r['block'], r['repeat']) for r in formal}
    assert len(keys) == expected, 'duplicate observations'
    groups = {}
    for row in formal:
        groups.setdefault((row['image'], row['workload'], row['variant']), []).append(row)
    medians = []
    for (image, workload, variant), group in sorted(groups.items()):
        assert len(group) == environment['blocks'] * environment['repeats']
        medians.append(dict(image=image, workload=workload, variant=variant,
                            median_wall_ms=1000 * statistics.median(r['wall_seconds'] for r in group)))
    for comparison in summary['comparisons']:
        image, workload = comparison['image'], comparison['workload']
        ratios = []
        for block in range(environment['blocks']):
            def median(variant):
                return statistics.median(r['wall_seconds'] for r in groups[(image, workload, variant)]
                                         if r['block'] == block)
            ratios.append(median(comparison['treatment']) / median(comparison['baseline']))
        assert ratios == comparison['paired_ratios']
    shared = read(path / 'pfns-vkso-fuse.json')['pages']
    copied = read(path / 'pfns-copied-fuse.json')['pages']
    assert shared and all(p['shared'] for p in shared) and all(not p['shared'] for p in copied)
    return dict(label=label, path=str(path), formal_observations=expected,
                correctness_cases=len(correctness['cases']), shared_pages=len(shared),
                environment=environment, medians=medians, comparisons=summary['comparisons'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='append', required=True, help='LABEL=RESULT_DIRECTORY')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    records = [campaign(label, Path(path)) for label, path in (r.split('=', 1) for r in args.run)]
    record = dict(status='audited', campaigns=records,
        interpretation=[
            'Each ratio pairs treatments with their own contemporaneous control, not another campaign.',
            'Eight blocks with three fresh mounts each; medians within blocks and geometric mean of paired ratios.',
            'Reported percentile bootstrap intervals are descriptive for these exploratory optimization runs.',
            'Warm backing images; filesystem caches begin with a fresh mount/process; output goes to tmpfs.',
            'Prepared and original differ in compiler instrumentation; compat is a diagnostic control.',
            'User-domain comparison uses identical copied/shared code and FUSE frontend; it is not an LKL comparison.',
            'Short Alpine scans are noisy; no equivalence conclusion follows merely from a non-significant difference.',
            'No net deployment memory saving or developer-time reduction follows from these timings.'
        ])
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    for run in records:
        print(run['label'], run['formal_observations'], 'observations')
        for c in run['comparisons']:
            if (c['baseline'], c['treatment']) not in [('original', 'prepared'), ('copied-fuse', 'vkso-fuse')]:
                continue
            lo, hi = c['bootstrap_95_percent']
            print(f"  {c['image']} {c['workload']} {c['baseline']} -> {c['treatment']}: "
                  f"{100*(c['geometric_mean_time_ratio']-1):+.2f}% [{100*(lo-1):+.2f}, {100*(hi-1):+.2f}]")


if __name__ == '__main__':
    main()
