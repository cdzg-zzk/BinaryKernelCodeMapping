#!/usr/bin/env python3
"""Recreate the native kernel build privately; never install or reboot it."""
import json
import os
from pathlib import Path
import shutil
import subprocess

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]
OUT = SECTION / 'build/native'


def main():
    OUT.mkdir(exist_ok=True)
    source = OUT / 'linux-5.15.198'
    build = OUT / 'kernel'
    archive = ROOT / 'test/test_gettime/vkso-tests/baremetal/artifacts/source-cache/linux-5.15.198.tar.xz'
    if not source.exists():
        subprocess.run(['tar', '-xf', str(archive), '-C', str(OUT)], check=True)
    build.mkdir(exist_ok=True)
    config = Path('/boot/config-vkso-final-raw-normal-5.15.198')
    if not (build / '.config').exists():
        shutil.copy2(config, build / '.config')
    env = dict(os.environ, KBUILD_BUILD_TIMESTAMP='2026-09-23 13:31:29 UTC',
               KBUILD_BUILD_USER='vkso-research', KBUILD_BUILD_HOST='controlled-build',
               KBUILD_BUILD_VERSION='1')
    make = ['make', '-C', str(source), 'O=' + str(build), 'CC=gcc-11', '-j3']
    with (OUT / 'kernel-build.log').open('w') as log:
        for targets in [['olddefconfig'], ['vmlinux', 'modules_prepare']]:
            subprocess.run(make + targets, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    shutil.copy2(build / 'vmlinux.symvers', build / 'Module.symvers')
    def build_id(path):
        notes = subprocess.check_output(['readelf', '-n', str(path)], text=True)
        return next(l.split('Build ID: ')[1] for l in notes.splitlines() if 'Build ID: ' in l)
    record = dict(kernel_build=str(build), original_config=str(config),
                  config_equal=(build / '.config').read_bytes() == config.read_bytes(),
                  built_id=build_id(build / 'vmlinux'),
                  installed_id=build_id(OUT / 'running-vmlinux'), environment=env | {})
    # Record only the deliberately set build environment, not caller environment.
    record['environment'] = {k: env[k] for k in env if k.startswith('KBUILD_BUILD_')}
    record['build_id_equal'] = record['built_id'] == record['installed_id']
    (OUT / 'kernel-build.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
