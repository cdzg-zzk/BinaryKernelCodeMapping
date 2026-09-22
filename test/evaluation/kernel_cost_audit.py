#!/usr/bin/env python3
"""Audit full-input LZ4/XZ records independently of the guest collector."""
from pathlib import Path
import argparse
from collections import Counter
import csv
import hashlib
import json
import re
import subprocess

BACKENDS = ('stock-kernel', 'matched-direct-kernel', 'owner-kernel')
SILESIA = ('dickens', 'mozilla', 'mr', 'nci', 'ooffice', 'osdb', 'reymont',
           'samba', 'sao', 'webster', 'x-ray', 'xml')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_bch(archive):
    from bch_kernel_audit import audit as bch_audit
    validation = archive / 'evidence/validation'
    directory = validation / 'kernel-cost'
    result = json.loads((archive / 'result.json').read_text())
    record = json.loads((directory / 'status.json').read_text())
    require(result['status'] == record['status'] == 'pass' and record['same_registered_owner'],
            'BCH registered guest failed')
    require(record['boot_id'] == result['guest_record']['boot_id'], 'different BCH boot')
    config = record['configuration']
    require(config == dict(measure=True, correctness_vectors=128, outer_runs=11, sample_ms=10, cpu=1),
            'BCH full configuration changed')
    audit_record = bch_audit(directory, measure=True)
    references = [int(json.loads((directory / f'modules-{name}.json').read_text())['vkso_bch']['refcnt'])
                  for name in ('before-driver', 'with-driver', 'after-driver')]
    require(references == [1, 2, 1], 'BCH registered/observer refcount differs')
    symbols = json.loads((directory / 'public-api-symbols.json').read_text())
    expected = {prefix + api for prefix in ('bch_', 'matched_bch_', 'vkso_bch_')
                for api in ('init', 'free', 'encode', 'decode')}
    require(len(symbols) == 12 and {s['name'] for s in symbols} == expected, 'BCH public APIs missing')
    dmesg = (directory / 'dmesg-after-driver.txt').read_text()
    for symbol in symbols:
        provider = '[vkso_bch]' if symbol['name'].startswith('vkso_') else (
            '[bch_matched]' if symbol['name'].startswith('matched_') else '[bch]')
        addresses = re.findall(r'BCH_KERNEL_BENCH api [^\n]*\b' +
                               re.escape(symbol['name']) + r'=([0-9a-fA-F]+)\b', dmesg)
        require(symbol['module'] == [provider] and len(addresses) == 1 and
                int(addresses[0], 16) == int(symbol['address'], 16) != 0, 'BCH API binding differs')
    owner = archive / 'payload/owner/vkso_bch.ko'
    build_id = re.search(r'Build ID: ([0-9a-f]+)', subprocess.check_output(['readelf', '-n', owner], text=True)).group(1)
    descriptor = [line.split() for line in (validation / 'export/vkso/metadata/owner_descriptors.txt').read_text().splitlines()
                  if line and not line.startswith('#')]
    require(len(descriptor) == 1 and descriptor[0][2:] == ['vkso_bch', build_id], 'different registered BCH owner')
    compiler = json.loads((archive / 'kernel-cost-build/compiler-comparison.json').read_text())
    require(compiler['status'] == 'pass' and compiler['records'][0]['normalized_compiler_argv'] ==
            compiler['records'][1]['normalized_compiler_argv'], 'BCH compiler control differs')
    pages = json.loads((validation / 'registered-pfns.json').read_text())
    require(pages['status'] == 'pass' and len(pages['pages']) == 4 and
            all(p['shared'] and p['user_pfn'] == p['kernel_pfn'] for p in pages['pages']), 'BCH PFN mismatch')
    require(result['guest_record']['restoration_verified'], 'BCH release not verified')
    return dict(**audit_record, same_registered_owner=True, owner_refcnt=references,
                owner_build_id=build_id, api_bindings=12, source_pages=4)


