#!/usr/bin/env python3
"""Capture bounded, read-only evidence for the owner residency audit."""
import datetime
import json
import re
import subprocess
from pathlib import Path

ROOT = Path('/home/zzk/BinaryKernelCodeMapping')
OUT = Path(__file__).resolve().parent
KERNEL = '5.15.0-119-generic'
VMLINUX = Path('/usr/lib/debug/boot') / ('vmlinux-' + KERNEL)
MODULES = Path('/lib/modules') / KERNEL
SOURCE = Path('/usr/src/linux-source-5.15.0/linux-source-5.15.0')
ledger = {'scope': 'Read-only residency classification; no benchmark or module changes',
          'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'kernel_package': KERNEL, 'commands': [], 'inputs': {},
          'limitations': [
              'Kernel source snippets explain call/build paths; exact package ELF/config evidence controls the classification.',
              'CONFIG=m and an installed module file establish availability, not runtime residency.',
              'The module snapshot describes capture time only, not historical benchmark sessions.',
              'No runtime kernel addresses are captured; ELF rows omit linked addresses too.',
              'ELF inspection is limited to named symbols, section identities, two caller functions and selected relocations.']}

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(name, data):
    with (OUT / name).open('x') as file:
        file.write(data)

def input_file(path):
    path = Path(path)
    stat = path.stat()
    ledger['inputs'][str(path)] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}

def command(argv, selector, output):
    started = utc()
    result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    ledger['commands'].append({'argv': argv, 'started_utc': started,
                               'finished_utc': utc(), 'exit_code': result.returncode,
                               'selection': selector, 'output': output,
                               'stderr': result.stderr})
    if result.returncode:
        raise RuntimeError(f'command failed: {argv}')
    return result.stdout

for name in ['ledger.json', 'config.txt', 'module-snapshot.txt', 'elf-symbols.tsv',
             'elf-sections.tsv', 'elf-build-identities.txt', 'caller-evidence.txt',
             'source-snippets.txt']:
    if (OUT / name).exists():
        raise SystemExit(f'refusing to overwrite {OUT / name}')

ledger['repository_head'] = command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                    'complete commit identity', 'ledger.json').strip()
config = Path('/boot') / ('config-' + KERNEL)
input_file(config)
keys = {'BCH', 'LZ4_COMPRESS', 'LZ4HC_COMPRESS', 'LZ4_DECOMPRESS', 'XZ_DEC',
        'XZ_DEC_X86', 'XZ_DEC_BCJ', 'XZ_DEC_TEST', 'SQUASHFS', 'SQUASHFS_LZ4',
        'SQUASHFS_XZ', 'MTD', 'MTD_NAND_CORE', 'MTD_NAND_ECC_SW_BCH',
        'CRYPTO_LZ4', 'CRYPTO_LZ4HC'}
config_lines = [f'# Source: {config}']
for line_number, line in enumerate(config.read_text().splitlines(), 1):
    if any(line.startswith('CONFIG_' + key + '=') for key in keys):
        config_lines.append(f'{line_number}: {line}')
write('config.txt', '\n'.join(config_lines) + '\n')

uname = command(['uname', '-r'], 'complete release string', 'module-snapshot.txt').strip()
snapshot_time = utc()
module_rows = [line.split() for line in Path('/proc/modules').read_text().splitlines()]
relevant_names = {'bch', 'lz4_compress', 'lz4hc_compress', 'lz4', 'lz4hc',
                  'xz_dec_test', 'vkso_bch', 'vkso_lz4', 'vkso_xz'}
ledger['module_snapshot'] = {'captured_utc': snapshot_time, 'source': '/proc/modules',
                             'uname_release': uname,
                             'present_relevant_names': sorted(row[0] for row in module_rows
                                                              if row[0] in relevant_names),
                             'searched_names': sorted(relevant_names),
                             'omitted_column': 'runtime address (column 6)'}
write('module-snapshot.txt', f'# Captured UTC: {snapshot_time}\n# uname -r: {uname}\n'
      '# Source: /proc/modules; columns 1-5, runtime address omitted\n'
      + '\n'.join(' '.join(row[:5]) for row in module_rows) + '\n')

symbols = {'LZ4_compress_default', 'LZ4_compress_fast', 'LZ4_decompress_safe',
           'LZ4_decompress_safe_partial', 'LZ4_decompress_fast',
           'bch_init', 'bch_free', 'bch_encode', 'bch_decode',
           'xz_dec_init', 'xz_dec_run', 'xz_dec_reset', 'xz_dec_end',
           'vkso_LZ4_compress_fast', 'vkso_LZ4_decompress_safe',
           'vkso_bch_init', 'vkso_bch_encode', 'vkso_bch_decode',
           'vkso_xz_dec_init', 'vkso_xz_dec_run'}
elf_paths = [VMLINUX, MODULES / 'kernel/lib/lz4/lz4_compress.ko',
             MODULES / 'kernel/lib/bch.ko',
             ROOT / 'test/test_lz4/kmod/vkso_lz4.ko',
             ROOT / 'test/test_BCH/kmod/vkso_bch.ko',
             ROOT / 'test/test_xz/kmod/vkso_xz.ko']
