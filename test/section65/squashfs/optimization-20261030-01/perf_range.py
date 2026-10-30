#!/usr/bin/env python3
"""Explain the finite rejected branch-selection candidate, not formal timing."""
import argparse, json, os, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--diagnostic',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert os.geteuid()==0
    diag=a.diagnostic.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
    for variant in ['dictionary-word','dictionary-word-branchless']:
        cmd=['/usr/lib/linux-tools-5.15.0-119/perf','stat','-e','cycles:u,instructions:u,branches:u,branch-misses:u','-r','3',
            '-o',str(out/(variant+'.txt')),'--','taskset','-c','1',str(diag/variant/'bench'),'single',
            str(diag/'blocks/python-2-data-0-000.xz'),str(diag/'blocks/python-2-data-0-000.raw'),'3000']
        with (out/(variant+'-decoder.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        rows.append(dict(variant=variant,argv=cmd));print(variant,'counters complete',flush=True)
    (out/'result.json').write_text(json.dumps(dict(status='complete',runs=rows,
        scope='Whole decoder harness user-mode counters, including output verification and initialization; not exclusive attribution to rc_bit'),indent=2)+'\n')

if __name__=='__main__':main()
