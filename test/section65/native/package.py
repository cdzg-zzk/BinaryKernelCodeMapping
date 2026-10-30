#!/usr/bin/env python3
"""Assemble a self-contained experiment package from already built artifacts."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--modules', type=Path, required=True)
    p.add_argument('--vmlinux', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--include-source', type=Path, default=SECTION / 'build/native/linux-5.15.198/include')
    p.add_argument('--no-archive', action='store_true')
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'modules').mkdir()
    modules = a.modules.resolve()
    for source in ('original/iso_original.ko', 'compat/iso_compat.ko', 'adapted/vkso_iso_core.ko',
                   'adapted/vkso_isofs.ko', 'registration/page_cache_replace.ko', 'reader/vkso_kernel_reader.ko'):
        shutil.copy2(modules / source, out / 'modules' / Path(source).name)
    for name in ('libiso-bridge.so', 'symbols.txt', 'shim.txt'):
        shutil.copy2(modules / 'adapted' / name, out / name)
    shutil.copy2(modules / 'vkso-isofuse', out / 'vkso-isofuse')
    shutil.copy2(modules / 'build.json', out / 'build.json')
    for source in (ROOT / 'kernel_cgd/src/krg', ROOT / 'page_cache_replace/manager',
                   ROOT / 'make_dll/build_PIC_so.py', SECTION / 'reference_guest.py'):
        shutil.copy2(source, out / source.name)
    for name in ('run.py', 'run.sh', 'README.md', 'Run-Iso9660.ps1'):
        source = SECTION / 'native' / name
        if source.exists():
            shutil.copy2(source, out / name)
    subprocess.run(['objcopy', '--strip-debug', str(a.vmlinux.resolve()), str(out / 'vmlinux')], check=True)
    notes = subprocess.check_output(['readelf', '-n', str(out / 'vmlinux')], text=True)
    build_id = next(l.split('Build ID: ')[1] for l in notes.splitlines() if 'Build ID: ' in l)
    reference = out / 'reference'
    reference.mkdir()
    for f in (ROOT / 'test/evaluation-local/runs/iso9660/reference-01/evidence').glob('*.json'):
        shutil.copy2(f, reference / f.name)
    images = out / 'images'
    images.mkdir()
    for f in (SECTION / 'build/images').iterdir():
        if f.suffix in ('.iso', '.json'):
            shutil.copy2(f, images / f.name)
    geniso = SECTION / 'build/tools/usr/bin/genisoimage'
    with (images / 'kernel-include-build.log').open('w') as stream:
        subprocess.run([str(geniso), '-R', '-J', '-quiet', '-V', 'LINUX515198', '-o',
                        str(images / 'kernel-include.iso'), str(a.include_source.resolve())],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    files = [f for f in a.include_source.rglob('*') if f.is_file()]
    write = lambda path, value: path.write_text(json.dumps(value, indent=2) + '\n')
    write(images / 'kernel-include-source.json', dict(source='unmodified Linux 5.15.198 include/ tree',
          files=len(files), bytes=sum(f.stat().st_size for f in files), command='genisoimage -R -J'))
    # The guest and native machine use the same GNU workload binaries, not BusyBox substitutes.
    (out / 'bin').mkdir()
    libraries = {Path('/usr/lib/x86_64-linux-gnu/libfuse3.so.3')}
    versions = {}
    for name in ('find', 'tar', 'taskset', 'unshare'):
        source = Path(shutil.which(name))
        shutil.copy2(source, out / 'bin' / name)
        versions[name] = subprocess.check_output([str(source), '--version'], text=True).splitlines()[0]
        ldd = subprocess.check_output(['ldd', str(source)], text=True)
        libraries.update(Path(s) for s in re.findall(r'=> (/\S+)', ldd))
    for lib in libraries:
        shutil.copy2(lib, out / lib.name)
    source_dir = out / 'source'
    source_dir.mkdir()
    for name in ('adapt.py', 'build_user.py', 'fuse_frontend.c', 'user_bridge.c'):
        shutil.copy2(SECTION / name, source_dir / name)
    shutil.copytree(SECTION / 'upstream', source_dir / 'upstream')
    for name in ('shared_core.c', 'kernel_support.c', 'core_metadata.c', 'support_types.h',
                 'support_remap.h', 'owner.h', 'kernel.patch', 'adaptation.json', 'Makefile', '.shared_core.o.cmd'):
        shutil.copy2(modules / 'adapted' / name, source_dir / ('core-compile-command.txt' if name.startswith('.') else name))
    shutil.copytree(SECTION / 'native', source_dir / 'native', ignore=shutil.ignore_patterns('__pycache__'))
    build_record = json.loads((modules / 'build.json').read_text())
    sdk_config = Path(build_record['kdir']) / '.config'
    if sdk_config.exists():
        shutil.copy2(sdk_config, source_dir / 'kernel-sdk.config')
    if build_record['kernel_release'] == '5.15.198':
        target_config = Path('/boot/config-vkso-final-raw-normal-5.15.198')
        shutil.copy2(target_config, source_dir / 'kernel-target.config')
        def effective_config(path):
            return [line for line in path.read_text().splitlines() if not line.startswith('CONFIG_CC_VERSION_TEXT=')]
        assert effective_config(sdk_config) == effective_config(target_config), 'kernel SDK configuration mismatch'
        write(source_dir / 'kernel-sdk-provenance.json', dict(
              target='Linux 5.15.198 raw-normal', effective_config_equal=True,
              compiler_alias_note='gcc and gcc-11 resolve to the same /usr/bin/x86_64-linux-gnu-gcc-11 binary; only CONFIG_CC_VERSION_TEXT differs',
              kernel_elf='extracted from the installed boot image, not the reconstructed SDK vmlinux',
              kernel_symbol_scope='ELF has no kernel symbol table; selected reuse closure is entirely in the owner module'))
    write(out / 'package.json', dict(name='ISO9660 native reassessment', kernel_build_id=build_id,
          inline_constant_memops=build_record.get('inline_constant_memops',False),
          keep_private_helpers=build_record.get('keep_private_helpers',False),
          kernel_release=json.loads((modules / 'build.json').read_text())['kernel_release'],
          expected_native_image='vkso-final-raw-normal-5.15.198.bzImage', variants=list(__import__('run').VARIANTS),
          benchmark_images=['alpine-virt-3.20.10-x86_64.iso', 'kernel-include.iso'], tools=versions,
          limits='Read-only, single-threaded FUSE service; no claim of complete Linux isofs feature parity.'))
    if not a.no_archive:
        archive = out.with_suffix('.tar.gz')
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(out, arcname=out.name)
        print(json.dumps(dict(package=str(out), archive=str(archive), bytes=archive.stat().st_size)))
    else:
        print(json.dumps(dict(package=str(out))))


if __name__ == '__main__':
    main()
