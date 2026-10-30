#!/usr/bin/env python3
"""Build small format-coverage images; the published Alpine image is separate."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'


def pattern(n, seed):
    return bytes((i * 17 + seed) % 251 for i in range(n))


def main():
    images = BUILD / 'images'
    images.mkdir(parents=True, exist_ok=True)
    tree = BUILD / 'fixture-tree'
    tree.mkdir(exist_ok=True)
    (tree / 'empty').write_bytes(b'')
    (tree / 'message.txt').write_text('ISO9660 complete image access\n')
    (tree / 'cross-block.bin').write_bytes(pattern(65537, 3))
    (tree / 'nested').mkdir(exist_ok=True)
    (tree / 'nested' / '中文-Καλημέρα.txt').write_text('Unicode and Joliet\n')
    (tree / ('long-' + 'a' * 170 + '.txt')).write_text('Rock Ridge continuation name\n')
    deep = tree
    for i in range(10):
        deep /= f'level-{i:02}'
        deep.mkdir(exist_ok=True)
    (deep / 'leaf.txt').write_text('Rock Ridge relocated directory\n')
    for name, target in [('relative-link', 'nested/../message.txt'),
                         ('long-link', './' * 100 + 'message.txt')]:
        link = tree / name
        if not link.is_symlink():
            link.symlink_to(target)
    maker = BUILD / 'tools/usr/bin/genisoimage'
    cases = []
    for name, flags in [('rock-ridge', ['-R']), ('joliet', ['-J', '-joliet-long']),
                        ('mixed', ['-R', '-J', '-joliet-long'])]:
        command = [str(maker), '-quiet', '-input-charset', 'utf-8', '-iso-level', '3',
                   *flags, '-o', str(images / (name + '.iso')), str(tree)]
        result = subprocess.run(command, capture_output=True, text=True)
        (images / (name + '.build.log')).write_text(result.stdout + result.stderr)
        result.check_returncode()
        cases.append(dict(name=name, image=name + '.iso', command=command))
    plain = BUILD / 'multi-tree'
    plain.mkdir(exist_ok=True)
    first, second = pattern(6144, 41), pattern(8193, 97)
    for name, data in [('MULTI.BIN', first), ('NOGAP.BIN', pattern(2048, 22)),
                       ('OTHER.BIN', second)]:
        (plain / name).write_bytes(data)
    multi_path = images / 'multi-extent.iso'
    subprocess.run([str(maker), '-quiet', '-iso-level', '3', '-o', str(multi_path),
                    str(plain)], check=True)
    image = bytearray(multi_path.read_bytes())
    pvd = 16 * 2048
    root_block = int.from_bytes(image[pvd+158:pvd+162], 'little')
    root_size = int.from_bytes(image[pvd+166:pvd+170], 'little')
    entries = {}
    off = root_block * 2048
    end = off + root_size
    while off < end:
        size = image[off]
        if not size:
            off = (off // 2048 + 1) * 2048
            continue
        name = bytes(image[off+33:off+33+image[off+32]])
        entries[name] = (off, bytes(image[off:off+size]))
        off += size
    first_off, first_rec = entries[b'MULTI.BIN;1']
    gap_off, gap_rec = entries[b'NOGAP.BIN;1']
    second_off, second_rec = entries[b'OTHER.BIN;1']
    assert gap_off == first_off + len(first_rec)
    assert len(gap_rec) == len(second_rec) == len(first_rec)
    image[first_off+25] |= 0x80
    second_rec = bytearray(second_rec)
    second_rec[33:44] = b'MULTI.BIN;1'
    image[gap_off:gap_off+len(gap_rec)] = second_rec
    image[second_off:second_off+len(gap_rec)] = gap_rec
    multi_path.write_bytes(image)
    cases.append(dict(name='multi-extent', image=multi_path.name,
                      description='Two consecutive directory records; noncontiguous file extents',
                      expected_file='multi.bin', expected_size=len(first + second),
                      expected_sha256=hashlib.sha256(first + second).hexdigest()))
    (images / 'fixtures.json').write_text(json.dumps({'cases': cases}, indent=2) + '\n')
    print(json.dumps({'fixtures': [c['name'] for c in cases]}))


if __name__ == '__main__':
    main()
