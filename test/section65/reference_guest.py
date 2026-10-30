#!/usr/bin/env python3
"""Record full pathname, metadata, link and byte results from real kernel isofs."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import traceback

WORK = Path('/work')
OUT = WORK / 'evidence'


def run(command):
    p = subprocess.run(command, capture_output=True, text=True)
    with (OUT / 'commands.jsonl').open('a') as f:
        f.write(json.dumps(dict(argv=command, returncode=p.returncode,
                               stdout=p.stdout, stderr=p.stderr)) + '\n')
    p.check_returncode()


def manifest(root):
    rows = []
    def visit(path):
        for child in sorted(path.iterdir()):
            s = child.lstat()
            row = dict(path=str(child.relative_to(root)), mode=s.st_mode,
                       size=s.st_size, uid=s.st_uid, gid=s.st_gid,
                       nlink=s.st_nlink, mtime_ns=s.st_mtime_ns)
            if stat.S_ISREG(s.st_mode):
                digest = hashlib.sha256()
                with child.open('rb') as stream:
                    while data := stream.read(65536):
                        digest.update(data)
                row['sha256'] = digest.hexdigest()
            elif stat.S_ISLNK(s.st_mode):
                row['target'] = os.readlink(child)
            rows.append(row)
            if stat.S_ISDIR(s.st_mode):
                visit(child)
    visit(root)
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    result = dict(status='running', scope='kernel reference functionality; no timings',
                  kernel=os.uname().release, cases=[])
    try:
        config = json.loads((WORK / 'config.json').read_text())
        if config.get('dependency'): run(['insmod',str(WORK/config['dependency'])])
        run(['insmod', str(WORK / config['module'])])
        mountpoint = Path('/mnt/iso')
        mountpoint.mkdir(parents=True, exist_ok=True)
        for image in sorted((WORK / 'images').glob('*.iso')):
            options = [('default', 'ro,loop')]
            if image.stem == 'mixed':
                options.append(('norock', 'ro,loop,norock'))
            for mode, opts in options:
                run(['mount', '-t', config['fstype'], '-o', opts, str(image), str(mountpoint)])
                try:
                    rows = manifest(mountpoint)
                    name = image.stem + '-' + mode
                    (OUT / (name + '.json')).write_text(json.dumps(rows, ensure_ascii=False,
                                                                 indent=2) + '\n')
                    result['cases'].append(dict(image=image.name, mode=mode,
                                                entries=len(rows), manifest=name+'.json'))
                    print('kernel_reference_case=' + name + ' entries=' + str(len(rows)), flush=True)
                finally:
                    run(['umount', str(mountpoint)])
        run(['rmmod', Path(config['module']).stem])
        if config.get('dependency'): run(['rmmod',Path(config['dependency']).stem])
        result['status'] = 'complete'
    except Exception:
        result['status'] = 'failed'
        result['error'] = traceback.format_exc()
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
