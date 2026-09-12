#!/usr/bin/env python3
"""Run full LZ4 CLI functional cases inside a disposable exact119 guest."""
from pathlib import Path
import hashlib
import ctypes
import csv
import io
import json
import os
import struct
import subprocess
import sys
import traceback

ROOT = Path('/work')
REPO = ROOT / 'repo'
OUT = ROOT / 'validation'
WORK = OUT / 'export'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            value.update(chunk)
    return value.hexdigest()


def execute(command, log, environment=None):
    command = list(map(str, command))
    with log.open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                env=environment)
    with (OUT / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps({'argv': command, 'log': str(log),
                                'returncode': result.returncode}) + '\n')
    if result.returncode:
        raise RuntimeError(f'command returned {result.returncode}; see {log}')


def observe_registered_pages(library, page_map):
    """Read pagemap without buffering after each page is faulted into the DSO."""
    sys.path.insert(0, str(ROOT / 'helpers'))
    from carrier import mappings
    plan = mappings(page_map)
    handle = ctypes.CDLL(str(library))
    assert handle is not None
    probe = Path('/sys/kernel/debug/vkso_kernel_reader')
    (probe / 'page_addresses').write_text(' '.join(hex(page[1]) for page in plan))
    source_pages = (probe / 'pages').read_text()
    (OUT / 'source-pages.csv').write_text(source_pages)
    source_pfns = {int(row['kernel_vaddr'], 0): int(row['pfn'])
                   for row in csv.DictReader(io.StringIO(source_pages))}
    regions = []
    maps = Path('/proc/self/maps').read_text()
    (OUT / 'carrier-process-maps.txt').write_text(maps)
    for line in maps.splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) == 6 and columns[5] == str(library):
            start, end = map(lambda text: int(text, 16), columns[0].split('-'))
            regions.append((start, end, int(columns[2], 16), columns[1]))
    record = {'library': str(library), 'pages': [], 'status': 'running',
              'pagemap_read': 'os.pread after each fault; no buffered stale adjacent entries'}
    fd = os.open('/proc/self/pagemap', os.O_RDONLY)
    try:
        for offset, address, kind, section in plan:
            region = next((row for row in regions if 'r' in row[3]
                           and row[2] <= offset < row[2] + row[1] - row[0]), None)
            assert region is not None, (offset, regions)
            virtual = region[0] + offset - region[2]
            ctypes.c_ubyte.from_address(virtual).value
            entry, = struct.unpack('Q', os.pread(fd, 8, virtual // 4096 * 8))
            pfn = entry & ((1 << 55) - 1)
            row = {'file_offset': offset, 'kernel_address': hex(address), 'kind': kind,
                   'section': section, 'virtual_address': hex(virtual), 'permissions': region[3],
                   'pagemap_entry': hex(entry), 'user_pfn': pfn,
                   'kernel_pfn': source_pfns.get(address), 'shared': pfn == source_pfns.get(address)}
            record['pages'].append(row)
            assert entry & (1 << 63) and pfn and row['shared'], row
            assert 'w' not in region[3], row
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
        raise
    finally:
        os.close(fd)
        write_json(OUT / 'registered-pfns.json', record)
    return record


def validate_cli():
    record = {'scope': 'full CLI functional validation; no performance observations',
              'status': 'running', 'cases': []}
    report = OUT / 'cli-validation.json'
    write_json(report, record)
    try:
        fields = dict(line.split('=', 1) for line in
                      (WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
        library = Path(fields['library']).resolve()
        footprint = observe_registered_pages(library, Path(fields['page_map']))
        record['library'] = str(library)
        record['shared_pages'] = len(footprint['pages'])
        record['owner_refcnt_during_registration'] = int(
            Path('/sys/module/vkso_lz4/refcnt').read_text())
        (OUT / 'dmesg-after-registration.txt').write_text(
            subprocess.check_output(['dmesg'], text=True))
        manifest = ROOT / 'corpus/manifest.txt'
        sources = [manifest.parent / line for line in manifest.read_text().splitlines()
                   if line and not line.startswith('#')]
        assert len(sources) == 12 and len(set(sources)) == 12
        stock, adapted = ROOT / 'cli/lz4-stock', ROOT / 'cli/lz4-adapted'
        environment = dict(os.environ)
        for key in ('VKSO_LZ4_LIBRARY', 'VKSO_LZ4_API', 'VKSO_LZ4_TRACE', 'LD_PRELOAD'):
            environment.pop(key, None)
        selected = dict(environment, VKSO_LZ4_LIBRARY=str(library), VKSO_LZ4_API='kernel')
        logs, scratch = OUT / 'cli-logs', OUT / 'cli-files'
        logs.mkdir()
        scratch.mkdir()
        common, encoded, decoded = [scratch / name for name in
                                    ('common.lz4', 'adapted.lz4', 'decoded')]
        for index, source in enumerate(sources):
            expected = digest(source)
            for block in (4, 6):
                tag = f'{index:02d}-{source.name}-b{block}'
                compression = ['-q', '-f', '-1', f'-B{block}', '-BI', '--content-size']
                execute([stock, *compression, source, common], logs / f'{tag}-stock.log', environment)
                calls = {}
                for operation, arguments in (
                    ('compress', [*compression, source, encoded]),
                    ('decompress', ['-q', '-f', '-d', '--no-sparse', common, decoded]),
                ):
                    trace = logs / f'{tag}-{operation}.trace'
                    try:
                        execute([adapted, *arguments], logs / f'{tag}-{operation}.log',
                                dict(selected, VKSO_LZ4_TRACE=str(trace)))
                    except RuntimeError:
                        if (ROOT / 'diagnose-runtime').exists():
                            diagnostic_arguments = [*arguments[:-1], scratch / 'diagnostic-output']
                            commands = ['gdb', '-nx', '-batch', '-iex', 'set auto-load off',
                                '-iex', 'set debuginfod enabled off', '-ex', 'set pagination off',
                                '-ex', 'set confirm off', '-ex', 'set startup-with-shell off',
                                '-ex', 'run', '-ex', 'info registers', '-ex', 'thread apply all bt',
                                '-ex', 'info proc mappings', '-ex', 'info sharedlibrary',
                                '-ex', 'info address memset', '-ex', 'x/12gx $rsp',
                                '-ex', 'x/12i *((unsigned long*)$rsp)-24',
                                '--args', adapted, *diagnostic_arguments]
                            with (OUT / 'full-cli-gdb-diagnostic.log').open('w') as stream:
                                diagnostic = subprocess.run(list(map(str, commands)), stdout=stream,
                                    stderr=subprocess.STDOUT,
                                    env=dict(selected, VKSO_LZ4_TRACE=str(logs / 'diagnostic.trace')))
                            record['diagnostic'] = {'gdb_returncode': diagnostic.returncode,
                                'argv': list(map(str, commands)),
                                'scope': 'same full CLI/input/block operation; debugger rerun is not a passing test'}
                        raise
                    values = dict(line.split('=', 1) for line in trace.read_text().splitlines())
                    assert int(values[operation + '_calls']) > 0, (tag, operation, values)
                    for field in ('compress_dso', 'decompress_dso'):
                        assert Path(values[field]).resolve() == library, (tag, values)
                    calls[operation] = int(values[operation + '_calls'])
                assert digest(decoded) == expected, (tag, 'kernel-backed decode mismatch')
                execute([stock, '-q', '-f', '-d', '--no-sparse', encoded, decoded],
                        logs / f'{tag}-stock-cross-decode.log', environment)
                assert digest(decoded) == expected, (tag, 'stock cross-decode mismatch')
                record['cases'].append({'input': source.name, 'bytes': source.stat().st_size,
                    'input_sha256': expected, 'block_id': block, 'block_bytes': 1 << (8 + 2 * block),
                    'backend': 'kernel-vkso', 'compress_calls': calls['compress'],
                    'decompress_calls': calls['decompress'], 'full_output_match': True,
                    'stock_cross_decode_match': True, 'selected_dso_match': True})
                write_json(report, record)
                for path in (common, encoded, decoded):
                    path.unlink()
            print(f'lz4_full_cli_input={source.name}:pass', flush=True)
        assert len(record['cases']) == 24
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
        raise
    finally:
        write_json(report, record)


def verify_restored_pages():
    active = json.loads((OUT / 'registered-pfns.json').read_text())
    assert active['status'] == 'pass', active
    fields = dict(line.split('=', 1) for line in
                  (WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                          ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.mmap.restype = ctypes.c_void_p
    libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    restored = {'library': fields['library'], 'pages': [], 'status': 'running'}
    fd = os.open(fields['library'], os.O_RDONLY)
    try:
        with Path('/proc/self/pagemap').open('rb', buffering=0) as stream:
            for page in active['pages']:
                address = libc.mmap(None, 4096, 1, 2, fd, page['file_offset'])
                if address == ctypes.c_void_p(-1).value:
                    raise OSError(ctypes.get_errno(), 'mmap restored carrier')
                try:
                    ctypes.c_ubyte.from_address(address).value
                    stream.seek(address // 4096 * 8)
                    entry, = struct.unpack('Q', stream.read(8))
                    pfn = entry & ((1 << 55) - 1)
                    assert entry & (1 << 63) and pfn
                    item = {'file_offset': page['file_offset'], 'source_pfn': page['kernel_pfn'],
                            'restored_user_pfn': pfn, 'source_backing_removed': pfn != page['kernel_pfn']}
                    restored['pages'].append(item)
                    assert item['source_backing_removed'], item
                finally:
                    assert libc.munmap(address, 4096) == 0
        restored['status'] = 'pass'
    except BaseException:
        restored['status'] = 'fail'
        restored['error'] = traceback.format_exc()
        raise
    finally:
        os.close(fd)
        write_json(OUT / 'restored-pfns.json', restored)


def main():
    OUT.mkdir()
    record = {'scope': 'exact119 KVM functional export and full CLI; no performance samples',
              'kernel': os.uname().release, 'uid': os.getuid(),
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'stage': 'environment', 'status': 'running'}
    loaded = []
    try:
        assert os.uname().release == '5.15.0-119-generic' and os.geteuid() == 0
        for name, source in (
            ('vkso_lz4', ROOT / 'owner/vkso_lz4.ko'),
            ('vkso_kernel_reader', ROOT / 'helpers/vkso_kernel_reader.ko'),
            ('page_cache_replace', REPO / 'page_cache_replace/page_cache_replace.ko'),
        ):
            execute(['insmod', source], OUT / f'load-{name}.log')
            loaded.append(name)
            assert Path('/sys/module', name).exists()
        record['owner_text'] = Path('/sys/module/vkso_lz4/sections/.text').read_text().strip()
        (OUT / 'runtime-kallsyms.txt').write_text(Path('/proc/kallsyms').read_text())
        record['stage'] = 'workspace-initialization'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'init', WORK, '--symbols', ROOT / 'symbols.txt'],
                OUT / 'workspace-init.log')
        record['stage'] = 'build-export-registration-and-cli'
        write_json(OUT / 'status.json', record)
        execute([REPO / 'vkso', 'exec', WORK, '--symbols', ROOT / 'symbols.txt',
                 '--module', ROOT / 'owner/vkso_lz4.ko', '--owner-ko', ROOT / 'owner/vkso_lz4.ko',
                 '--vmlinux', ROOT / 'vmlinux-5.15.0-119-generic',
                 '--', 'python3', ROOT / 'guest.py', '--validate-cli'], OUT / 'export-and-cli.log')
        validation = json.loads((OUT / 'cli-validation.json').read_text())
        assert validation['status'] == 'pass' and len(validation['cases']) == 24
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
            import shutil
            shutil.copytree(runtime, OUT / 'manager-runtime-after-exec')
        replacement_log = WORK / 'vkso/metadata/page_replace.log'
        possible_registration = replacement_log.exists() and replacement_log.stat().st_size > 0
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
            record['module_cleanup'] = 'Skipped unload because restoration is unverified; private guest powers off.'
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
    print('lz4_guest_validation=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--validate-cli']:
        validate_cli()
    else:
        raise SystemExit(main())
