#!/usr/bin/env python3
"""Separate BCH counter builds; never part of the formal timing campaign."""
import argparse
import re
import shutil
from pathlib import Path
from run_layer3_v2 import command, module_session, identity
from layer3_v2 import BUILDS, dump, sha, write_csv

p=argparse.ArgumentParser();p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output=a.output.resolve();a.campaign=a.campaign.resolve()
a.output.mkdir(parents=True,exist_ok=False);identity(a.output)
rows=[]
for build in BUILDS:
    src=a.campaign/'02_bch_encode'/build
    work=a.output/build;work.mkdir()
    for name in ['bench_kmod.c','Makefile']:shutil.copy2(src/name,work/name)
    flags=(src/'flags.txt').read_text().strip()+' -DPGOT_DIAGNOSTIC=1'
    (work/'flags.txt').write_text(flags+'\n')
    (work/'build.log').write_text(command(['make','-j2','V=1',f'KCFLAGS={flags}'],cwd=work))
    ko=work/'bench_kmod.ko'
    (work/'objdump.txt').write_text(command(['objdump','-dr',ko]))
    log,session=module_session(ko,['cpu=2'],work/'diagnostic.log')
    assert 'PGOT_V2_CORRECTNESS,pass' in log and 'PGOT_L3_RAW' not in log
    values=re.findall(r'PGOT_V2_BCH_HELPER,(\w+),(\d+),(\d+)',log)
    assert len(values)==16 and len({(v,s) for v,s,n in values})==16
    assert {v for v,s,n in values}=={'origin','data_pgot','func_pgot','all_pgot'}
    assert all(int(n)==1 for v,s,n in values)
    for v,s,n in values:rows.append(dict(build=build,variant=v,site=int(s),calls=int(n)))
    dump(work/'objects.json',{p.name:sha(p) for p in work.glob('*.o')})
write_csv(a.output/'bch-helper-counts.csv',rows)
dump(a.output/'status.json',dict(status='complete',timing=False,workload='one fixed 512-byte encode per variant',sites=4))
print('BCH diagnostic: all four sites execute once per operation in every variant/build')
