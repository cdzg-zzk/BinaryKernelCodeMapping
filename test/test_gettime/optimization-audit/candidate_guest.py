#!/usr/bin/env python3
"""Full existing public ABI tests on isolated candidate carrier instances."""
import json
import os
from pathlib import Path
import subprocess


def run(args, output=None, env=None):
    if output:
        with output.open('w') as stream:
            subprocess.run(list(map(str, args)), check=True, env=env,
                           stdout=stream, stderr=subprocess.STDOUT)
    else:
        subprocess.run(list(map(str, args)), check=True, env=env)


def main():
    root = Path('/work')
    output = root / 'results'
    output.mkdir()
    run(['insmod', root / 'package/page_cache_replace.ko'])
    run(['insmod', root / 'vkso_m09_clock.ko'])
    results = []
    for name in ['baseline', 'entry-null', 'coarse-late-offset']:
        package = root / name
        with (package / 'libkernel.so').open('rb') as stream:
            os.fsync(stream.fileno())
        run([package / 'manager', 'validate', package / 'libkernel.so', package / 'page_mappings.txt'])
        run([package / 'manager', 'replace', package / 'libkernel.so', package / 'page_mappings.txt'])
        env = {**os.environ, 'LD_LIBRARY_PATH': str(package), 'VKSO_TEST_DYNAMIC_CLOCK': '/dev/vkso-m09-clock'}
        try:
            log = output / f'{name}-abi.log'
            run([package / 'vkso-abi-matrix'], output=log, env=env)
            assert 'abi_matrix_status=pass' in log.read_text()
            clock = Path('/sys/devices/system/clocksource/clocksource0')
            original = (clock / 'current_clocksource').read_text().strip()
            alternate = next(s for s in (clock / 'available_clocksource').read_text().split() if s != original)
            try:
                (clock / 'current_clocksource').write_text(alternate)
                run([package / 'vkso-abi-matrix', '--provider-fallback'],
                    output=output / f'{name}-provider.log', env=env)
            finally:
                (clock / 'current_clocksource').write_text(original)
            run([package / 'vkso-abi-matrix', '--lifecycle-smoke'],
                output=output / f'{name}-lifecycle.log', env=env)
            results.append(dict(method=name, abi='pass', provider='pass', lifecycle='pass',
                shared_code=name == 'entry-null', ordinary_kernel='unchanged archived image'))
        finally:
            run([package / 'manager', 'restore', package / 'libkernel.so', package / 'page_mappings.txt'])
    run(['rmmod', 'vkso_m09_clock'])
    run(['rmmod', 'page_cache_replace'])
    (output / 'candidates.json').write_text(json.dumps(results, indent=2))
    print('candidate_validation=pass', flush=True)


if __name__ == '__main__':
    main()
