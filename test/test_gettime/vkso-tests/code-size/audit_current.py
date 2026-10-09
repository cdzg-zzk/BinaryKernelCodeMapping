#!/usr/bin/env python3
"""Reproduce the current semantic source inventory (no build or target changes).

The reviewed JSON owns scope. This program checks source identity, ranges and
unique ownership, then emits every counted source line and category subtotal.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import tarfile
from collections import defaultdict

from audit_changes import lexical_lines, ranges

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / 'current-evidence'


def csv_text(rows, fields):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def sources(manifest, check_worktree=True):
    required = defaultdict(set)
    for row in manifest['slices']:
        required[row['origin']].add(row['path'])
    required['Raw'].update(required['Platform'])
    texts = {}
    archive = REPO / manifest['raw_archive']
    with tarfile.open(archive, 'r|xz') as tar:
        for member in tar:
            path = member.name.removeprefix('linux-5.15.198/')
            if path in required['Raw']:
                texts['Raw', path] = tar.extractfile(member).read().decode()
    for origin in ['VKSO', 'Project']:
        for path in required[origin]:
            repo_path = manifest['kernel_root'] + '/' + path if origin == 'VKSO' else path
            texts[origin, path] = subprocess.check_output(
                ['git', 'show', manifest['revision'] + ':' + repo_path], cwd=REPO, text=True)
            if check_worktree and (REPO / repo_path).read_text() != texts[origin, path]:
                raise ValueError('current source differs from evidence revision: ' + repo_path)
    platform = {r['path']: r for r in json.loads((HERE / 'platform-baseline.json').read_text())}
    for path in required['Platform']:
        lines = texts['Raw', path].splitlines(True)
        for edit in reversed(platform[path]['edits']):
            lines[edit['start']:edit['end']] = edit['lines']
        texts['Platform', path] = ''.join(lines)
        if check_worktree:
            assert texts['Platform', path] == (REPO / manifest['kernel_root'] / path).read_text()
    for path in required['GlibcReference']:
        texts['GlibcReference', path] = (HERE / manifest['glibc_reference'] / path).read_text()
    # Untracked pre-existing platform edits are captured by the older immutable
    # platform ledger. Only needed when a selected VKSO dependency is untracked.
    for key in required:
        for path in required[key]:
            if (key, path) not in texts:
                raise ValueError('source missing: ' + repr((key, path)))
    return texts


def inventory(manifest, texts):
    seen = {}
    details, slices = [], []
    totals = defaultdict(int)
    for row in manifest['slices']:
        text = texts[row['origin'], row['path']]
        selected = ranges(row['ranges'], len(text.splitlines()))
        code = dict(lexical_lines(row['path'], text))
        counted = sorted(selected & code.keys())
        for n in counted:
            key = (row['system'], row['origin'], row['path'], n)
            if key in seen:
                raise ValueError(f'double ownership: {key}: {seen[key]} / {row["id"]}')
            seen[key] = row['id']
            details.append(dict(system=row['system'], scope=row['scope'],
                                category=row['category'], component=row['component'],
                                slice_id=row['id'], origin=row['origin'], path=row['path'],
                                line=n, source=code[n]))
        slices.append({**row, 'sloc': len(counted)})
        totals[row['system'], row['scope'], row['category'], row['component']] += len(counted)
    summary = [dict(zip(['system', 'scope', 'category', 'component', 'sloc'], (*key, value)))
               for key, value in sorted(totals.items())]
    return {
        'source-lines.csv': csv_text(details, list(details[0])),
        'source-slices.csv': csv_text(slices, list(slices[0])),
        'source-summary.csv': csv_text(summary, list(summary[0])),
        'source-totals.json': json.dumps({
            'revision': manifest['revision'], 'metric': 'nonblank noncomment physical source lines',
            'deduplication': 'system/origin/path/line; duplicate ownership is an error',
            'rows': summary,
            'totals': {s: {scope: sum(r['sloc'] for r in summary if r['system'] == s and r['scope'] == scope)
                           for scope in sorted({r['scope'] for r in summary if r['system'] == s})}
                       for s in ['Raw', 'VKSO']},
        }, indent=2, ensure_ascii=False) + '\n',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--historical', action='store_true',
                        help='check the measured Git revision, without asserting current-worktree identity')
    args = parser.parse_args()
    manifest = json.loads((OUT / 'source-manifest.json').read_text())
    if args.historical and not args.check:
        parser.error('--historical requires --check; measured evidence must not be overwritten')
    outputs = inventory(manifest, sources(manifest, check_worktree=not args.historical))
    for name, data in outputs.items():
        path = OUT / name
        if args.check:
            if path.read_text() != data:
                raise ValueError('stale output: ' + name)
        else:
            path.write_text(data)
    print(outputs['source-totals.json'])
    print('source_inventory_check=PASS' if args.check else 'source_inventory_written=PASS')
    if args.historical:
        print('source_scope=measured revision; current worktree is not certified')


if __name__ == '__main__':
    main()
