#!/usr/bin/env python3
"""Exercise the existing complete BCH correctness mode in a private guest."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import traceback

from lz4_guest_helpers import (execute, observe_registered_pages,
                              verify_restored_pages, write_json)

ROOT = Path('/work')
REPO = ROOT / 'repo'
OUT = ROOT / 'validation'
WORK = OUT / 'export'


def validate_bch():
    record = {'scope': 'unchanged BCH correctness-only mode; no performance samples',
              'status': 'running', 'correctness_vectors': 128}
    try:
        fields = dict(line.split('=', 1) for line in
                      (WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
        library = Path(fields['library']).resolve()
        sys.path.insert(0, str(ROOT / 'setup'))
        from collect import active as collect_setup
        collect_setup('bch', ROOT, OUT / 'setup-full', WORK)
        pages = observe_registered_pages(library, Path(fields['page_map']))
        record['library'] = str(library)
        record['shared_pages'] = len(pages['pages'])
        record['owner_refcnt_during_registration'] = int(
            Path('/sys/module/vkso_bch/refcnt').read_text())
        assert record['owner_refcnt_during_registration'] == 1
        execute([ROOT / 'binaries/bch-bench', '--kernel', library,
                 '--kernel-native', ROOT / 'binaries/libbch-kernel-native.so',
                 '--standalone', ROOT / 'binaries/libbch-author-standalone.so',
                 '--correctness-only', '--correctness-vectors', '128'],
                OUT / 'bch-correctness.log')
        log = (OUT / 'bch-correctness.log').read_text()
        for t in (4, 8):
            expected = f'correctness: m=13 t={t} vectors=128 backends=3 ok'
            assert log.count(expected) == 1, (expected, log)
        assert 'BCH evaluation completed;' in log
        record['coverage'] = {
            'parameters': [{'m': 13, 't': 4, 'errors': list(range(5))},
                           {'m': 13, 't': 8, 'errors': list(range(9))}],
            'data_length_bytes': 512,
            'backends': ['kernel-vkso', 'kernel-native', 'author-standalone'],
            'decode_modes': ['decode-precomputed', 'decode-full'],
            'checks': ['equal BCH geometry', 'equal parity bytes',
                       'exact error locations', 'corrected codeword equals original'],
            'decode_checks_from_unchanged_loop': 128 * (5 + 9) * 3 * 2,
        }
        if (ROOT / 'kernel-cost').exists():
            from bch_kernel_guest import run_registered
            record['kernel_cost'] = run_registered()
            final = observe_registered_pages(library, Path(fields['page_map']))
            assert [(p['file_offset'], p['kernel_pfn']) for p in pages['pages']] == [
                (p['file_offset'], p['kernel_pfn']) for p in final['pages']]
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
        raise
    finally:
        write_json(OUT / 'bch-validation.json', record)


def main():
    OUT.mkdir()
    record = {'scope': 'exact119 private KVM; full BCH export and correctness only',
              'kernel': os.uname().release, 'uid': os.getuid(),
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'stage': 'environment', 'status': 'running'}
    loaded = []
    try:
        assert os.uname().release == '5.15.0-119-generic' and os.geteuid() == 0
        for name, path in [('vkso_bch', ROOT / 'owner/vkso_bch.ko'),
                           ('vkso_kernel_reader', ROOT / 'helpers/vkso_kernel_reader.ko'),
                           ('page_cache_replace', REPO / 'page_cache_replace/page_cache_replace.ko')]:
            execute(['insmod', path], OUT / f'load-{name}.log')
            loaded.append(name)
        record['owner_text'] = Path('/sys/module/vkso_bch/sections/.text').read_text().strip()
        record['stage'] = 'workspace-initialization'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'init', WORK, '--symbols', ROOT / 'symbols.txt'],
                OUT / 'workspace-init.log')
        record['stage'] = 'full-export-registration-and-correctness'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'exec', WORK, '--symbols', ROOT / 'symbols.txt',
                 '--module', ROOT / 'owner/vkso_bch.ko',
                 '--owner-ko', ROOT / 'owner/vkso_bch.ko',
                 '--vmlinux', ROOT / 'vmlinux-5.15.0-119-generic',
                 '--', 'python3', ROOT / 'guest.py', '--validate-bch'],
                OUT / 'export-and-correctness.log', dict(os.environ,
                    VKSO_SETUP_TRACE=str(OUT / 'setup-stages.tsv'), VKSO_SETUP_CLOCK=str(ROOT / 'setup/setup-clock')))
        assert json.loads((OUT / 'bch-validation.json').read_text())['status'] == 'pass'
        assert not (REPO / 'page_cache_replace/runtime/manager.pid').exists()
        record['stage'] = 'normal-release'
        verify_restored_pages()
        record['restoration_verified'] = True
        sys.path.insert(0, str(ROOT / 'setup'))
        from collect import ready as collect_ready
        collect_ready('bch', ROOT, OUT / 'setup-ready', WORK)
        verify_restored_pages()
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
    print('bch_guest_validation=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--validate-bch']:
        validate_bch()
    else:
        raise SystemExit(main())
