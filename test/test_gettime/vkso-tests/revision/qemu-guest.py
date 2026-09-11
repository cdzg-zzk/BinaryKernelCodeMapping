#!/usr/bin/python3
"""Functional validation only, using the actual packaged kernels and collector."""
import csv
import os
from pathlib import Path
from types import SimpleNamespace
from collect import (clone_package, registered, run, collect_read, collect_update,
                     materialize, WRITER, FIELDS)


def main():
    package = Path('/work')
    backend = (package / 'backend').read_text().strip()
    output = package / 'validation'
    output.mkdir()
    os.sched_setaffinity(0, {0})
    run(['insmod', package / 'vkso_m09_clock.ko'])
    run(['insmod', package / 'vkso_kernel_reader.ko'])
    if backend == 'vkso':
        run(['insmod', package / 'page_cache_replace.ko'])
    args = SimpleNamespace(cpu=2, rounds=3, processes=2, iterations=2000, warmup=100,
                           reader_cpus='1,2,3', rate=1000000, block=0, update_rounds=1,
                           seconds=3, paced_iterations=10000, paced_warmup=1000,
                           multireader=package / 'vkso-multireader')
    for method in (['raw'] if backend == 'raw' else ['vkso', 'compact-split']):
        target = output / method
        target.mkdir()
        carrier = target / 'package'
        clone_package(package, carrier)
        if method == 'compact-split':
            with registered(carrier):
                copied = materialize(carrier / 'libkernel.so', carrier / 'page_mappings.txt', target / 'copied')
            import shutil
            shutil.copyfile(copied / 'libkernel.so', carrier / 'libkernel.so')
            shutil.copyfile(copied / 'page_mappings.txt', carrier / 'page_mappings.txt')
        import contextlib
        with registered(carrier) if backend == 'vkso' else contextlib.nullcontext():
            env = {**os.environ, 'LD_LIBRARY_PATH': str(carrier),
                   'VKSO_TEST_DYNAMIC_CLOCK': '/dev/vkso-m09-clock'}
            run([carrier / f'{backend}-abi-matrix'], output=target / 'functional.log', env=env)
            if 'abi_matrix_status=pass' not in (target / 'functional.log').read_text():
                raise ValueError('ABI matrix did not pass')
            if method == 'compact-split':
                # This complete copy is new: exercise the existing event tests
                # against it in the guest, outside all performance collection.
                binary = carrier / f'{backend}-abi-matrix'
                run([binary, '--time-events'], output=target / 'time-events.log', env=env)
                clock = Path('/sys/devices/system/clocksource/clocksource0')
                current = (clock / 'current_clocksource').read_text().strip()
                alternate = next(s for s in (clock / 'available_clocksource').read_text().split()
                                 if s != current)
                try:
                    (clock / 'current_clocksource').write_text(alternate)
                    run([binary, '--provider-fallback'], output=target / 'provider-fallback.log', env=env)
                finally:
                    (clock / 'current_clocksource').write_text(current)
                run([binary, '--lifecycle-smoke'], output=target / 'provider-restored.log', env=env)
                run([binary, '--suspend-resume'], output=target / 'suspend-resume.log', env=env)
            if backend == 'vkso':
                # Run in a fresh process so dlclose cannot leave a live registration.
                run(['python3', package / 'revision/footprint.py', carrier / 'libkernel.so',
                     package / 'page_mappings.txt', method], output=target / 'footprint.json', env=env)
            identity = dict(variant='normal', role='validation', method=method,
                            boot_id='qemu-functional-only', image_sha256='not-performance-evidence')
            measurements = []
            collect_read(carrier, target, backend, identity, args, measurements)
            if (WRITER / 'control').exists():
                collect_update(carrier, target, backend, identity, args, measurements)
            with (target / 'measurements.csv').open('w') as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(measurements)
        print(f'revision_method={method} status=pass', flush=True)
    if backend == 'vkso':
        run(['rmmod', 'page_cache_replace'])
    run(['rmmod', 'vkso_kernel_reader'])
    run(['rmmod', 'vkso_m09_clock'])
    print('revision_preflight=pass', flush=True)


if __name__ == '__main__':
    main()
