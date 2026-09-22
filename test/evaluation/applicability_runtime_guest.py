#!/usr/bin/env python3
"""Actual built-in xxh32/sort exports and typed functional checks in exact119.

Uses the unchanged public workflow and separate workspaces. Prospective static
campaign records remain untouched. A failed carrier is retained as a case
outcome; it does not remove the other selected root from the experiment.
"""
from pathlib import Path
import csv
import json
import os
import shutil
import subprocess
import sys
import traceback

from lz4_guest_helpers import write_json
import lz4_guest_helpers as mapping

ROOT = Path('/work')
REPO = ROOT / 'repo'
OUT = ROOT / 'validation'
RUNTIME = ROOT / 'runtime'
CASES = ('xxh32', 'sort')


def execute(command, log, check=True):
    argv = list(map(str, command))
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
    with (OUT / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps({'argv': argv, 'log': str(log), 'returncode': result.returncode}) + '\n')
    if check and result.returncode:
        raise RuntimeError(f'command exit {result.returncode}; see {log}')
    return result.returncode


def set_mapping_paths(name):
    mapping.OUT = OUT / name
    mapping.WORK = mapping.OUT / 'export'


def validate(name):
    set_mapping_paths(name)
    directory = OUT / name
    fields = dict(line.split('=', 1) for line in
                  (mapping.WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
    library, page_map = Path(fields['library']).resolve(), Path(fields['page_map'])
    headers = list(mapping.WORK.rglob('vkso_types.h'))
    if len(headers) != 1:
        raise RuntimeError(f'expected one generated API header: {headers}')
    execute(['gcc', '-std=gnu11', '-fsyntax-only', '-DAR_CHECK_' + name.upper(),
             '-DAR_GENERATED_HEADER="' + str(headers[0]) + '"', RUNTIME / 'types_check.c'],
            directory / 'generated-types.log')
    # This observer is a separate loader from the typed driver; both use the
    # same actively registered carrier inode in this hold session.
    mapping.observe_registered_pages(library, page_map)
    execute([RUNTIME / 'applicability-user', '--' + name, library,
             '--output', directory / 'user'], directory / 'user-driver.log')
    write_json(directory / 'user-command.json', {'status': 'pass', 'root': name,
        'library': str(library), 'scope': 'typed user driver completed; kernel/reference/raw result audit is separate'})


def main():
    OUT.mkdir()
    record = {'kernel': os.uname().release, 'uid': os.geteuid(),
        'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'scope': 'two eligible prospective builtin roots; unchanged actual exporter, full typed API checks, no performance samples',
        'status': 'running', 'cases': [], 'stage': 'environment'}
    loaded = []
    cleanup_safe = True
    try:
        assert record['kernel'] == '5.15.0-119-generic' and record['uid'] == 0
        for name, path in [('vkso_kernel_reader', ROOT / 'helpers/vkso_kernel_reader.ko'),
                           ('page_cache_replace', REPO / 'page_cache_replace/page_cache_replace.ko'),
                           ('applicability_runtime', RUNTIME / 'applicability_runtime.ko')]:
            execute(['insmod', path], OUT / f'load-{name}.log')
            loaded.append(name)
        kernel = OUT / 'kernel'
        kernel.mkdir()
        for name in ('status', 'xxh32.csv', 'sort.csv'):
            (kernel / name).write_bytes((Path('/sys/kernel/debug/applicability_runtime') / name).read_bytes())
        kernel_status = json.loads((kernel / 'status').read_text())
        if (kernel_status['status'] != 'pass' or kernel_status['errno'] != 0
                or kernel_status['xxh32_checks'] != 247 or kernel_status['sort_checks'] != 1152):
            raise RuntimeError('actual kernel API functional matrix failed; see kernel/status')
        (OUT / 'kallsyms.txt').write_bytes(Path('/proc/kallsyms').read_bytes())
        (OUT / 'modules-before-export.txt').write_bytes(Path('/proc/modules').read_bytes())
        krg = None
        for name in CASES:
            directory = OUT / name
            directory.mkdir()
            symbols = directory / 'symbols.txt'
            symbols.write_text(name + '\n')
            work = directory / 'export'
            item = {'root': name, 'stage': 'init', 'status': 'running',
                    'carrier': 'not_attempted', 'runtime': 'not_attempted'}
            record['cases'].append(item)
            write_json(OUT / 'status.json', record)
            try:
                execute([REPO / 'vkso', 'init', work, '--symbols', symbols], directory / 'init.log')
                item['stage'] = 'actual-export-register-and-use'
                argv = [REPO / 'vkso', 'exec', work, '--symbols', symbols,
                        '--vmlinux', ROOT / 'vmlinux-5.15.0-119-generic']
                if krg:
                    argv += ['--krg', krg]
                argv += ['--', sys.executable, ROOT / 'guest.py', '--validate-root', name]
                code = execute(argv, directory / 'export-and-use.log', check=False)
                item['command_exit_code'] = code
                metadata = work / 'vkso/metadata'
                if (metadata / 'out.krg').exists() and krg is None:
                    krg = metadata / 'out.krg'
                if (metadata / 'outputs.env').exists():
                    item['carrier'] = 'constructed'
                if (directory / 'user-command.json').exists():
                    item['runtime'] = 'driver_completed_pending_raw_audit'
                set_mapping_paths(name)
                if (directory / 'registered-pfns.json').exists():
                    mapping.verify_restored_pages()
                    item['fresh_mapping_restoration'] = 'pass'
                else:
                    replacement_log = metadata / 'page_replace.log'
                    if replacement_log.exists() and replacement_log.stat().st_size:
                        cleanup_safe = False
                        item['fresh_mapping_restoration'] = 'unverified'
                item['status'] = 'pass' if code == 0 and item.get('fresh_mapping_restoration') == 'pass' else 'fail'
            except BaseException:
                item['status'] = 'fail'
                item['error'] = traceback.format_exc()
                # Do not start a second graft after an unverified active hold.
                if (REPO / 'page_cache_replace/runtime/manager.pid').exists():
                    cleanup_safe = False
            finally:
                runtime = REPO / 'page_cache_replace/runtime'
                if runtime.exists():
                    shutil.copytree(runtime, directory / 'manager-runtime-after-exec')
                write_json(directory / 'case.json', item)
                write_json(OUT / 'status.json', record)
            if not cleanup_safe:
                break
        record['status'] = 'pass' if len(record['cases']) == 2 and all(x['status'] == 'pass' for x in record['cases']) else 'fail'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
    finally:
        if cleanup_safe:
            for name in reversed(loaded):
                try:
                    execute(['rmmod', name], OUT / f'unload-{name}.log')
                except BaseException:
                    record.setdefault('cleanup_errors', []).append(traceback.format_exc())
                    record['status'] = 'fail'
        else:
            record['cleanup'] = 'Registration restoration unverified; retain modules until private guest powers off.'
        record['modules_after'] = Path('/proc/modules').read_text()
        (OUT / 'dmesg.txt').write_bytes(subprocess.check_output(['dmesg']))
        write_json(OUT / 'status.json', record)
        os.sync()
    print('applicability_runtime_guest=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['--validate-root']:
        validate(sys.argv[2])
    else:
        raise SystemExit(main())
