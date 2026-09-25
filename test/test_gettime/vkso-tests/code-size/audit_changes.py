#!/usr/bin/env python3
"""Reproduce the classified Clocktime source audit from immutable Git sources.

The manifest owns scope/category decisions. This program only projects the
listed diagnostic ranges, computes a lexical line diff, and checks coverage.
No kernel or source tree is built or modified.
"""
import argparse
import csv
import difflib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
from collections import defaultdict

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
COMMENTS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*[\s\S]*?\*/|//[^\n]*')


def lexical_lines(path, text):
    """Return (physical line, normalized noncomment source), preserving strings."""
    path = Path(path)
    is_build = path.name in ('Makefile', 'Kconfig') or path.name.endswith('defconfig') or path.suffix == '.sh'
    if not is_build:
        text = COMMENTS.sub(lambda m: re.sub(r'[^\n]', ' ', m[0])
                            if m[0].startswith(('/*', '//')) else m[0], text)
    lines = []
    help_indent = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        indent = len(line.expandtabs(8)) - len(line.expandtabs(8).lstrip())
        if path.name == 'Kconfig':
            if help_indent is not None:
                if not stripped or indent > help_indent:
                    continue
                help_indent = None
            if stripped in ('help', '---help---'):
                help_indent = indent
                continue
        if not stripped or (is_build and stripped.startswith('#')):
            continue
        # Ignore formatting whitespace, but retain whitespace inside literals.
        tokens = re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\s"\']+', stripped)
        lines.append((number, ' '.join(tokens)))
    return lines


