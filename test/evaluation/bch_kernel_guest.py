#!/usr/bin/env python3
"""Validate the stock BCH and actual export-owner APIs in a private guest."""
from pathlib import Path
import json
import os
import re
import subprocess
import struct
import traceback

from bch_kernel_audit import audit, new_log_window

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


def main(registered=False):
    OUT.mkdir(exist_ok=False)
    record = {'scope': 'private exact119 guest; full three-backend functional/collector validation',
              'status': 'running', 'guest_timings_are_formal_performance': False,
              'kernel': os.uname().release,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'stage': 'environment', 'commands': []}
    loaded = []
    try:
        assert os.geteuid() == 0 and os.uname().release == '5.15.0-119-generic'
        if not registered:
            assert 'vkso_bch_kernel_guest=1' in Path('/proc/cmdline').read_text().split()
        modules_path = WORK / ('kernel-cost' if registered else 'modules')
        config_path = WORK / 'kernel-cost/configuration.json' if registered else WORK / 'configuration.json'
        config = json.loads(config_path.read_text())
        record['same_registered_owner'] = registered
        assert config['cpu'] in os.sched_getaffinity(0)
        assert isinstance(config['measure'], bool)
        record['configuration'] = config
        physical = config.get('measurement_environment') == 'physical-host'
        if physical:
            assert 'hypervisor' not in Path('/proc/cpuinfo').read_text().split()
            record['scope'] = config['scope']
            record.pop('guest_timings_are_formal_performance')
            record['measurement_environment'] = 'physical-host'
        (OUT / 'modules-before.txt').write_text(Path('/proc/modules').read_text())
        debugfs_mounts = [line.split() for line in Path('/proc/mounts').read_text().splitlines()
                          if line.split()[1] == '/sys/kernel/debug']
        if debugfs_mounts:
            assert all(fields[2] == 'debugfs' for fields in debugfs_mounts)
            save('debugfs-existing-mount.json', debugfs_mounts)
        else:
            execute(['mount', '-t', 'debugfs', 'debugfs', '/sys/kernel/debug'], 'debugfs-mount.log')
        reuse_stock = physical and registered and Path('/sys/module/bch').exists()
        if reuse_stock:
            # A distribution module can already be resident without any VKSO
            # experiment. Reuse it only when its linked identity matches the
            # archived stock control, and leave its lifetime unchanged.
            note = Path('/sys/module/bch/notes/.note.gnu.build-id').read_bytes()
            namesz, descsz, kind = struct.unpack_from('III', note)
            start = 12 + ((namesz + 3) & ~3)
            saved = subprocess.check_output(['readelf', '-n', str(modules_path/'bch.ko')], text=True)
            assert kind == 3 and note[12:12+namesz] == b'GNU\0'
            build_id = re.search(r'Build ID: ([0-9a-f]+)', saved).group(1)
            assert note[start:start+descsz].hex() == build_id
            record['reused_stock_build_id'] = build_id
        for module in MODULES:
            if module == 'bch' and reuse_stock:
                continue
            if registered and module == 'vkso_bch':
                assert int(Path('/sys/module/vkso_bch/refcnt').read_text()) == 1
                continue
            assert not Path('/sys/module', module).exists(), module
        for module in MODULES[:-1]:
            if module == 'bch' and reuse_stock:
                continue
            if registered and module == 'vkso_bch':
                continue
            argv = ['insmod', modules_path / (module + '.ko')]
            record['commands'].append(list(map(str, argv)))
            execute(argv, f'load-{module}.log')
            loaded.append(module)
        snapshot('modules-before-driver.json')
        record['stage'] = 'full-kernel-correctness'
        save('status.json', record)
        argv = ['insmod', modules_path / 'bch_kernel_bench.ko',
                f'measure={int(config["measure"])}', f'correctness_vectors={config["correctness_vectors"]}',
                f'outer_runs={config["outer_runs"]}', f'sample_ms={config["sample_ms"]}']
        if config.get('aligned_inputs'):
            argv.append('aligned_inputs=1')
        record['commands'].append(list(map(str, argv)))
        record['driver_affinity_cpu'] = config['cpu']
        prior_dmesg = subprocess.check_output(['dmesg'], text=True) if physical else ''
        if physical:
            (OUT / 'dmesg-before-driver.txt').write_text(prior_dmesg)
        execute(argv, 'load-bch_kernel_bench.log', cpu=config['cpu'])
        loaded.append('bch_kernel_bench')
        active_modules = snapshot('modules-with-driver.json')
        for module in MODULES[:-1]:
            assert int(active_modules[module]['refcnt']) >= 1, module
        if registered:
            assert int(active_modules['vkso_bch']['refcnt']) == 2
        debug = Path('/sys/kernel/debug/bch_kernel_bench')
        for name in ('status', 'results', 'vectors'):
            (OUT / ('driver-' + name + '.txt')).write_bytes((debug / name).read_bytes())
        if config.get('aligned_inputs'):
            (OUT / 'driver-inputs.csv').write_bytes((debug / 'inputs').read_bytes())
        dmesg = subprocess.check_output(['dmesg'], text=True)
        (OUT / 'dmesg-after-driver.txt').write_text(dmesg)
        if physical:
            (OUT / 'dmesg-before-driver.txt').write_text(prior_dmesg)
            dmesg = new_log_window(prior_dmesg, dmesg)
            (OUT / 'dmesg-driver-window.txt').write_text(dmesg)
        passed = re.findall(r'BCH_KERNEL_BENCH status=pass[^\n]*', dmesg)
        assert len(passed) == 1, passed
        assert re.search(r'\berrno=0\b', passed[0]), passed[0]
        assert not re.search(r'BCH_KERNEL_BENCH status=fail|Kernel panic|BUG:|WARNING:', dmesg)
        record['completion_marker'] = passed[0]
        audit_record = audit(OUT, measure=config['measure'], expected_cpu=config['cpu'],
                             correctness_vectors=config['correctness_vectors'],
                             outer_runs=config['outer_runs'], sample_ms=config['sample_ms'],
                             aligned_inputs=config.get('aligned_inputs', False))
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
                    if registered:
                        assert int(Path('/sys/module/vkso_bch/refcnt').read_text()) == 1
            except BaseException:
                record['status'] = 'fail'
                record.setdefault('cleanup_errors', []).append(traceback.format_exc())
        (OUT / 'modules-after.txt').write_text(Path('/proc/modules').read_text())
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        save('status.json', record)
        os.sync()
    print('bch_kernel_guest_validation=' + record['status'], flush=True)
    return 0 if record['status'] == 'pass' else 1


def run_registered():
    global OUT
    OUT = WORK / 'validation/kernel-cost'
    assert main(registered=True) == 0, 'BCH registered kernel workload failed'
    return dict(status='pass', directory=str(OUT), same_registered_owner=True,
                scope='private guest full functional and collection validation')


if __name__ == '__main__':
    raise SystemExit(main())
