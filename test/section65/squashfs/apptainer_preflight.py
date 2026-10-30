#!/usr/bin/env python3
"""Run GNU tar inside a real SIF using stock and kernel-core FUSE helpers.

This is an application integration check. It does not measure performance or
establish physical sharing: --core can select a separately registered carrier.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import traceback

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent


def executable(root, source):
    """Copy a host executable and its ELF dependencies at their original paths."""
    source = Path(source)
    paths = [source]
    dependencies = subprocess.run(['ldd', str(source)], capture_output=True, text=True)
    paths += [Path(p) for p in re.findall(r'(/[^\s()]+)', dependencies.stdout)]
    for path in paths:
        target = root / path.relative_to('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(path.stat().st_mode & 0o777)


def archive_manifest(path):
    rows = {}
    with tarfile.open(path) as archive:
        for member in archive:
            assert member.name not in rows, ('duplicate archive member', member.name)
            row = dict(type=member.type.decode(), size=member.size, mode=member.mode,
                       uid=member.uid, gid=member.gid, link=member.linkname)
            if member.isfile():
                row['sha256'] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            rows[member.name] = row
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--apptainer', type=Path,
                   default=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer')
    p.add_argument('--build', type=Path, default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--headers', type=Path, default=SECTION/'build/native/linux-5.15.198/include')
    p.add_argument('--core', default='-')
    p.add_argument('--bridge', type=Path)
    p.add_argument('--runtime', type=Path, default=SECTION/'build/squashfs/apptainer/runtime')
    p.add_argument('--image', type=Path, help='reuse an existing SIF image')
    p.add_argument('--hold-reader', action='store_true', help='wait for reader/release before running tar, for external PFN observation')
    p.add_argument('--translator', choices=['c','python'], default='c')
    args = p.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    app, build = args.apptainer.resolve(), args.build.resolve()
    env = dict(os.environ, APPTAINER_CACHEDIR=str(out/'cache'),
               APPTAINER_CONFIGDIR=str(out/'config'), APPTAINER_TMPDIR=str(out/'tmp'))
    env['LD_LIBRARY_PATH'] = str(args.runtime.resolve()/'usr/lib/x86_64-linux-gnu')
    if args.hold_reader:
        env['VKSO_SQ_STATE'] = '1'
    for directory in ['cache', 'config', 'tmp', 'rootfs', 'helper-bin']:
        (out/directory).mkdir()
    root = out/'rootfs'
    result = dict(status='running', scope='SIF application integration; no performance or PFN claim')

    def run(command, name):
        with (out/(name+'.log')).open('w') as log:
            subprocess.run(list(map(str, command)), env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=300)

    try:
        if args.image:
            sif = args.image.resolve()
        else:
            for directory in ['bin', 'usr/bin', 'etc', 'dev', 'proc', 'sys', 'tmp',
                              'var/tmp', 'work', 'root', 'home', 'opt']:
                (root/directory).mkdir(parents=True, exist_ok=True)
            shutil.copy2('/usr/bin/busybox', root/'bin/busybox')
            for name in subprocess.check_output(['/usr/bin/busybox', '--list'], text=True).splitlines():
                if name != 'busybox':
                    (root/'bin'/name).symlink_to('busybox')
            executable(root, '/usr/bin/tar')
            (root/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
            (root/'etc/group').write_text('root:x:0:\n')
            (root/'etc/os-release').write_text('ID=ubuntu\nVERSION_ID="22.04"\n')
            shutil.copytree(args.headers, root/'opt/linux-headers', symlinks=True)
            sif = out/'headers.sif'
            run([app, 'build', '--mksquashfs-args', '-comp gzip -processors 2', sif, root], 'build-sif')
        run([app, 'sif', 'list', sif], 'sif-partitions')
        helper = out/'helper-bin/squashfuse_ll'
        bridge = (args.bridge or build/'libsq-copy.so').resolve()
        translator = ([str(build/'vkso-squash-helper')] if args.translator=='c' else
                      [sys.executable,str(HERE/'apptainer_helper.py')])
        helper_command = translator+[
                          '--frontend', str(build/'vkso-squashfuse'), '--core', args.core,
                          '--bridge', str(bridge), '--trace', str(out/'helper.jsonl'), '--']
        helper.write_text('#!/bin/sh\nexec '+shlex.join(helper_command)+' "$@"\n')
        helper.chmod(0o755)
        config = out/'reader.conf'
        config.write_text((app.parent.parent/'etc/apptainer/apptainer.conf').read_text()+
                          '\nbinary path = '+str(helper.parent)+':$PATH:/usr/bin:/bin\n')
        records = {}
        for label, conf in [('stock', []), ('reader', ['--config', config])]:
            work = out/label; work.mkdir()
            application = ['/usr/bin/tar', '-cf', '/work/headers.tar', '-C', '/opt/linux-headers', '.']
            if label == 'reader' and args.hold_reader:
                application = ['/bin/sh', '-c',
                    'touch /work/ready; while [ ! -e /work/release ]; do sleep 0.05; done; exec '+shlex.join(application)]
            run([app, '--debug', *conf, 'exec', '--contain', '--cleanenv', '--no-home',
                 '--no-mount', 'cwd', '--pwd', '/work', '--bind', str(work)+':/work',
                 sif, *application], label)
            records[label] = archive_manifest(work/'headers.tar')
            (work/'manifest.json').write_text(json.dumps(records[label], indent=2)+'\n')
        assert records['stock'] == records['reader'], 'archive results differ'
        invocations = [json.loads(line) for line in (out/'helper.jsonl').read_text().splitlines()]
        assert invocations and all(row['offset'] > 0 for row in invocations)
        assert all(row['source'].startswith('/proc/self/fd/') for row in invocations)
        result.update(status='pass', entries=len(records['stock']), helper_invocations=invocations,
                      image=str(sif), apptainer_version=subprocess.check_output([app, '--version'], text=True).strip())
    except BaseException:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