def audit(archive):
    archive = Path(archive)
    validation = archive / 'evidence/validation'
    directory = validation / 'kernel-cost'
    if (directory / 'driver-status.txt').exists():
        return audit_bch(archive)
    result = json.loads((archive / 'result.json').read_text())
    record = json.loads((directory / 'collection.json').read_text())
    config = record['configuration']
    algorithm = config['algorithm']
    backends = config.get('backends', BACKENDS)
    new_xz = config.get('matched_definition') == 'original-source-owner-codegen'
    require(algorithm in ('lz4', 'xz'), 'unsupported algorithm')
    require(result['status'] == record['status'] == 'pass', 'guest or collector failed')
    require(config['outer_runs'] == 11 and config['sample_ms'] == 10 and config['cpu'] == 1,
            'not the complete collector configuration')
    require(record['cpu_affinity'] == [1], 'caller was not pinned')
    require(record['boot_id'] == result['guest_record']['boot_id'], 'different guest boot')
    require([record['owner_refcnt_' + name] for name in ('before', 'active', 'after')] == [1, 2, 1],
            'registration/observer owner references differ')
    require(all(row['returncode'] == 0 for row in record['module_commands']), 'module command failed')
    cases = [(name, size) for name in SILESIA for size in (65536, 1048576)] if algorithm == 'lz4' else [
        (name, 0) for name in ('bash', 'python3', 'libc.so.6')]
    require([(row['case'], row['block_bytes']) for row in record['inputs']] == cases,
            'full input matrix missing or changed')
    inputs = {}
    for item in record['inputs']:
        path = archive / 'payload' / ('corpus' if algorithm == 'lz4' else 'inputs') / item['case']
        require(item['bytes'] == path.stat().st_size and item['sha256'] == sha(path), 'wrong full input identity')
        inputs[item['case'], item['block_bytes']] = item
    if algorithm == 'lz4':
        require(sum(item['bytes'] for item in record['inputs']) == 2 * 211938580,
                'Silesia bytes do not cover the complete corpus')
    else:
        for item in record['inputs']:
            path = archive / str(Path(item['compressed_path']).relative_to('/work')).replace(
                'validation/', 'evidence/validation/', 1)
            require(path.stat().st_size == item['compressed_bytes'] and sha(path) == item['compressed_sha256'],
                    'wrong compressed input identity')
    expected = Counter((case, block, outer, backends[(position + outer + index) % 3], position)
        for index, (case, block) in enumerate(cases) for outer in range(11) for position in range(3))
    observed = Counter((r['case'], r['block_bytes'], r['outer_run'], r['backend'], r['position'])
                       for r in record['trials'])
    require(expected == observed, 'missing, duplicated or misordered trial identities')
    operations = ('compress', 'decompress') if algorithm == 'lz4' else ('decompress',)
    for trial in record['trials']:
        item = inputs[trial['case'], trial['block_bytes']]
        require(trial['full_output_match'] is True and trial['output_sha256'] == item['sha256'] and
                trial['bytes'] == item['bytes'] and trial['rows'] == len(operations), 'full output check differs')
        if algorithm == 'lz4':
            count = (item['bytes'] + item['block_bytes'] - 1) // item['block_bytes']
            require(trial['independent_cross_decode_match'] is True and trial['blocks'] == count,
                    'independent full block decode missing')
    rows = list(csv.DictReader((directory / 'raw.csv').open()))
    expected_rows = Counter((case, block, outer, backend, operation)
        for case, block in cases for outer in range(11) for backend in backends for operation in operations)
    observed_rows = Counter((r['case'], int(r['block_bytes']), int(r['outer_run']), r['backend'], r['operation'])
                            for r in rows)
    require(expected_rows == observed_rows, 'raw result matrix missing or duplicated')
    for row in rows:
        item = inputs[row['case'], int(row['block_bytes'])]
        require(row['status'] == 'pass' and int(row['cpu']) == 1 and int(row['bytes']) == item['bytes'] and
                int(row['repeats']) > 0 and int(row['elapsed_ns']) >= 10000000, 'invalid raw measurement')
        if algorithm == 'xz':
            require(int(row['compressed_bytes']) == item['compressed_bytes'] and int(row['blocks']) == 1,
                    'XZ did not consume the full compressed input')
        else:
            require(int(row['blocks']) == (item['bytes'] + item['block_bytes'] - 1) // item['block_bytes'],
                    'LZ4 did not cover all blocks')
    symbols = {}
    for line in (directory / 'kallsyms.txt').read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            symbols.setdefault(fields[2], []).append((int(fields[0], 16),
                fields[3].strip('[]') if len(fields) > 3 else 'vmlinux'))
    require(len(record['bindings']) == (6 if algorithm == 'lz4' else 13 if new_xz else 14), 'missing public APIs')
    methods = {'compress': 'LZ4_compress_default', 'decode': 'LZ4_decompress_safe'} if algorithm == 'lz4' else {
        'init': 'xz_dec_init', 'run': 'xz_dec_run', 'reset': 'xz_dec_reset', 'end': 'xz_dec_end', 'crc_init': 'xz_crc32_init'}
    require(Counter((r['backend'], r['method'], r['symbol']) for r in record['bindings']) ==
            Counter((backend, method, prefix + symbol) for backend, prefix in zip(backends, ('', 'matched_', 'vkso_'))
                    for method, symbol in methods.items() if not (method == 'crc_init' and
                    (backend == 'stock-kernel' or (new_xz and backend == 'matched-build-kernel')))),
            'public API identity set differs')
    for binding in record['bindings']:
        address, provider = int(binding['address'], 16), binding['provider']
        require(address and symbols.get(binding['symbol']) == [(address, provider)], 'wrong API address/provider')
        expected_provider = ('vkso_' + algorithm if binding['backend'] == 'owner-kernel' else
            'matched_' + algorithm if binding['backend'] in ('matched-direct-kernel', 'matched-build-kernel') else
            'lz4_compress' if algorithm == 'lz4' and binding['method'] == 'compress' else 'vmlinux')
        require(provider == expected_provider, 'wrong backend provider')
    owner = archive / f'payload/owner/vkso_{algorithm}.ko'
    identity = subprocess.check_output(['readelf', '-n', owner], text=True)
    build_id = re.search(r'Build ID: ([0-9a-f]+)', identity).group(1)
    descriptor = (validation / 'export/vkso/metadata/owner_descriptors.txt').read_text().splitlines()
    descriptor = [line.split() for line in descriptor if line and not line.startswith('#')]
    require(len(descriptor) == 1 and descriptor[0][2:] == ['vkso_' + algorithm, build_id],
            'registered owner differs from supplied kernel module')
    compiler = json.loads((archive / 'kernel-cost-build/compiler-comparison.json').read_text())
    require(compiler['status'] == 'pass' and len(compiler['objects']) == (2 if algorithm == 'lz4' else 3 if new_xz else 4),
            'compiler control incomplete')
    for obj in compiler['objects']:
        require(obj['records'][0]['normalized'] == obj['records'][1]['normalized'], 'compiler options differ')
    pages = json.loads((validation / 'registered-pfns.json').read_text())
    require(pages['status'] == 'pass' and len(pages['pages']) == (5 if algorithm == 'lz4' else 4),
            'registered page set differs')
    require(all(p['user_pfn'] == p['kernel_pfn'] and p['shared'] for p in pages['pages']), 'PFN mismatch')
    require(result['guest_record']['restoration_verified'] is True, 'release not verified')
    return dict(status='pass', algorithm=algorithm, cases=len(cases), trials=len(record['trials']),
                rows=len(rows), api_bindings=len(record['bindings']), source_pages=len(pages['pages']),
                timed_full_file_passes=sum(int(row['repeats']) for row in rows),
                owner_build_id=build_id, scope='guest collection and record audit; no physical speed claim',
                replay_limit=('full byte comparisons' + (' and independent liblz4 decodes' if algorithm == 'lz4' else '') +
                              ' ran in the guest; per-trial output digests are retained, not all output blobs'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    report = audit(args.archive)
    (args.archive / 'kernel-cost-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
