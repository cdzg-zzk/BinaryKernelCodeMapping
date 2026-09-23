#!/usr/bin/env python3
"""Build/run public namespace and invalid-clock diagnostics; never a formal READ run."""
import argparse
from contextlib import contextmanager
import gzip
import platform
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from bundle import sha256, write_json, kv_file
from package_check import check
from collect import preflight

HERE = Path(__file__).resolve().parent

@contextmanager
def controlled_tuning(package):
    manifest = kv_file(package / 'boot-manifest.txt')
    if platform.release() != '5.15.198' or platform.version() != manifest['vkso_uts_version']:
        raise ValueError('wrong target kernel; no tuning performed')
    with gzip.open('/proc/config.gz', 'rb') as f:
        if f.read() != (package / 'vkso.config').read_bytes():
            raise ValueError('wrong target config; no tuning performed')
    saved, irq_active = [], False
    try:
        settings = [(Path('/sys/devices/system/cpu/intel_pstate') / k, v)
                    for k, v in [('no_turbo','1'),('max_perf_pct','100'),('min_perf_pct','100')]]
        settings += [(p, 'performance') for p in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_governor')]
        for path, value in settings:
            old = path.read_text().strip()
            if old != value:
                saved.append((path, old))
                path.write_text(value + '\n')
                if path.read_text().strip() != value: raise ValueError('tuning failed: '+str(path))
        irq_active = subprocess.run(['systemctl','is-active','--quiet','irqbalance']).returncode == 0
        if irq_active: subprocess.run(['systemctl','stop','irqbalance'],check=True)
        yield
    finally:
        errors = []
        for path, old in reversed(saved):
            try:
                if path.read_text().strip() != old: path.write_text(old + '\n')
                if path.read_text().strip() != old: raise ValueError('restore mismatch')
            except (OSError, ValueError) as exc: errors.append(str(path)+': '+str(exc))
        if irq_active:
            if subprocess.run(['systemctl','start','irqbalance']).returncode: errors.append('irqbalance restore')
        if errors: raise ValueError('environment cleanup failed: '+repr(errors))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True, help='opt2 package of same variant')
    p.add_argument('--out', type=Path, required=True, help='new diagnostic output directory')
    p.add_argument('--cpu', type=int, default=2)
    p.add_argument('--execute', action='store_true', help='requires root on matching VKSO boot; registers/restores carrier')
    args = p.parse_args()
    if any(os.environ.get(k) for k in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'LD_AUDIT')):
        raise ValueError('remove injected loader environment')
    packages = [args.reference.resolve(), args.package.resolve()]
    builds = [check(x) for x in packages]
    if builds[0]['build_variant'] != builds[1]['build_variant']:
        raise ValueError('different build variants')
    for name in ('vkso-bzImage', 'vkso.config', 'libkernel.so', 'page_mappings.txt'):
        if sha256(packages[0]/name) != sha256(packages[1]/name):
            raise ValueError('changed kernel/carrier: ' + name)
    if args.execute and os.geteuid() != 0:
        raise ValueError('--execute requires root; no target tests executed')
    out = args.out.resolve()
    if any(out == x or x in out.parents for x in packages):
        raise ValueError('diagnostics must be outside immutable packages')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='NOT_RUN', scope='diagnostic; invalid-call loop includes errno checks, not formal API latency',
                  cpu=args.cpu, boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  packages=[dict(path=str(x), inventory_sha256=sha256(x/'SHA256SUMS')) for x in packages],
                  inputs={str(x): sha256(x) for x in (HERE/'tests/test_public_target.c',
                          HERE.parent/'functional/abi_matrix.c', HERE/'vkso_time.h',
                          HERE.parent/'functional/vkso_abi.h', Path(__file__))})
    lock = None
    def run(argv, log):
        with (out/log).open('x') as f:
            subprocess.run(list(map(str,argv)), stdout=f, stderr=subprocess.STDOUT, check=True, timeout=180)
    try:
        cc = shutil.which('gcc')
        if subprocess.check_output([cc, '-dumpfullversion','-dumpversion'],text=True).strip() != builds[0]['compiler_version']:
            raise ValueError('compiler mismatch')
        for label, package in zip(('reference','candidate'), packages):
            run([cc,'-O2','-g','-Wall','-Wextra','-Werror','-fno-builtin',
                 '-I'+str(HERE.parent/'functional'), HERE/'tests/test_public_target.c',
                 '-L'+str(package/'direct'),'-lvkso_time','-L'+str(package),'-lkernel','-pthread','-ldl',
                 '-Wl,-z,now','-Wl,-rpath,'+str(package/'direct')+':'+str(package),
                 '-o',out/label],label+'-build.log')
        record['binary_sha256']={x:sha256(out/x) for x in ('reference','candidate')}
        if args.execute:
            lock = open('/run/vkso-direct-api.lock','a')
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if Path('/sys/module/page_cache_replace').exists():
                raise ValueError('manager module already active; refusing interference')
            with controlled_tuning(packages[0]):
                record['environment'] = []
                for package in packages:
                    _,_,_,env = preflight(package/'direct','vkso-'+builds[0]['build_variant'],args.cpu)
                    record['environment'].append(env)
                for label,package in zip(('reference','candidate'),packages):
                    loaded = attempted = False
                    try:
                        run(['insmod',package/'page_cache_replace.ko'],label+'-module.log');loaded=True
                        common=[package/'libkernel.so',package/'page_mappings.txt']
                        run([package/'manager','validate',*common],label+'-validate.log')
                        attempted=True
                        run([package/'manager','replace',*common],label+'-replace.log')
                        for mode in ('namespace','errors'):
                            run(['taskset','-c',str(args.cpu),out/label,'--'+mode],label+'-'+mode+'.log')
                    finally:
                        # A failed restore raises before unload, retaining the backing module.
                        if attempted: run([package/'manager','restore',*common],label+'-restore.log')
                        if loaded: run(['rmmod','page_cache_replace'],label+'-unload.log')
            record['status']='PASS'
        print('status='+record['status']+' out='+str(out))
    except BaseException as exc:
        record['status']='FAIL';record['error']=str(exc)
        raise
    finally:
        write_json(out/'diagnostic.json',record)
        if lock:lock.close()

if __name__ == '__main__':
    try: main()
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        sys.exit('supplemental refused/failed: '+str(exc))
