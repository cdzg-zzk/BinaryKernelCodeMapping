#!/usr/bin/env python3
"""Full existing five-codec checks plus actual directory continuation semantics."""
import argparse
import json
from pathlib import Path
import sys
import traceback

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from check_fuse import check as filesystem_check,mounted
from check_directory import check as directory_check


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--core',type=Path,default=ROOT/'test/evaluation-local/runs/iso9660/squash-application-gzip-formal-01/libsq-materialized.so')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    target=out/'mount';target.mkdir();build=a.build.resolve()
    state=dict(status='running',scope='Valid-image mounted candidate correctness; same baseline materialized core.',cases=[])
    save=lambda:(out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    try:
        for image in sorted((ROOT/'test/section65/build/squashfs/fixtures').glob('*.squashfs')):
            expected=json.loads((ROOT/'test/evaluation-local/runs/iso9660/squash-native-guest-02/evidence'/(image.stem+'-squashfs.json')).read_text())
            with mounted([str(build/'vkso-squashfuse'),str(a.core.resolve()),str(build/'libsq-bridge.so'),str(image),'0',str(target)],target,out/(image.stem+'.log')):
                record=filesystem_check(target,expected,out,image.stem)
                record['directory_cursor']=directory_check(target/'directory')
                state['cases'].append(record);save()
            print(image.stem,'complete',flush=True)
        assert len(state['cases'])==5
        state['status']='complete'
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());raise
    finally:save()


if __name__=='__main__':main()
