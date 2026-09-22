#!/usr/bin/env python3
"""Measure algorithm adaptation diffs and retain the exact compared sources.

Source-line changes describe implementation size, not developer time or the
fraction of Linux APIs that can be exported. Runtime evidence stays separate.
"""
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
COUNT_PATH = ROOT / 'test/test_gettime/vkso-tests/code-size/count_manifest.py'
spec = importlib.util.spec_from_file_location('source_counts', COUNT_PATH)
counter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(counter)


def compare(original, adapted, name):
    before, after = original.splitlines(), adapted.splitlines()
    old_flags = counter.lexical_code_flags(Path(name), before)
    new_flags = counter.lexical_code_flags(Path(name), after)
    counts = dict(added_lines=0, deleted_lines=0, added_code_lines=0,
                  deleted_code_lines=0, original_code_lines=sum(old_flags),
                  adapted_code_lines=sum(new_flags))
    # Match unified_diff's alignment so the archived patch reproduces the counts.
    for tag, a, b, c, d in difflib.SequenceMatcher(None, before, after).get_opcodes():
        if tag == 'equal':
            continue
        counts['deleted_lines'] += b - a
        counts['added_lines'] += d - c
        counts['deleted_code_lines'] += sum(old_flags[a:b])
        counts['added_code_lines'] += sum(new_flags[c:d])
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path,
                   default=ROOT / 'test/section63/source/linux-5.15.0-119.129')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    pairs = {'bch': [('lib/bch.c', 'test/test_BCH/adapted/bch.c')]}
    pairs['lz4'] = [('lib/lz4/' + n, 'test/test_lz4/kmod/' + n)
                    for n in ('lz4_compress.c', 'lz4_decompress.c', 'lz4defs.h')]
    pairs['xz'] = [('lib/xz/' + n, 'test/test_xz/kmod/' + n)
                   for n in ('xz_dec_stream.c', 'xz_dec_lzma2.c', 'xz_dec_bcj.c',
                             'xz_crc32.c', 'xz_private.h', 'xz_stream.h', 'xz_lzma2.h')]
    pairs['xz'].append(('include/linux/xz.h', 'test/test_xz/kmod/xz.h'))
    support = {
        'lz4': ['test/test_lz4/kmod/module_meta.c', 'test/test_lz4/kmod/Makefile',
                'test/test_lz4/config/data-bindings.json'],
        'bch': ['test/test_BCH/kmod/module_meta.c', 'test/test_BCH/kmod/Makefile'],
        'xz': ['test/test_xz/kmod/module_meta.c', 'test/test_xz/kmod/Makefile',
               'test/test_xz/config/data-bindings.json'],
    }
    # Validate all inputs before creating the immutable comparison directory.
    for group in pairs.values():
        for before, after in group:
            assert (args.source_root / before).is_file(), before
            assert (ROOT / after).is_file(), after
    for group in support.values():
        for path in group:
            assert (ROOT / path).is_file(), path
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, args.output / Path(__file__).name)
    shutil.copy2(COUNT_PATH, args.output / 'count_manifest.py')
    records = []
    for name, group in pairs.items():
        directory = args.output / name
        (directory / 'original').mkdir(parents=True)
        (directory / 'adapted').mkdir()
        (directory / 'support').mkdir()
        files, patches = [], []
        for before, after in group:
            original, adapted = args.source_root / before, ROOT / after
            filename = adapted.name
            shutil.copy2(original, directory / 'original' / filename)
            shutil.copy2(adapted, directory / 'adapted' / filename)
            old, new = original.read_text(), adapted.read_text()
            files.append({'original': str(original), 'adapted': after,
                          'name': filename, **compare(old, new, filename)})
            patches.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                           fromfile='original/' + filename, tofile='adapted/' + filename))
        (directory / 'source.diff').write_text(''.join(patches))
        additions = []
        for source in support[name]:
            path = ROOT / source
            shutil.copy2(path, directory / 'support' / path.name)
            # JSON is a binding contract, not executable source SLOC.
            additions.append({'path': source, 'physical_lines': len(path.read_text().splitlines()),
                              'lexical_sloc': (None if path.suffix == '.json' else
                                sum(counter.lexical_code_flags(path, path.read_text().splitlines())))})
        keys = ('added_lines', 'deleted_lines', 'added_code_lines', 'deleted_code_lines',
                'original_code_lines', 'adapted_code_lines')
        records.append({'algorithm': name, 'files': files, 'support_files': additions,
                        'totals': {k: sum(row[k] for row in files) for k in keys}})
    result = {'scope': 'full algorithm C/header diffs against the retained original Linux source tree',
              'source_root': str(args.source_root.resolve()),
              'counting': 'SequenceMatcher default line alignment, matching the archived unified diff; lexical code flags from the existing Clocktime counter',
              'exclusions': 'generic builder/shim changes, user baseline compatibility layers, test drivers and build tools; module metadata and Kbuild are listed separately',
              'identity_limit': ('The source baseline is Ubuntu 5.15.0-119.129, retained with package provenance. Compiler and runtime identity are checked separately by the section 6.3 campaign.' if (args.source_root / 'source.json').exists() and json.loads((args.source_root / 'source.json').read_text()).get('version') == '5.15.0-119.129' else 'This is a source adaptation count; compiler and runtime identity require separate evidence.'),
              'algorithms': records}
    (args.output / 'ledger.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Algorithm source adaptation ledger', '', result['scope'] + '.', '',
             '| Algorithm | Compared files | Added / deleted physical lines | Added / deleted code lines | Module metadata SLOC | Kbuild noncomment lines |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in records:
        t = row['totals']
        s = {Path(x['path']).name: x for x in row['support_files']}
        lines.append(f"| {row['algorithm']} | {len(row['files'])} | {t['added_lines']} / {t['deleted_lines']} | {t['added_code_lines']} / {t['deleted_code_lines']} | {s['module_meta.c']['lexical_sloc']} | {s['Makefile']['lexical_sloc']} |")
    lines += ['', result['counting'] + '.', '', result['exclusions'] + '.', '',
              result['identity_limit'], '',
              'Each algorithm directory retains both compared source sets, its complete diff, and support files. Line edits include API/build compatibility changes; they are not person-hours. Runtime success must be read from the corresponding deployment archive.', '']
    (args.output / 'README.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
