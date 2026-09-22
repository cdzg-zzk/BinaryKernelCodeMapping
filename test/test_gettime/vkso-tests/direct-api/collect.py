#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Strict, manually booted four-case collector. Default: read-only preflight.
--execute explicitly permits loading the package's modules and grafting/restoring
its carrier. Never installs kernels, modifies GRUB, reboots, or tunes sysfs.
"""
import argparse
import csv
import fcntl
import gzip
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

from bundle import PROTOCOL, REQUIRED, kv_file, sha256, verify_sums, write_json
from results import CASE_NAMES, validate_rows

CASES = ('raw-normal', 'vkso-normal', 'raw-no-retpoline', 'vkso-no-retpoline')


def text(path):
    return Path(path).read_text().strip()


def cpu_list(value):
    cpus = set()
    for item in value.strip().split(','):
        if not item:
            continue
        parts = [int(x) for x in item.split('-')]
        if len(parts) == 1:
            cpus.add(parts[0])
        elif len(parts) == 2 and parts[0] <= parts[1]:
            cpus.update(range(parts[0], parts[1] + 1))
        else:
            raise ValueError('invalid CPU range: ' + item)
    return cpus


def must(condition, reason):
    if not condition:
        raise ValueError(reason)


def preflight(bundle, case, cpu):
    bundle = bundle.resolve()
    must(not any(os.environ.get(key) for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT')),
         'remove injected loader environment before collecting')
    verify_sums(bundle, {'build.json', 'native-bench', 'vkso-bench',
                         'src/direct-api/collect.py', 'src/direct-api/results.py'})
    build = json.loads((bundle / 'build.json').read_text())
    must(build['protocol'] == PROTOCOL, 'wrong sidecar protocol')
    for name in ('collect.py', 'results.py', 'bundle.py'):
        must(sha256(Path(__file__).parent / name) == sha256(bundle / 'src/direct-api' / name),
             'collector/helper differs from bundled source: ' + name)
    package = Path(build['package']).resolve()
    verify_sums(package, REQUIRED)
    must(sha256(package / 'SHA256SUMS') == build['package_checksums_sha256'], 'kernel package inventory changed')
    must(sha256(package / 'libkernel.so') == build['carrier_sha256'], 'carrier changed')
    must(os.path.samefile(bundle / 'carrier/libkernel.so', package / 'libkernel.so'),
         'linked carrier must be the manager-registered inode, not a copy')
    backend, variant = case.split('-', 1)
    original = kv_file(package / 'boot-manifest.txt')
    must(build['build_variant'] == variant == original['build_variant'], 'wrong mitigation bundle')
    must(build['compiler_version'] == original['cc_version'] == '11.4.0', 'unmatched toolchains')
    must(original.get('update_bench') == '0' and original.get('vkso_validation_tests') == '0',
         'instrumented images are not public READ images')
    must(platform.machine() == 'x86_64' and platform.release() == '5.15.198', 'requires target Linux 5.15.198/x86-64')
    must(platform.version() == original[backend + '_uts_version'], 'running kernel UTS identity differs')
    with gzip.open('/proc/config.gz', 'rb') as stream:
        running_config = stream.read()
    must(running_config == (package / (backend + '.config')).read_bytes(), 'running .config differs from package')
    config = running_config.decode()
    must(('CONFIG_VKSO_TIME=y\n' in config) == (backend == 'vkso'), 'kernel VKSO selection mismatch')
    if variant == 'normal':
        must('CONFIG_RETPOLINE=y\n' in config and 'CONFIG_RETHUNK=y\n' in config, 'Normal mitigations absent')
    else:
        for name in ('RETPOLINE', 'RETHUNK', 'CPU_UNRET_ENTRY', 'CPU_SRSO', 'MITIGATION_ITS'):
            must('CONFIG_' + name + '=y\n' not in config, 'no-retpoline family still enabled: ' + name)
    args = text('/proc/cmdline').split()
    boot_image = next((a.partition('=')[2] for a in args if a.startswith('BOOT_IMAGE=')), '')
    image_name = 'vkso-final-' + case + '-5.15.198.bzImage'
    must(Path(boot_image).name == image_name, 'wrong explicitly booted image')
    must(sha256(Path('/boot') / image_name) == sha256(package / (backend + '-bzImage')), 'installed image differs')
    required_args = ('nokaslr', 'nosmt', 'clocksource=tsc', 'tsc=reliable',
                     'isolcpus=domain,managed_irq,1-3', 'nohz_full=1-3', 'rcu_nocbs=1-3',
                     'irqaffinity=0', 'idle=poll', 'nmi_watchdog=0', 'nowatchdog', 'audit=0')
    must(all(a in args for a in required_args), 'missing controlled boot arguments; see README')
    must(text('/sys/devices/system/clocksource/clocksource0/current_clocksource') == 'tsc', 'clocksource is not TSC')
    must(cpu in os.sched_getaffinity(0) and 0 in os.sched_getaffinity(0), 'controller/measurement CPU unavailable')
    must(cpu in cpu_list(text('/sys/devices/system/cpu/isolated')), 'measurement CPU not isolated')
    must(text('/sys/devices/system/cpu/smt/active') == '0', 'SMT not disabled')
    tuning = {}
    for name, value in (('no_turbo', '1'), ('min_perf_pct', '100'), ('max_perf_pct', '100')):
        path = '/sys/devices/system/cpu/intel_pstate/' + name
        tuning[path] = text(path)
        must(tuning[path] == value, 'unexpected tuning (not modified): ' + path)
    for path in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_governor'):
        tuning[str(path)] = text(path)
        must(tuning[str(path)] == 'performance', 'governor is not performance')
    modules = text('/proc/modules')
    for name in ('page_cache_replace', 'vkso_m09_clock'):
        must(not any(line.startswith(name + ' ') for line in modules.splitlines()), 'module already active: ' + name)
    try:
        active = subprocess.run(['systemctl', 'is-active', '--quiet', 'irqbalance'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        must(not active, 'stop irqbalance explicitly before collecting')
    except FileNotFoundError:
        pass
    runner = ['setarch', platform.machine(), '-R']
    probe = subprocess.check_output(runner + [str(bundle / 'native-bench'), '--probe'], text=True)
    fields = dict(line.split('=', 1) for line in probe.splitlines())
    must(fields['protocol'] == PROTOCOL, 'probe protocol mismatch')
    must(fields['native_vdso'] == ('1' if backend == 'raw' else '0') and
         fields['vkso_mm_auxv'] == ('0' if backend == 'raw' else '1'), 'running backend probe mismatch')
    return package, build, runner, {
        'case': case, 'protocol': PROTOCOL, 'cpu': cpu,
        'backend': 'native-libc' if backend == 'raw' else 'vkso-direct',
        'boot_id': text('/proc/sys/kernel/random/boot_id'),
        'kernel_release': platform.release(), 'kernel_uts': platform.version(),
        'tuning': tuning, 'controlled_boot_arguments': list(required_args),
        'cpu_info': {k.strip(): v.strip() for line in text('/proc/cpuinfo').split('\n\n')[0].splitlines()
                     for k, sep, v in [line.partition(':')] if sep and k.strip() in ('model name', 'microcode', 'flags')},
        'bundle_build_sha256': sha256(bundle / 'build.json'),
        'package_manifest_sha256': sha256(package / 'boot-manifest.txt'),
        'compiler_version': build['compiler_version'],
        'source_fingerprint': build['source_fingerprint'], 'base_cflags': build['base_cflags'],
        'benchmark_source_sha256': sha256(bundle / 'src/direct-api/time_bench.c'),
        'header_sha256': sha256(bundle / 'src/direct-api/vkso_time.h'),
        'binary_sha256': sha256(bundle / ('native-bench' if backend == 'raw' else 'vkso-bench')),
        'counter_unit': 'TSC ticks, not unhalted core cycles',
        'pfn_identity': 'NOT_RUN: manager validation is not an independent PFN observation',
        'kernel_reader_publisher': 'NOT_RUN: use separate existing kernel-side protocols',
    }


def logged(argv, destination, env, timeout=600):
    """Wait synchronously; on interruption stop this command's process group."""
    with Path(destination).open('xb') as output:
        process = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise
    if code:
        raise RuntimeError('command failed (' + str(code) + '): ' + ' '.join(map(str, argv)) + '; log=' + str(destination))


