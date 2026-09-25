#!/usr/bin/env python3
"""Build a selected kernel, carrier, or user benchmark into a new package.

VKSO Kbuild output is cached by scope and variant; packages remain immutable.
"""
import argparse
import fcntl
import hashlib
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
VKSO_SOURCE = Path(os.environ.get('VKSO_SOURCE',
    ROOT/'test/test_gettime/linux-5.15.198-vkso')).resolve()
RAW_DIAGNOSTIC_SYMBOLS = ('TIMEKEEPING_UPDATE_CACHE_PREP_DIAG',
                          'TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG')


def run(argv, **kw):
    subprocess.run(list(map(str, argv)), check=True, **kw)


def inventory(package):
    files = sorted(p for p in package.rglob('*') if p.is_file() and not p.is_symlink()
                   and p.name != 'SHA256SUMS')
    (package / 'SHA256SUMS').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(package)) + '\n' for p in files))


def direct_inventory(direct):
    (direct / 'SHA256SUMS').write_text(''.join(sha256(p) + '  ' + str(p.relative_to(direct)) + '\n'
        for p in sorted(direct.rglob('*')) if p.is_file() and not p.is_symlink() and p.name != 'SHA256SUMS'))


def ordinary_config_symbols(text):
    """Compare parent and result without Kconfig's optional diagnostic entries."""
    return sorted(line for line in text.splitlines()
        if (line.startswith('CONFIG_') or line.startswith('# CONFIG_'))
        and not any('CONFIG_'+name in line for name in RAW_DIAGNOSTIC_SYMBOLS))


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
    # Collection/build Python changes do not require recompiling the measured
    # binaries, but the package's source snapshot must still describe the
    # current tooling so all four packages share one source fingerprint.
    packaged_scripts = direct/'src/direct-api'
    live_scripts = {p.relative_to(HERE):p for p in HERE.rglob('*.py')
                    if not {'build','__pycache__'}.intersection(p.relative_to(HERE).parts)}
    for old in packaged_scripts.rglob('*.py'):
        if old.relative_to(packaged_scripts) not in live_scripts:
            old.unlink()
    for name, live in live_scripts.items():
        target=packaged_scripts/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(live,target)
    source_hashes={str(p.relative_to(direct/'src')):sha256(p)
                   for p in sorted((direct/'src').rglob('*'))
                   if p.is_file() and p.suffix in ('.c','.h','.py')}
    source_hashes['direct-api/Makefile']=sha256(packaged_scripts/'Makefile')
    data['source_hashes']=source_hashes
    data['source_fingerprint']=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    data['source_git_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    data['source_dirty_patch_sha256']=hashlib.sha256(subprocess.check_output(
        ['git','diff','--binary','--no-ext-diff','HEAD','--'],cwd=ROOT)).hexdigest()
    sums = verify_sums(dest)
    data.update(kernel_checksums=sums, package_manifest_sha256=sums['boot-manifest.txt'],
                carrier_sha256=sums['libkernel.so'],
                kernel_package_commit=kv_file(dest / 'boot-manifest.txt')['git_commit'],
                kernel_candidate_patch_sha256=kv_file(dest / 'boot-manifest.txt')['candidate_patch_sha256'],
                reused_direct_build_sha256=sha256(source / 'direct/build.json'),
                runtime_tests='NOT_RUN', kernel_build='SELECTIVE_REBUILD')
    (direct / 'build.json').write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    direct_inventory(direct)


def stamp_candidate(dest, manifest):
    """Bind a reused kernel image to the current candidate without editing it."""
    patch=subprocess.check_output(['git','diff','--binary','--no-ext-diff','HEAD','--'],cwd=ROOT)
    (dest/'source.patch').write_bytes(patch)
    manifest.update(prepared_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    git_worktree_dirty='1' if patch else '0',
                    candidate_patch_sha256=sha256(dest/'source.patch'))
    (dest/'boot-manifest.txt').write_text(''.join(k+'='+v+'\n' for k,v in manifest.items()))


