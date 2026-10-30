// SPDX-License-Identifier: GPL-2.0-or-later
/* POSIX/compression bindings, isolated from the pinned kernel header ABI. */
#define _FILE_OFFSET_BITS 64
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>
#include <lzma.h>
#include <zstd.h>
#include <lz4.h>
#include <lzo/lzo1x.h>
#if defined(VKSO_SQ_SHARED_XZ) || defined(VKSO_SQ_BIND_XZ)
#include <string.h>
#include "xz_services.h"
static void xz_user_free(const void *p) { free((void *)p); }
static uint32_t xz_user_crc(const uint8_t *p, size_t n, uint32_t crc)
{ return (uint32_t)crc32_z(crc, p, n); }
static void __attribute__((constructor)) bind_xz(void)
{
    const struct sq_xz_services services = {
        .alloc=malloc, .valloc=malloc, .free=xz_user_free, .vfree=xz_user_free,
        .copy=memcpy, .move=memmove, .set=memset, .compare=memcmp, .crc32=xz_user_crc,
    };
    sq_bind_xz(&services);
}
#endif
#if defined(VKSO_SQ_SHARED_LZ4) || defined(VKSO_SQ_BIND_LZ4)
#include <string.h>
extern int vkso_LZ4_decompress_safe(const char *,char *,int,int);
extern void sq_bind_lz4(void *(*)(void *,const void *,size_t),
                        void *(*)(void *,const void *,size_t),
                        void *(*)(void *,int,size_t));
static void __attribute__((constructor)) bind_lz4(void)
{
    sq_bind_lz4(memcpy,memmove,memset);
}
#endif
#include "profile.h"
#ifdef VKSO_SQ_PROFILE
#include <time.h>
unsigned long long sq_profile_clock(void)
{
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC_RAW,&ts);
    return (unsigned long long)ts.tv_sec*1000000000ULL+ts.tv_nsec;
}
#endif

int sq_posix_open(const char *path, uint64_t offset, uint64_t *bytes)
{
    struct stat st;
    int fd=open(path,O_RDONLY|O_CLOEXEC);
    if (fd<0) return -errno;
    if (fstat(fd,&st)<0) { int e=errno; close(fd); return -e; }
    if (st.st_size<0 || offset>(uint64_t)st.st_size) { close(fd); return -EINVAL; }
    *bytes=(uint64_t)st.st_size-offset;
    return fd;
}

struct codec {
    int id;
    z_stream z;
#ifdef VKSO_SQ_SHARED_XZ
    struct xz_dec *xz;
#else
    lzma_stream xz;
#endif
    ZSTD_DCtx *zstd;
};

void sq_codec_close(void *handle)
{
    struct codec *c=handle;
    if (!c) return;
    if (c->id==1) inflateEnd(&c->z);
#ifdef VKSO_SQ_SHARED_XZ
    if (c->id==4) xz_dec_end(c->xz);
#else
    if (c->id==4) lzma_end(&c->xz);
#endif
    if (c->id==6) ZSTD_freeDCtx(c->zstd);
    free(c);
}

void *sq_codec_open(int id)
{
    struct codec *c=calloc(1,sizeof(*c));
    if (!c) return NULL;
    c->id=id;
    if ((id==1 && inflateInit(&c->z)!=Z_OK) ||
#ifdef VKSO_SQ_SHARED_XZ
        (id==4 && !(c->xz=xz_dec_init(XZ_SINGLE,0))) ||
#endif
        (id==3 && lzo_init()!=LZO_E_OK) ||
        (id==6 && !(c->zstd=ZSTD_createDCtx()))) {
        sq_codec_close(c); return NULL;
    }
    return c;
}

static int codec_decode(void *handle, const void *input, size_t n, void *output, size_t capacity)
{
    struct codec *c=handle;
    size_t result;
    switch (c->id) {
    case 1:
        if (inflateReset(&c->z)!=Z_OK) return -EIO;
        c->z.next_in=(void *)input; c->z.avail_in=n;
        c->z.next_out=output; c->z.avail_out=capacity;
        if (inflate(&c->z,Z_FINISH)!=Z_STREAM_END || c->z.avail_in) return -EIO;
        return c->z.total_out;
    case 3: {
        lzo_uint size=capacity;
        if (lzo1x_decompress_safe(input,n,output,&size,NULL)!=LZO_E_OK) return -EIO;
        return size;
    }
    case 4:
#ifdef VKSO_SQ_SHARED_XZ
    {
        struct xz_buf b = {.in=input, .in_size=n, .out=output, .out_size=capacity};
        if (xz_dec_run(c->xz,&b)!=XZ_STREAM_END || b.in_pos!=n) return -EIO;
        return b.out_pos;
    }
#else
        if (lzma_stream_decoder(&c->xz,UINT64_MAX,0)!=LZMA_OK) return -ENOMEM;
        c->xz.next_in=input; c->xz.avail_in=n;
        c->xz.next_out=output; c->xz.avail_out=capacity;
        if (lzma_code(&c->xz,LZMA_FINISH)!=LZMA_STREAM_END || c->xz.avail_in) return -EIO;
        return c->xz.total_out;
#endif
    case 5:
#ifdef VKSO_SQ_SHARED_LZ4
        result=vkso_LZ4_decompress_safe(input,output,n,capacity);
#else
        result=LZ4_decompress_safe(input,output,n,capacity);
#endif
        return (int)result<0 ? -EIO : (int)result;
    case 6:
        result=ZSTD_decompressDCtx(c->zstd,output,capacity,input,n);
        return ZSTD_isError(result) ? -EIO : (int)result;
    default: return -EOPNOTSUPP;
    }
}
int sq_codec_decode(void *handle, const void *input, size_t n, void *output, size_t capacity)
{
    SQ_START(start);
    int ret=codec_decode(handle,input,n,output,capacity);
    SQ_COUNT(codec_calls,1); SQ_COUNT(codec_input_bytes,n);
    if (ret>=0) SQ_COUNT(codec_output_bytes,ret);
    SQ_ELAPSED(codec_ns,start);
    return ret;
}
