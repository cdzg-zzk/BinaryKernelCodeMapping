#!/usr/bin/env python3
"""Differential one-bit range state transitions; valid-stream tests are separate."""
import argparse, hashlib, json, subprocess
from pathlib import Path

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
ORIGINAL
CANDIDATE
static uint32_t state=653004;
static uint32_t rng(void){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
int main(void){
 size_t tests=0;uint8_t input[8];
 for(unsigned probability=0;probability<=RC_BIT_MODEL_TOTAL;probability++)for(int k=0;k<256;k++){
  for(int j=0;j<8;j++)input[j]=(uint8_t)rng();
  struct rc_dec a;memset(&a,0,sizeof(a));a.range=rng();a.code=rng();a.in=input;
  if(k<4)a.range=(uint32_t[]){0,RC_TOP_VALUE-1,RC_TOP_VALUE,UINT32_MAX}[k];
  struct rc_dec b;memcpy(&b,&a,sizeof(a));uint16_t pa=probability,pb=probability;
  int x=original(&a,&pa),y=candidate(&b,&pb);
  if(x!=y||pa!=pb||memcmp(&a,&b,sizeof(a))){fprintf(stderr,"range mismatch p=%u k=%d\n",probability,k);return 1;}
  tests++;
 }
 printf("%zu range transitions passed\n",tests);return 0;
}
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--diagnostic',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    diag=a.diagnostic.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    base=(diag/'prepared/xz_dec_lzma2.c').read_text();new=(diag/'dictionary-word-branchless/xz_dec_lzma2.c').read_text()
    def extract(text,start,end):
        i=text.index(start);j=text.index(end,i)+len(end);return text[i:j]
    struct=extract(base,'struct rc_dec {','\n};')
    normalize=extract(base,'static __always_inline void rc_normalize(','\n}')
    original=extract(base,'static __always_inline int rc_bit(','\n}').replace('rc_bit(','original(',1)
    candidate=extract(new,'static __always_inline int rc_bit(','\n}').replace('rc_bit(','candidate(',1)
    source=out/'range_states.c';source.write_text(HARNESS.replace('RC_STRUCT',struct).replace('NORMALIZE',normalize).replace('ORIGINAL',original).replace('CANDIDATE',candidate))
    subprocess.run(['gcc','-O2','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(diag/'prepared'),source,'-o',out/'range_states'],check=True)
    output=subprocess.check_output([out/'range_states'],text=True)
    (out/'result.json').write_text(json.dumps(dict(status='pass',transitions=2049*256,output=output,
        scope='One-bit state/probability transition equality with ASAN/UBSAN, including normalization boundaries; no end-to-end proof',
        candidate_sha256=hashlib.sha256(new.encode()).hexdigest()),indent=2)+'\n');print(output)

if __name__=='__main__':main()
