#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Boot-level descriptive summaries. Does not turn processes into independent boots.
Ratios > 1 mean VKSO costs more. No significance/equivalence claim is made.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys
from collect import PROTOCOL, validate_rows

def verify_result_files(root):
    expected = set()
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, sep, name = line.partition('  ')
        path = Path(name)
        if not sep or len(digest) != 64 or path.is_absolute() or '..' in path.parts:
            raise ValueError('invalid result checksum entry')
        if name in expected or not name or (root / path).is_symlink():
            raise ValueError('duplicate/unsafe result checksum entry')
        expected.add(name)
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError('result checksum mismatch: ' + name)
    if not {'manifest.json', 'public.csv', 'build-manifest.json'}.issubset(expected):
        raise ValueError('missing result integrity records')


def load_boots(roots):
    found = sorted({p.resolve() for root in roots
                    for p in Path(root).glob('**/public/manifest.json')})
    if not found:
        raise ValueError('no public-direct boot manifests found')
    seen_boots = set()
    source_identity = None
    boots = []
    for path in found:
        verify_result_files(path.parent)
        meta = json.loads(path.read_text())
        if meta['protocol'] != PROTOCOL or meta['status'] != 'complete':
            raise ValueError(f'incomplete or mixed protocol: {path}')
        case_dir = path.parent.parent
        if case_dir.name != meta['case'] or not (case_dir / 'complete').is_file():
            raise ValueError(f'outer registration/cleanup did not complete: {path}')
        completion = (case_dir / 'complete').read_text().splitlines()
        if 'status=complete' not in completion or 'case=' + meta['case'] not in completion:
            raise ValueError('invalid outer completion record')
        boot_id = meta['boot_id']
        if not boot_id or boot_id in seen_boots:
            raise ValueError(f'reused boot_id is not an independent repeat: {boot_id}')
        seen_boots.add(boot_id)
        if meta['case'] not in {'raw-normal', 'vkso-normal',
                               'raw-no-retpoline', 'vkso-no-retpoline'}:
            raise ValueError('unknown configuration')
        if not meta['case'].startswith(meta['backend'] + '-'):
            raise ValueError('backend/case mismatch')
        expected = {'raw': 'native-libc', 'vkso': 'vkso-direct'}[meta['backend']]
        if expected != meta['implementation']:
            raise ValueError('backend/caller mismatch')
        build = json.loads((path.parent / 'build-manifest.json').read_text())
        identity = (build['cc_version'], build['flags'], build['sources'], build['libc_version'],
                    meta['libc'], meta['iterations'], meta['warmup'], meta['cpu'],
                    meta['repeats'], meta['processes'])
        if source_identity is not None and identity != source_identity:
            raise ValueError('mixed source, compiler, flags or libc build; analyze separately')
        source_identity = identity
        with (path.parent / 'public.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        validate_rows(rows, expected, meta['repeats'], meta['iterations'])
        values = {}
        for row in rows:
            values.setdefault(row['api'], []).append(float(row['tsc_cycles_per_call']))
        for api, costs in values.items():
            boots.append(dict(case=meta['case'], boot_id=boot_id, api=api,
                              tsc_cycles_per_call=statistics.median(costs),
                              batches=len(costs), source=str(path)))
    return boots

def comparisons(boots):
    configurations = {row['case'] for row in boots}
    expected = {'raw-normal', 'vkso-normal', 'raw-no-retpoline', 'vkso-no-retpoline'}
    if configurations != expected:
        raise ValueError('the formal summary requires all four configurations')
    groups = {}
    for row in boots:
        groups.setdefault((row['case'], row['api']), []).append(row['tsc_cycles_per_call'])
    result = []
    for variant in ('normal', 'no-retpoline'):
        for api in sorted({row['api'] for row in boots}):
            raw = groups.get(('raw-' + variant, api), [])
            vkso = groups.get(('vkso-' + variant, api), [])
            if not raw or not vkso:
                continue
            a, b = statistics.median(raw), statistics.median(vkso)
            result.append(dict(variant=variant, api=api, raw_boots=len(raw),
                          vkso_boots=len(vkso), raw_median=a, vkso_median=b,
                          cost_ratio=b / a, percent_change=(b / a - 1) * 100,
                          scope='boot-level descriptive; not an equivalence test'))
    return result

def write_csv(path, rows):
    if not rows:
        raise ValueError('no matched configurations to summarize')
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roots', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        boots = load_boots(args.roots)
        ratios = comparisons(boots)
        args.out.mkdir()
        write_csv(args.out / 'boots.csv', boots)
        write_csv(args.out / 'comparisons.csv', ratios)
    except (OSError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
