#!/usr/bin/env python3
"""Audit the complete libc-baseline guest collection against its raw artifacts."""
from pathlib import Path
import argparse
import csv
import itertools
import json
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'test/test_lz4/scripts'))
from parse_official import parse_log


def audit(out):
    v = out / 'evidence/validation'
    result = json.loads((out / 'result.json').read_text())
    assert result['status'] == 'pass' and result['qemu_returncode'] == 0 and not result['kernel_failure']
    assert result['guest_record']['restoration_verified']
    assert {x.split()[0] for x in result['guest_record']['modules_after'].splitlines()} == {'virtio_blk'}
    validation = json.loads((v / 'cli-validation.json').read_text())
    assert validation['status'] == 'pass' and len(validation['cases']) == 24
    assert validation['owner_refcnt_during_registration'] == 1
    assert all(r['full_output_match'] and r['stock_cross_decode_match'] for r in validation['cases'])
    assert 'different implementations' in validation['rep_baseline_identity_refusal']
    run = v / 'runner-validation'
    assert (run / 'correctness.log').read_text().strip() == 'cross-backend correctness: PASS (6 compressors x 6 decompressors x 12 sizes)'
    rows = list(csv.DictReader((run / 'raw.csv').open()))
    backends = {'user-default', 'user-nosimd', 'kernel-userspace-native', 'kernel-userspace-nosimd', 'kernel-userspace-libc', 'kernel-vkso'}
    expected = set(itertools.product([0], backends, [4096, 65536, 1048576], ['compress', 'decompress']))
    keys = [(int(r['run']), r['backend'], int(r['block_size']), r['operation']) for r in rows]
    assert len(rows) == len(set(keys)) == 36 and set(keys) == expected
    logs = sorted((run / 'official-logs').glob('*.log'))
    assert len(logs) == 18
    parsed = [row for log in logs for row in parse_log(log)]
    assert rows == [{k: str(v) for k, v in row.items()} for row in parsed]
    helper = json.loads((run / 'helper-targets.json').read_text())
    assert helper['status'] == 'pass' and Path(helper['same_source']).name == 'libkernel-userspace-libc.so'
    assert {r['name'] for r in helper['helpers']} == {'memcpy', 'memmove', 'memset'}
    for h in helper['helpers']:
        assert h['baseline_imports']
        assert all(i['target'] == h['provider'] for i in h['baseline_imports'])
        assert Path(h['provider']['dso']).name == 'libc.so.6'
        assert Path(h['bridge']['dso']).name == 'libshim.so'
    before = json.loads((v / 'registered-pfns.json').read_text())['pages']
    after = json.loads((v / 'restored-pfns.json').read_text())['pages']
    assert len(before) == len(after) == 5
    for a, b in zip(before, after):
        assert a['file_offset'] == b['file_offset']
        assert a['user_pfn'] == a['kernel_pfn'] == b['source_pfn'] != b['restored_user_pfn']
    app = run / 'cli-workflow'
    metadata = json.loads((app / 'metadata.json').read_text())
    assert metadata['rounds'] == 1 and metadata['block_ids'] == [4, 6]
    assert metadata['backends']['same-source'] == ['/work/baselines/libkernel-userspace-libc.so', 'kernel']
    inputs = {Path(i['path']).name: i for i in metadata['inputs']}
    assert len(inputs) == 12
    application_rows = list(csv.DictReader((app / 'raw.csv').open()))
    expected_app = set(itertools.product([0], [4, 6], inputs, metadata['backends'], ['compress', 'decompress']))
    app_keys = [(int(r['round']), int(r['block_id']), r['input'], r['backend'], r['operation']) for r in application_rows]
    assert len(application_rows) == len(set(app_keys)) == 192 and set(app_keys) == expected_app
    assert all(int(r['plain_bytes']) == inputs[r['input']]['bytes'] and int(r['wall_ns']) > 0 for r in application_rows)
    for r in application_rows:
        tag = f"r{r['round']}-b{r['block_id']}-i{list(inputs).index(r['input'])}-{r['backend']}-{r['operation']}"
        assert (app / 'logs' / (tag+'.log')).exists()
        if r['operation'] == 'compress': assert (app / 'logs' / (tag+'-verify.log')).exists()
    complete = json.loads((app / 'complete.json').read_text())
    assert complete['rows'] == 192 and complete['output_checks'] == 'all complete file outputs matched'
    for name in ('upstream-dso', 'same-source', 'kernel-vkso'):
        for block, op in itertools.product([4, 6], ['compress', 'decompress']):
            trace = dict(x.split('=', 1) for x in (app/'logs'/f'trace-{block}-{name}-{op}.txt').read_text().splitlines())
            assert int(trace[op+'_calls']) > 0
            assert trace['compress_dso'] == trace['decompress_dso'] == metadata['backends'][name][0]
    # Both ordinary variants compile the same translation units with the same
    # flags; only the linked scalar-helper source and output identities differ.
    commands = (out / 'baseline-build.log').read_text().replace('\\\n', '').splitlines()
    variants = {}
    for line in commands:
        if line.startswith(('cc ', 'gcc ')) and '-shared' in line:
            tokens = shlex.split(line)
            output = tokens[tokens.index('-o')+1]
            if Path(output).name in ('libkernel-userspace-libc.so', 'libkernel-userspace-nosimd.so'):
                variants[Path(output).name] = tokens
    assert len(variants) == 2
    def algorithm_flags(tokens):
        return [t for t in tokens if t != 'userspace_kernel/scalar_mem.c' and
                not t.startswith('-Wl,-soname,') and not t.endswith('.so')]
    assert algorithm_flags(variants['libkernel-userspace-libc.so']) == algorithm_flags(variants['libkernel-userspace-nosimd.so'])
    assert 'userspace_kernel/scalar_mem.c' not in variants['libkernel-userspace-libc.so']
    simd = (out / 'baseline-simd-audit.log').read_text()
    assert '`kernel-userspace-libc`: 0 disassembly lines' in simd
    return dict(status='pass', boot_id=result['guest_record']['boot_id'], shared_pages=5,
        owner_reference=1, cross_backend_decode_checks=432, component_processes=18, component_rows=36,
        complete_application_rows=192, helper_targets=helper['helpers'],
        libc_and_rep_algorithm_flags_equal=True, compiler_commands=variants,
        scope='complete functional/collector validation; guest times excluded from formal performance tables')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = audit(args.directory.resolve())
    (args.directory / 'independent-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('helper_targets', 'compiler_commands')}, indent=2))
