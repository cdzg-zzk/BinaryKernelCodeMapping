#!/usr/bin/env python3
"""Wrap the unchanged BCH launcher with an isolated resource-observation guest."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepared', type=Path,
                        default=HERE / 'results/lz4-cli-qemu-20260912-attempt06')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    assert os.geteuid() != 0
    running = subprocess.run(['pgrep', '-x', 'qemu-system-x86'], capture_output=True, text=True)
    assert running.returncode == 1, 'another QEMU guest is active; serialize guests'
    output = args.output.resolve()
    assert not output.exists(), 'fresh output required'
    preparation = output.with_name(output.name + '-preparation')
    preparation.mkdir(parents=True, exist_ok=False)
    wrapper = preparation / 'wrapper'
    wrapper.mkdir()
    for source, name in [('bch_resource_guest.py', 'bch_guest.py'),
                         ('bch_qemu.py', 'bch_qemu.py'), ('lz4_guest.py', 'lz4_guest.py')]:
        shutil.copy2(HERE / source, wrapper / name)
    prepared = preparation / 'prepared'
    payload = prepared / 'payload'
    payload.mkdir(parents=True)
    original = args.prepared.resolve()
    for directory in ('repo', 'helpers'):
        shutil.copytree(original / 'payload' / directory, payload / directory)
    shutil.copy2(HERE / 'bch_guest.py', payload / 'helpers/bch_functional.py')
    (payload / 'vmlinux-5.15.0-119-generic').symlink_to(original / 'payload/vmlinux-5.15.0-119-generic')
    (prepared / 'initramfs.cpio.gz').symlink_to(original / 'initramfs.cpio.gz')
    shutil.copy2(__file__, preparation / 'bch_resource_qemu.py')
    (preparation / 'wrapper-identity.json').write_text(json.dumps({
        'original_launcher': str(HERE / 'bch_qemu.py'), 'prepared_original': str(original),
        'guest_wrapper_source': str(HERE / 'bch_resource_guest.py'),
        'functional_guest_source': str(HERE / 'bch_guest.py'), 'host_euid': os.geteuid(),
        'scope': 'new output/preparation only; unchanged owner, core, builder, shim and full correctness benchmark'}, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('original_bch_launcher', HERE / 'bch_qemu.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    launcher.HERE = wrapper
    sys.argv = [str(HERE / 'bch_qemu.py'), '--output', str(output),
                '--prepared', str(prepared), '--timeout', str(args.timeout)]
    result = launcher.main()
    resource = output / 'evidence/validation/bch_resources/result.json'
    assert resource.exists() and json.loads(resource.read_text())['status'] == 'pass', resource
    return result


if __name__ == '__main__':
    raise SystemExit(main())
