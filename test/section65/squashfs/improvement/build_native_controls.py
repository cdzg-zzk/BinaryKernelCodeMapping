#!/usr/bin/env python3
"""Apply the exact bounded-copy helper to normal and relaxed unadapted modules."""
import argparse,difflib,hashlib,json
from pathlib import Path
import shutil,subprocess,sys,traceback
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'test/section65/squashfs';sys.path.insert(0,str(HERE));from prepare import span

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);raw=ROOT/'test/evaluation-local/runs/iso9660'
    small=ROOT/'test/section65/build/squashfs/improve-native-small-copy-01'
    candidate=json.loads((small/'candidate.json').read_text());assert candidate['small_copy'] and not candidate['force_inline']
    refs={'native-normal':dict(module=str(raw/'squash-maintenance-reference-01/build/sq_reference.ko'),filesystem='sqreference')}
    result=dict(status='running',scope='Exact same small-copy helper in unadapted native modules; no performance selection or new core implementation.',builds=[])
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');write()
    try:
        for label,source in [('native-small-normal',raw/'squash-maintenance-reference-01/build'),('native-small-relaxed',raw/'squash-maintenance-relaxed-reference-01/build')]:
            build=out/label;shutil.copytree(source,build);path=build/'cache.c';before=path.read_text();start,end=span(before,'squashfs_copy_data')
            assert before[start:end]==candidate['before']
            after=before[:start]+candidate['after']+before[end:];path.write_text(after)
            (out/(label+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before/cache.c',tofile='optimized/cache.c')))
            with (out/(label+'-build.log')).open('w') as f:subprocess.run(['make','-C',str(ROOT/'test/section65/build/native/kernel'),'M='+str(build),'-j2','modules'],stdout=f,stderr=subprocess.STDOUT,check=True)
            asm=subprocess.check_output(['objdump','-dr','--disassemble=squashfs_copy_data',build/'sq_reference.ko'],text=True);(out/(label+'-copy-data.asm')).write_text(asm)
            refs[label]=dict(module=str(build/'sq_reference.ko'),filesystem='sqreference')
            result['builds'].append(dict(label=label,base=str(source),module_sha256=hashlib.sha256((build/'sq_reference.ko').read_bytes()).hexdigest(),cache_compile_command=(build/'.cache.o.cmd').read_text().splitlines()[0],
                helper_source_sha256=hashlib.sha256(candidate['after'].encode()).hexdigest()));write()
        (out/'references.json').write_text(json.dumps(refs,indent=2)+'\n')
        (out/'prepared.json').write_text(json.dumps({'prepared-small-copy':str(small)},indent=2)+'\n')
        images=json.loads((ROOT/'test/section65/build/squashfs/native-images-01/images.json').read_text());images['cases']=[c for c in images['cases'] if c['compressor'] in ['gzip','xz','lz4']]
        (out/'images.json').write_text(json.dumps(images,indent=2)+'\n');result['status']='complete'
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:write()
if __name__=='__main__':main()
