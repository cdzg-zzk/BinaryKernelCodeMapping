#!/usr/bin/env python3
"""Build the pinned lklfuse baseline without changing filesystem source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

SECTION = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('default', 'iso-only', 'squash-only'), required=True)
    parser.add_argument('--jobs', type=int, default=3)
    args = parser.parse_args()
    build = SECTION / 'build/lkl'
    provenance = json.loads((build / 'acquisition-03.json').read_text())
    assert provenance['status'] == 'source verified'
    source = Path(provenance['directory'])
    out = build / ('build-' + args.profile)
    out.mkdir(exist_ok=True)
    env = dict(os.environ, CPATH=str(SECTION / 'build/fuse-deps/usr/include'),
               LIBRARY_PATH=str(SECTION / 'build/fuse-deps/usr/lib/x86_64-linux-gnu'))
    record = dict(status='building', profile=args.profile, source=provenance,
                  output=str(out), commands=[], started=time.time())
    def write():
        (out / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    attempt = 1 + len(list(out.glob('build-*.log')))
    with (out / f'build-{attempt:02d}.log').open('w') as log:
        def run(argv):
            argv = list(map(str, argv))
            record['commands'].append(argv)
            write()
            subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        try:
            tools = ['make', '-C', source / 'tools/lkl', f'O={out}']
            kernel = ['make', '-C', source, f'O={out}', 'ARCH=lkl']
            run(tools + ['conf'])
            run(kernel + ['defconfig'])
            configure = [source / 'scripts/config', '--file', out / '.config',
                         '--enable', 'ISO9660_FS', '--enable', 'JOLIET', '--enable', 'ZISOFS',
                         '--set-str', 'NLS_DEFAULT', 'utf8']
            if args.profile == 'squash-only':
                for name in ['ISO9660_FS', 'JOLIET', 'ZISOFS']:
                    configure.extend(['--disable', name])
                for name in ['SQUASHFS', 'SQUASHFS_XATTR', 'SQUASHFS_ZLIB', 'SQUASHFS_LZ4',
                             'SQUASHFS_LZO', 'SQUASHFS_XZ', 'SQUASHFS_ZSTD']:
                    configure.extend(['--enable', name])
            if args.profile in ('iso-only', 'squash-only'):
                # The stock host library links socket syscall wrappers even in
                # lklfuse. Retain NET for that ABI; omit unused protocol stacks.
                disabled = ['INET', 'IPV6', 'NETDEVICES', 'NET_SCHED', 'PCI',
                            'EXT4_FS', 'XFS_FS', 'BTRFS_FS', 'FAT_FS', 'VFAT_FS',
                            'KALLSYMS', 'CRYPTO_ANSI_CPRNG']
                for line in (out / '.config').read_text().splitlines():
                    if line.startswith('CONFIG_NLS_') and line.endswith('=y'):
                        name = line.split('=', 1)[0].removeprefix('CONFIG_')
                        if name not in ('NLS_UTF8', 'NLS_ASCII', 'NLS_ISO8859_1'):
                            disabled.append(name)
                for name in disabled:
                    configure.extend(['--disable', name])
                record['disabled_from_default'] = disabled
                record['retained_network_abi'] = 'CONFIG_NET=y is required by socket wrappers linked in the unmodified host library'
            run(configure)
            run(kernel + ['olddefconfig', 'syncconfig'])
            config = (out / '.config').read_text()
            required = (('SQUASHFS', 'SQUASHFS_XATTR', 'SQUASHFS_ZLIB', 'SQUASHFS_LZ4',
                         'SQUASHFS_LZO', 'SQUASHFS_XZ', 'SQUASHFS_ZSTD', 'VIRTIO_BLK')
                        if args.profile == 'squash-only' else
                        ('ISO9660_FS', 'JOLIET', 'ZISOFS', 'VIRTIO_BLK'))
            for name in required:
                assert f'CONFIG_{name}=y' in config, name
            # Upstream appends /tools/lkl/ to an OUTPUT already ending in /.
            # Make target matching preserves that double slash.
            run(tools + [f'-j{args.jobs}', str(out) + '//tools/lkl/lklfuse'])
            record.update(status='built', binary=str(out / 'tools/lkl/lklfuse'), finished=time.time())
        except BaseException as error:
            record.update(status='failed', error=repr(error), finished=time.time())
            raise
        finally:
            write()
    print(json.dumps({k: record[k] for k in ('status', 'profile', 'binary')}))


if __name__ == '__main__':
    main()
