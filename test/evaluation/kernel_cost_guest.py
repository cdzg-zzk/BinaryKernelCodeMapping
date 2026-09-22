"""Run full-input kernel comparisons inside the existing registered session."""
from pathlib import Path
import csv
import ctypes
import hashlib
import io
import json
import os
import subprocess
import traceback

BACKENDS = ['stock-kernel', 'matched-direct-kernel', 'owner-kernel']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(algorithm, root, output):
    root, output = Path(root), Path(output)
    configuration = json.loads((root / 'kernel-cost/configuration.json').read_text())
    backends = configuration.get('backends', BACKENDS)
    assert configuration['algorithm'] == algorithm
    output.mkdir()
    debug = Path('/sys/kernel/debug/vkso_kernel_cost')
    owner = 'vkso_' + algorithm
    refcnt = Path('/sys/module') / owner / 'refcnt'
    record = dict(status='running', scope=configuration['scope'], configuration=configuration,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  inputs=[], trials=[], module_commands=[])
    loaded = []
    affinity = os.sched_getaffinity(0)

    def save():
        (output / 'collection.json').write_text(json.dumps(record, indent=2) + '\n')

    def command(argv):
        result = subprocess.run(list(map(str, argv)), capture_output=True, text=True)
        record['module_commands'].append(dict(argv=list(map(str, argv)), returncode=result.returncode,
                                              stdout=result.stdout, stderr=result.stderr))
        save()
        if result.returncode:
            raise RuntimeError(record['module_commands'][-1])

    def control(value):
        (debug / 'control').write_text(value + '\n')
        assert (debug / 'status').read_text().startswith('errno=0\n')

    try:
        os.sched_setaffinity(0, {configuration['cpu']})
        record['cpu_affinity'] = sorted(os.sched_getaffinity(0))
        record['owner_refcnt_before'] = int(refcnt.read_text())
        assert record['owner_refcnt_before'] == 1
        for module in configuration['modules']:
            command(['insmod', root / 'kernel-cost' / (module + '.ko')])
            loaded.append(module)
        record['owner_refcnt_active'] = int(refcnt.read_text())
        assert record['owner_refcnt_active'] == 2
        symbols = {}
        kallsyms = Path('/proc/kallsyms').read_text()
        (output / 'kallsyms.txt').write_text(kallsyms)
        for line in kallsyms.splitlines():
            fields = line.split()
            if len(fields) >= 3:
                symbols.setdefault(fields[2], []).append((int(fields[0], 16),
                    fields[3].strip('[]') if len(fields) == 4 else 'vmlinux'))
        status = (debug / 'status').read_text()
        (output / 'api-status.txt').write_text(status)
        methods = {'compress': 'LZ4_compress_default', 'decode': 'LZ4_decompress_safe'} if algorithm == 'lz4' else {
            'init': 'xz_dec_init', 'run': 'xz_dec_run', 'reset': 'xz_dec_reset',
            'end': 'xz_dec_end', 'crc_init': 'xz_crc32_init'}
        bindings = []
        for line in status.splitlines()[2:]:
            fields = line.split()
            index = backends.index(fields[0])
            for field in fields[1:]:
                method, address = field.split('=')
                if method == 'crc_init' and (index == 0 or
                        (index == 1 and configuration.get('matched_definition') == 'original-source-owner-codegen')):
                    assert int(address, 16) == 0
                    continue
                name = ['', 'matched_', 'vkso_'][index] + methods[method]
                provider = (('lz4_compress' if method == 'compress' else 'vmlinux')
                            if algorithm == 'lz4' else 'vmlinux') if index == 0 else [None, 'matched_' + algorithm, owner][index]
                assert symbols.get(name) == [(int(address, 16), provider)], (name, address, symbols.get(name))
                assert int(address, 16) != 0
                bindings.append(dict(backend=fields[0], method=method, symbol=name,
                                     address=address, provider=provider))
        assert len(bindings) == (6 if algorithm == 'lz4' else
                                13 if configuration.get('matched_definition') else 14)
        record['bindings'] = bindings
        if algorithm == 'lz4':
            names = (root / 'corpus/manifest.txt').read_text().splitlines()
            names = [name for name in names if name and not name.startswith('#')]
            assert len(names) == len(set(names)) == 12
            cases = [(name, root / 'corpus' / name, None, block)
                     for name in names for block in (65536, 1048576)]
            oracle = ctypes.CDLL(str(root / 'kernel-cost/liblz4.so.1'))
            oracle.LZ4_decompress_safe.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            oracle.LZ4_decompress_safe.restype = ctypes.c_int
        else:
            manifest = list(csv.reader((root / 'validation/corpus/manifest.csv').read_text().splitlines()))
            assert [row[0] for row in manifest] == ['bash', 'python3', 'libc.so.6']
            cases = [(name, Path(plain), Path(compressed), 0) for name, plain, compressed in manifest]
        raw = output / 'raw.csv'
        for case_index, (name, plain_path, compressed_path, block) in enumerate(cases):
            plain = plain_path.read_bytes()
            input_record = dict(case=name, path=str(plain_path), bytes=len(plain),
                                sha256=digest(plain), block_bytes=block)
            if compressed_path:
                input_record.update(compressed_path=str(compressed_path),
                    compressed_bytes=compressed_path.stat().st_size, compressed_sha256=digest(compressed_path.read_bytes()))
            record['inputs'].append(input_record)
            control(f'LOAD {name} {plain_path} {compressed_path or "-"} {block}')
            for outer in range(configuration['outer_runs']):
                for position in range(3):
                    backend = (position + outer + case_index) % 3
                    control(f'RUN {backend} {outer} {configuration["sample_ms"]}')
                    result = (debug / 'results').read_text()
                    rows = list(csv.DictReader(io.StringIO(result)))
                    assert len(rows) == (2 if algorithm == 'lz4' else 1)
                    for row in rows:
                        assert row['status'] == 'pass' and row['backend'] == backends[backend]
                        assert row['case'] == name and int(row['bytes']) == len(plain)
                        assert int(row['outer_run']) == outer and int(row['block_bytes']) == block
                        assert int(row['repeats']) > 0 and int(row['elapsed_ns']) >= configuration['sample_ms'] * 1000000
                        assert int(row['cpu']) == configuration['cpu']
                    with raw.open('a') as stream:
                        stream.write(result if raw.stat().st_size == 0 else result.split('\n', 1)[1])
                    decoded = (debug / 'output').read_bytes()
                    assert decoded == plain, (name, backends[backend], 'full kernel decode')
                    trial = dict(case=name, block_bytes=block, outer_run=outer, position=position,
                        backend=backends[backend], full_output_match=True, output_sha256=digest(decoded),
                        bytes=len(decoded), rows=len(rows))
                    if algorithm == 'lz4':
                        encoded = (debug / 'encoded').read_bytes()
                        blocks_text = (debug / 'blocks').read_text()
                        blocks = list(csv.DictReader(io.StringIO(blocks_text)))
                        assert len(blocks) == (len(plain) + block - 1) // block
                        full = bytearray()
                        for item in blocks:
                            offset, count, length = (int(item[key]) for key in ('encoded_offset', 'encoded_bytes', 'input_bytes'))
                            assert int(item['input_offset']) == len(full)
                            target = ctypes.create_string_buffer(length)
                            source = ctypes.create_string_buffer(encoded[offset:offset + count])
                            assert oracle.LZ4_decompress_safe(source, target, count, length) == length
                            full.extend(target.raw)
                        assert full == plain, (name, BACKENDS[backend], 'independent liblz4 cross decode')
                        trial.update(independent_cross_decode_match=True, encoded_sha256=digest(encoded),
                                     encoded_buffer_bytes=len(encoded), blocks=len(blocks))
                        # Retain every final-round block table; full bytes were
                        # compared above for every trial, outside kernel timers.
                        if outer == configuration['outer_runs'] - 1:
                            (output / f'{name}-{block}-{backend}-blocks.csv').write_text(blocks_text)
                    record['trials'].append(trial)
                    save()
        record['status'] = 'pass'
    except BaseException:
        record.update(status='fail', error=traceback.format_exc())
        raise
    finally:
        errors = []
        for module in reversed(loaded):
            try:
                command(['rmmod', module])
            except Exception as error:
                errors.append(str(error))
        record['owner_refcnt_after'] = int(refcnt.read_text())
        if errors or record['owner_refcnt_after'] != 1:
            record.update(status='fail', cleanup_errors=errors)
        os.sched_setaffinity(0, affinity)
        save()
    assert record['status'] == 'pass', record
    return dict(status='pass', directory=str(output), trials=len(record['trials']),
                rows=sum(trial['rows'] for trial in record['trials']), scope=record['scope'])
