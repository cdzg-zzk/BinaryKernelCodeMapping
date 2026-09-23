#!/usr/bin/env python3
"""Build only a selected kernel/dependencies or user benchmark into a new package."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from bundle import sha256, kv_file, verify_sums, build, write_json
from package_check import check
import workflow

HERE = Path(__file__).resolve().parent
BARE = HERE.parent / 'baremetal'
ROOT = BARE.parents[3]


def run(argv, **kw):
    subprocess.run(list(map(str, argv)), check=True, **kw)


def inventory(package):
    files = sorted(p for p in package.rglob('*') if p.is_file() and not p.is_symlink()
                   and p.name != 'SHA256SUMS')
    (package / 'SHA256SUMS').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(package)) + '\n' for p in files))


def direct_inventory(direct):
    (direct / 'SHA256SUMS').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(direct)) + '\n'
        for p in sorted(direct.rglob('*')) if p.is_file() and not p.is_symlink() and p.name != 'SHA256SUMS'))


def clone(source, dest, omit_direct=False):
    # manager creates root-owned transient locks after collection. They are not
    # build inputs; never clone them into a new artifact inventory.
    if any(name.startswith('runtime/') for name in verify_sums(source)):
        raise ValueError('unexpected packaged runtime state')
    shutil.copytree(source, dest, symlinks=True,
                    ignore=(lambda directory, names: (['runtime'] + (['direct'] if omit_direct else []))
                            if Path(directory) == source else []))


def bind_existing_direct(source, dest):
    # Retain actual compiled sources/binaries. Rebinding changes no machine code.
    shutil.copytree(source / 'direct', dest / 'direct', symlinks=True)
    direct = dest / 'direct'
    data = json.loads((direct / 'build.json').read_text())
    sums = verify_sums(dest)
    data.update(kernel_checksums=sums, package_manifest_sha256=sums['boot-manifest.txt'],
                carrier_sha256=sums['libkernel.so'],
                kernel_package_commit=kv_file(dest / 'boot-manifest.txt')['git_commit'],
                kernel_candidate_patch_sha256=kv_file(dest / 'boot-manifest.txt')['candidate_patch_sha256'],
                reused_direct_build_sha256=sha256(source / 'direct/build.json'),
                runtime_tests='NOT_RUN', kernel_build='SELECTIVE_REBUILD')
    (direct / 'build.json').write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    direct_inventory(direct)


def raw_build(source, dest, work, args, manifest):
    clone(source, dest, omit_direct=True)
    raw_source = Path(os.environ.get('RAW_SOURCE', manifest['raw_source']))
    if not (raw_source / 'Makefile').is_file():
        archive = Path(os.environ.get('RAW_TARBALL', '/tmp/linux-5.15.198.tar.xz'))
        if not archive.is_file():
            raise ValueError('Raw source unavailable; set RAW_SOURCE or RAW_TARBALL')
        raw_source = work / 'raw-source'; raw_source.mkdir()
        run(['tar', '-xf', archive, '-C', raw_source, '--strip-components=1'])
    if subprocess.check_output(['make','-s','-C',str(raw_source),'kernelversion'],text=True).strip() != '5.15.198':
        raise ValueError('Raw source must be Linux 5.15.198')
    if args.scope == 'update':
        run([BARE.parent/'update-bench/prepare-raw-source.sh',raw_source])
        for key,name in [('update_bench_header_sha256','include/linux/timekeeping_update_bench.h'),
                         ('update_bench_recorder_sha256','kernel/time/timekeeping_update_bench.c')]:
            if sha256(raw_source/name) != manifest[key]:
                raise ValueError('recorder changed: rebuild both instrumented implementations')
    raw_hash = subprocess.check_output([str(BARE/'source-tree-hash.sh'),str(raw_source)],text=True).strip()
    kernel = work / 'raw'; kernel.mkdir()
    shutil.copy2(source / 'raw.config', kernel / '.config')
    make = ['make','-C',raw_source,'O='+str(kernel),'CC='+args.cc,'-j'+str(args.jobs)]
    env = dict(os.environ, KBUILD_BUILD_TIMESTAMP=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime()),
               KBUILD_BUILD_USER='vkso-research', KBUILD_BUILD_HOST='controlled-build')
    run(make+['olddefconfig'],env=env)
    # An interface/config change needs paired redesign, not an accidental one-sided baseline.
    if (kernel / '.config').read_bytes() != (source / 'raw.config').read_bytes():
        raise ValueError('Raw config changed during olddefconfig; review full build configuration')
    run(make+['bzImage','modules_prepare'],env=env)
    shutil.copy2(kernel / 'vmlinux.symvers',kernel / 'Module.symvers')
    for name, directory, output in [('reader','revision/kernel-reader','vkso_kernel_reader'),
                                     ('clock','m09-posix-clock','vkso_m09_clock')]:
        module = work / name
        shutil.copytree(BARE.parent / directory,module,
                        ignore=shutil.ignore_patterns('*.o','*.ko','*.mod*','.*.cmd','Module.symvers','modules.order'))
        run(['make','-C',kernel,'M='+str(module),'CC='+args.cc,'-j'+str(args.jobs),'modules'],env=env)
        shutil.copy2(module / (output+'.ko'),dest / ('raw-kernel-reader.ko' if name=='reader' else 'raw-m09-clock.ko'))
    shutil.copy2(kernel / 'arch/x86/boot/bzImage',dest / 'raw-bzImage')
    for source_name, report_name in [('vmlinux','raw-vmlinux-sections.txt'),
                                     ('arch/x86/entry/vdso/vdso64.so.dbg','raw-vdso-sections.txt')]:
        with (dest/report_name).open('w') as report:
            subprocess.run(['size','-A',str(kernel/source_name)],stdout=report,check=True)
    shutil.copy2(kernel / 'kernel/config_data',dest / 'raw.image.config')
    if (dest / 'raw.image.config').read_bytes() != (dest / 'raw.config').read_bytes():
        raise ValueError('compiled config mismatch')
    if subprocess.check_output([str(BARE/'source-tree-hash.sh'),str(raw_source)],text=True).strip() != raw_hash:
        raise ValueError('Raw source changed during build')
    uts = (kernel / 'include/generated/compile.h').read_text().split('#define UTS_VERSION "')[1].split('"')[0]
    # Preserve package-wide original provenance; new Raw provenance is explicit below.
    manifest.update(raw_uts_version=uts, raw_image_sha256=sha256(dest/'raw-bzImage'),
                    raw_build=str(kernel), raw_source=str(raw_source),
                    raw_source_tree_sha256=subprocess.check_output([str(BARE/'source-tree-hash.sh'),str(raw_source)],text=True).strip())
    (dest/'boot-manifest.txt').write_text(''.join(k+'='+v+'\n' for k,v in manifest.items()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=['raw-normal','vkso-normal','raw-no-retpoline','vkso-no-retpoline','bench-normal','bench-no-retpoline'])
    p.add_argument('--package',type=Path,help='verified parent package; default from NORMAL_PACKAGE/NO_RETPOLINE_PACKAGE')
    p.add_argument('--out',type=Path,required=True,help='new package path (never overwrite parent)')
    p.add_argument('--cc',default=os.environ.get('CC','gcc'))
    p.add_argument('--jobs',type=int,default=int(os.environ.get('JOBS','4')))
    p.add_argument('--scope',choices=['read','update'],default='read')
    p.add_argument('--plan',action='store_true',help='validate parent and print actions without building')
    args=p.parse_args();backend,variant=args.target.split('-',1)
    package=(args.package or Path(os.environ.get('NORMAL_PACKAGE' if variant=='normal' else 'NO_RETPOLINE_PACKAGE',BARE/'artifacts'/('direct-'+variant)))).resolve()
    checker=check
    if args.scope=='update':
        sys.path.insert(0,str(BARE.parent/'update-bench'))
        from stateful import check as checker
    parent=checker(package);manifest=kv_file(package/'boot-manifest.txt')
    if manifest['build_variant']!=variant:raise ValueError('wrong parent build variant')
    if args.jobs<1:raise ValueError('jobs must be positive')
    if subprocess.check_output([args.cc,'-dumpfullversion','-dumpversion'],text=True).strip()!=manifest['cc_version']:
        raise ValueError('compiler must match parent package')
    if backend!='bench' and args.scope=='read':workflow.compatible(HERE,package)
    dest=args.out.resolve()
    if dest.exists() or package in dest.parents or dest in package.parents:
        raise ValueError('output must be a new directory outside the parent package')
    print('target='+args.target+'; kernel builds='+('none' if backend=='bench' else backend)+
          '; unchanged other kernel retained; output='+str(dest),flush=True)
    if args.plan:return
    work=dest.with_name(dest.name+'.work');work.mkdir(parents=True,exist_ok=False)
    with (work/'build.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stage=dest.with_name(dest.name+'.building');
        if stage.exists():raise ValueError('staging exists; choose a new output')
        try:
            if backend=='bench':
                clone(package,stage,omit_direct=True)
                inventory(stage)
                build(stage,stage/'direct',args.cc,args.scope)
            elif backend=='raw':
                raw_build(package,stage,work,args,manifest)
                inventory(stage)
                bind_existing_direct(package,stage)
            else:
                env=dict(os.environ,RAW_PACKAGE=str(package),BUILD_VARIANT=variant,UPDATE_BENCH='1' if args.scope=='update' else '0',
                         VKSO_VALIDATION_TESTS='0',BUILD_ROOT=str(work),OUT=str(stage),CURRENT_LINK='',
                         JOBS=str(args.jobs),CC=args.cc,
                         KBUILD_BUILD_TIMESTAMP=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime()),
                         KBUILD_BUILD_USER=manifest.get('kbuild_build_user','vkso-research'),
                         KBUILD_BUILD_HOST=manifest.get('kbuild_build_host','controlled-build'))
                run([BARE/'build-images.sh'],env=env)
                # Reused raw module, benchmark and image identities remain explicit.
                bind_existing_direct(package,stage)
            shutil.copy2(package/'boot-manifest.txt',stage/'parent-package-manifest.txt')
            shutil.copy2(package/'SHA256SUMS',stage/'parent-package-checksums.txt')
            provenance={'target':args.target,'parent_package':str(package),
                        'parent_inventory_sha256':sha256(package/'SHA256SUMS'),
                        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                        'runtime_tests':'NOT_RUN','unchanged_kernel':'both' if backend=='bench' else ('vkso' if backend=='raw' else 'raw')}
            patch=subprocess.check_output(['git','diff','--binary','HEAD'])
            (stage/'rebuild.patch').write_bytes(patch)
            provenance['patch_sha256']=sha256(stage/'rebuild.patch')
            if (stage/'rebuild.json').exists():
                provenance['parent_rebuild'] = json.loads((stage/'rebuild.json').read_text())
            (stage/'rebuild.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
            # A second selective rebuild replaces these provenance sidecars.
            # Bind their final contents, not the copied grandparent records.
            direct_manifest = stage / 'direct/build.json'
            direct_data = json.loads(direct_manifest.read_text())
            for name in ('parent-package-manifest.txt', 'parent-package-checksums.txt',
                         'rebuild.json', 'rebuild.patch'):
                if name in direct_data['kernel_checksums']:
                    direct_data['kernel_checksums'][name] = sha256(stage / name)
            direct_manifest.write_text(json.dumps(direct_data, indent=2, sort_keys=True) + '\n')
            direct_inventory(stage/'direct');inventory(stage)
            # Include the inner inventory in the outer inventory (no circular self-hash).
            with (stage/'SHA256SUMS').open('a') as f:f.write(sha256(stage/'direct/SHA256SUMS')+'  direct/SHA256SUMS\n')
            checker(stage)
            other='vkso' if backend=='raw' else 'raw'
            for name in ([other+'-bzImage',other+'.config'] if backend!='bench' else ['raw-bzImage','vkso-bzImage','libkernel.so']):
                if sha256(stage/name)!=sha256(package/name):raise ValueError('unexpected change to retained artifact: '+name)
            stage.rename(dest)
            print('package='+str(dest)+'; runtime_tests=NOT_RUN')
        except BaseException:
            print('failed build preserved at '+str(stage)+' and '+str(work),file=sys.stderr)
            raise


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('selective build failed: '+str(exc))
