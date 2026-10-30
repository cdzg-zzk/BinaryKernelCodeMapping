#!/usr/bin/env python3
"""Compare the actual prepared native consumer with built-in SquashFS in TCG."""
import json
import os
from pathlib import Path
import subprocess
import traceback
from reference_guest import manifest

PACKAGE = Path('/work/package')
OUT = Path('/work/evidence')


def command(argv):
    p = subprocess.run(argv, capture_output=True, text=True)
    with (OUT / 'commands.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(argv=argv, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)) + '\n')
    p.check_returncode()


def main():
    OUT.mkdir(exist_ok=False)
    result = dict(status='running', scope='TCG native-consumer correctness only; no performance claim', cases=[])
    mount = Path('/mnt/squash-test')
    loaded = []
    try:
        mount.mkdir(parents=True, exist_ok=True)
        for module in ['vkso_sq_core', 'vkso_squashfs']:
            command(['insmod', str(PACKAGE / (module + '.ko'))])
            loaded.append(module)
        for image in sorted((PACKAGE / 'images').glob('*.squashfs')):
            reference = None
            for filesystem in ['squashfs', 'vksosquash']:
                command(['mount', '-t', filesystem, '-o', 'ro,loop', str(image), str(mount)])
                try:
                    rows = manifest(mount)
                    assert (mount / 'pattern').stat().st_ino == (mount / 'hardlink').stat().st_ino
                    assert os.getxattr(mount / 'pattern', 'user.vkso_fixture') == b'metadata retained'
                    assert all(r['uid'] == 123 and r['gid'] == 456 for r in rows)
                    if reference is None: reference = rows
                    else: assert rows == reference, (image.name, 'manifest differs')
                    name = f'{image.stem}-{filesystem}.json'
                    (OUT / name).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
                    result['cases'].append(dict(image=image.name, filesystem=filesystem, entries=len(rows), manifest=name))
                    print('squashfs_case=' + name, flush=True)
                finally:
                    command(['umount', str(mount)])
        result['status'] = 'complete'
    except Exception:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        try:
            for module in reversed(loaded): command(['rmmod', module])
            result['modules_unloaded'] = True
        except Exception:
            result.update(status='failed', cleanup_error=traceback.format_exc())
            raise
        finally:
            (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
