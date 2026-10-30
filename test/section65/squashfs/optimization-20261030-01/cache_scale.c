// Valid original-image diagnostic only; never used for application timings.
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <malloc.h>
#include <sys/stat.h>
struct metadata { uint64_t size,ino,blocks,rdev; int64_t sec,nsec; uint32_t mode,uid,gid,nlink; };
static void *(*sq_open_image)(const char*,uint64_t),*(*sq_root_inode)(void*),*(*sq_lookup_child)(void*,const char*,unsigned);
static void (*sq_inode_pin)(void*),(*sq_inode_release)(void*),(*sq_inode_metadata)(void*,struct metadata*),(*sq_close_image)(void*),(*sq_cache_stats)(void*,uint64_t*);
static int (*sq_list_inode)(void*,int(*)(void*,const char*,int),void*);
struct names {char **v;size_t n,cap;};
static int collect(void *opaque,const char *name,int len) {
    struct names *v=opaque;
    if(v->n==v->cap){v->cap=v->cap?2*v->cap:32;v->v=realloc(v->v,v->cap*sizeof(char*));assert(v->v);}
    v->v[v->n]=strndup(name,len);assert(v->v[v->n]);v->n++;return 0;
}
static uint64_t walk(void *inode) {
    struct metadata m;sq_inode_metadata(inode,&m);uint64_t count=1;
    if(!S_ISDIR(m.mode))return count;
    sq_inode_pin(inode);struct names names={0};assert(sq_list_inode(inode,collect,&names)==0);
    for(size_t i=0;i<names.n;i++) {
        void *child=sq_lookup_child(inode,names.v[i],strlen(names.v[i]));assert(child);
        count+=walk(child);free(names.v[i]);
    }
    free(names.v);sq_inode_release(inode);return count;
}
static void snapshot(void *im,const char *phase,uint64_t count) {
    uint64_t values[8];sq_cache_stats(im,values);assert(values[0]<=2048 && values[1]<=4096);
    FILE *f=fopen("/proc/self/smaps_rollup","r");assert(f);char line[256];unsigned long pss=0,rss=0;
    while(fgets(line,sizeof(line),f)){if(sscanf(line,"Pss: %lu kB",&pss)==1)continue;sscanf(line,"Rss: %lu kB",&rss);}fclose(f);
    struct mallinfo2 m=mallinfo2();
    printf("{\"phase\":\"%s\",\"entries\":%llu,\"pss_kib\":%lu,\"rss_kib\":%lu,\"allocated_heap_bytes\":%zu,\"free_arena_bytes\":%zu,\"cache\":[",phase,(unsigned long long)count,pss,rss,m.uordblks,m.fordblks);
    for(int i=0;i<8;i++)printf("%s%llu",i?",":"",(unsigned long long)values[i]);puts("]}");
}
int main(int argc,char **argv) {
    assert(argc==4);void *library=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);if(!library){fprintf(stderr,"%s\n",dlerror());return 1;}
#define LOAD(n) do {*(void**)(&n)=dlsym(library,#n);assert(n);}while(0)
    LOAD(sq_open_image);LOAD(sq_root_inode);LOAD(sq_lookup_child);LOAD(sq_inode_pin);LOAD(sq_inode_release);LOAD(sq_inode_metadata);LOAD(sq_close_image);LOAD(sq_cache_stats);LOAD(sq_list_inode);
    void *im=sq_open_image(argv[2],strtoull(argv[3],NULL,10));assert(im);
    void *inode=sq_root_inode(im);inode=sq_lookup_child(inode,"opt",3);assert(inode);inode=sq_lookup_child(inode,"linux-headers",13);assert(inode);sq_inode_pin(inode);
    snapshot(im,"before",0);
    for(int pass=0;pass<3;pass++){char phase[32];snprintf(phase,sizeof(phase),"scan-%d",pass);snapshot(im,phase,walk(inode));}
    // A diagnostic allocator operation, never installed in the production path.
    malloc_trim(0);snapshot(im,"after-diagnostic-trim",0);
    sq_inode_release(inode);sq_close_image(im);dlclose(library);return 0;
}
