#!/usr/bin/env python3
"""Untimed common-core stream work attribution; no formal performance claim."""
import json,shutil,subprocess,sys,time
from pathlib import Path
from prerequisite import ROOT,RUNS,verify
sys.path.insert(0,str(ROOT/'test/section65/squashfs'))
from check_fuse import mounted
verify()
assert json.loads((RUNS/'cache-development-queue-01/result.json').read_text())['status']=='complete'
out=RUNS/'stream-profile-01';out.mkdir()
core=RUNS/'squash-optimized-application-final-gzip-01/libsq-materialized.so'
bases={'old':RUNS/'builds/optimization-cache-01','data16':RUNS/'builds/data-cache-controls-02/data-16','data48':RUNS/'builds/data-cache-controls-02/data-48'}
state={'status':'building','cases':[],'scope':'Instrumented direct FUSE GNU tar; work counters and codec CPU attribution only, not complete-application timing.'}
def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
save()
for key,base in bases.items():
 dest=out/key;shutil.copytree(base,dest)
 with (out/(key+'-build.log')).open('w') as log:
  subprocess.run([sys.executable,ROOT/'test/section65/squashfs/build_user.py','--build',dest,'--source-dir',dest/'xz-user-source','--profile','--bridge-only','--directory-cache','--direct-decode','--shared-lz4','--shared-xz'],stdout=log,stderr=subprocess.STDOUT,check=True)
for codec in ['gzip','lz4','xz']:
 for key in bases:
  dest=out/key;case=out/(codec+'-'+key);case.mkdir();target=case/'mount';target.mkdir()
  image=ROOT/'test/section65/build/squashfs/application-images-01'/(codec+'.sif')
  with mounted([str(dest/'vkso-squashfuse'),str(core),str(dest/'libsq-bridge.so'),str(image),'36864',str(target)],target,case/'daemon.log'):
   subprocess.run(['taskset','-c','1','tar','-cf',str(case/'payload.tar'),'-C',str(target/'opt/stream-data'),'.'],check=True)
  lines=(case/'daemon.log').read_text().splitlines()
  profile=[json.loads(x[len('SQ_PROFILE '):]) for x in lines if x.startswith('SQ_PROFILE ')]
  frontend=[json.loads(x[len('SQ_FRONTEND '):]) for x in lines if x.startswith('SQ_FRONTEND ')]
  assert len(profile)==len(frontend)==1
  state['cases'].append({'codec':codec,'variant':key,'profile':profile[0],'frontend':frontend[0]});save();print(codec,key,profile[0],flush=True)
state['status']='complete';save()
