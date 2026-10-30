#!/usr/bin/env python3
"""Guest-only maintenance test; the old native read intentionally ends this VM."""
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from reference_guest import manifest
from check_fuse import mounted, observe

PACKAGE = Path('/work/package')
OUT = Path('/work/evidence')


def main():
    OUT.mkdir()
    mode = (PACKAGE/'mode').read_text().strip()
    result = dict(status='running', mode=mode, stage='load')
    loaded, registered, library = [], False, None
    mount = OUT/'mount'; mount.mkdir()
    carrier = OUT/'carrier'; carrier.mkdir()

    def write():
        with (OUT/'result.json').open('w') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
            stream.flush(); os.fsync(stream.fileno())

    def command(argv, label, cwd=None):
        with (OUT/(label+'.log')).open('w') as log:
            subprocess.run(list(map(str, argv)), cwd=cwd, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=180)

    def native(image, negative=False):
        command(['mount', '-t', 'vksosquash', '-o', 'ro,loop', image, mount], 'native-mount')
        try:
            if negative:
                result['stage'] = 'native-negative-read'; write()
                # Persist the successful user-domain observations before the old kernel panics.
                subprocess.run(['sync'], check=True)
                try: data = (mount/'payload').read_bytes()
                except OSError as exc: return dict(errno=exc.errno)
                return dict(errno=0, bytes=len(data), zero_filled=not any(data),
                            sha256=hashlib.sha256(data).hexdigest())
            assert (mount/'payload').read_bytes() == (PACKAGE/'case/source/payload').read_bytes()
            return dict(status='pass')
        finally: command(['umount', mount], 'native-unmount')

    def fuse_case(image, label, core, shared, negative=False):
        argv = [PACKAGE/'vkso-squashfuse', core, PACKAGE/'libsq-bridge.so', image, '0', mount]
        # A crashing old daemon is an observed outcome; mounted() requires clean exit.
        with (OUT/(label+'.log')).open('w') as log:
            child = subprocess.Popen(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+30
                while not os.path.ismount(mount):
                    assert child.poll() is None
                    assert time.monotonic() < deadline
                    time.sleep(.05)
                observe(child.pid, core, carrier/'page_mappings.txt', OUT/(label+'.log'),
                        OUT/(label+'-pfns.json'), shared)
                try:
                    data = (mount/'payload').read_bytes()
                    outcome = dict(client_errno=0, bytes=len(data), zero_filled=not any(data),
                                   sha256=hashlib.sha256(data).hexdigest())
                    if not negative:
                        assert data == (PACKAGE/'case/source/payload').read_bytes()
                except OSError as exc:
                    assert negative
                    outcome = dict(client_errno=exc.errno)
                # Observe survival before a normal unmount terminates the daemon.
                if negative:
                    time.sleep(.2)
                outcome['daemon_alive_after_read'] = child.poll() is None
            finally:
                if os.path.ismount(mount):
                    command(['umount', mount], label+'-unmount')
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.terminate(); child.wait(timeout=10)
            outcome['daemon_returncode'] = child.returncode
        return outcome

    try:
        os.environ['VKSO_SQ_STATE'] = '1'
        for name in ['vkso_sq_core', 'vkso_squashfs', 'vkso_kernel_reader', 'page_cache_replace']:
            command(['insmod', PACKAGE/(name+'.ko')], 'load-'+name); loaded.append(name)
        result['native_valid'] = native(PACKAGE/'case/valid.squashfs')
        command([PACKAGE/'krg', 'build', PACKAGE/'vmlinux', '--module', PACKAGE/'vkso_sq_core.ko',
                 '-o', carrier/'out.krg'], 'krg')
        command([sys.executable, PACKAGE/'build_PIC_so.py', '--symbols', PACKAGE/'symbols.txt',
                 '--krg', carrier/'out.krg', '--ko', PACKAGE/'vkso_sq_core.ko',
                 '--shim-list', PACKAGE/'shim.txt', '--vmlinux', PACKAGE/'vmlinux'], 'carrier', carrier)
        library = next(carrier.glob('lib*.so')).resolve(); before = library.read_bytes()
        command([PACKAGE/'manager', 'replace', library, carrier/'page_mappings.txt'], 'register', PACKAGE)
        registered = True
        copied = OUT/'libsq-materialized.so'
        copied.write_bytes(library.read_bytes())
        for label, core in [('copied', copied), ('shared', library)]:
            result[label+'_valid'] = fuse_case(PACKAGE/'case/valid.squashfs', label+'-valid', core, label=='shared')
            result[label+'_negative'] = fuse_case(PACKAGE/'case/negative.squashfs', label+'-negative', core, label=='shared', True)
            write()
        write()
        if mode == 'fixed':
            # Existing full-image oracle and boundary-read suite, on the unchanged user adapter.
            command([sys.executable, PACKAGE/'check_fuse.py', '--build', PACKAGE,
                     '--images', PACKAGE/'images', '--reference', PACKAGE/'reference',
                     '--core', library, '--bridge', PACKAGE/'libsq-bridge.so',
                     '--pfn-plan', carrier/'page_mappings.txt', '--expect-shared',
                     '--output', OUT/'regression-shared'], 'regression-shared')
            command([sys.executable, PACKAGE/'check_fuse.py', '--build', PACKAGE,
                     '--images', PACKAGE/'images', '--reference', PACKAGE/'reference',
                     '--core', copied, '--bridge', PACKAGE/'libsq-bridge.so',
                     '--pfn-plan', carrier/'page_mappings.txt',
                     '--output', OUT/'regression-copied'], 'regression-copied')
            result['native_regression'] = []
            for image in sorted((PACKAGE/'images').glob('*.squashfs')):
                command(['mount', '-t', 'vksosquash', '-o', 'ro,loop', image, mount], 'regression-mount')
                try:
                    rows = manifest(mount)
                    expected = json.loads((PACKAGE/'reference'/(image.stem+'-squashfs.json')).read_text())
                    assert rows == expected
                    result['native_regression'].append(dict(image=image.name, entries=len(rows)))
                finally: command(['umount', mount], 'regression-unmount')
        command([PACKAGE/'manager', 'restore', library, carrier/'page_mappings.txt'], 'restore', PACKAGE)
        registered = False
        assert library.read_bytes() == before
        result['restored'] = True; write()
        result['native_negative'] = native(PACKAGE/'case/negative.squashfs', True)
        assert mode == 'fixed', 'old native path unexpectedly survived; inspect before accepting'
        result.update(status='complete', stage='complete')
    except BaseException:
        result.update(status='failed', error=traceback.format_exc()); raise
    finally:
        try:
            if registered: command([PACKAGE/'manager', 'restore', library, carrier/'page_mappings.txt'], 'cleanup-restore', PACKAGE)
            for name in reversed(loaded): command(['rmmod', name], 'unload-'+name)
            result['modules_unloaded'] = True
        finally: write()


if __name__ == '__main__': main()
