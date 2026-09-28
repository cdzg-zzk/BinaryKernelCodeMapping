#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Reconstruct and compile reviewed Clocktime objects; never alter the host kernel.

Requires a pristine extracted Linux 5.15.198 tree, GCC/Kbuild prerequisites and
Git history. All reconstruction occurs in a temporary copy. Output retains logs,
configs, object disassembly, source identities and shared-text equality checks.
The optional minimal QEMU smoke is functional only, not the experimental image
or performance evidence. It never boots or changes the host kernel.
"""
import argparse
import csv
import gzip
import io
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
PREFIX = 'test/test_gettime/linux-5.15.198-vkso'
READER = 'test/test_gettime/vkso-tests/revision/kernel-reader'
PLATFORM = 'test/test_gettime/vkso-tests/code-size/platform-baseline.json'
BASE = '09b9505667f1d1c3da71ac8aaaa7d6054255bc62'
OBJECTS = ['kernel/time/timekeeping.o', 'kernel/time/posix-timers.o',
           'kernel/time/time.o', 'kernel/sys.o', 'kernel/time/vkso_time_core.o',
           'kernel/time/vkso_time_cycles.o', 'kernel/time/vkso_time.o',
           'arch/x86/kernel/vkso_getcpu.o']
SHARED = ['kernel/time/vkso_time_core.o', 'kernel/time/vkso_time_cycles.o',
          'arch/x86/kernel/vkso_getcpu.o']


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbol_sizes(text):
    return {m[3]: int(m[2], 16) for line in text.splitlines()
            if (m := re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) [tTwW] (\S+)', line))}


def validate_config(config, variant):
    """Fail closed if Kconfig dependencies silently erased a requested variant."""
    lines = set(config.splitlines())
    for name in ('VKSO_TIME', 'CPU_MITIGATIONS'):
        if 'CONFIG_' + name + '=y' not in lines:
            raise ValueError('configuration missing ' + name)
    for name in ('RETPOLINE', 'RETHUNK', 'CPU_UNRET_ENTRY'):
        enabled = 'CONFIG_' + name + '=y' in lines
        if enabled != (variant == 'normal'):
            raise ValueError('configuration does not implement ' + variant + ': ' + name)


def initramfs(entries):
    """Create deterministic newc bytes without privileged filesystem operations."""
    result = bytearray()
    for inode, entry in enumerate([*entries, ('TRAILER!!!', b'', 0)], 1):
        name, data, mode, *device = entry
        major, minor = device[0] if device else (0, 0)
        name = name.encode() + b'\0'
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name), 0]
        result.extend(b'070701' + ''.join(f'{v:08x}' for v in fields).encode())
        result.extend(name)
        result.extend(b'\0' * (-len(result) % 4))
        result.extend(data)
        result.extend(b'\0' * (-len(result) % 4))
    return gzip.compress(result, mtime=0)


def boot_smoke(source, work, out, options, env, run):
    """Boot only an isolated candidate VM; keep its timings out of performance data."""
    build = work / 'smoke-build'
    build.mkdir()
    cmd = ['make', '-C', source, 'O=' + str(build), 'CC=' + options.cc,
           '-j' + str(options.jobs)]
    run([*cmd, 'tinyconfig'], 'smoke-build.log')
    enable = ['64BIT', 'SMP', 'ACPI', 'CPU_MITIGATIONS', 'MODULES', 'MODULE_UNLOAD', 'PRINTK', 'TTY',
              'SERIAL_8250', 'SERIAL_8250_CONSOLE', 'BINFMT_ELF', 'BINFMT_SCRIPT', 'BLK_DEV_INITRD',
              'RD_GZIP', 'PROC_FS', 'SYSFS', 'DEBUG_FS', 'DEVTMPFS', 'TMPFS',
              'NAMESPACES', 'TIME_NS', 'POSIX_TIMERS', 'FUTEX', 'HIGH_RES_TIMERS', 'SHMEM',
              'IKCONFIG', 'IKCONFIG_PROC', 'HPET_TIMER', 'KALLSYMS']
    flags = [v for name in enable for v in ('--enable', name)]
    flags += ['--set-val', 'NR_CPUS', '2', '--disable', 'IA32_EMULATION',
              '--disable', 'X86_X32', '--disable', 'VKSO_TIME_TEST',
              '--set-str', 'SYSTEM_TRUSTED_KEYS', '',
              '--set-str', 'SYSTEM_REVOCATION_KEYS', '']
    for name in ['RETPOLINE', 'RETHUNK', 'CPU_UNRET_ENTRY']:
        flags += ['--enable' if options.variant == 'normal' else '--disable', name]
    run([source / 'scripts/config', '--file', build / '.config', *flags], 'smoke-build.log')
    run([*cmd, 'olddefconfig'], 'smoke-build.log')
    config = (build / '.config').read_text()
    validate_config(config, options.variant)
    for name in ['64BIT', 'SMP', 'MODULES', 'PROC_FS', 'SYSFS', 'DEBUG_FS',
                 'SERIAL_8250_CONSOLE', 'BINFMT_ELF', 'BLK_DEV_INITRD', 'VKSO_TIME']:
        if 'CONFIG_' + name + '=y\n' not in config:
            raise ValueError('smoke config missing ' + name)
    shutil.copy2(build / '.config', out / 'smoke.config')
    run([*cmd, 'bzImage', 'modules'], 'smoke-build.log')
    module = work / 'smoke-module'
    module.mkdir()
    for name in ['Makefile', 'vkso_kernel_reader.c']:
        (module / name).write_bytes(git('show', options.head + ':' + READER + '/' + name))
    run([*cmd, 'M=' + str(module), 'modules'], 'smoke-build.log')
    kernel = build / 'arch/x86/boot/bzImage'
    ko = module / 'vkso_kernel_reader.ko'
    result = dict(scope='minimal VM; functional only; NOT formal timing',
                  accelerator='TCG', kernel_sha256=digest(kernel), module_sha256=digest(ko), boots={})
    if not options.busybox.is_file():
        raise ValueError('static BusyBox is required for --boot-smoke')
    readelf = subprocess.check_output(['readelf', '-l', str(options.busybox)], text=True)
    if 'INTERP' in readelf:
        raise ValueError('BusyBox must be statically linked')
    probe = work / 'syscall-smoke'
    probe_source = work / 'syscall_smoke.c'
    probe_source.write_bytes(git('show', options.head + ':' + READER + '/syscall_smoke.c'))
    run([options.cc, '-O2', '-static', '-D_GNU_SOURCE', '-Wall', '-Wextra', '-Werror',
         probe_source, '-o', probe], 'smoke-build.log')
    for clock in ('tsc', 'jiffies'):
        init = f"""#!/bin/busybox sh