def raw_build(source, dest, work, args, manifest, cache):
    clone(source, dest, omit_direct=True)
    if args.scope == 'update':
        shutil.copy2(BARE.parent/'update-bench/stateful.py',dest/'stateful.py')
    cacheprep = os.environ.get('UPDATE_CACHE_PREP_DIAG') == '1'
    percall_pmu = os.environ.get('UPDATE_PERCALL_PMU_DIAG') == '1'
    if cacheprep and percall_pmu:
        raise ValueError('choose only one Raw UPDATE diagnostic mode')
    if (cacheprep or percall_pmu) and (args.scope != 'update' or args.target != 'raw-normal'):
        raise ValueError('Raw UPDATE diagnosis requires update/raw-normal')
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
            if not (cacheprep or percall_pmu) and sha256(raw_source/name) != manifest[key]:
                raise ValueError('recorder changed: rebuild both instrumented implementations')
    raw_hash = subprocess.check_output([str(BARE/'source-tree-hash.sh'),str(raw_source)],text=True).strip()
    kernel = cache / ('raw-pmu' if percall_pmu else 'raw') / 'build'
    kernel.mkdir(parents=True,exist_ok=True)
    identity = dict(source=str(raw_source.resolve()), compiler=args.cc,
                    config=sha256(source/'raw.config'),
                    cacheprep=cacheprep,
                    percall_pmu=percall_pmu,
                    timestamp=manifest.get('kbuild_build_timestamp'))
    identity_file = kernel.parent / 'identity.json'
    if identity_file.exists():
        cached_identity=json.loads(identity_file.read_text())
        # The cache-preparation build predates the separate per-call PMU mode.
        # Its missing flag means false; all original identity fields must match.
        cached_identity.setdefault('percall_pmu',False)
        if cached_identity != identity:
            raise ValueError('Raw Kbuild cache identity changed; choose another --cache-root')
    if not identity_file.exists(): write_json(identity_file,identity)
    current_config=(kernel/'.config').read_text() if (kernel/'.config').exists() else ''
    diagnostic_symbol=('TIMEKEEPING_UPDATE_CACHE_PREP_DIAG' if cacheprep else
                       'TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG' if percall_pmu else None)
    if diagnostic_symbol:
        if f'CONFIG_{diagnostic_symbol}=y\n' not in current_config:
            shutil.copy2(source/'raw.config',kernel/'.config')
            run([raw_source/'scripts/config','--file',kernel/'.config',
                 '--enable',diagnostic_symbol])
    elif not current_config or (kernel/'.config').read_bytes() != (source/'raw.config').read_bytes():
        shutil.copy2(source/'raw.config',kernel/'.config')
    make = ['make','-C',raw_source,'O='+str(kernel),'CC='+args.cc,'-j'+str(args.jobs)]
    env = dict(os.environ, KBUILD_BUILD_TIMESTAMP=manifest.get('kbuild_build_timestamp',time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime())),
               KBUILD_BUILD_USER='vkso-research', KBUILD_BUILD_HOST='controlled-build')
    run(make+['olddefconfig'],env=env)
    # An interface/config change needs paired redesign, not an accidental one-sided baseline.
    if not diagnostic_symbol and (kernel / '.config').read_bytes() != (source / 'raw.config').read_bytes():
        raise ValueError('Raw config changed during olddefconfig; review full build configuration')
    if diagnostic_symbol:
        result_config=(kernel/'.config').read_text()
        if f'CONFIG_{diagnostic_symbol}=y\n' not in result_config:
            raise ValueError('Raw diagnostic config did not enable: '+diagnostic_symbol)
        # The parent config predates these optional diagnosis symbols. Kconfig
        # adds explicit "not set" lines for both, even when only one is used.
        if any(f'CONFIG_{name}=y\n' in result_config for name in RAW_DIAGNOSTIC_SYMBOLS
               if name != diagnostic_symbol):
            raise ValueError('another Raw diagnostic option was enabled')
        if ordinary_config_symbols(result_config)!=ordinary_config_symbols(
                (source/'raw.config').read_text()):
            raise ValueError('Raw config changed beyond the diagnostic option')
        shutil.copy2(kernel/'.config',dest/'raw.config')
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
    if cacheprep:
        # The traced call sites differ between the two order branches. Preserve
        # the exact image's symbol addresses for offline PT interpretation.
        with (dest/'raw-update-disassembly.txt').open('w') as report:
            for symbol in ('timekeeping_update', 'update_fast_timekeeper'):
                subprocess.run(['objdump','-drwC','--disassemble='+symbol,
                                str(kernel/'vmlinux')],stdout=report,check=True)
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
    if cacheprep:
        manifest.update(raw_cacheprep_diagnostic='1',
                        raw_prefetch_diagnostic='1',
                        raw_order_diagnostic='1',
                        config_difference='diagnostic_raw_cacheprep_only',
                        raw_update_bench_header_sha256=sha256(raw_source/'include/linux/timekeeping_update_bench.h'),
                        raw_update_bench_recorder_sha256=sha256(raw_source/'kernel/time/timekeeping_update_bench.c'))
    if percall_pmu:
        manifest.update(raw_percall_pmu_diagnostic='1',
                        config_difference='diagnostic_raw_percall_pmu_only',
                        raw_update_bench_header_sha256=sha256(raw_source/'include/linux/timekeeping_update_bench.h'),
                        raw_update_bench_recorder_sha256=sha256(raw_source/'kernel/time/timekeeping_update_bench.c'))
    (dest/'boot-manifest.txt').write_text(''.join(k+'='+v+'\n' for k,v in manifest.items()))


