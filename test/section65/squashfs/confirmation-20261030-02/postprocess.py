#!/usr/bin/env python3
"""Wait for measured campaigns, then produce audited data and a report only."""
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'optimization-20261030-01'
RUNS=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
BUILD=RUNS/'builds/data-cache-controls-02/data-48'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--queue-output',type=Path,required=True)
    p.add_argument('--queue-pid',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    state=dict(status='waiting',queue=str(a.queue_output),queue_pid=a.queue_pid,scope='Data audit and experiment report only; no manuscript or figure generation.',steps=[])
    def save():(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    def command(name,args):
        state.update(status='running',stage=name);save();print(name,flush=True)
        with (out/(name+'.log')).open('w') as log:subprocess.run(list(map(str,args)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        state['steps'].append(dict(stage=name,argv=list(map(str,args)),status='complete'));save()
    save()
    try:
        while True:
            q=read(a.queue_output/'result.json')
            if q['status']=='complete':break
            assert q['status']=='running',q
            try:os.kill(a.queue_pid,0)
            except ProcessLookupError:raise RuntimeError('Queue process exited without complete status')
            except PermissionError:pass
            time.sleep(15)
        assert not {'sq_reference','vkso_sq_core','vkso_squashfs','page_cache_replace','vkso_kernel_reader'}.intersection(l.split()[0] for l in Path('/proc/modules').read_text().splitlines())
        registration=HERE/'recovered-registration.json';queue=HERE/'recovered-formal-queue.json'
        for path,digest in read(registration)['identities'].items():assert sha(Path(path))==digest,path
        analysis=RUNS/'data48-analysis-01'
        command('analysis',[sys.executable,HERE/'analyze.py','--queue',queue,'--output',analysis])
        command('audit',[sys.executable,HERE/'audit.py','--queue',queue,'--registration',registration,'--analysis',analysis/'analysis.json','--output',analysis/'audit.json'])
        command('costs',[sys.executable,OLD/'cost_ledger.py','--build',BUILD,'--source-dir',BUILD/'xz-user-source','--output',analysis/'costs.json'])
        command('reuse',[sys.executable,OLD/'reuse_audit.py','--build',BUILD,'--ledger',analysis/'costs.json','--output',analysis/'reuse-audit'])
        command('resources',[sys.executable,HERE/'resources.py','--queue',queue,'--resource-queue',HERE/'resource-queue.json','--minimal',RUNS/'data48-minimal-01/result.json','--output',analysis/'resource-ledger'])
        command('report',[sys.executable,HERE/'experiment_report.py','--analysis',analysis])
        state.update(status='awaiting-review',analysis=str(analysis),next='Review numeric findings and report, preserve raw evidence, verify cleanup, and commit. User will push.')
    except BaseException:state.update(status='failed',error=traceback.format_exc());raise
    finally:save()
if __name__=='__main__':main()
