#!/usr/bin/env python3
"""Read-only source/ELF/archived-record capture; never executes BCH binaries."""
from pathlib import Path
import csv
import hashlib
import io
import json
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BCH = ROOT / 'test/test_BCH'
ledger = {'scope': 'static source/disassembly and existing July17 rows only; no benchmark, guest, live helper IP or core edit',
          'codegraph': 'CodeGraph explore was attempted first and returned unrelated ELFIO symbols; targeted source/ELF fallback used',
          'commands': [], 'sources': []}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def excerpt(relative, ranges, output):
    path = ROOT / relative
    lines = path.read_text().splitlines()
    text = '\n\n'.join('\n'.join(f'{index + 1}\t{lines[index]}' for index in range(start - 1, end))
                       for start, end in ranges)
    (OUT / output).write_text(f'SOURCE {relative}\n' + text + '\n')
    ledger['sources'].append({'path': relative, 'sha256': sha(path), 'ranges': ranges, 'output': output})


def command(argv, name):
    result = subprocess.run(list(map(str, argv)), capture_output=True, text=True)
    (OUT / name).write_text(result.stdout + result.stderr)
    ledger['commands'].append({'argv': list(map(str, argv)), 'output': name, 'returncode': result.returncode})
    assert result.returncode == 0


excerpt('test/test_BCH/src/bch_bench.c', [(16, 40), (106, 151), (153, 291), (300, 350), (402, 456), (519, 637)], 'benchmark-source.txt')
excerpt('test/test_BCH/adapted/bch.c', [(77, 139), (212, 232), (425, 519), (649, 694), (963, 1140)], 'adapted-source.txt')
excerpt('test/test_BCH/vendor/parrot-bch/lib/bch.c', [(987, 1054)], 'author-decode-source.txt')
for relative, name in [('Makefile', 'userspace-Makefile.txt'), ('kmod/Makefile', 'owner-Makefile.txt'),
                       ('results/metadata.txt', 'original-metadata.txt'),
                       ('results/artifacts.sha256', 'original-artifacts.sha256'),
                       ('results/correctness-and-progress.log', 'original-correctness.log'),
                       ('results/kernel-page_mappings.txt', 'original-page_mappings.txt'),
                       ('results/kernel-relocations.txt', 'original-carrier-relocations.txt')]:
    source = BCH / relative
    (OUT / name).write_bytes(source.read_bytes())
    ledger['sources'].append({'path': str(source.relative_to(ROOT)), 'sha256': sha(source), 'output': name})

identities = []
for line in (BCH / 'results/artifacts.sha256').read_text().splitlines():
    expected, name = line.split(maxsplit=1)
    path = Path(name)
    actual = sha(path)
    assert expected == actual, path
    identities.append({'path': str(path.relative_to(ROOT)), 'recorded_sha256': expected,
                       'current_sha256': actual, 'matches_original_record': True})
adapted_sha = sha(BCH / 'adapted/bch.c')
assert adapted_sha in (BCH / 'results/metadata.txt').read_text()
for relative in ['test/evaluation/results/bch-qemu-20260912-attempt01/build-source/adapted/bch.c',
                 'test/evaluation/results/bch_resource-qemu-20260912-attempt03/build-source/adapted/bch.c']:
    assert sha(ROOT / relative) == adapted_sha
identities.append({'path': 'test/test_BCH/adapted/bch.c', 'current_sha256': adapted_sha,
                   'matches_original_metadata_and_fresh_guest_source': True})
(OUT / 'artifact-identity.json').write_text(json.dumps(identities, indent=2) + '\n')

for kind, path, symbols in [
    ('bench', BCH / 'build/bch-bench', ['prepare_decode_context', 'decode_once', 'run_context.isra.0', 'measure_context']),
    ('owner', BCH / 'kmod/vkso_bch.ko', ['vkso_bch_decode', 'find_poly_roots', 'load_ecc8']),
    ('native', BCH / 'build/libbch-kernel-native.so', ['bch_decode', 'find_poly_roots', 'load_ecc8']),
]:
    for symbol in symbols:
        command(['objdump', '-drwC', '-Mintel', '--disassemble=' + symbol, path], f'{kind}-{symbol}.asm')
    command(['nm', '-S', '--defined-only', path], f'{kind}-symbols.txt')
command(['readelf', '-Ws', BCH / 'work/vkso/lib/libvkso_bch.so'], 'carrier-symbols.txt')
command(['readelf', '-lW', BCH / 'work/vkso/lib/libvkso_bch.so'], 'carrier-load-segments.txt')
command(['objdump', '-drwC', '-Mintel', '--start-address=0x222e', '--stop-address=0x23ab',
         BCH / 'build/bch-bench'], 'bench-mode-dependent-seed.asm')
