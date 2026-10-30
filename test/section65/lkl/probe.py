#!/usr/bin/env python3
"""Check an actual lklfuse build against the original-kernel image oracle."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]
sys.path.insert(0, str(SECTION))
from reference_guest import manifest


def lkl_argv(binary, memory, image, mount, norock=False):
    # Backslash escapes the comma inside the value of FUSE's opts= argument.
    options = 'utf8' + ('\\,norock' if norock else '')
    return [str(binary), str(image), str(mount), '-f', '-s', '-o',
            f'ro,type=iso9660,mb={memory},opts={options}']


def memory(pid):
    result = {}
    for filename, fields in [('smaps_rollup', ['Rss', 'Pss', 'Private_Clean', 'Private_Dirty']),
                              ('status', ['VmHWM', 'VmRSS', 'VmSize', 'Threads'])]:
        for line in Path(f'/proc/{pid}/{filename}').read_text().splitlines():
            name, _, value = line.partition(':')
            if name in fields:
                result[name] = int(value.strip().split()[0])
    return result


@contextlib.contextmanager
def mounted(argv, target, log_path):
    with log_path.open('w') as log:
        start = time.perf_counter()
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while not os.path.ismount(target):
                assert child.poll() is None, f'FUSE exited: {log_path}'
                assert time.monotonic() < deadline, f'mount timeout: {log_path}'
                time.sleep(.005)
            # LKL creates the FUSE mount before booting its library kernel.
            # A completed root getattr establishes readiness on both paths.
            subprocess.run(['stat', '--printf=', str(target)], check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=log)
            yield child, time.perf_counter() - start
        finally:
            unmount = ['umount', str(target)] if os.geteuid() == 0 else ['fusermount3', '-u', str(target)]
            try:
                if os.path.ismount(target):
                    subprocess.run(unmount, check=True, timeout=15, stdout=log, stderr=log)
            finally:
                if child.poll() is None:
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.terminate()
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            # An insufficient-memory LKL boot can panic before
                            # entering the FUSE loop that handles termination.
                            child.kill()
                            child.wait(timeout=5)
                if os.path.ismount(target):
                    subprocess.run(unmount, check=True, timeout=15, stdout=log, stderr=log)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--memory', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package', type=Path, default=ROOT / 'test/evaluation-local/packages/iso9660-native-optimized-20261029')
    args = parser.parse_args()
    out, package = args.output.resolve(), args.package.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = out / 'mount'
    target.mkdir()
    result = dict(status='running', binary=str(args.binary.resolve()), memory_parameter_mib=args.memory,
                  scope='complete mounted-image functionality; no performance conclusion', cases=[])
    write = lambda: (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    cases = json.loads((package / 'reference/result.json').read_text())['cases']
    cases += [dict(image='kernel-include.iso', mode='default', manifest='kernel-include-reference.json')]
    try:
        for index, case in enumerate(cases):
            result['active_case'] = case
            write()
            argv = lkl_argv(args.binary.resolve(), args.memory, package / 'images' / case['image'],
                            target, case['mode'] == 'norock')
            with mounted(argv, target, out / f'daemon-{index}.log') as (child, startup):
                before = memory(child.pid)
                rows = manifest(target)
                oracle = (ROOT / 'test/evaluation-local/runs/iso9660/native-private-20261029-agent-01/kernel-include-reference.json'
                          if case['image'] == 'kernel-include.iso' else package / 'reference' / case['manifest'])
                expected = json.loads(oracle.read_text())
                if rows != expected:
                    (out / f'observed-{index}.json').write_text(json.dumps(rows, indent=2) + '\n')
                assert rows == expected, case
                after = memory(child.pid)
                result['cases'].append(dict(case, entries=len(rows), memory_before=before, memory_after=after,
                                            ready_seconds=startup))
            assert child.returncode == 0, child.returncode
            print('pass', case['image'], case['mode'], flush=True)
        result.update(status='pass', active_case=None)
    except BaseException:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        write()


if __name__ == '__main__':
    main()
