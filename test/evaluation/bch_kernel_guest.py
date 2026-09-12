#!/usr/bin/env python3
"""Validate the stock BCH and actual export-owner APIs in a private guest."""
from pathlib import Path
import json
import os
import re
import subprocess
import traceback

from bch_kernel_audit import audit

WORK = Path('/work')
OUT = WORK / 'validation'
MODULES = ('bch', 'bch_matched', 'vkso_bch', 'bch_kernel_bench')


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def execute(argv, log, cpu=None):
    previous_affinity = os.sched_getaffinity(0)
    try:
        if cpu is not None:
            os.sched_setaffinity(0, {cpu})
        result = subprocess.run(list(map(str, argv)), capture_output=True, text=True)
    finally:
        if cpu is not None:
            os.sched_setaffinity(0, previous_affinity)
    (OUT / log).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{argv[0]} returned {result.returncode}; see {log}')
    return result.stdout


def snapshot(name):
    value = {}
    for module in MODULES:
        path = Path('/sys/module') / module
        if path.exists():
            value[module] = {key: (path / key).read_text().strip()
                             for key in ('refcnt', 'coresize', 'initsize')}
            value[module]['sections'] = {p.name: p.read_text().strip()
                for p in (path / 'sections').iterdir() if p.is_file()}
    save(name, value)
    return value


def main():
    OUT.mkdir(exist_ok=False)
    record = {'scope': 'private exact119 guest; full three-backend functional/collector validation',
              'status': 'running', 'guest_timings_are_formal_performance': False,
              'kernel': os.uname().release,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'stage': 'environment', 'commands': []}
    loaded = []
    try:
        assert os.geteuid() == 0 and os.uname().release == '5.15.0-119-generic'
        assert 'vkso_bch_kernel_guest=1' in Path('/proc/cmdline').read_text().split()
        config = json.loads((WORK / 'configuration.json').read_text())
        assert config['cpu'] in os.sched_getaffinity(0)
        assert isinstance(config['measure'], bool)
        record['configuration'] = config
        (OUT / 'modules-before.txt').write_text(Path('/proc/modules').read_text())
        debugfs_mounts = [line.split() for line in Path('/proc/mounts').read_text().splitlines()
                          if line.split()[1] == '/sys/kernel/debug']
        if debugfs_mounts:
            assert all(fields[2] == 'debugfs' for fields in debugfs_mounts)
            save('debugfs-existing-mount.json', debugfs_mounts)
        else:
            execute(['mount', '-t', 'debugfs', 'debugfs', '/sys/kernel/debug'], 'debugfs-mount.log')
        for module in MODULES:
            assert not Path('/sys/module', module).exists(), module
        for module in MODULES[:-1]:
            argv = ['insmod', WORK / 'modules' / (module + '.ko')]
            record['commands'].append(list(map(str, argv)))
            execute(argv, f'load-{module}.log')
            loaded.append(module)
        snapshot('modules-before-driver.json')
        record['stage'] = 'full-kernel-correctness'
        save('status.json', record)
        argv = ['insmod', WORK / 'modules/bch_kernel_bench.ko',
                f'measure={int(config["measure"])}', f'correctness_vectors={config["correctness_vectors"]}',
                f'outer_runs={config["outer_runs"]}', f'sample_ms={config["sample_ms"]}']
        record['commands'].append(list(map(str, argv)))
        record['driver_affinity_cpu'] = config['cpu']
        execute(argv, 'load-bch_kernel_bench.log', cpu=config['cpu'])
        loaded.append('bch_kernel_bench')
        active_modules = snapshot('modules-with-driver.json')
        for module in MODULES[:-1]:
            assert int(active_modules[module]['refcnt']) >= 1, module
        debug = Path('/sys/kernel/debug/bch_kernel_bench')
        for name in ('status', 'results', 'vectors'):
            (OUT / ('driver-' + name + '.txt')).write_bytes((debug / name).read_bytes())
        dmesg = subprocess.check_output(['dmesg'], text=True)
        (OUT / 'dmesg-after-driver.txt').write_text(dmesg)
        passed = re.findall(r'BCH_KERNEL_BENCH status=pass[^\n]*', dmesg)
        assert len(passed) == 1, passed
        assert re.search(r'\berrno=0\b', passed[0]), passed[0]
        assert not re.search(r'BCH_KERNEL_BENCH status=fail|Kernel panic|BUG:|WARNING:', dmesg)
        record['completion_marker'] = passed[0]
        audit_record = audit(OUT, measure=config['measure'], expected_cpu=config['cpu'],
                             correctness_vectors=config['correctness_vectors'],
                             outer_runs=config['outer_runs'], sample_ms=config['sample_ms'])
        save('coverage-audit.json', audit_record)
        symbols = []
        names = {prefix + api for prefix in ('bch_', 'matched_bch_', 'vkso_bch_')
                 for api in ('init', 'free', 'encode', 'decode')}
        for line in Path('/proc/kallsyms').read_text().splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[2] in names:
                symbols.append({'address': fields[0], 'type': fields[1],
                                'name': fields[2], 'module': fields[3:]})
        assert {s['name'] for s in symbols} == names
        for symbol in symbols:
            expected = ('[vkso_bch]' if symbol['name'].startswith('vkso_') else
                        '[bch_matched]' if symbol['name'].startswith('matched_') else '[bch]')
            assert symbol['module'] == [expected] and int(symbol['address'], 16)
            printed = re.findall(r'BCH_KERNEL_BENCH api [^\n]*\b' +
                                 re.escape(symbol['name']) + r'=([0-9a-fA-F]+)\b', dmesg)
            assert len(printed) == 1 and int(printed[0], 16) == int(symbol['address'], 16), symbol
        save('public-api-symbols.json', symbols)
        record['coverage'] = audit_record
        record['status'] = 'pass'
    except BaseException:
        record['status'] = 'fail'
        record['error'] = traceback.format_exc()
    finally:
        for module in reversed(loaded):
            try:
                execute(['rmmod', module], f'unload-{module}.log')
                assert not Path('/sys/module', module).exists()
                if module == 'bch_kernel_bench':
                    snapshot('modules-after-driver.json')
            except BaseException:
                record['status'] = 'fail'
                record.setdefault('cleanup_errors', []).append(traceback.format_exc())
        (OUT / 'modules-after.txt').write_text(Path('/proc/modules').read_text())
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        save('status.json', record)
        os.sync()
    print('bch_kernel_guest_validation=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
