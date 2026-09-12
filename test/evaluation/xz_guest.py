#!/usr/bin/env python3
"""Exercise unchanged full XZ Embedded decoding and declared pages in a private guest."""
from pathlib import Path
import json
import csv
import os
import shutil
import subprocess
import sys
import traceback

from lz4_guest_helpers import (execute, observe_registered_pages,
                              verify_restored_pages, write_json, digest)

ROOT = Path('/work')
REPO = ROOT / 'repo'
OUT = ROOT / 'validation'
WORK = OUT / 'export'


def validate_xz():
    record = {'scope': 'unchanged complete XZ workload; guest timing fields are diagnostic only',
              'status': 'running', 'repeats': 20, 'outer_runs': 7}
    try:
        fields = dict(line.split('=', 1) for line in
                      (WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
        library = Path(fields['library']).resolve()
        page_map = Path(fields['page_map'])
        record['library'] = str(library)
        execute(['python3', ROOT / 'scripts/audit_kernel_dso.py',
                 '--library', library, '--page-map', page_map,
                 '--report', OUT / 'kernel-dso-audit.md'], OUT / 'kernel-dso-audit.log')
        pages = observe_registered_pages(library, page_map)
        shutil.copy2(OUT / 'registered-pfns.json', OUT / 'registered-pfns-before-workload.json')
        record['shared_pages'] = len(pages['pages'])
        record['owner_refcnt_during_registration'] = int(
            Path('/sys/module/vkso_xz/refcnt').read_text())
        manifest = list(csv.reader((OUT / 'corpus/manifest.csv').read_text().splitlines()))
        assert [row[0] for row in manifest] == ['bash', 'python3', 'libc.so.6'], manifest
        inputs = []
        for label, plain, compressed in manifest:
            original = ROOT / 'inputs' / label
            assert digest(Path(plain)) == digest(original)
            inputs.append({'label': label, 'plain': plain, 'compressed': compressed,
                           'bytes': Path(plain).stat().st_size,
                           'compressed_bytes': Path(compressed).stat().st_size,
                           'source_sha256': digest(original)})
        record['inputs'] = inputs
        write_json(OUT / 'xz-validation.json', record)
        execute(['taskset', '-c', '0', ROOT / 'binaries/xz-bench',
                 '--native', ROOT / 'binaries/libxz-native.so', '--kernel', library,
                 '--repeats', '20', '--outer-runs', '7', '--',
                 *[value for row in manifest for value in row]], OUT / 'raw-diagnostic.csv')
        rows = list(csv.DictReader((OUT / 'raw-diagnostic.csv').read_text().splitlines()))
        expected = {(backend, item['label'], run) for backend in ('native', 'kernel-vkso')
                    for item in inputs for run in range(7)}
        actual = {(row['backend'], row['case'], int(row['outer_run'])) for row in rows}
        assert len(rows) == len(expected) == 42 and actual == expected
        for row in rows:
            source = next(item for item in inputs if item['label'] == row['case'])
            assert int(row['bytes']) == source['bytes']
            assert int(row['compressed_bytes']) == source['compressed_bytes']
            assert int(row['repeats']) == 20
        after = observe_registered_pages(library, page_map)
        assert [(item['file_offset'], item['kernel_pfn']) for item in pages['pages']] == [
            (item['file_offset'], item['kernel_pfn']) for item in after['pages']]
        record['coverage'] = {
            'inputs': len(inputs), 'backends': ['native', 'kernel-vkso'],
            'completed_rows': len(rows), 'complete_decodes': 42 * 21,
            'kernel_backed_complete_decodes': 21 * 21,
            'full_output_checks': 42 * 2, 'guard_pairs_checked': 42,
            'checks_in_unchanged_benchmark': ['XZ_STREAM_END for every decode',
                'entire compressed input consumed', 'entire original output produced',
                'full memcmp after warm-up and repeat loop', 'both 64-byte output guards'],
            'api': ['crc32_init', 'dec_init', 'dec_run', 'dec_reset', 'dec_end'],
            'source': '/work/benchmark-source/src/xz-bench.c',
            'page_observation': 'all declared pages before and after full workload',
        }
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
        raise
    finally:
        write_json(OUT / 'xz-validation.json', record)


def main():
    OUT.mkdir()
    record = {'scope': 'exact119 private KVM; full XZ export and functional decoding; guest timings are diagnostic only',
              'kernel': os.uname().release, 'uid': os.getuid(),
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'stage': 'environment', 'status': 'running'}
    loaded = []
    try:
        assert os.uname().release == '5.15.0-119-generic' and os.geteuid() == 0
        for name, path in [('vkso_xz', ROOT / 'owner/vkso_xz.ko'),
                           ('vkso_kernel_reader', ROOT / 'helpers/vkso_kernel_reader.ko'),
                           ('page_cache_replace', REPO / 'page_cache_replace/page_cache_replace.ko')]:
            execute(['insmod', path], OUT / f'load-{name}.log')
            loaded.append(name)
        record['owner_text'] = Path('/sys/module/vkso_xz/sections/.text').read_text().strip()
        (OUT / 'runtime-kallsyms.txt').write_text(Path('/proc/kallsyms').read_text())
        record['stage'] = 'corpus-preparation'
        execute([ROOT / 'scripts/prepare_corpus.sh', OUT / 'corpus',
                 OUT / 'corpus/manifest.csv', ROOT / 'inputs/bash',
                 ROOT / 'inputs/python3', ROOT / 'inputs/libc.so.6'], OUT / 'corpus-prepare.log')
        record['stage'] = 'workspace-initialization'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'init', WORK, '--symbols', ROOT / 'symbols.txt'],
                OUT / 'workspace-init.log')
        record['stage'] = 'full-export-registration-and-correctness'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'exec', WORK, '--symbols', ROOT / 'symbols.txt',
                 '--module', ROOT / 'owner/vkso_xz.ko',
                 '--owner-ko', ROOT / 'owner/vkso_xz.ko',
                 '--vmlinux', ROOT / 'vmlinux-5.15.0-119-generic',
                 '--', 'python3', ROOT / 'guest.py', '--validate-xz'],
                OUT / 'export-and-correctness.log')
        assert json.loads((OUT / 'xz-validation.json').read_text())['status'] == 'pass'
        assert not (REPO / 'page_cache_replace/runtime/manager.pid').exists()
        record['stage'] = 'normal-release'
        verify_restored_pages()
        record['restoration_verified'] = True
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
    finally:
        runtime = REPO / 'page_cache_replace/runtime'
        if runtime.exists():
            shutil.copytree(runtime, OUT / 'manager-runtime-after-exec')
        log = WORK / 'vkso/metadata/page_replace.log'
        possible_registration = log.exists() and log.stat().st_size > 0
        unload_safe = not possible_registration
        if possible_registration:
            try:
                if not record.get('restoration_verified'):
                    verify_restored_pages()
                unload_safe = True
            except BaseException:
                record['restore_verification_error'] = traceback.format_exc()
                record['status'] = 'fail'
        if not unload_safe:
            record['module_cleanup'] = 'Skipped unload: restoration unverified; private guest powers off.'
        for name in reversed(loaded) if unload_safe else ():
            try:
                execute(['rmmod', name], OUT / f'unload-{name}.log')
                assert not Path('/sys/module', name).exists()
            except BaseException:
                record.setdefault('cleanup_errors', []).append(traceback.format_exc())
                record['status'] = 'fail'
        record['modules_after'] = Path('/proc/modules').read_text()
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        write_json(OUT / 'status.json', record)
        os.sync()
    print('xz_guest_validation=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--validate-xz']:
        validate_xz()
    else:
        raise SystemExit(main())
