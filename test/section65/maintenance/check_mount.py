#!/usr/bin/env python3
"""Observe the real long-Joliet regression through a mounted filesystem."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def observe(mount, expected, fixed):
    names = os.listdir(os.fsencode(mount))
    key = expected['name'].encode()
    try:
        data = (mount / expected['name']).read_bytes()
        found = True
    except FileNotFoundError:
        data = None
        found = False
    assert found == fixed, (found, fixed)
    if fixed:
        assert key in names and data.decode() == expected['payload']
    else:
        assert [len(n) for n in names] == [44]
    return dict(status='pass', fixed=fixed, name_bytes=[len(n) for n in names],
                names_hex=[n.hex() for n in names], full_name_lookup=found,
                payload_bytes=len(data) if data else None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frontend', type=Path, required=True)
    p.add_argument('--core', type=Path, required=True)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--fixed', action='store_true')
    p.add_argument('--shared', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    mount = a.output.resolve() / 'mount'
    mount.mkdir()
    expected = json.loads((a.case / 'expected.json').read_text())
    with (a.output / 'daemon.log').open('w') as stream:
        child = subprocess.Popen(list(map(str, [a.frontend.resolve(), a.core.resolve(), a.bridge.resolve(),
                                  (a.case / 'long-joliet.iso').resolve(), '0', mount])),
                                 stdout=stream, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while not os.path.ismount(mount):
                assert child.poll() is None, 'FUSE exited'
                assert time.monotonic() < deadline
                time.sleep(.05)
            result = observe(mount, expected, a.fixed)
            if a.shared:
                from check_fuse import observe_process
                observe_process(child.pid, a.core.resolve(), a.output / 'pfns.json')
            result.update(core=str(a.core), bridge=str(a.bridge), scope='mounted compatibility regression, not performance')
            (a.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
        finally:
            if os.path.ismount(mount):
                subprocess.run(['umount' if os.geteuid() == 0 else 'fusermount3',
                                *([] if os.geteuid() == 0 else ['-u']), str(mount)], check=True)
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)


if __name__ == '__main__':
    main()
