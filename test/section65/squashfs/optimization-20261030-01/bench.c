/* Fixed-input diagnostic. No PFN-sharing or complete-application timing claim. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <lzma.h>
#include <zlib.h>
#include "sq_xz_api.h"
#ifndef ORDINARY_XZ
#include "xz_services.h"
static void release(const void *p){free((void *)p);}
static uint32_t checksum(const uint8_t *p,size_t n,uint32_t c){return crc32_z(c,p,n);}
#endif
static double clock_s(clockid_t clock){struct timespec t;clock_gettime(clock,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static unsigned char *load(const char *path,size_t *n){
 FILE *f=fopen(path,"rb");if(!f){perror(path);exit(2);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);
 unsigned char *p=malloc(*n?*n:1);if(!p||fread(p,1,*n,f)!=*n)exit(2);fclose(f);return p;
}
int main(int argc,char **argv){
 if(argc!=5){fprintf(stderr,"MODE XZ RAW REPEATS\n");return 2;}
 size_t ni,no;unsigned char *in=load(argv[2],&ni),*ref=load(argv[3],&no),*out=malloc(no+1);
 int library=!strcmp(argv[1],"library"),prealloc=!strcmp(argv[1],"prealloc"),repeat=atoi(argv[4]);
 if(!out||repeat<1)return 2;
#ifndef ORDINARY_XZ
 const struct sq_xz_services services={malloc,malloc,release,release,memcpy,memmove,memset,memcmp,checksum};
 sq_bind_xz(&services);
#else
 xz_crc32_init();
#endif
 struct xz_dec *d=library?NULL:xz_dec_init(prealloc?XZ_PREALLOC:XZ_SINGLE,1U<<20);
 lzma_stream stream=LZMA_STREAM_INIT;
 if(!library&&!d)return 3;
 double elapsed=0,cpu=0;
 for(int i=-1;i<repeat;i++){
  double w=clock_s(CLOCK_MONOTONIC_RAW),c=clock_s(CLOCK_PROCESS_CPUTIME_ID);
  if(library){
   if(lzma_stream_decoder(&stream,UINT64_MAX,0)!=LZMA_OK)return 4;
   stream.next_in=in;stream.avail_in=ni;stream.next_out=out;stream.avail_out=no+1;
   if(lzma_code(&stream,LZMA_FINISH)!=LZMA_STREAM_END||stream.avail_in||stream.total_out!=no)return 5;
  }else{
   if(prealloc)xz_dec_reset(d);
   struct xz_buf b={.in=in,.in_size=ni,.out=out,.out_size=no+1};
   if(xz_dec_run(d,&b)!=XZ_STREAM_END||b.in_pos!=ni||b.out_pos!=no)return 6;
  }
  double dc=clock_s(CLOCK_PROCESS_CPUTIME_ID)-c,dw=clock_s(CLOCK_MONOTONIC_RAW)-w;
  if(memcmp(ref,out,no)){fprintf(stderr,"output mismatch\n");return 7;}
  if(i>=0){elapsed+=dw;cpu+=dc;}
 }
 if(d)xz_dec_end(d);lzma_end(&stream);
 printf("{\"wall_seconds\":%.9f,\"cpu_seconds\":%.9f,\"repeats\":%d,\"input_bytes\":%zu,\"output_bytes\":%zu,\"valid\":true}\n",elapsed,cpu,repeat,ni,no);
 free(in);free(ref);free(out);return 0;
}
