#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Build the direct-API portion of a new coherent kernel package; never run kernel code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROTOCOL = 'clocktime-direct-api-v2'
FUNCTIONAL_BLOBS = {
    'vkso_abi.h': '85fb8caa676e019e1dca7763d14bc5d595961097',
    'vkso_user_wrapper.c': '6a4c2148371fd07529f13ed27e6d3f0573f0c2d6',
    'vkso_user_wrapper.h': 'f96e83a43ab85e2b88b7ba238ffe02536289998c',
}
REQUIRED = {'boot-manifest.txt', 'raw-bzImage', 'vkso-bzImage', 'raw.config',
            'vkso.config', 'libkernel.so', 'page_mappings.txt', 'manager',
            'page_cache_replace.ko', 'vkso_m09_clock.ko', 'raw-abi-matrix',
            'vkso-abi-matrix', 'owner_descriptors.txt', 'kernel_identity.txt', 'raw-kernel-reader.ko', 'vkso-kernel-reader.ko'}
CFLAGS = '-O2 -g -std=gnu11 -Wall -Wextra -Werror -fno-lto -fno-builtin -fPIC'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def kv_file(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep:
            if key in values:
                raise ValueError('duplicate manifest key: ' + key)
            values[key] = value
    return values


def checked_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('unsafe manifest path: ' + relative)
    result = root / path
    # Manifest payloads are regular files inside the package, not escaping links.
    if result.is_symlink() or root not in result.resolve().parents:
        raise ValueError('manifest path escapes package: ' + relative)
    return result


def verify_sums(root, required=()):
    root = Path(root).resolve()
    entries = {}
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64}) [ *](.+)', line)
        if not match:
            raise ValueError('invalid SHA256SUMS record')
        expected, name = match.groups()
        if name in entries:
            raise ValueError('duplicate checksum path: ' + name)
        path = checked_path(root, name)
        if not path.is_file() or sha256(path) != expected:
            raise ValueError('checksum mismatch: ' + str(path))
        entries[name] = expected
    if not entries or not set(required).issubset(entries):
        raise ValueError('missing required checksums: ' + ', '.join(sorted(set(required) - entries.keys())))
    return entries


