#!/usr/bin/env python3
"""Validate the fixed finite matrix, then regenerate the complete analysis."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import traceback
from audit_application import audit as application_audit
from audit_native import audit as native_audit

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUNS=ROOT/'test/evaluation-local/runs/iso9660'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--with-cache',action='store_true',help='require the separate nine-campaign matched-cache diagnostic')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    result=dict(status='running',scope='Analysis completion only; manuscript/figure review is a separate gate.')
    try:
        application=[RUNS/f'squash-application-{codec}-formal-{i:02d}' for i in range(1,4) for codec in ['gzip','xz','lz4']]
        native=[RUNS/f'squash-native-five-formal-{i:02d}' for i in range(1,8)]
        native += [RUNS/f'squash-native-{kind}-formal-{i:02d}' for kind in ['stream','normal-module','relaxed-module'] for i in range(1,4)]
        applications=[application_audit(p) for p in application]
        natives=[native_audit(p) for p in native]
        cache=[RUNS/f'squash-cache-{codec}-formal-{i:02d}' for i in range(1,4) for codec in ['gzip','xz','lz4']] if a.with_cache else []
        cache_audits=[application_audit(p) for p in cache]
        if cache:assert len(cache_audits)==9 and sum(r['observations'] for r in cache_audits)==1440
        matrix=[]
        for path in native+application+cache:
            is_native=path in native;data_path=path if is_native else path/'benchmark'
            detail=json.loads((data_path/'result.json').read_text())
            matrix.append(dict(campaign=detail['campaign'],source=str(path.relative_to(ROOT)),
                scope=('native:'+detail.get('baseline_label',detail.get('original_filesystem','squashfs'))+':'+detail.get('subtree','opt/linux-headers')) if is_native else detail.get('analysis_group','application'),
                codecs=','.join(c['compressor'] for c in detail['cases']) if is_native else Path(detail['image']).stem,
                variants='original,prepared' if is_native else ','.join(detail['variants']),
                workloads=','.join(detail.get('workloads',['archive','scan'])),
                blocks=detail['blocks'],fresh_repeats=1 if is_native else detail['repeats'],
                warm_repeats=detail.get('warm_repeats',0),seed=detail['seed'],
                observations=detail['observations'],status=detail['status']))
        with (out/'matrix.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
        fixed=json.loads((RUNS/'squash-maintenance-02/result.json').read_text())
        for path in native:
            env=json.loads((path/'environment.json').read_text())
            assert env['modules']['vkso_sq_core.ko']==fixed['owners']['fixed']
        for path in application+cache:
            env=json.loads((path/'benchmark/environment.json').read_text())
            binaries={Path(k).name:v for k,v in env['binaries'].items()}
            assert binaries['vkso_sq_core.ko']==fixed['owners']['fixed']
            for name,hashes in fixed['unchanged_user_binaries'].items():assert binaries[name]==hashes['fixed']
        assert len(applications)==9 and sum(r['observations'] for r in applications)==3456
        assert len(natives)==16 and sum(r['observations'] for r in natives)==9072
        (out/'application-audit.json').write_text(json.dumps(applications,indent=2)+'\n')
        (out/'native-audit.json').write_text(json.dumps(natives,indent=2)+'\n')
        (out/'cache-audit.json').write_text(json.dumps(cache_audits,indent=2)+'\n')
        commands=[
          [sys.executable,str(HERE/'audit_existing.py'),'--output',str(out/'existing-audit.json')],
          [sys.executable,str(HERE/'maintenance_artifacts.py'),'--output',str(out/'maintenance-artifacts.json')],
          [sys.executable,str(HERE/'audit_reference_build.py'),'--output',str(out/'reference-build')],
          [sys.executable,str(HERE/'cost_ledger.py'),'--build',str(ROOT/'test/section65/build/squashfs/evaluation-fixed-01/build'),'--output',str(out/'costs.json')],
          [sys.executable,str(HERE/'analyze_campaigns.py'),*[str(p/'benchmark') for p in application],'--output',str(out/'application')],
          [sys.executable,str(HERE/'analyze_campaigns.py'),*map(str,native),'--output',str(out/'native')],
          [sys.executable,str(HERE/'resource_ledger.py'),*map(str,application),'--observer-free',str(RUNS/'squash-observer-free-01'),'--output',str(out/'resources.json')]]
        if cache:
            commands += [[sys.executable,str(HERE/'analyze_campaigns.py'),*[str(p/'benchmark') for p in cache],'--output',str(out/'cache')],
                         [sys.executable,str(HERE/'resource_ledger.py'),*map(str,cache),'--observer-free',str(RUNS/'squash-observer-free-01'),'--output',str(out/'resources-cache.json')]]
        commands += [[sys.executable,str(HERE/'validate_analysis.py'),'--analysis',str(out/group/'analysis.json'),
                      '--output',str(out/(group+'-statistics-validation.json'))] for group in ['native','application']+(['cache'] if cache else [])]
        for i,command in enumerate(commands):
            with (out/f'analysis-{i}.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        result.update(status='complete',application_campaigns=9,native_campaigns=16,
                      application_observations=3456,native_observations=9072,commands=commands,
                      matched_cache_campaigns=len(cache),matched_cache_observations=1440 if cache else 0)
    except BaseException:
        result.update(status='failed',error=traceback.format_exc());raise
    finally:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
