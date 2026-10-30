#!/usr/bin/env python3
"""Bounded metadata-work diagnostic; interposition counts are never timing evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'test/section65/squashfs'
sys.path.insert(0,str(HERE));from check_fuse import mounted


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--core',type=Path,required=True)
    p.add_argument('--library-bridge',type=Path,required=True)
    p.add_argument('--interposer',type=Path,required=True);a=p.parse_args()
    assert os.geteuid()==0
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);target=out/'mount';target.mkdir()
    runs=(ROOT/'test/section65/build/squashfs/optimization-runs-01').resolve()
    build=a.build.resolve()
    core=a.core.resolve()
    image=ROOT/'test/section65/build/squashfs/application-images-01/xz.sif'
    stock=ROOT/'test/section65/build/squashfs/apptainer/jammy/usr/libexec/apptainer/bin/squashfuse_ll'
    variants={'stock':[stock,'-f','-o','offset=36864',image,target],
              'stock-single':[stock,'-f','-s','-o','offset=36864',image,target],
              'copied':[build/'vkso-squashfuse',core,build/'libsq-bridge.so',image,'36864',target],
              'copied-library':[build/'vkso-squashfuse',core,a.library_bridge.resolve(),image,'36864',target]}
    files=[Path(v) for args in variants.values() for v in args if isinstance(v,Path) and v.is_file()]
    result=dict(status='running',binaries={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},scope='Current word-copy/bounded metadata/48-slot private data cache build, direct FUSE mount plus original include-tree find task; decoded bytes/calls, not elapsed performance. Includes mount-time decoder work. Stock buffer and internal streaming counters are separate APIs and must not be summed.',cases=[])
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');write();expected=None
    try:
        for repeat in range(3):
            for label,args in variants.items():
                name=f'{label}-{repeat}';counts=out/(name+'-counts.json')
                command=['env','LD_PRELOAD='+str(a.interposer.resolve()),'VKSO_DECODER_COUNTS='+str(counts),'taskset','-c','2',*map(str,args)]
                with mounted(command,target,out/(name+'.log')) as child:
                    before=Path(f'/proc/{child.pid}/stat').read_text()
                    observed=subprocess.check_output(['taskset','-c','1','find',str(target/'opt/linux-headers'),'-type','f'])
                    after=Path(f'/proc/{child.pid}/stat').read_text()
                    digest=hashlib.sha256(observed).hexdigest()
                    if expected is None:expected=digest
                    assert digest==expected
                value=json.loads(counts.read_text());assert sum(v['calls'] for v in value.values())>0
                result['cases'].append(dict(variant=label,repeat=repeat,counts=value,output_sha256=digest,stat_before=before,stat_after=after));write()
        result['status']='complete'
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:write()


if __name__=='__main__':main()
