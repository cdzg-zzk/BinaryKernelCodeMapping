#!/usr/bin/env python3
"""Package and run the prepared native SquashFS module in a disposable guest."""
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--build', type=Path, default=SECTION / 'build/squashfs/adapted')
    p.add_argument('--fixtures', type=Path, default=SECTION / 'build/squashfs/fixtures')
    p.add_argument('--kernel', type=Path, default=Path('/boot/vkso-final-raw-normal-5.15.198.bzImage'))
    p.add_argument('--export', action='store_true', help='also register and verify actual kernel-shared user pages')
    args = p.parse_args()
    out = args.output.resolve()
    assert not out.exists(), out
    package = out.parent / (out.name + '-package')
    package.mkdir(parents=True, exist_ok=False)
    assert json.loads((args.build / 'build.json').read_text())['common_undefined_symbols'] == ['sq_support']
    for name in ['vkso_sq_core.ko', 'vkso_squashfs.ko', 'adaptation.json', 'kernel.patch', 'build.json']:
        shutil.copy2(args.build / name, package / name)
    shutil.copy2(SECTION / 'reference_guest.py', package / 'reference_guest.py')
    shutil.copy2(HERE / 'kernel_guest.py', package / 'kernel_guest.py')
    (package / 'images').mkdir()
    for image in args.fixtures.glob('*.squashfs'):
        shutil.copy2(image, package / 'images' / image.name)
    entry='kernel_guest.py'
    if args.export:
        base=ROOT/'test/evaluation-local/packages/iso9660-native-optimized-20261029'
        for name in ['krg','manager','vmlinux']:
            shutil.copy2(base/name,package/name)
        shutil.copy2(ROOT/'make_dll/build_PIC_so.py',package/'build_PIC_so.py')
        for name in ['vkso_kernel_reader.ko','page_cache_replace.ko']:
            shutil.copy2(base/'modules'/name,package/name)
        for name in ['symbols.txt','shim.txt','libsq-bridge.so','vkso-squashfuse','user-build.json']:
            shutil.copy2(args.build/name,package/name)
        for name in ['export_guest.py','check_fuse.py']:
            shutil.copy2(HERE/name,package/name)
        (package/'reference').mkdir()
        reference=ROOT/'test/evaluation-local/runs/iso9660/squash-native-guest-03/evidence'
        for p in reference.glob('*-squashfs.json'):
            shutil.copy2(p,package/'reference'/p.name)
        for name in ['libsq-bridge.so','vkso-squashfuse']:
            deps=subprocess.check_output(['ldd',str(package/name)],text=True)
            for library in re.findall(r'=> (/\S+)',deps):
                shutil.copy2(library,package/Path(library).name)
        shutil.copytree(base/'bin',package/'bin')
        for path in base.glob('lib*.so.*'):
            if not (package/path.name).exists():shutil.copy2(path,package/path.name)
        entry='export_guest.py'
    (package / 'run.sh').write_text('#!/bin/bash\nset -eu\ncd /work/package\nexport LD_LIBRARY_PATH=/work/package\nexport PATH=/work/package/bin:$PATH\nexec python3 -u '+entry+'\n')
    subprocess.run(['python3', str(SECTION / 'native/qemu.py'), '--package', str(package),
                    '--output', str(out), '--kernel', str(args.kernel), '--native-ide', '--timeout', '1200'], check=True)


if __name__ == '__main__': main()
