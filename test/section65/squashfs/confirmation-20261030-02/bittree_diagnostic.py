#!/usr/bin/env python3
"""One mechanism-based follow-up: fixed-depth tree unrolling, unchanged rc_bit."""
import argparse,hashlib,json,os,random,shlex,shutil,statistics,subprocess,sys,traceback
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path('/home/zzk/BinaryKernelCodeMapping/test/section65/squashfs/optimization-20261030-01')
RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve()
BASE=RUNS/'builds/optimization-cache-01';ORIGINAL=SECTION/'build/squashfs/optimization-cache-01'
HARNESS=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#undef __always_inline
#define __always_inline inline __attribute__((always_inline))
#include "xz_lzma2.h"
RC_STRUCT
NORMALIZE
RC_BIT
ORIGINAL
CANDIDATE
static uint32_t state=653008;
static uint32_t rng(void){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
int main(void){
 size_t tests=0;uint8_t input[64];uint16_t pa[256],pb[256];
 for(unsigned limit=2;limit<=256;limit*=2)for(int k=0;k<4096;k++){
  for(unsigned j=0;j<sizeof(input);j++)input[j]=(uint8_t)rng();
  for(unsigned j=0;j<256;j++)pa[j]=rng()%(RC_BIT_MODEL_TOTAL+1);
  memcpy(pb,pa,sizeof(pa));
  struct rc_dec a;memset(&a,0,sizeof(a));a.range=rng();a.code=rng();a.in=input;
  if(k<4)a.range=(uint32_t[]){0,RC_TOP_VALUE-1,RC_TOP_VALUE,UINT32_MAX}[k];
  struct rc_dec b;memcpy(&b,&a,sizeof(a));
  unsigned x=original(&a,pa,limit),y=candidate(&b,pb,limit);
  if(x!=y||memcmp(pa,pb,sizeof(pa))||memcmp(&a,&b,sizeof(a))){fprintf(stderr,"tree mismatch limit=%u k=%d\n",limit,k);return 1;}
  tests++;
 }
 printf("%zu tree transitions passed\n",tests);return 0;
}
'''
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def extract(text,start,end='\n}\n'):
    i=text.index(start);j=text.index(end,i)+len(end);return text[i:j]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert os.geteuid()!=0
    from prerequisite import verify
    verify()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    result=dict(status='running',hypothesis='The Python range-decoder hotspot includes repeated small fixed-depth bit-tree loop control. Unroll only depths 3/6/8; preserve branch-based probability updates, native ISA and hardening flags. This is distinct from the rejected all-mask rc_bit candidate.',
        promotion='Diagnostic only. Any accepted new common owner would need a new version, native/PFN/guest validation and affected-workload confirmation. Current frozen version is unchanged.',commands=[])
    save(out/'result.json',result)
    try:
        objects=['xz_dec_stream','xz_dec_lzma2','xz_dec_bcj','xz_support']
        with (out/'build.log').open('w') as log:
            def run(cmd,cwd=None):
                cmd=list(map(str,cmd));result['commands'].append(cmd)
                log.write(shlex.join(cmd)+'\n');log.flush();subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
            for variant in ['prepared','tree-unrolled']:
                dest=out/variant;dest.mkdir()
                for path in BASE.iterdir():
                    if path.is_file() and path.suffix in ['.c','.h']:shutil.copy2(path,dest/path.name)
                for name in objects:shutil.copy2(BASE/(name+'.o'),dest/(name+'.o'))
                if variant=='tree-unrolled':
                    path=dest/'xz_dec_lzma2.c';text=path.read_text();old=extract(text,'static __always_inline uint32_t rc_bittree(')
                    new=(HERE/'bittree_unrolled.inc').read_text().strip();assert text.count(old)==1
                    path.write_text(text.replace(old,new))
                    cmd=shlex.split((BASE/'.xz_dec_lzma2.o.cmd').read_text().splitlines()[0].split(' := ',1)[1]);cmd=cmd[:cmd.index('-c')]
                    cmd=[x.replace(str(ORIGINAL),str(dest)).replace(str(BASE),str(dest)) for x in cmd if not x.startswith('-Wp,-MMD')]
                    run(cmd+['-c',str(path),'-o',str(dest/'xz_dec_lzma2.o')],SECTION/'build/native/kernel')
                run(['gcc','-O2','-I'+str(dest),'-I'+str(SECTION/'build/squashfs/deps/usr/include'),HERE/'bench.c',
                    *[dest/(name+'.o') for name in objects],'-lz','-Wl,-l:liblzma.so.5','-o',dest/'bench'])
            original=(out/'prepared/xz_dec_lzma2.c').read_text();candidate=(out/'tree-unrolled/xz_dec_lzma2.c').read_text()
            harness=HARNESS.replace('RC_STRUCT',extract(original,'struct rc_dec {','\n};')).replace('NORMALIZE',extract(original,'static __always_inline void rc_normalize('))
            harness=harness.replace('\nRC_BIT\n','\n'+extract(original,'static __always_inline int rc_bit(')+'\n')
            harness=harness.replace('ORIGINAL',extract(original,'static __always_inline uint32_t rc_bittree(').replace('rc_bittree(','original(',1))
            harness=harness.replace('CANDIDATE',extract(candidate,'static __always_inline uint32_t rc_bittree(').replace('rc_bittree(','candidate(',1))
            (out/'tree_states.c').write_text(harness)
            run(['gcc','-O2','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(out/'prepared'),out/'tree_states.c','-o',out/'tree_states'])
            result['differential']=subprocess.check_output([out/'tree_states'],text=True).strip()
            run([sys.executable,HERE/'validate_dictionary.py','--diagnostic',out,'--variant','tree-unrolled','--output',out/'valid-streams'])
        previous=read(RUNS/'xz-diagnostic-05/capture.json')
        selected=[r for r in previous['blocks'] if r['name'].endswith('-000') and ('-data-' in r['name'] or '-mount-' in r['name'])]
        assert len(selected)==8
        for record in selected:
            assert sha(Path(record['xz']))==record['input_sha256'] and sha(Path(record['raw']))==record['output_sha256']
        conditions=[('word-single','prepared','single'),('word-prealloc','prepared','prealloc'),
                    ('tree-single','tree-unrolled','single'),('tree-prealloc','tree-unrolled','prealloc'),('library','prepared','library')]
        rows=[];rng=random.Random(653008)
        for block in range(5):
            cells=[(record,condition) for record in selected for condition in conditions];rng.shuffle(cells)
            for record,(name,binary,mode) in cells:
                row=json.loads(subprocess.check_output(['taskset','-c','1',str(out/binary/'bench'),mode,record['xz'],record['raw'],'150'],text=True))
                row.update(block=block,input=record['name'],variant=name);rows.append(row)
                with (out/'samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            print('tree diagnostic block',block+1,'complete',flush=True)
        summary=[]
        for record in selected:
            for name,_,_ in conditions:
                ratios=[]
                for block in range(5):
                    cell={r['variant']:r for r in rows if r['input']==record['name'] and r['block']==block}
                    ratios.append(cell[name]['cpu_seconds']/cell['word-single']['cpu_seconds'])
                summary.append(dict(input=record['name'],variant=name,median_paired_cpu_ratio=statistics.median(ratios),ratios=ratios))
        result.update(status='complete',observations=len(rows),summary=summary,selected_blocks=selected,
            object_size={name:subprocess.check_output(['size',out/name/'xz_dec_lzma2.o'],text=True) for name in ['prepared','tree-unrolled']},
            binaries={name:sha(out/name/'bench') for name in ['prepared','tree-unrolled']})
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:save(out/'result.json',result)
    print('tree diagnostic complete; no production version changed')

if __name__=='__main__':main()
