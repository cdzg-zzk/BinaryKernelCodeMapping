/* Diagnostic only: interpose decoder APIs to count work, never time this build. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <lzma.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "sq_xz_api.h"
static _Atomic unsigned long long common_calls, common_in, common_out;
static _Atomic unsigned long long library_calls, library_in, library_out;
static _Atomic unsigned long long stream_calls, stream_in, stream_out;
enum xz_ret vkso_xz_dec_run(struct xz_dec *s, struct xz_buf *b)
{
    enum xz_ret (*next)(struct xz_dec *,struct xz_buf *)=dlsym(RTLD_NEXT,"vkso_xz_dec_run");
    if (!next) abort();
    size_t in=b->in_pos,out=b->out_pos;
    enum xz_ret r=next(s,b);
    atomic_fetch_add(&common_calls,1);atomic_fetch_add(&common_in,b->in_pos-in);atomic_fetch_add(&common_out,b->out_pos-out);
    return r;
}
lzma_ret lzma_stream_buffer_decode(uint64_t *limit,uint32_t flags,const lzma_allocator *allocator,
    const uint8_t *input,size_t *in_pos,size_t in_size,uint8_t *output,size_t *out_pos,size_t out_size)
{
    lzma_ret (*next)(uint64_t *,uint32_t,const lzma_allocator *,const uint8_t *,size_t *,size_t,uint8_t *,size_t *,size_t)=dlsym(RTLD_NEXT,"lzma_stream_buffer_decode");
    if (!next) abort();
    size_t in=*in_pos,out=*out_pos;
    lzma_ret r=next(limit,flags,allocator,input,in_pos,in_size,output,out_pos,out_size);
    atomic_fetch_add(&library_calls,1);atomic_fetch_add(&library_in,*in_pos-in);atomic_fetch_add(&library_out,*out_pos-out);
    return r;
}
lzma_ret lzma_code(lzma_stream *s,lzma_action action)
{
    lzma_ret (*next)(lzma_stream *,lzma_action)=dlsym(RTLD_NEXT,"lzma_code");
    if (!next) abort();
    size_t in=s->avail_in,out=s->avail_out;
    lzma_ret r=next(s,action);
    atomic_fetch_add(&stream_calls,1);atomic_fetch_add(&stream_in,in-s->avail_in);atomic_fetch_add(&stream_out,out-s->avail_out);
    return r;
}
__attribute__((destructor)) static void finish(void)
{
    const char *path=getenv("VKSO_DECODER_COUNTS");if (!path)return;
    FILE *f=fopen(path,"w");if (!f)abort();
    fprintf(f,"{\"common\":{\"calls\":%llu,\"input\":%llu,\"output\":%llu},\"buffer_library\":{\"calls\":%llu,\"input\":%llu,\"output\":%llu},\"stream_library\":{\"calls\":%llu,\"input\":%llu,\"output\":%llu}}\n",
        common_calls,common_in,common_out,library_calls,library_in,library_out,stream_calls,stream_in,stream_out);
    fclose(f);
}