def write_json(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def audit_binary(binary, backend):
    dynamic = subprocess.check_output(['readelf', '-dW', str(binary)], text=True)
    undefined = subprocess.check_output(['nm', '-u', str(binary)], text=True)
    disassembly = subprocess.check_output(['objdump', '-d', str(binary)], text=True)
    needs = re.findall(r'\(NEEDED\).*\[(.+?)\]', dynamic)
    if any('adapter' in name for name in needs) or re.search(r'\b(?:dlopen|dlsym|dlvsym)(?:@|\s|$)', undefined):
        raise ValueError('unexpected dynamic provider resolver/adapter')
    if backend == 'vkso':
        if 'libvkso_time.so' not in needs:
            raise ValueError('VKSO executable does not DT_NEEDED libvkso_time.so')
        prefix = ''
    else:
        if 'libkernel.so' in needs or '__vkso_' in undefined:
            raise ValueError('native executable depends on VKSO')
        prefix = ''
    for symbol in ('clock_gettime', 'clock_getres', 'gettimeofday', 'time', 'getcpu'):
        if not re.search(r'\b' + prefix + symbol + r'(?:@|\s|$)', undefined):
            raise ValueError('missing direct undefined entry: ' + prefix + symbol)
        if not re.search(r'call[^\n]*<' + prefix + symbol + r'@plt>', disassembly):
            raise ValueError('expected direct PLT call not found: ' + prefix + symbol)
    return dynamic, undefined, disassembly


def audit_public_library(library):
    undefined = subprocess.check_output(['nm', '-u', str(library)], text=True)
    dynamic = subprocess.check_output(['readelf', '-dW', str(library)], text=True)
    assembly = subprocess.check_output(['objdump', '-d', str(library)], text=True)
    if '[libkernel.so]' not in dynamic or any(x in undefined for x in ('dlopen', 'dlsym', 'dlvsym')):
        raise ValueError('public API must directly depend on the carrier without dynamic lookup')
    for name in ('clock_gettime', 'clock_getres', 'gettimeofday', 'time', 'getcpu'):
        if not re.search(r'(?:call|jmp)[^\n]*<__vkso_' + name + r'@plt>', assembly):
            raise ValueError('missing direct carrier call: ' + name)
        if re.search(r'\b' + name + r'(?:@|\s|$)', undefined):
            raise ValueError('recursive public API fallback: ' + name)
    return dynamic, undefined, assembly


def build(package, out, compiler):
    package = package.resolve()
    package_sums = verify_sums(package, REQUIRED)
    original = kv_file(package / 'boot-manifest.txt')
    if original.get('build_variant') not in ('normal', 'no-retpoline'):
        raise ValueError('unknown package mitigation variant')
    if original.get('update_bench') != '0' or original.get('vkso_validation_tests') != '0':
        raise ValueError('this public-READ workflow requires non-instrumented production images')
    if original.get('cc_version') != '11.4.0':
        raise ValueError('expected paper kernel toolchain GCC 11.4.0; do not silently mix builds')
    compiler = shutil.which(compiler)
    if not compiler or any(c.isspace() for c in compiler):
        raise ValueError('compiler must be an executable path without whitespace')
    version = subprocess.check_output([compiler, '-dumpfullversion', '-dumpversion'], text=True).strip()
    if version != original['cc_version']:
        raise ValueError('direct API compiler must match package: expected ' + original['cc_version'] + ', got ' + version)
    here = Path(__file__).resolve().parent
    for name, expected in FUNCTIONAL_BLOBS.items():
        data = (here.parent / 'functional' / name).read_bytes()
        if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != expected:
            raise ValueError('review changed functional ABI/initializer before building: ' + name)
    out = out.resolve()
    if out == here or here in out.parents:
        raise ValueError('output must be outside the source directory')
    carrier_symbols = subprocess.check_output(['nm', '-D', '--defined-only', str(package / 'libkernel.so')], text=True)
    if 'vkso_test_only_mock_carrier' in carrier_symbols:
        raise ValueError('test-only mock carrier cannot be a target artifact')
    out.mkdir(parents=True, exist_ok=False)
    try:
        (out / 'src' / 'functional').mkdir(parents=True)
        for name in FUNCTIONAL_BLOBS:
            shutil.copy2(here.parent / 'functional' / name, out / 'src' / 'functional' / name)
        shutil.copytree(here, out / 'src' / 'direct-api', ignore=shutil.ignore_patterns('__pycache__', 'build', '*.pyc'))
        (out / 'carrier').mkdir()
        (out / 'carrier' / 'libkernel.so').symlink_to('../../libkernel.so')
        # Explicit flags, no inherited preload, linker search path, or Make overrides.
        env = dict(os.environ)
        for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT', 'MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES',
                    'CPPFLAGS', 'CFLAGS', 'LDFLAGS', 'CXXFLAGS'):
            env.pop(key, None)
        flags = CFLAGS + ' -ffile-prefix-map=' + str(out) + '=/vkso-direct'
        command = ['make', '-C', str(out / 'src' / 'direct-api'), 'native', 'vkso',
                   'OUT=' + str(out), 'CC=' + compiler, 'CFLAGS=' + flags]
        with (out / 'build.log').open('x') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        audit_public_library(out / 'libvkso_time.so')
        for backend in ('native', 'vkso'):
            outputs = audit_binary(out / (backend + '-bench'), backend)
            for suffix, content in zip(('dynamic.txt', 'undefined.txt', 'disassembly.txt'), outputs):
                (out / (backend + '-' + suffix)).write_text(content)
        source_hashes = {str(p.relative_to(out / 'src')): sha256(p)
                         for p in sorted((out / 'src').rglob('*'))
                         if p.is_file() and p.suffix in ('.c', '.h', '.py')}
        source_hashes['direct-api/Makefile'] = sha256(out / 'src/direct-api/Makefile')
        source_fingerprint = hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()
        manifest = {
            'protocol': PROTOCOL,
            'source_git_commit': subprocess.check_output(['git', '-C', str(here), 'rev-parse', 'HEAD'], text=True).strip(),
            'source_dirty_patch_sha256': hashlib.sha256(subprocess.check_output(
                ['git', '-C', str(here), 'diff', '--binary', '--no-ext-diff', 'HEAD', '--'])).hexdigest(),
            'build_variant': original['build_variant'], 'package': '..',
            'kernel_checksums': package_sums,
            'package_manifest_sha256': package_sums['boot-manifest.txt'],
            'carrier_sha256': package_sums['libkernel.so'],
            'compiler': compiler, 'compiler_version': version, 'cflags': flags, 'base_cflags': CFLAGS,
            'source_fingerprint': source_fingerprint, 'source_hashes': source_hashes,
            'kernel_package_commit': original.get('git_commit'),
            'kernel_candidate_patch_sha256': original.get('candidate_patch_sha256'),
            'runtime_tests': 'NOT_RUN', 'kernel_build': 'BUILT_WITH_PACKAGE',
            'redis': 'NOT_INCLUDED', 'registration': 'external; same carrier inode required',
        }
        write_json(out / 'build.json', manifest)
        files = sorted(p for p in out.rglob('*') if p.is_file() and not p.is_symlink())
        with (out / 'SHA256SUMS').open('x') as stream:
            for path in files:
                stream.write(sha256(path) + '  ' + str(path.relative_to(out)) + '\n')
        print(str(out))
    except Exception as exc:
        write_json(out / 'FAILED.json', {'status': 'FAIL', 'error': str(exc)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cc', default='gcc')
    args = parser.parse_args()
    try:
        if args.out.resolve() != args.package.resolve() / 'direct':
            raise ValueError('direct API must be built inside the coherent package at PACKAGE/direct')
        build(args.package, args.out, args.cc)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('BUILD FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
