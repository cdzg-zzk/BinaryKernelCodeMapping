#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess


def run(args, log=None, env=None):
    if log:
        with log.open('w') as f:
            subprocess.run(list(map(str,args)),check=True,env=env,stdout=f,stderr=subprocess.STDOUT)
    else:
        subprocess.run(list(map(str,args)),check=True,env=env)


def main():
    root=Path('/work');p=root/'package';out=root/'results';out.mkdir()
    for name in ['page_cache_replace','vkso_m09_clock','page_refs']:
        run(['insmod',p/(name+'.ko')])
    with (p/'libkernel.so').open('rb') as f:os.fsync(f.fileno())
    run([p/'manager','validate',p/'libkernel.so',p/'page_mappings.txt'])
    run([p/'manager','replace',p/'libkernel.so',p/'page_mappings.txt'])
    env={**os.environ,'LD_LIBRARY_PATH':str(p),'VKSO_TEST_DYNAMIC_CLOCK':'/dev/vkso-m09-clock'}
    try:
        run([p/'vkso-abi-matrix'],out/'abi.log',env)
        assert 'abi_matrix_status=pass' in (out/'abi.log').read_text()
        run(['python3',root/'probe.py'],out/'sharing.log',env)
        assert 'namespace_sharing_probe=pass' in (out/'sharing.log').read_text()
        clock=Path('/sys/devices/system/clocksource/clocksource0')
        original=(clock/'current_clocksource').read_text().strip()
        alternate=next(s for s in (clock/'available_clocksource').read_text().split() if s!=original)
        try:
            (clock/'current_clocksource').write_text(alternate)
            run([p/'vkso-abi-matrix','--provider-fallback'],out/'provider.log',env)
        finally:(clock/'current_clocksource').write_text(original)
        run([p/'vkso-abi-matrix','--lifecycle-smoke'],out/'lifecycle.log',env)
        # Retain shared live bytes for before/after reader-code comparison.
        (out/'live-carrier.so').write_bytes((p/'libkernel.so').read_bytes())
        run([p/'vkso-abi-matrix','--time-events'],out/'time-events.log',env)
        run([p/'vkso-abi-matrix','--suspend-resume'],out/'suspend.log',env)
    finally:run([p/'manager','restore',p/'libkernel.so',p/'page_mappings.txt'])
    for name in ['page_refs','vkso_m09_clock','page_cache_replace']:run(['rmmod',name])
    (out/'complete.json').write_text(json.dumps(dict(status='pass',scope='namespace physical sharing and complete ABI/events; not performance')))
    print('namespace_guest=pass',flush=True)


if __name__=='__main__':main()