symbol_rows = ['file\tsymbol\tsize_bytes\tbind\tsection_index\tsection_name']
section_rows = ['file\tsection_index\tsection_name\ttype']
identities = []
ledger['elf_symbol_selection'] = sorted(symbols)
ledger['elf_symbol_matches'] = {}
for path in elf_paths:
    input_file(path)
    raw = command(['readelf', '-SW', str(path)],
                  'section index/name/type for .text, .init.text and .rodata only; no addresses',
                  'elf-sections.tsv')
    sections = {}
    for line in raw.splitlines():
        match = re.match(r'\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)', line)
        if match:
            index, name, kind = match.groups()
            sections[index] = name
            if name in {'.text', '.init.text', '.rodata'}:
                section_rows.append('\t'.join([str(path), index, name, kind]))
    raw = command(['readelf', '-Ws', str(path)],
                  'FUNC entries whose names are in ledger elf_symbol_selection; linked addresses omitted',
                  'elf-symbols.tsv')
    found = []
    for line in raw.splitlines():
        row = line.split()
        if len(row) >= 8 and row[3] == 'FUNC' and row[7] in symbols:
            symbol_rows.append('\t'.join([str(path), row[7], row[2], row[4],
                                           row[6], sections.get(row[6], row[6])]))
            found.append(row[7])
    ledger['elf_symbol_matches'][str(path)] = sorted(set(found))
    raw = command(['readelf', '-n', str(path)], 'Build ID lines only',
                  'elf-build-identities.txt')
    identities.append(str(path) + '\n' + '\n'.join(line.strip() for line in raw.splitlines()
                                                  if 'Build ID:' in line))
write('elf-symbols.tsv', '\n'.join(symbol_rows) + '\n')
write('elf-sections.tsv', '\n'.join(section_rows) + '\n')
write('elf-build-identities.txt', '\n\n'.join(identities) + '\n')

callers = []
for function, targets in [('lz4_uncompress', {'LZ4_decompress_safe'}),
                          ('squashfs_xz_uncompress', {'xz_dec_reset', 'xz_dec_run'})]:
    raw = command(['objdump', '-d', '--disassemble=' + function, str(VMLINUX)],
                  f'call instructions to {sorted(targets)}; only instruction bytes and target names retained',
                  'caller-evidence.txt')
    callers.append(f'Source ELF: {VMLINUX}\nCaller function: {function}')
    matched = []
    for line in raw.splitlines():
        match = re.search(r'\bcall\s+[^<]*<([^>]+)>', line)
        if match and match.group(1) in targets:
            byte_part = line.split(':', 1)[1].split('call', 1)[0].strip()
            matched.append(f'  bytes: {byte_part}; call target: {match.group(1)}')
    if len(matched) != len(targets):
        raise RuntimeError(f'unexpected selected call count for {function}: {matched}')
    callers.extend(matched)
for path, targets in [(MODULES / 'kernel/crypto/lz4.ko',
                       {'LZ4_compress_default', 'LZ4_decompress_safe'}),
                      (MODULES / 'kernel/drivers/mtd/nand/nandcore.ko',
                       {'bch_init', 'bch_encode', 'bch_decode'})]:
    input_file(path)
    raw = command(['readelf', '-rW', str(path)],
                  f'relocations to {sorted(targets)}; only type and target retained',
                  'caller-evidence.txt')
    callers.append(f'Caller module: {path}')
    for line in raw.splitlines():
        row = line.split()
        if len(row) >= 5 and row[4] in targets:
            callers.append(f'  {row[2]} {row[4]}')
write('caller-evidence.txt', '\n'.join(callers) + '\n')

snippets = []
for path in [ROOT / 'test/test_lz4/kmod/Makefile',
             ROOT / 'test/test_BCH/kmod/Makefile',
             ROOT / 'test/test_xz/kmod/Makefile']:
    input_file(path)
    snippets.append(f'## {path}')
    snippets.extend(f'{number}: {line}' for number, line in enumerate(path.read_text().splitlines(), 1))
for path, pattern in [
        (ROOT / 'test/test_lz4/run.sh', r'insmod|rmmod|--owner-ko'),
        (ROOT / 'test/test_BCH/run.sh', r'insmod|rmmod|--owner-ko'),
        (ROOT / 'test/test_xz/run.sh', r'insmod|rmmod|--owner-ko'),
        (SOURCE / 'lib/Makefile', r'CONFIG_(BCH|LZ4|XZ_DEC)'),
        (SOURCE / 'lib/lz4/Makefile', r'CONFIG_LZ4'),
        (SOURCE / 'lib/xz/Makefile', r'CONFIG_XZ_DEC'),
        (SOURCE / 'drivers/mtd/nand/Makefile', r'ecc-sw-bch'),
        (SOURCE / 'fs/squashfs/lz4_wrapper.c', r'LZ4_decompress_safe'),
        (SOURCE / 'fs/squashfs/xz_wrapper.c', r'xz_dec_(init|run)'),
        (SOURCE / 'crypto/lz4.c', r'LZ4_(compress_default|decompress_safe)'),
        (SOURCE / 'drivers/mtd/nand/ecc-sw-bch.c', r'\bbch_(init|encode|decode)\(')]:
    input_file(path)
    snippets.append(f'## {path} [selection: {pattern}]')
    snippets.extend(f'{number}: {line}' for number, line in enumerate(path.read_text().splitlines(), 1)
                    if re.search(pattern, line))
builtin = MODULES / 'modules.builtin'
input_file(builtin)
snippets.append(f'## {builtin} [selection: lib/lz4/ or lib/xz/]')
snippets.extend(f'{number}: {line}' for number, line in enumerate(builtin.read_text().splitlines(), 1)
                if '/lib/lz4/' in line or '/lib/xz/' in line)
write('source-snippets.txt', '\n'.join(snippets) + '\n')
ledger['finished_utc'] = utc()
write('ledger.json', json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
print('Residency audit evidence saved:', OUT)
