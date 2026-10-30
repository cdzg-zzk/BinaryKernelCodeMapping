#!/usr/bin/env python3
"""Generate finite new-output pilot queues; do not launch or overwrite old runs."""
import hashlib, json, shutil
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
RUNS=SECTION/'build/squashfs/optimization-runs-01';BUILD=SECTION/'build/squashfs'

def save(path,v):
    assert not path.exists(),path
    path.write_text(json.dumps(v,indent=2)+'\n')

def main():
    runs=RUNS.resolve();staged=runs/'builds';staged.mkdir()
    identities={}
    for source in ['optimization-word-01','optimization-cache-01']:
        target=staged/source;shutil.copytree(BUILD/source,target)
        identities[source]={}
        for name in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse','vkso-squash-helper']:
            assert (target/name).read_bytes()==(BUILD/source/name).read_bytes()
            identities[source][name]=hashlib.sha256((target/name).read_bytes()).hexdigest()
    save(staged/'identities.json',identities)
    save(HERE/'cache-control.json',{'copied-unbounded':{'build':str(staged/'optimization-word-01')}})
    refs=json.loads((BUILD/'optimization-native-controls-01/references.json').read_text())
    # Keep the existing optimized native reference as a separately labeled
    # predecessor; normal/relaxed word references are the new fair controls.
    refs.update(json.loads((SECTION/'squashfs/refinement/native-references.json').read_text()))
    save(HERE/'native-references.json',refs)
    save(HERE/'native-builds.json',{
        'prepared-xz':str(BUILD/'refine-xz-01'),
        'prepared-optimized':str(staged/'optimization-cache-01')})
    jobs=[]
    variants=['stock','stock-single','copied','vkso','lkl-512','lkl-cache-512']
    for phase,source in [('word','optimization-word-01'),('cache','optimization-cache-01')]:
        groups=[('application','application-images-01',c,['startup','archive','scan','stream']) for c in (['xz'] if phase=='word' else ['gzip','xz','lz4'])]
        groups += [('python','heldout-python-images-01',c,['compile']) for c in (['xz'] if phase=='word' else ['gzip','xz'])]
        for group,images,codec,workloads in groups:
            name=f'{phase}-{group}-{codec}-pilot-01';out=runs/name
            argv=['unshare','--mount','--propagation','private','python3',str(SECTION/'squashfs/apptainer_shared.py'),
                '--user','zzk','--benchmark','--build',str(staged/source),'--image',str(BUILD/images/(codec+'.sif')),
                '--lkl',str(SECTION/'build/lkl/build-squash-only/sif-frontend/lklfuse'),
                '--lkl-cache',str(SECTION/'build/lkl/cache-frontend-01/lklfuse-cache'),'--lkl-memory','512',
                '--variant-set',*variants,*(['stock-wrapped'] if group=='application' else []),
                *(['copied-unbounded'] if phase=='cache' else []),'--workloads',*workloads,
                '--blocks','4','--repeats','1','--seed',str(68002 if group=='application' else 68003),
                '--campaign',name,'--pilot','--analysis-group','optimization-pilot','--output',str(out)]
            if phase=='cache':argv+=['--extra-readers',str(HERE/'cache-control.json')]
            jobs.append(dict(name=name,kind='pilot',argv=argv,result=str(out/'result.json')))
    name='native-pilot-01';out=runs/name
    jobs.append(dict(name=name,kind='native-pilot',argv=['unshare','--mount','--propagation','private','python3',
        str(SECTION/'squashfs/improvement/native_compare.py'),'--builds',str(HERE/'native-builds.json'),
        '--references',str(HERE/'native-references.json'),'--image-set',str(BUILD/'native-images-01/images.json'),
        '--blocks','4','--seed','68001','--campaign',name,'--pilot','--output',str(out)],result=str(out/'result.json')))
    save(HERE/'pilot-queue.json',jobs)
    resource=[]
    for scale in [1,4,16]:
        name=f'resource-scale-{scale:02}-01';out=runs/name
        resource.append(dict(name=name,kind='resource',argv=['unshare','--mount','--propagation','private','python3',
            str(SECTION/'squashfs/apptainer_shared.py'),'--user','zzk','--benchmark','--resources-only','--pilot',
            '--build',str(staged/'optimization-cache-01'),'--image',str(BUILD/'refine-scale-images-01'/f'scale-{scale}.sif'),
            '--lkl-cache',str(SECTION/'build/lkl/cache-frontend-01/lklfuse-cache'),
            '--variant-set','stock','stock-single','copied','vkso','copied-unbounded','lkl-cache-512',
            '--extra-readers',str(HERE/'cache-control.json'),'--blocks','1','--repeats','1',
            '--campaign',name,'--output',str(out)],result=str(out/'result.json')))
    save(HERE/'resource-queue.json',resource)
    print('prepared',len(jobs),'pilots and',len(resource),'untimed resource cases; not launched')

if __name__=='__main__':main()
