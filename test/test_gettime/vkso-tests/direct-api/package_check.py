#!/usr/bin/env python3
"""Verify coherent v2 packages; legacy sidecars/packages must be rebuilt."""
import json
import os
from pathlib import Path
import sys
from bundle import PROTOCOL, REQUIRED, verify_sums, sha256, kv_file, audit_binary, audit_public_library


def check(package):
    package = Path(package).resolve()
    sums = verify_sums(package, REQUIRED | {'direct/build.json', 'direct/SHA256SUMS',
        'direct/native-bench', 'direct/vkso-bench', 'direct/libvkso_time.so'})
    direct = package / 'direct'
    verify_sums(direct, {'build.json', 'native-bench', 'vkso-bench', 'libvkso_time.so'})
    build = json.loads((direct / 'build.json').read_text())
    manifest = kv_file(package / 'boot-manifest.txt')
    if build['protocol'] != PROTOCOL or build['build_variant'] != manifest['build_variant']:
        raise ValueError('protocol/build variant mismatch: rebuild package')
    if build['package'] != '..' or not os.path.samefile(direct / 'carrier/libkernel.so', package / 'libkernel.so'):
        raise ValueError('carrier link must resolve to registered package inode')
    for name, digest in build['kernel_checksums'].items():
        if sums.get(name) != digest:
            raise ValueError('kernel-to-benchmark identity mismatch: ' + name)
    if build['carrier_sha256'] != sums['libkernel.so'] or build['package_manifest_sha256'] != sums['boot-manifest.txt']:
        raise ValueError('carrier/manifest identity mismatch')
    for name, digest in build['source_hashes'].items():
        if sha256(direct / 'src' / name) != digest:
            raise ValueError('source identity mismatch: ' + name)
    audit_public_library(direct / 'libvkso_time.so')
    for name in ('native', 'vkso'):
        audit_binary(direct / (name + '-bench'), name)
    return build


def main():
    try:
        builds = [check(p) for p in sys.argv[1:]]
        if len(builds) != 2:
            raise ValueError('supply normal and no-retpoline packages')
        for key in ('protocol', 'source_fingerprint', 'compiler_version', 'base_cflags'):
            if builds[0][key] != builds[1][key]:
                raise ValueError('cross-variant direct API mismatch: ' + key)
        for name in ('native-bench', 'vkso-bench', 'libvkso_time.so'):
            if sha256(Path(sys.argv[1]) / 'direct' / name) != sha256(Path(sys.argv[2]) / 'direct' / name):
                raise ValueError('user API binary differs across mitigation variants: ' + name)
        print('direct_api_package_validation=PASS')
    except (OSError, ValueError, KeyError) as exc:
        sys.exit('package refused: ' + str(exc))


if __name__ == '__main__':
    main()
