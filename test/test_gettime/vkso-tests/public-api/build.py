#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Build direct-link user tools in a NEW build-all staging package.
Never executes a carrier or benchmark, installs a kernel, or edits boot state.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FLAGS = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fno-lto',
         '-fno-omit-frame-pointer', '-Wl,-z,now']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

def build(package, cc):
    package = Path(package).resolve()
    if '.building-' not in package.name:
        raise ValueError('only a new build-all .building-* package is accepted')
    run(['sha256sum', '-c', 'SHA256SUMS'], cwd=package)
    carrier = package / 'libkernel.so'
    symbols = run(['readelf', '-Ws', carrier]).stdout
    if 'vkso_fixture_marker' in symbols:
        raise ValueError('test fixture is not a kernel carrier')
    required = ['__vkso_clock_gettime', '__vkso_clock_getres', '__vkso_gettimeofday',
                '__vkso_time', '__vkso_getcpu', '__vkso_bind_context', '__vkso_shared_data']
    for symbol in required:
        if symbol not in symbols:
            raise ValueError(f'carrier export missing: {symbol}')
    output = package / 'public-api'
    output.mkdir()  # refuse to overwrite or silently reuse old executables
    commands = []
    common = [cc, *FLAGS, '-I' + str(HERE), '-I' + str(HERE.parent / 'functional')]
    commands.append([*common, HERE / 'public_time_bench.c', '-o', output / 'raw-public-bench'])
    commands.append([*common, '-DVKSO_BACKEND', HERE / 'public_time_bench.c',
                     HERE.parent / 'functional/vkso_user_wrapper.c',
                     '-L' + str(package), '-Wl,--no-as-needed', '-lkernel',
                     '-Wl,-rpath,$ORIGIN/..', '-o', output / 'vkso-public-bench'])
    for command in commands:
        result = run(command)
        with (output / 'build.log').open('a') as log:
            log.write(json.dumps([str(a) for a in command]) + '\n')
            log.write(result.stdout + result.stderr)
    for kind in ('raw', 'vkso'):
        binary = output / f'{kind}-public-bench'
        dynamic = run(['readelf', '-dW', binary]).stdout
        (output / f'{kind}.dynamic.txt').write_text(dynamic)
        (output / f'{kind}.disassembly.txt').write_text(run(['objdump', '-drwC', binary]).stdout)
        has_carrier = 'Shared library: [libkernel.so]' in dynamic
        if has_carrier != (kind == 'vkso') or 'adapter.so' in dynamic:
            raise ValueError(f'incorrect DT_NEEDED in {binary}')
        undefined = run(['nm', '-u', binary]).stdout
        if 'dlsym' in undefined or 'dlopen' in undefined:
            raise ValueError('runtime provider resolver found in public executable')
        if kind == 'raw' and '__vkso_' in undefined:
            raise ValueError('native executable depends on VKSO symbols')
    # Archive source inputs, not just their hashes.
    sdk = output / 'source'
    sdk.mkdir()
    for name in ('vkso_time.h', 'public_time_bench.c', 'collect.py', 'build.py', 'README.md'):
        shutil.copy2(HERE / name, sdk / name)
    for name in ('vkso_abi.h', 'vkso_user_wrapper.h', 'vkso_user_wrapper.c'):
        shutil.copy2(HERE.parent / 'functional' / name, sdk / name)
    shutil.copy2(HERE / 'collect.py', output / 'collect.py')
    meta = {
        'protocol': 'public-direct-v1', 'api_count': 17,
        'cc': cc, 'cc_version': run([cc, '--version']).stdout.splitlines()[0],
        'flags': FLAGS, 'libc_version': run(['getconf', 'GNU_LIBC_VERSION']).stdout.strip(),
        'carrier_sha256': sha(carrier),
        'runtime_validation': 'NOT_RUN',
        'paths': {'raw': 'native-libc', 'vkso': 'vkso-direct'},
        'sources': {p.name: sha(p) for p in sorted(sdk.iterdir())},
    }
    (output / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
    # The original manifest remains a legacy-probe description. The new
    # measurement protocol has its own manifest and is required by collection.
    checksum_file = package / 'SHA256SUMS'
    old_names = []
    for line in checksum_file.read_text().splitlines():
        _, name = line.split(None, 1)
        old_names.append(name.lstrip('*'))
    names = sorted(set(old_names) | {str(p.relative_to(package))
                   for p in output.rglob('*') if p.is_file()})
    checksum_file.write_text(''.join(f'{sha(package / n)}  {n}\n' for n in names))
    run(['sha256sum', '-c', 'SHA256SUMS'], cwd=package)
    return meta

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--cc', default=os.environ.get('CC', 'gcc'))
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.package, args.cc), indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'public build failed: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        sys.exit(1)
