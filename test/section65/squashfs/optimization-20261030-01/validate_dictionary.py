#!/usr/bin/env python3
"""Differential dictionary semantics and valid-stream tests, outside timing."""
import argparse, hashlib, json, lzma, random, subprocess
from pathlib import Path

SOURCE=Path(__file__).resolve().parent
HARNESS=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
struct dictionary {uint8_t *buf;size_t pos,full,limit,end,size;};
ORIGINAL
CANDIDATE
static uint32_t state=653002;
static uint32_t rng(void){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
int main(void){
 size_t sizes[]={1,2,3,7,8,9,15,16,17,31,32,33,127,128,129,4096};
 size_t tests=0;
 for(size_t s=0;s<sizeof(sizes)/sizeof(sizes[0]);s++)for(int trial=0;trial<4096;trial++){
  size_t n=sizes[s];uint8_t *a=malloc(n),*b=malloc(n);
  for(size_t j=0;j<n;j++)a[j]=(uint8_t)rng();memcpy(b,a,n);
  size_t pos=rng()%n,limit=pos+1+rng()%(n-pos);
  struct dictionary x={a,pos,n,limit,n,n},y=x;y.buf=b;
  uint32_t dist=(trial%4==0)?0:(trial%4==1?7:rng()%n);
  uint32_t lx=1+rng()%(n+16),ly=lx;
  bool rx=original(&x,&lx,dist),ry=candidate(&y,&ly,dist);
  if(rx!=ry||lx!=ly||x.pos!=y.pos||x.full!=y.full||memcmp(a,b,n)){
   fprintf(stderr,"mismatch n=%zu pos=%zu limit=%zu dist=%u trial=%d\n",n,pos,limit,dist,trial);return 1;
  }
  free(a);free(b);tests++;
 }
 printf("%zu differential dictionary states passed\n",tests);return 0;
}
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--diagnostic',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--variant',default='dictionary-word');a=p.parse_args()
    diag=a.diagnostic.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    def body(path):
        text=path.read_text();start=text.index('static bool dict_repeat(');end=text.index('/* Copy uncompressed data',start)
        return text[start:end].strip()
    original=body(diag/'prepared/xz_dec_lzma2.c').replace('dict_repeat(','original(',1)
    candidate=body(diag/a.variant/'xz_dec_lzma2.c').replace('dict_repeat(','candidate(',1)
    src=out/'dictionary_states.c';src.write_text(HARNESS.replace('ORIGINAL',original).replace('CANDIDATE',candidate))
    command=['gcc','-O2','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(src),'-o',str(out/'dictionary_states')]
    subprocess.run(command,check=True)
    state_result=subprocess.check_output([out/'dictionary_states'],text=True)
    rng=random.Random(653003);checks=[]
    sizes=[0,1,7,8,9,31,32,33,4095,4096,4097,131071,131072,131073,262144]
    for size in sizes:
        for kind in ['one','period7','period32','random']:
            data=(b'x'*size if kind=='one' else
                  (b'abcdefg'*((size+6)//7))[:size] if kind=='period7' else
                  (bytes(range(32))*((size+31)//32))[:size] if kind=='period32' else rng.randbytes(size))
            filters=[{'id':lzma.FILTER_LZMA2,'dict_size':4096}]
            packed=lzma.compress(data,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32,filters=filters)
            stem=f'{kind}-{size}';xp=out/(stem+'.xz');rp=out/(stem+'.raw');xp.write_bytes(packed);rp.write_bytes(data)
            for variant in ['prepared',a.variant]:
                for mode in ['single','prealloc']:
                    command=[str(diag/variant/'bench'),mode,str(xp),str(rp),'2']
                    result=json.loads(subprocess.check_output(command,text=True))
                    assert result['valid'];checks.append(dict(input=stem,variant=variant,mode=mode))
    data=bytes(range(256))*1024
    packed=lzma.compress(data,check=lzma.CHECK_CRC32,filters=[{'id':lzma.FILTER_X86},{'id':lzma.FILTER_LZMA2,'dict_size':4096}])
    xp=out/'bcj.xz';rp=out/'bcj.raw';xp.write_bytes(packed);rp.write_bytes(data)
    for variant in ['prepared',a.variant]:
        for mode in ['single','prealloc']:
            subprocess.run([diag/variant/'bench',mode,xp,rp,'2'],check=True,stdout=subprocess.DEVNULL)
            checks.append(dict(input='bcj',variant=variant,mode=mode))
    result=dict(status='pass',scope='Valid user-space inputs only; not a guest malformed-image or native/PFN regression',
                dictionary_states=65536,state_result=state_result,decoder_checks=len(checks),checks=checks,
                candidate_sha256=hashlib.sha256((diag/a.variant/'xz_dec_lzma2.c').read_bytes()).hexdigest(),variant=a.variant)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(state_result.strip());print('valid-stream checks:',len(checks))
if __name__=='__main__':main()
