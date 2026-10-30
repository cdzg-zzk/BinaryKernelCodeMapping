#!/usr/bin/env python3
"""Build three real SIFs with conflicting same-name private filesystem objects."""
import argparse, hashlib, json, os
from pathlib import Path
import shutil, subprocess
ROOT=Path(__file__).resolve().parents[4]
SECTION=ROOT/'test/section65'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--format',choices=['gzip','xz','lz4'],default='gzip');a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    app=SECTION/'build/squashfs/apptainer/jammy/usr/bin/apptainer'
    base=ROOT/'test/evaluation-local/runs/iso9660/squash-apptainer-copied-02/rootfs'
    env=dict(os.environ,LD_LIBRARY_PATH=str(SECTION/'build/squashfs/apptainer/runtime/usr/lib/x86_64-linux-gnu'))
    result=dict(status='running',codec=a.format,scope='Same paths, different content, uid/gid, mode and timestamps; each phase first touches a distinct subtree.',cases=[])
    write=lambda:(out/'images.json').write_text(json.dumps(result,indent=2)+'\n')
    write()
    for index,label in enumerate(['A','B','C']):
        tree=out/('root-'+label);shutil.copytree(base,tree,symlinks=True)
        shutil.rmtree(tree/'opt/linux-headers')
        domain=tree/'opt/domain';domain.mkdir()
        payloads={}
        for phase in range(8):
            d=domain/('phase'+str(phase));d.mkdir()
            data=((label+':'+str(phase)+':private payload\n').encode()*400000)[:8<<20]
            (d/'data').write_bytes(data);os.link(d/'data',d/'hardlink');(d/'symlink').symlink_to('data')
            (d/'empty').write_bytes(b'');(d/'small').write_text(label+' private object '+str(phase)+'\n')
            (d/'data').chmod([0o644,0o444,0o664][index])
            for f in d.iterdir():
                if not f.is_symlink():os.utime(f,(1700000000+index,1700000000+index))
            payloads[str(phase)]=hashlib.sha256(data).hexdigest()
        image=out/(label+'.sif')
        args=f'-comp {a.format} -processors 1 -b 131072 -force-uid {100+index} -force-gid {200+index} -all-time {1700000000+index} -mkfs-time 1700000000'
        command=[str(app),'build','--mksquashfs-args',args,str(image),str(tree)]
        with (out/(label+'-build.log')).open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        listing=subprocess.check_output([app,'sif','list',image],env=env,text=True)
        row=[line.split('|') for line in listing.splitlines() if 'FS (Squashfs/' in line];assert len(row)==1
        result['cases'].append(dict(label=label,image=str(image),offset=int(row[0][3].strip().split('-')[0]),
            sha256=hashlib.sha256(image.read_bytes()).hexdigest(),command=command,payloads=payloads))
        write();print('built',label,flush=True)
    result['status']='complete';write()
if __name__=='__main__':main()
