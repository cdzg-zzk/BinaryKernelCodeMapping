#!/usr/bin/env python3
"""Snapshot the investigated isofs sources and build an unmodified driver."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = ('inode.c', 'namei.c', 'dir.c', 'util.c', 'rock.c', 'export.c',
         'joliet.c', 'compress.c', 'isofs.h', 'rock.h', 'zisofs.h', 'Kconfig', 'Makefile')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--linux', type=Path,
                   default=Path('/usr/src/linux-source-5.15.0/linux-source-5.15.0'))
    p.add_argument('--kdir', type=Path,
                   default=Path('/usr/src/linux-headers-5.15.0-119-generic'))
    args = p.parse_args()
    upstream = HERE / 'upstream'
    upstream.mkdir(exist_ok=True)
    records = []
    for name in FILES:
        src, dst = args.linux / 'fs/isofs' / name, upstream / name
        data = src.read_bytes()
        if dst.exists() and dst.read_bytes() != data:
            raise RuntimeError(f'refusing to replace a different source snapshot: {dst}')
        dst.write_bytes(data)
        records.append(dict(path=name, bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest()))
    nls_source = args.linux / 'fs/nls/nls_base.c'
    nls_data = nls_source.read_bytes()
    nls_target = upstream / 'nls_base.c'
    if nls_target.exists() and nls_target.read_bytes() != nls_data:
        raise RuntimeError('different Unicode helper snapshot')
    nls_target.write_bytes(nls_data)
    records.append(dict(path='nls_base.c',source_path='fs/nls/nls_base.c',bytes=len(nls_data),
                        sha256=hashlib.sha256(nls_data).hexdigest()))
    (upstream / 'provenance.json').write_text(json.dumps({
        'source': str(args.linux), 'component': 'fs/isofs',
        'linux_makefile_version': (args.linux / 'Makefile').read_text().splitlines()[:6],
        'description': 'Unmodified local Linux source snapshot; license notices retained',
        'files': records}, indent=2) + '\n')
    build = HERE / 'build/raw'
    build.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if name != 'Makefile':
            shutil.copy2(upstream / name, build / name)
    (build / 'Makefile').write_text('''obj-m += isofs_probe.o
isofs_probe-y := namei.o inode.o dir.o util.o rock.o export.o joliet.o compress.o
''')
    command = ['make', '-C', str(args.kdir.resolve()), f'M={build}', '-j2', 'modules']
    with (build / 'build.log').open('w') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    (build / 'build.json').write_text(json.dumps({
        'command': command, 'returncode': result.returncode,
        'kernel_release': (args.kdir / 'include/config/kernel.release').read_text().strip(),
        'source_version': '5.15.198',
        'note': 'Source version and guest ABI version are recorded separately; no host module load'
    }, indent=2) + '\n')
    print(json.dumps({'returncode': result.returncode, 'log': str(build / 'build.log')}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