def ranges(spec, length):
    result = set()
    for item in spec.split(',') if spec else []:
        ends = [int(x) for x in item.split('-')]
        start, end = ends[0], ends[-1]
        if start < 1 or end < start or end > length:
            raise ValueError(f'invalid range {item} for {length} lines')
        selected = set(range(start, end + 1))
        if result & selected:
            raise ValueError('overlapping ranges')
        result |= selected
    return result


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tarball', type=Path, default=HERE.parent / 'baremetal/artifacts/source-cache/linux-5.15.198.tar.xz')
    parser.add_argument('--check', action='store_true', help='compare with committed evidence without writing')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'change-manifest.json').read_text())
    platform = json.loads((HERE / 'platform-baseline.json').read_text())
    revision = manifest['revision']
    kernel_root = manifest['kernel_root']
    tracked = set(git('ls-tree', '-r', '--name-only', revision, '--', kernel_root).splitlines())
    selected = {kernel_root + '/' + row['path'] for row in manifest['kernel_files']}
    if tracked != selected:
        raise ValueError(f'kernel manifest coverage mismatch: {tracked ^ selected}')
    required = {r['path'] for r in manifest['kernel_files'] + manifest['raw_user_implementation'] + platform} | {'Makefile'}
    raw = {}
    prefix = 'linux-' + manifest['kernel_version'] + '/'
    with tarfile.open(args.tarball, 'r|xz') as archive:
        for member in archive:
            if member.name.startswith(prefix) and member.name[len(prefix):] in required:
                raw[member.name[len(prefix):]] = archive.extractfile(member).read().decode()
    for key, expected in [('VERSION', '5'), ('PATCHLEVEL', '15'), ('SUBLEVEL', '198')]:
        if not re.search(r'^' + key + r'\s*=\s*' + expected + r'\s*$', raw['Makefile'], re.M):
            raise ValueError('wrong Linux baseline version')
    rows = []
    totals = defaultdict(lambda: {'added': 0, 'deleted': 0})
    details = []
    user_inventory = []
    non_source = []
    for origin in ('kernel', 'project', 'platform'):
        for record in platform if origin == 'platform' else manifest[origin + '_files']:
            path = record['path']
            repo_path = path if origin == 'project' else kernel_root + '/' + path
            old = raw.get(path, '') if origin != 'project' else ''
            if origin == 'platform':
                new_lines = old.splitlines(True)
                for edit in reversed(record['edits']):
                    new_lines[edit['start']:edit['end']] = edit['lines']
                new = ''.join(new_lines)
                p = Path(path)
                if p.suffix not in ('.c', '.h', '.S', '.sh') and p.name not in ('Makefile', 'Kconfig'):
                    non_source.append(path)
                    continue
            else:
                new = git('show', revision + ':' + repo_path)
            new_lines, old_lines = lexical_lines(path, new), lexical_lines(path, old)
            diagnostic = ranges(record.get('diagnostic_ranges', ''), len(new.splitlines()))
            if record['category'] == 'diagnostics':
                diagnostic = {n for n, _ in new_lines}
            diagnostic_lines = [(n, s) for n, s in new_lines if n in diagnostic]
            production = [(n, s) for n, s in new_lines if n not in diagnostic]
            categories = {}
            for side, text in [('old', old), ('new', new)]:
                for override in record.get('overrides', {}).get(side, []):
                    for n in ranges(override['ranges'], len(text.splitlines())):
                        if (side, n) in categories:
                            raise ValueError('overlapping category overrides')
                        categories[side, n] = override['category']
            counts = defaultdict(lambda: {'added': 0, 'deleted': 0})
            def add(side, items, forced=None):
                operation = 'added' if side == 'new' else 'deleted'
                for n, line in items:
                    category = forced or categories.get((side, n), record['category'])
                    counts[category][operation] += 1
                    details.append({'path': repo_path, 'side': side, 'line': n,
                                    'category': category, 'source': line})
            diff = difflib.SequenceMatcher(None, [s for _, s in old_lines],
                                           [s for _, s in production], autojunk=False)
            for op, i, j, k, l in diff.get_opcodes():
                if op in ('delete', 'replace'):
                    add('old', old_lines[i:j])
                if op in ('insert', 'replace'):
                    add('new', production[k:l])
            add('new', diagnostic_lines, 'diagnostics')
            assert sum(x['added'] - x['deleted'] for x in counts.values()) == len(new_lines) - len(old_lines), repo_path
            for category, count in sorted(counts.items()):
                rows.append({'path': repo_path, 'category': category, **count})
                for kind, value in count.items():
                    totals[category][kind] += value
            if origin == 'project':
                user_inventory.append({'path': path, 'sloc': len(new_lines)})
    raw_inventory = []
    for record in manifest['raw_user_implementation']:
        text = raw[record['path']]
        selected = ranges(record['ranges'], len(text.splitlines()))
        raw_inventory.append({**record, 'sloc': sum(n in selected for n, _ in lexical_lines(record['path'], text))})
    result = {'source_revision': revision, 'baseline': 'Linux ' + manifest['kernel_version'],
              'metric': 'nonblank noncomment source lines; Kconfig help prose excluded; whitespace normalized; no macro expansion',
              'diff': 'SequenceMatcher(autojunk=False) after diagnostic projection; replacement counts once added and once deleted',
              'categories': dict(sorted(totals.items())), 'files': rows,
              'platform_non_source_excluded': non_source,
              'vkso_user_inventory': user_inventory, 'raw_user_implementation': raw_inventory}
    outputs = {'change-counts.json': json.dumps(result, ensure_ascii=False, indent=2) + '\n'}
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['path', 'side', 'line', 'category', 'source'], lineterminator='\n')
    writer.writeheader(); writer.writerows(details)
    outputs['change-lines.csv'] = output.getvalue()
    for name, content in outputs.items():
        target = HERE / name
        if args.check:
            if target.read_text() != content:
                raise ValueError('audit evidence differs: ' + str(target))
        else:
            target.write_text(content)
    print(json.dumps(result['categories'], indent=2))
    print('vkso_user_total=', sum(x['sloc'] for x in user_inventory))
    print('raw_user_implementation=', sum(x['sloc'] for x in raw_inventory))
    print('audit_check=PASS' if args.check else 'audit_written=PASS')


if __name__ == '__main__':
    main()