def collect(options, package, build, runner, record):
    must(os.geteuid() == 0, '--execute needs root for the explicitly requested module setup')
    out = options.out.resolve()
    for protected in (package.resolve(), options.bundle.resolve()):
        must(out != protected and protected not in out.parents, 'results must be outside package and bundle')
    out.mkdir(parents=True, exist_ok=False)
    bundle = options.bundle.resolve()
    backend = options.case.split('-', 1)[0]
    binary = bundle / ('native-bench' if backend == 'raw' else 'vkso-bench')
    env = dict(os.environ)
    for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT'):
        env.pop(key, None)
    clock_loaded = manager_loaded = replacement_attempted = False
    failure = None
    cleanup_errors = []
    record.update(iterations=options.iterations, warmup=options.warmup,
                  repeats=options.repeats, processes=options.processes,
                  expected_api_count=len(CASE_NAMES), status='RUNNING')
    write_json(out / 'start.json', record)
    (out / 'package-boot-manifest.txt').write_bytes((package / 'boot-manifest.txt').read_bytes())
    (out / 'bundle-build.json').write_bytes((bundle / 'build.json').read_bytes())
    (out / 'interrupts-before.txt').write_text(text('/proc/interrupts') + '\n')
    try:
        os.sched_setaffinity(0, {0})
        logged(['insmod', str(package / 'vkso_m09_clock.ko')], out / 'clock-module.log', env)
        clock_loaded = True
        for _ in range(50):
            if (Path('/dev/vkso-m09-clock').is_char_device()):
                break
            time.sleep(0.1)
        must(Path('/dev/vkso-m09-clock').is_char_device(), 'dynamic clock device missing')
        if backend == 'vkso':
            logged(['insmod', str(package / 'page_cache_replace.ko')], out / 'manager-module.log', env)
            manager_loaded = True
            common = [str(package / 'libkernel.so'), str(package / 'page_mappings.txt')]
            logged([str(package / 'manager'), 'validate'] + common, out / 'manager-validate.log', env)
            replacement_attempted = True  # includes partial/failed replacement
            logged([str(package / 'manager'), 'replace'] + common, out / 'manager-replace.log', env)
        legacy_env = dict(env, VKSO_TEST_DYNAMIC_CLOCK='/dev/vkso-m09-clock', LD_LIBRARY_PATH=str(package))
        logged(runner + [str(package / (backend + '-abi-matrix'))], out / 'legacy-abi.log', legacy_env)
        must('abi_matrix_status=pass' in (out / 'legacy-abi.log').read_text(), 'legacy ABI matrix did not pass')
        for mode in ('--check', '--check-fast'):
            logged(runner + [str(binary), mode, '--cpu', str(options.cpu)], out / (mode[2:] + '.log'), env)
        rows = []
        remaining = options.repeats
        for process in range(options.processes):
            local_repeats = (remaining + options.processes - process - 1) // (options.processes - process)
            destination = out / ('process-%02d.csv' % process)
            logged(runner + [str(binary), '--bench', '--cpu', str(options.cpu),
                            '--iterations', str(options.iterations), '--warmup', str(options.warmup),
                            '--repeats', str(local_repeats), '--process-index', str(process)], destination, env)
            with destination.open() as stream:
                rows.extend(csv.DictReader(stream))
            remaining -= local_repeats
        validate_rows(rows, record)
        with (out / 'samples.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    except BaseException as exc:
        failure = repr(exc)
    finally:
        # If restoration fails, do NOT unload the backing module or report PASS.
        if replacement_attempted:
            try:
                logged([str(package / 'manager'), 'restore', str(package / 'libkernel.so'),
                        str(package / 'page_mappings.txt')], out / 'manager-restore.log', env, timeout=120)
            except BaseException as exc:
                cleanup_errors.append('RESTORE FAILED; leave module loaded and recover manually: ' + repr(exc))
        if manager_loaded and not cleanup_errors:
            try:
                logged(['rmmod', 'page_cache_replace'], out / 'manager-unload.log', env)
            except BaseException as exc:
                cleanup_errors.append(repr(exc))
        if clock_loaded:
            try:
                logged(['rmmod', 'vkso_m09_clock'], out / 'clock-unload.log', env)
            except BaseException as exc:
                cleanup_errors.append(repr(exc))
        try:
            (out / 'interrupts-after.txt').write_text(text('/proc/interrupts') + '\n')
        except OSError as exc:
            cleanup_errors.append('could not record final interrupts: ' + repr(exc))
        record.update(status='COMPLETE' if not failure and not cleanup_errors else 'FAIL',
                      error=failure, cleanup_errors=cleanup_errors)
        write_json(out / 'run.json', record)
        with (out / 'SHA256SUMS').open('x') as stream:
            for path in sorted(out.iterdir()):
                if path.is_file() and path.name != 'SHA256SUMS':
                    stream.write(sha256(path) + '  ' + path.name + '\n')
    if record['status'] != 'COMPLETE':
        raise RuntimeError('collection failed; preserve ' + str(out) + ': ' + str(failure or cleanup_errors))
    print('public_api_collection=COMPLETE; PFN and kernel-side tests remain separate; ' + str(out))


def interrupted(signum, frame):
    raise InterruptedError('received signal ' + str(signum))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--cpu', type=int, default=2)
    parser.add_argument('--iterations', type=int, default=500000)
    parser.add_argument('--warmup', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=31)
    parser.add_argument('--processes', type=int, default=7)
    parser.add_argument('--execute', action='store_true')
    options = parser.parse_args()
    lock = None
    try:
        if options.execute:
            must(os.geteuid() == 0, '--execute requires root')
            lock = open('/run/vkso-direct-api.lock', 'a')
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            for number in (signal.SIGTERM, signal.SIGHUP):
                signal.signal(number, interrupted)
        must(1 <= options.processes <= options.repeats <= 10000, 'invalid repetition hierarchy')
        must(0 < options.iterations <= 1000000000 and 0 <= options.warmup <= 1000000000, 'invalid batch size')
        package, build, runner, record = preflight(options.bundle, options.case, options.cpu)
        if not options.execute:
            print(json.dumps({'preflight': 'PASS', 'kernel_setup': 'NOT_RUN', 'environment': record}, indent=2))
            return 0
        must(options.out is not None, '--out is required with --execute')
        collect(options, package, build, runner, record)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print('REFUSED/FAILED: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    sys.exit(main())