command(['readelf', '-p', '.GCC.command.line', BCH / 'kmod/bch_impl.o'], 'owner-recorded-compiler-flags.txt')
cmd_path = BCH / 'kmod/.bch_impl.o.cmd'
(OUT / 'owner-build-command.txt').write_text(cmd_path.read_text().splitlines()[0] + '\n')
ledger['sources'].append({'path': str(cmd_path.relative_to(ROOT)), 'sha256': sha(cmd_path),
                          'output': 'owner-build-command.txt', 'ranges': [[1, 1]]})
ledger['compiler_metadata_note'] = 'The optional .GCC.command.line section is absent; its readelf warning is retained. Owner build command is separately preserved from .bch_impl.o.cmd.'

with (BCH / 'results/raw.csv').open() as stream:
    reader = csv.DictReader(stream)
    fields = reader.fieldnames
    rows = [row for row in reader if row['m'] == '13' and row['t'] in ('4', '8')
            and row['errors'] == '2' and row['operation'] in ('decode-precomputed', 'decode-full')]
assert len(rows) == 132
with (OUT / 'original-two-error-rows.csv').open('w') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
summaries = []
for t in (4, 8):
    for mode in ('decode-precomputed', 'decode-full'):
        paired = []
        for outer in range(11):
            group = {row['backend']: row for row in rows if int(row['t']) == t
                     and row['operation'] == mode and int(row['outer']) == outer}
            assert set(group) == {'kernel-vkso', 'kernel-native', 'author-standalone'}
            # Reconstruct per-call time from integer duration/iteration fields.
            values = {key: int(row['total_ns']) / int(row['iterations']) for key, row in group.items()}
            paired.append({'outer': outer, 'ns_per_op_from_integers': values,
                           'vkso_over_native': values['kernel-vkso'] / values['kernel-native']})
        ratios = [row['vkso_over_native'] for row in paired]
        summaries.append({'m': 13, 't': t, 'errors': 2, 'operation': mode,
                          'median_paired_ratio': statistics.median(ratios),
                          'min_paired_ratio': min(ratios), 'max_paired_ratio': max(ratios),
                          'rounds_slower': sum(value > 1 for value in ratios), 'rounds': 11,
                          'paired': paired})
(OUT / 'original-two-error-summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
with (BCH / 'results/paired.csv').open() as stream:
    recorded = [row for row in csv.DictReader(stream) if row['m'] == '13' and row['errors'] == '2']
assert len(recorded) == 4
for summary in summaries:
    original = next(row for row in recorded if int(row['t']) == summary['t']
                    and row['operation'] == summary['operation'])
    assert abs(float(original['median_vkso_over_kernel_native']) - summary['median_paired_ratio']) < 2e-8
(OUT / 'original-paired-summary-rows.json').write_text(json.dumps(recorded, indent=2) + '\n')

# Static ABI/layout accounting, derived from recorded source formulas and ELF symbols.
static = {'scope': 'source-derived expectations for valid two-error codewords; not runtime branch/helper traces',
          'cases': [{'m': 13, 't': t, 'ecc_words': (13*t+31)//32,
                     'ecc_bytes': (13*t+7)//8, 'syndromes': 2*t,
                     'syndrome_clear_bytes': 8*t, 'each_BM_polynomial_clear_bytes': 8*t+8,
                     'BM_iteration_bound': t,
                     'load_ecc8_tail_memcpy_bytes': (13*t+7)//8 - 4*((13*t+31)//32-1),
                     'two_error_root_degree': 2, 'root_solver': 'find_poly_deg2_roots'} for t in (4, 8)],
          'elf_decode_spans': [
              {'backend': 'registered-carrier', 'elf_vaddr': 0x2e80, 'symbol_bytes': 1306,
               'end_exclusive': 0x2e80+1306, 'virtual_page_offsets': [0x2000, 0x3000]},
              {'backend': 'native', 'elf_vaddr': 0x2720, 'symbol_bytes': 1307,
               'end_exclusive': 0x2720+1307, 'virtual_page_offsets': [0x2000]}],
          'interpretation': 'Static page span and differing helper call mechanisms are candidate diagnostics, not evidence of a cache/TLB/helper cause.'}
(OUT / 'static-path-facts.json').write_text(json.dumps(static, indent=2) + '\n')
(OUT / 'ledger.json').write_text(json.dumps(ledger, indent=2) + '\n')
print(json.dumps([{key: row[key] for key in ('t', 'operation', 'median_paired_ratio', 'rounds_slower')}
                  for row in summaries], indent=2))
