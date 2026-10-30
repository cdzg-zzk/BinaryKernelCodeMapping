#!/usr/bin/env python3
"""Reconstruct the pinned LKL tree from the official base tar and fork diff.

The GitHub diff omits binary additions. Fetch those by pinned raw URL, then
verify the complete source tree against the commit's Git tree before building.
Inputs downloaded under build/lkl are retained as provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import time
import urllib.request

BUILD = Path(__file__).resolve().parents[1] / 'build/lkl'
COMMIT = 'd0f76a77e8c2ca68bd7d96190b8da09040eab072'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--omit-unused-binaries', action='store_true',
                        help='omit foreign tool binaries and fuzz seeds; verify their tree entries from API metadata')
    args = parser.parse_args()
    source = BUILD / 'linux-6.12'
    if not source.exists():
        with tarfile.open(BUILD / 'linux-6.12.tar.xz') as archive:
            archive.extractall(BUILD)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    git('init', '-q')
    chunks = (BUILD / 'from-v6.12.diff').read_text().split('diff --git ')[1:]
    binaries = []
    for chunk in chunks:
        if 'Binary files ' not in chunk:
            continue
        path = chunk.splitlines()[0].split(' b/', 1)[1]
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        mode = int(re.search(r'^new file mode (\d+)$', chunk, re.M)[1], 8)
        blob = re.search(r'^index [0-9a-f]+\.\.([0-9a-f]+)$', chunk, re.M)[1]
        binaries.append((path, mode, blob))
    marker = BUILD / 'text-patch-applied'
    if not marker.exists():
        excludes = ['--exclude=' + path for path, _, _ in binaries]
        git('apply', '--check', *excludes, '../from-v6.12.diff')
        git('apply', *excludes, '../from-v6.12.diff')
        marker.touch()
    missing = []
    metadata = {}
    if args.omit_unused_binaries:
        for name in ('binary-tools', 'fuzz-seeds'):
            metadata.update({r['path']: r for r in json.loads((BUILD / (name + '.json')).read_text())})
    for name, mode, blob in binaries:
        path = source / name
        def matches(data):
            value = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            return value.startswith(blob)
        if not path.exists() or not matches(path.read_bytes()):
            if args.omit_unused_binaries:
                assert name.startswith(('tools/lkl/bin/', 'tools/lkl/fuzzers/hid/seeds/'))
                expected_blob = metadata[name]['sha']
                assert expected_blob.startswith(blob)
                missing.append(dict(path=name, mode=mode, blob=expected_blob))
                continue
            url = f'https://raw.githubusercontent.com/lkl/linux/{COMMIT}/{name}'
            request = urllib.request.Request(url, headers={'User-Agent': 'ISO9660-research'})
            data = urllib.request.urlopen(request, timeout=60).read()
            assert matches(data), name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            time.sleep(1)
        path.chmod(mode & 0o777)
        print('binary source', name, path.stat().st_size, flush=True)
    git('add', '-f', '--all')
    for row in missing:
        git('update-index', '--add', '--cacheinfo', f"{row['mode']:o},{row['blob']},{row['path']}")
    actual = git('write-tree', '--missing-ok')
    expected = json.loads((BUILD / 'lkl-commit.json').read_text())['commit']['tree']['sha']
    assert actual == expected, (actual, expected)
    record = dict(status='source verified', commit=COMMIT, tree=actual,
        method='official Linux 6.12 tarball plus official fork diff; all present source contents and modes verified by matching the pinned Git tree, using API tree entries for explicitly absent unused binaries',
        omitted_unused_binaries=missing,
        base_url='https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.tar.xz',
        diff_url=f'https://github.com/lkl/linux/compare/torvalds:v6.12...{COMMIT}.diff',
        directory=str(source), finished=time.time())
    (BUILD / 'acquisition-03.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
