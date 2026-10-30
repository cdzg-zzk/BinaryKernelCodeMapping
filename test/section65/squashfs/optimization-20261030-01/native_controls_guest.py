#!/usr/bin/env python3
"""Inside the disposable guest: valid images only, ordinary native references."""
import json, os, subprocess, traceback
from pathlib import Path
from reference_guest import manifest
P=Path('/work/package');O=Path('/work/evidence')

def main():
    O.mkdir();mount=O/'mount';mount.mkdir();result=dict(status='running',cases=[]);loaded=False
    def save():(O/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args):subprocess.run(list(map(str,args)),check=True,timeout=120)
    save()
    try:
        for policy in ['normal','relaxed']:
            run(['insmod',P/('native-word-'+policy+'.ko')]);loaded=True
            for image in sorted((P/'images').glob('*.squashfs')):
                run(['mount','-t','sqreference','-o','ro,loop',image,mount])
                try:
                    observed=manifest(mount)
                    expected=json.loads((P/'reference'/(image.stem+'-squashfs.json')).read_text())
                    assert observed==expected,(policy,image.name)
                    result['cases'].append(dict(policy=policy,image=image.name,entries=len(observed)))
                    save();print('native-word',policy,image.name,'passed',flush=True)
                finally:run(['umount',mount])
            run(['rmmod','sq_reference']);loaded=False
        result.update(status='complete',modules_unloaded=True)
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:
        if os.path.ismount(mount):run(['umount',mount])
        if loaded:run(['rmmod','sq_reference'])
        save()

if __name__=='__main__':main()
