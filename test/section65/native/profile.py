#!/usr/bin/env python3
"""Profile only find's kernel work; exclude mount/unmount from perf sampling."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]
PACKAGE = ROOT / 'test/evaluation-local/packages/iso9660-native-20261029'
PERF = '/usr/lib/linux-tools/5.15.0-119-generic/perf'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=24)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('iso_native_runner', PACKAGE / 'run.py')
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    run = bench.Campaign(argparse.Namespace(output=a.output, client_cpu=1, server_cpu=2,
                                             blocks=1, repeats=a.repeats, functional=False))
    run.status['scope'] = 'diagnostic kernel profile; not formal benchmark timing'
    try:
        run.preflight()
        image = PACKAGE / 'images/kernel-include.iso'
        with image.open('rb') as stream:
            while stream.read(1 << 20):
                pass
        (run.out / 'kallsyms.txt').write_text(Path('/proc/kallsyms').read_text())
        for variant in ('original', 'prepared', 'compat'):
            run.stage('profiling ' + variant)
            control_read, control_write = os.pipe()
            ack_read, ack_write = os.pipe()
            with (run.out / (variant + '-record.log')).open('w') as log:
                perf = subprocess.Popen([PERF, 'record', '-a', '-C', '1', '-e', 'cycles:k', '-F', '997',
                     '-g', '-D', '-1', f'--control=fd:{control_read},{ack_write}',
                     '-o', str(run.out / (variant + '.data'))], pass_fds=(control_read, ack_write),
                     stdout=log, stderr=subprocess.STDOUT)
                os.close(control_read)
                os.close(ack_write)

                def control(command):
                    assert perf.poll() is None, 'perf exited; inspect record log'
                    os.write(control_write, command.encode() + b'\n')
                    assert select.select([ack_read], [], [], 15)[0], 'perf control acknowledgement timeout'
                    acknowledgement = os.read(ack_read, 64)
                    assert acknowledgement.rstrip(b'\0\r\n') == b'ack', repr(acknowledgement)

                try:
                    for repeat in range(a.repeats):
                        with run.mounted(variant, image):
                            with (run.scratch / 'scan.txt').open('wb') as output:
                                control('enable')
                                try:
                                    subprocess.run(['taskset', '-c', '1', str(PACKAGE / 'bin/find'),
                                      str(run.mount), '-printf', '%y %s %m %p %l\n'], stdout=output,
                                      check=True, timeout=30)
                                finally:
                                    control('disable')
                        print(variant, repeat + 1, '/', a.repeats, flush=True)
                finally:
                    if perf.poll() is None:
                        perf.send_signal(signal.SIGINT)
                    code = perf.wait(timeout=30)
                    os.close(control_write)
                    os.close(ack_read)
                    assert code in (0, -signal.SIGINT), ('perf record', code)
            for view, flags in [('self', ['--no-children']), ('inclusive', ['--children'])]:
                run.command([PERF, 'report', '-i', run.out / (variant + '.data'), '--stdio',
                    '--stdio-color', 'never', '--comms', 'find', '--sort', 'symbol,dso',
                    '--percent-limit', '0.5', '--kallsyms', run.out / 'kallsyms.txt', *flags],
                    variant + '-' + view)
        run.status.update(status='complete', stage='complete')
    except BaseException:
        import traceback
        run.status.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        errors = run.cleanup()
        if errors:
            run.status.update(status='failed', cleanup_errors=errors)
        bench.write(run.out / 'result.json', run.status)


if __name__ == '__main__':
    main()