def carrier_build(source, dest, work, args, manifest, cache):
    """Rebuild the private entry against the exact cached kernel image."""
    kernel=cache/'build/vkso'
    for name in ('vmlinux','System.map','.config','arch/x86/boot/bzImage'):
        if not (kernel/name).is_file():
            raise ValueError('carrier-only needs a seeded Kbuild cache: '+str(kernel/name))
    if sha256(kernel/'arch/x86/boot/bzImage')!=sha256(source/'vkso-bzImage'):
        raise ValueError('cached VKSO image differs from parent; use vkso-* instead')
    if (kernel/'.config').read_bytes()!=(source/'vkso.config').read_bytes():
        raise ValueError('cached VKSO config differs from parent; use vkso-* instead')
    current_source=subprocess.check_output([BARE/'source-tree-hash.sh',
        VKSO_SOURCE],text=True).strip()
    if current_source!=manifest['vkso_source_tree_sha256']:
        raise ValueError('kernel source changed; carrier-only is unsafe; use vkso-*')
    clone(source,dest,omit_direct=True)
    krg=work/'vkso.krg'
    run([ROOT/'kernel_cgd/src/krg','build',kernel/'vmlinux','-o',krg,
         '--kallsyms',kernel/'System.map'])
    dso=work/'dso';dso.mkdir()
    for name in ('symbols.txt','shared_data.txt'):
        shutil.copy2(BARE/name,dso/name)
    if manifest['build_variant']=='normal':
        shutil.copy2(BARE/'reusable_text.txt',dso/'reusable_text.txt')
    run([args.cc,'-I'+str(VKSO_SOURCE/'include'),
         '-c','-fPIC','-o',dso/'vkso_user_entry.o',
         ROOT/'test/test_gettime/vkso-tests/functional/vkso_user_entry.S'])
    command=['python3',ROOT/'make_dll/build_PIC_so.py','--symbols','symbols.txt',
             '--krg',krg,'--shim-list',ROOT/'make_dll/shim.txt',
             '--shared-data-list','shared_data.txt','--vmlinux',kernel/'vmlinux',
             '--private-wrapper-object','vkso_user_entry.o',
             '--symbol-addresses','resolved_symbol_addresses.txt',
             '--page-map','page_mappings.txt']
    if manifest['build_variant']=='normal':
        command[6:6]=['--reusable-text-list','reusable_text.txt']
    run(command,cwd=dso)
    if (dso/'kernel_identity.txt').read_bytes()!=(source/'kernel_identity.txt').read_bytes():
        raise ValueError('carrier kernel identity changed despite identical cached image')
    for name in ('libkernel.so','page_mappings.txt','owner_descriptors.txt',
                 'kernel_identity.txt','resolved_symbol_addresses.txt'):
        shutil.copy2(dso/name,dest/name)
    with (dest/'vkso-carrier-sections.txt').open('w') as out:
        subprocess.run(['size','-A',str(dest/'libkernel.so')],stdout=out,check=True)
    symbols=subprocess.check_output(['nm','-a',str(dest/'libkernel.so')],text=True)
    for symbol,output in (('vkso_shared_page','vkso-shared-st-value.txt'),
                          ('vkso_clock_gettime_hres','vkso-text-anchor-st-value.txt')):
        values=[fields[0] for line in symbols.splitlines()
                if len(fields:=line.split())>=3 and fields[2]==symbol]
        if not values:raise ValueError('missing carrier symbol: '+symbol)
        (dest/output).write_text('0x'+values[0]+'\n')
    stamp_candidate(dest,manifest)
    final_source=subprocess.check_output([BARE/'source-tree-hash.sh',
        VKSO_SOURCE],text=True).strip()
    if final_source!=current_source:
        raise ValueError('kernel source changed during carrier build')
    inventory(dest)
    bind_existing_direct(source,dest)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=['raw-normal','vkso-normal','carrier-normal','metadata-normal',
        'raw-no-retpoline','vkso-no-retpoline','carrier-no-retpoline',
        'metadata-no-retpoline','bench-normal','bench-no-retpoline'])
    p.add_argument('--package',type=Path,help='verified parent package; default from NORMAL_PACKAGE/NO_RETPOLINE_PACKAGE')
    p.add_argument('--out',type=Path,required=True,help='new package path (never overwrite parent)')
    p.add_argument('--cc',default=os.environ.get('CC','gcc'))
    p.add_argument('--jobs',type=int,default=int(os.environ.get('JOBS','4')))
    p.add_argument('--scope',choices=['read','update'],default='read')
    p.add_argument('--cache-root',type=Path,default=BARE/'artifacts'/'.kbuild-cache',
                   help='persistent, per-scope/variant VKSO Kbuild cache')
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
    # A VKSO carrier/ABI change can be staged before rebuilding the direct
    # library. The copied old binary remains valid in that intermediate
    # package; bench-* must then rebuild it against the new carrier. A Raw-only
    # rebuild still requires the existing compiled user inputs to match.
    if backend=='raw' and args.scope=='read':workflow.compatible(HERE,package)
    dest=args.out.resolve()
    if dest.exists() or package in dest.parents or dest in package.parents:
        raise ValueError('output must be a new directory outside the parent package')
    cache=(args.cache_root.resolve() / args.scope / variant)
    cached_image=cache/'build/vkso/arch/x86/boot/bzImage'
    cache_key={'scope':args.scope,'variant':variant,
               'source':str(VKSO_SOURCE),
               'compiler':str(Path(shutil.which(args.cc) or args.cc).resolve()),
               'compiler_version':manifest['cc_version'],
               'timestamp':manifest.get('kbuild_build_timestamp'),
               'build_user':manifest.get('kbuild_build_user'),
               'build_host':manifest.get('kbuild_build_host')}
    if backend=='carrier':
        identity=cache/'identity.json'
        if not identity.is_file() or not cached_image.is_file():
            raise ValueError('carrier-only needs a seeded Kbuild cache; build vkso-* once')
        if json.loads(identity.read_text())!=cache_key:
            raise ValueError('Kbuild cache identity differs from this build')
        if sha256(cached_image)!=sha256(package/'vkso-bzImage'):
            raise ValueError('cached VKSO image differs from parent; use vkso-* instead')
    print('target='+args.target+'; kernel builds='+('none' if backend in ('bench','carrier','metadata') else backend)+
          '; unchanged other kernel retained; output='+str(dest)+
          ('; kbuild_cache='+str(cache)+'; cache_image='+('present' if cached_image.is_file() else 'absent')
           if backend in ('vkso','carrier') else ''),flush=True)
    if args.plan:return
    work=dest.with_name(dest.name+'.work')
    stage=dest.with_name(dest.name+'.building')
    if work.exists() or stage.exists():
        raise ValueError('previous build state exists; choose a new --out; preserved: '+
                         ', '.join(str(path) for path in (stage,work) if path.exists()))
    work.mkdir(parents=True,exist_ok=False)
    with (work/'build.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            if backend=='bench':
                clone(package,stage,omit_direct=True)
                stamp_candidate(stage,manifest)
                inventory(stage)
                build(stage,stage/'direct',args.cc,args.scope)
            elif backend=='metadata':
                clone(package,stage,omit_direct=True)
                stamp_candidate(stage,manifest)
                inventory(stage)
                bind_existing_direct(package,stage)
            elif backend=='raw':
                cache.mkdir(parents=True,exist_ok=True)
                with (cache/'raw-build.lock').open('a+') as cache_lock:
                    fcntl.flock(cache_lock,fcntl.LOCK_EX)
                    raw_build(package,stage,work,args,manifest,cache)
                inventory(stage)
                bind_existing_direct(package,stage)
            elif backend=='carrier':
                if not (cache/'build.lock').is_file():
                    raise ValueError('carrier-only needs a seeded Kbuild cache; build vkso-* once')
                with (cache/'build.lock').open('r') as cache_lock:
                    fcntl.flock(cache_lock,fcntl.LOCK_SH)
                    carrier_build(package,stage,work,args,manifest,cache)
            else:
                cache.mkdir(parents=True,exist_ok=True)
                with (cache/'build.lock').open('w') as cache_lock:
                    fcntl.flock(cache_lock,fcntl.LOCK_EX)
                    key_file=cache/'identity.json'
                    if key_file.exists() and json.loads(key_file.read_text())!=cache_key:
                        raise ValueError('Kbuild cache identity changed; choose another --cache-root')
                    if not key_file.exists():write_json(key_file,cache_key)
                    env=dict(os.environ,RAW_PACKAGE=str(package),BUILD_VARIANT=variant,UPDATE_BENCH='1' if args.scope=='update' else '0',
                             VKSO_VALIDATION_TESTS='0',BUILD_ROOT=str(cache/'build'),
                             VKSO_SOURCE=str(VKSO_SOURCE),VKSO_PREPARED_SOURCE=str(cache/'source'),
                             INCREMENTAL_BUILD='1',
                             OUT=str(stage),CURRENT_LINK='',
                             JOBS=str(args.jobs),CC=args.cc,
                             KBUILD_BUILD_TIMESTAMP=manifest.get('kbuild_build_timestamp',time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime())),
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
            retained=([other+'-bzImage',other+'.config'] if backend in ('raw','vkso')
                      else ['raw-bzImage','vkso-bzImage'] if backend=='carrier'
                      else ['raw-bzImage','vkso-bzImage','libkernel.so'])
            for name in retained:
                if sha256(stage/name)!=sha256(package/name):raise ValueError('unexpected change to retained artifact: '+name)
            stage.rename(dest)
            print('package='+str(dest)+'; runtime_tests=NOT_RUN')
        except BaseException:
            print('failed build preserved at '+str(stage)+' and '+str(work),file=sys.stderr)
            raise


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:sys.exit('selective build failed: '+str(exc))
