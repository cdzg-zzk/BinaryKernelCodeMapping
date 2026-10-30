/* Dynamic copied/shared harness: same modes, user services and actual blocks. */
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <zlib.h>
#include "sq_xz_api.h"
#include "xz_services.h"
static void release(const void *p){free((void *)p);}
static uint32_t checksum(const uint8_t *p,size_t n,uint32_t c){return crc32_z(c,p,n);}
static double seconds(clockid_t c){struct timespec t;clock_gettime(c,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static unsigned char *load(const char *path,size_t *n){
 FILE *f=fopen(path,"rb");if(!f){perror(path);exit(2);}fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);
 unsigned char *p=malloc(*n?*n:1);if(!p||fread(p,1,*n,f)!=*n)exit(2);fclose(f);return p;
}
int main(int argc,char **argv){
 if(argc!=7){fprintf(stderr,"CORE BRIDGE MODE XZ RAW REPEATS\n");return 2;}
 void *core=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);if(!core){fprintf(stderr,"%s\n",dlerror());return 3;}
 void *bridge=dlopen(argv[2],RTLD_NOW|RTLD_GLOBAL);if(!bridge){fprintf(stderr,"%s\n",dlerror());return 3;}
 struct xz_dec *(*init)(enum xz_mode,uint32_t)=dlsym(core,"vkso_xz_dec_init");
 void (*reset)(struct xz_dec *)=dlsym(core,"vkso_xz_dec_reset");
 enum xz_ret (*run)(struct xz_dec *,struct xz_buf *)=dlsym(core,"vkso_xz_dec_run");
 void (*end)(struct xz_dec *)=dlsym(core,"vkso_xz_dec_end");
 void (*bind)(const struct sq_xz_services *)=dlsym(core,"sq_bind_xz");
 if(!init||!reset||!run||!end||!bind)return 4;
 const struct sq_xz_services services={malloc,malloc,release,release,memcpy,memmove,memset,memcmp,checksum};bind(&services);
 size_t ni,no;unsigned char *in=load(argv[4],&ni),*ref=load(argv[5],&no),*out=malloc(no+1);
 int prealloc=!strcmp(argv[3],"prealloc"),repeats=atoi(argv[6]);if(!out||repeats<1)return 5;
 struct xz_dec *d=init(prealloc?XZ_PREALLOC:XZ_SINGLE,1U<<20);if(!d)return 5;
 printf("{\"status\":\"ready\",\"pid\":%ld}\n",(long)getpid());fflush(stdout);
 if(getchar()!='\n')return 6;
 double wall=0,cpu=0;
 for(int k=-1;k<repeats;k++){
  double w=seconds(CLOCK_MONOTONIC_RAW),c=seconds(CLOCK_PROCESS_CPUTIME_ID);
  if(prealloc)reset(d);
  struct xz_buf b={.in=in,.in_size=ni,.out=out,.out_size=no+1};
  if(run(d,&b)!=XZ_STREAM_END||b.in_pos!=ni||b.out_pos!=no)return 7;
  double dc=seconds(CLOCK_PROCESS_CPUTIME_ID)-c,dw=seconds(CLOCK_MONOTONIC_RAW)-w;
  if(memcmp(ref,out,no))return 8;
  if(k>=0){wall+=dw;cpu+=dc;}
 }
 end(d);free(in);free(ref);free(out);
 printf("{\"valid\":true,\"repeats\":%d,\"wall_seconds\":%.9f,\"cpu_seconds\":%.9f}\n",repeats,wall,cpu);
 dlclose(bridge);dlclose(core);return 0;
}
