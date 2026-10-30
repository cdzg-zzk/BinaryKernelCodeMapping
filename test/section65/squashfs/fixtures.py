#!/usr/bin/env python3
"""Make compressed read-path fixtures for the prepared SquashFS consumer."""
import argparse
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE.parent / 'build/squashfs/fixtures')
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = out / 'source'
    root.mkdir()
    (root / 'empty').write_bytes(b'')
    (root / 'pattern').write_bytes(bytes(range(256)) * 17003)
    (root / 'random').write_bytes(random.Random(20261029).randbytes((2 << 20) + 123))
    (root / 'tail').write_bytes(b'SquashFS fragment contents\n' * 3)
    with (root / 'sparse').open('wb') as stream:
        stream.write(b'begin\n')
        stream.seek((3 << 20) + 27)
        stream.write(b'end\n')
    os.link(root / 'pattern', root / 'hardlink')
    (root / 'symlink').symlink_to('pattern')
    (root / 'dangling').symlink_to('absent')
    os.mkfifo(root / 'fifo')
    os.setxattr(root / 'pattern', 'user.vkso_fixture', b'metadata retained')
    (root / 'directory').mkdir()
    for i in range(400):
        (root / 'directory' / (f'{i:04d}-' + 'name' * 35)).write_bytes(f'entry {i}\n'.encode())
    (root / 'directory' / ('中' * 70)).write_text('unicode\n')
    shutil.copy2('/bin/busybox', root / 'busybox')
    records = []
    for compressor in ('gzip', 'xz', 'zstd', 'lz4', 'lzo'):
        image = out / (compressor + '.squashfs')
        command = ['mksquashfs', str(root), str(image), '-noappend', '-processors', '1',
                   '-comp', compressor, '-b', '131072', '-always-use-fragments',
                   '-force-uid', '123', '-force-gid', '456', '-all-time', '1700000000',
                   '-mkfs-time', '1700000000', '-no-progress']
        with (out / (compressor + '.log')).open('w') as stream:
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)
        records.append(dict(image=image.name, compressor=compressor, bytes=image.stat().st_size, command=command))
    (out / 'fixtures.json').write_text(json.dumps(dict(status='built', cases=records,
        coverage=['compressed/uncompressed data', 'metadata spanning blocks', 'fragments',
                  'sparse blocks', 'hardlink', 'symlink', 'long directory index', 'xattr', 'uid/gid', 'FIFO']), indent=2) + '\n')
    print(json.dumps(dict(output=str(out), images=len(records))))


if __name__ == '__main__': main()