/bin/busybox --install -s /bin
export PATH=/bin
set -eu
trap 'echo CLOCKTIME_BOOT_SMOKE_FAIL; reboot -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t debugfs debugfs /sys/kernel/debug
uname -r
# init may run before late TSC registration; do not mistake tsc-early for
# the requested clock. Wait with a bound, select explicitly, then verify.
control=/sys/devices/system/clocksource/clocksource0/current_clocksource
available=/sys/devices/system/clocksource/clocksource0/available_clocksource
tries=0
while :; do
    case " $(cat "$available") " in
        *" {clock} "*) break ;;
    esac
    tries=$((tries + 1))
    test "$tries" -lt 20
    sleep 1
done
printf '%s\\n' '{clock}' >"$control"
echo EXPECTED_CLOCK={clock}
cat "$control"
test "$(cat "$control")" = '{clock}'
# Require the configured SMP VM, rather than silently testing one CPU.
cat /sys/devices/system/cpu/online
test "$(cat /sys/devices/system/cpu/online)" = '0-1'
/syscall-smoke
insmod /reader.ko
printf '0 2000 3 100\\n' >/sys/kernel/debug/vkso_kernel_reader/control
echo TIMESPEC_BEGIN
cat /sys/kernel/debug/vkso_kernel_reader/samples
echo TIMESPEC_END
printf '0 2000 3 100\\n' >/sys/kernel/debug/vkso_kernel_reader/scalar_control
echo SCALAR_BEGIN
cat /sys/kernel/debug/vkso_kernel_reader/scalar_samples
echo SCALAR_END
rmmod vkso_kernel_reader
echo CLOCKTIME_BOOT_SMOKE_PASS_{clock}
trap - EXIT
reboot -f
"""
        entries = [(n, b'', 0o40755) for n in ['bin', 'dev', 'proc', 'sys']]
        entries += [('dev/console', b'', 0o20600, (5, 1)),
                    ('dev/null', b'', 0o20666, (1, 3)),
                    ('syscall-smoke', probe.read_bytes(), 0o100755),
                    ('init', init.encode(), 0o100755),
                    ('bin/busybox', options.busybox.read_bytes(), 0o100755),
                    ('reader.ko', ko.read_bytes(), 0o100644)]
        initrd = work / ('smoke-' + clock + '.cpio.gz')
        initrd.write_bytes(initramfs(entries))
        argv = ['qemu-system-x86_64', '-accel', 'tcg', '-cpu', 'max', '-m', '512', '-smp', '2',
                '-no-reboot', '-nographic', '-nic', 'none', '-kernel', str(kernel),
                '-initrd', str(initrd), '-append',
                f'console=ttyS0 rdinit=/init panic=1 nokaslr clocksource={clock} tsc=reliable']
        log = 'smoke-' + clock + '.log'
        run(argv, log)
        text = (out / log).read_text()
        if 'CLOCKTIME_BOOT_SMOKE_FAIL' in text or 'CLOCKTIME_BOOT_SMOKE_PASS_' + clock not in text:
            raise ValueError('QEMU boot did not pass: ' + log)
        if 'CLOCKTIME_SYSCALL_SMOKE_PASS' not in text:
            raise ValueError('syscall smoke did not pass: ' + log)
        suites = {'syscall_abi': 'PASS'}
        for label, apis in [('TIMESPEC', ['monotonic', 'monotonic_raw', 'monotonic_coarse']),
                            ('SCALAR', ['ktime_get', 'ktime_get_raw', 'ktime_get_real',
                                        'ktime_get_boottime', 'ktime_get_tai'])]:
            csv_text = text.split(label + '_BEGIN\n', 1)[1].split(label + '_END', 1)[0]
            rows = list(csv.DictReader(io.StringIO(csv_text)))
            expected = {(api, str(r)) for api in apis for r in range(3)}
            if len(rows) != len(expected) or {(r['api'], r['round']) for r in rows} != expected:
                raise ValueError('incomplete QEMU suite ' + label)
            if any(int(r['total_tsc_cycles']) <= 0 or r['cpu'] != '0' or r['iterations'] != '2000' for r in rows):
                raise ValueError('invalid QEMU samples ' + label)
            suites[label] = len(rows)
        result['boots'][clock] = dict(status='PASS', suites=suites)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--base', default=BASE)
    p.add_argument('--head', default='HEAD')
    p.add_argument('--cc', default='gcc')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--variant', choices=['normal', 'no-retpoline'], default='normal')
    p.add_argument('--boot-smoke', action='store_true',
                   help='also build a minimal candidate kernel and boot it with QEMU TCG')
    p.add_argument('--busybox', type=Path, default=Path('/bin/busybox'))
    a = p.parse_args()
    if not 1 <= a.jobs <= 256:
        p.error('jobs must be in 1..256')
    version = (a.source / 'Makefile').read_text()
    for key, val in [('VERSION', '5'), ('PATCHLEVEL', '15'), ('SUBLEVEL', '198')]:
        if not re.search(r'^' + key + r'\s*=\s*' + val + r'\s*$', version, re.M):
            p.error('requires pristine Linux 5.15.198 source')
    out = a.out.resolve()
    if out == a.source.resolve() or a.source.resolve() in out.parents:
        p.error('output must be outside the pristine source tree')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='FAIL', scope='Kbuild objects; optional minimal VM smoke; never formal performance',
                  variant=a.variant, revisions={}, shared_text={}, function_bytes={})
    env = dict(os.environ, KBUILD_BUILD_TIMESTAMP='2026-09-28 00:00:00 UTC',
               KBUILD_BUILD_USER='clocktime', KBUILD_BUILD_HOST='validation')
    def run(args, log):
        with (out / log).open('a') as stream:
            stream.write('$ ' + ' '.join(map(str, args)) + '\n'); stream.flush()
            subprocess.run(list(map(str, args)), stdout=stream, stderr=subprocess.STDOUT,
                           env=env, check=True, timeout=600)
    try:
        report['compiler'] = subprocess.check_output([a.cc, '--version'], text=True)
        with tempfile.TemporaryDirectory(prefix='clocktime-kbuild-') as work:
            work = Path(work)
            source = work / 'linux'
            shutil.copytree(a.source, source, symlinks=True)
            edits = json.loads(git('show', a.base + ':' + PLATFORM))
            for item in edits:
                path = Path(item['path'])
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('invalid platform path')
                target = source / path
                text = target.read_text().splitlines(True) if target.exists() else []
                for edit in reversed(item['edits']):
                    if not 0 <= edit['start'] <= edit['end'] <= len(text):
                        raise ValueError('invalid platform edit: ' + str(path))
                    text[edit['start']:edit['end']] = edit['lines']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(''.join(text))
            for label, ref in [('base', a.base), ('candidate', a.head)]:
                rev = git('rev-parse', '--verify', ref + '^{commit}').decode().strip()
                report['revisions'][label] = rev
                paths = git('ls-tree', '-r', '--name-only', rev, '--', PREFIX).decode().splitlines()
                for name in paths:
                    target = source / Path(name).relative_to(PREFIX)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(git('show', rev + ':' + name))
                build = work / (label + '-build')
                build.mkdir()
                cmd = ['make', '-C', source, 'O=' + str(build), 'CC=' + a.cc, '-j' + str(a.jobs)]
                run([*cmd, 'defconfig'], label + '.log')
                flags = ['--enable', 'TIME_NS', '--enable', 'MODULES', '--enable', 'DEBUG_FS',
                         '--enable', 'CPU_MITIGATIONS',
                         '--disable', 'IA32_EMULATION', '--disable', 'X86_X32',
                         '--disable', 'VKSO_TIME_TEST', '--disable', 'DEBUG_INFO',
                         '--disable', 'DEBUG_INFO_BTF', '--disable', 'FUNCTION_TRACER',
                         '--disable', 'STACKPROTECTOR', '--disable', 'STACKPROTECTOR_STRONG',
                         '--set-str', 'SYSTEM_TRUSTED_KEYS', '',
                         '--set-str', 'SYSTEM_REVOCATION_KEYS', '']
                if a.variant == 'no-retpoline':
                    for flag in ['RETPOLINE', 'RETHUNK', 'CPU_UNRET_ENTRY']:
                        flags += ['--disable', flag]
                run([source / 'scripts/config', '--file', build / '.config', *flags], label + '.log')
                run([*cmd, 'olddefconfig'], label + '.log')
                validate_config((build / '.config').read_text(), a.variant)
                run([*cmd, 'modules_prepare'], label + '.log')
                shutil.copy2(build / '.config', out / (label + '.config'))
                run([*cmd, *OBJECTS], label + '.log')
                module = work / (label + '-module')
                module.mkdir()
                for name in ['Makefile', 'vkso_kernel_reader.c']:
                    (module / name).write_bytes(git('show', rev + ':' + READER + '/' + name))
                run([*cmd, 'M=' + str(module), 'vkso_kernel_reader.o'], label + '.log')
                for obj in OBJECTS + [str(module / 'vkso_kernel_reader.o')]:
                    path = Path(obj) if Path(obj).is_absolute() else build / obj
                    target = label + '-' + path.name
                    run(['objdump', '-dr', path], target + '.disassembly.txt')
                    run(['nm', '-S', '--size-sort', path], target + '.symbols.txt')
                    report['function_bytes'][target] = symbol_sizes(
                        (out / (target + '.symbols.txt')).read_text())
                    if obj in SHARED:
                        text = out / (target + '.shared-text')
                        run(['objcopy', '--dump-section', '.vkso.text=' + str(text), path], label + '.log')
                        report['shared_text'].setdefault(obj, {})[label] = digest(text)
            for obj, hashes in report['shared_text'].items():
                if hashes['base'] != hashes['candidate']:
                    raise ValueError('shared text changed: ' + obj)
            if (out / 'base.config').read_bytes() != (out / 'candidate.config').read_bytes():
                raise ValueError('configuration mismatch')
            report['function_changes'] = []
            for obj in OBJECTS + ['vkso_kernel_reader.o']:
                name = Path(obj).name
                before = report['function_bytes']['base-' + name]
                after = report['function_bytes']['candidate-' + name]
                for symbol in sorted(before.keys() | after.keys()):
                    if before.get(symbol, 0) != after.get(symbol, 0):
                        report['function_changes'].append(dict(object=name, symbol=symbol,
                            before=before.get(symbol, 0), after=after.get(symbol, 0)))
            if a.boot_smoke:
                report['boot_smoke'] = boot_smoke(source, work, out, a, env, run)
            report['status'] = 'PASS'
    except BaseException as e:
        report['error'] = str(e)
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        (out / 'SHA256SUMS').write_text(''.join(digest(f) + '  ' + f.name + '\n'
            for f in sorted(out.iterdir()) if f.is_file() and f.name != 'SHA256SUMS'))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
