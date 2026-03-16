/* zutil.c -- kernel-adapted utility functions for the compression library
 * Derived from zlib 1.2.11 zutil.c
 * Copyright (C) 1995-2017 Jean-loup Gailly
 * For conditions of distribution and use, see copyright notice in zlib.h
 */

#include "zutil.h"

z_const char * const z_errmsg[10] = {
	(z_const char *)"need dictionary",     /* Z_NEED_DICT       2  */
	(z_const char *)"stream end",          /* Z_STREAM_END      1  */
	(z_const char *)"",                    /* Z_OK              0  */
	(z_const char *)"file error",          /* Z_ERRNO         (-1) */
	(z_const char *)"stream error",        /* Z_STREAM_ERROR  (-2) */
	(z_const char *)"data error",          /* Z_DATA_ERROR    (-3) */
	(z_const char *)"insufficient memory", /* Z_MEM_ERROR     (-4) */
	(z_const char *)"buffer error",        /* Z_BUF_ERROR     (-5) */
	(z_const char *)"incompatible version",/* Z_VERSION_ERROR (-6) */
	(z_const char *)""
};

/*
 * Keep the version-string pointer in writable data so the rodata reference is
 * carried by a data relocation instead of being materialized in .text.
 */
static struct {
	const char *version;
} zlib_pic_ctx __attribute__((section(".data"))) = {
	.version = ZLIB_VERSION,
};

struct zutil_pic_ctx_s {
	void *(*kvmalloc)(size_t size, gfp_t flags);
	void (*kvfree)(const void *ptr);
};

static struct zutil_pic_ctx_s zutil_pic_ctx __attribute__((section(".data"))) = {
	.kvmalloc = kvmalloc,
	.kvfree = kvfree,
};

const char * ZEXPORT zlibVersion(void)
{
	return zlib_pic_ctx.version;
}

uLong ZEXPORT zlibCompileFlags(void)
{
	uLong flags;

	flags = 0;
	switch ((int)(sizeof(uInt))) {
	case 2:		break;
	case 4:		flags += 1;		break;
	case 8:		flags += 2;		break;
	default:	flags += 3;
	}
	switch ((int)(sizeof(uLong))) {
	case 2:		break;
	case 4:		flags += 1 << 2;	break;
	case 8:		flags += 2 << 2;	break;
	default:	flags += 3 << 2;
	}
	switch ((int)(sizeof(voidpf))) {
	case 2:		break;
	case 4:		flags += 1 << 4;	break;
	case 8:		flags += 2 << 4;	break;
	default:	flags += 3 << 4;
	}
	switch ((int)(sizeof(z_off_t))) {
	case 2:		break;
	case 4:		flags += 1 << 6;	break;
	case 8:		flags += 2 << 6;	break;
	default:	flags += 3 << 6;
	}
#ifdef ZLIB_DEBUG
	flags += 1 << 8;
#endif
#if defined(ASMV) || defined(ASMINF)
	flags += 1 << 9;
#endif
#ifdef ZLIB_WINAPI
	flags += 1 << 10;
#endif
#ifdef BUILDFIXED
	flags += 1 << 12;
#endif
#ifdef DYNAMIC_CRC_TABLE
	flags += 1 << 13;
#endif
#ifdef NO_GZCOMPRESS
	flags += 1L << 16;
#endif
#ifdef NO_GZIP
	flags += 1L << 17;
#endif
#ifdef PKZIP_BUG_WORKAROUND
	flags += 1L << 20;
#endif
#ifdef FASTEST
	flags += 1L << 21;
#endif
#if defined(STDC) || defined(Z_HAVE_STDARG_H)
# ifdef NO_vsnprintf
	flags += 1L << 25;
#  ifdef HAS_vsprintf_void
	flags += 1L << 26;
#  endif
# else
#  ifdef HAS_vsnprintf_void
	flags += 1L << 26;
#  endif
# endif
#else
	flags += 1L << 24;
# ifdef NO_snprintf
	flags += 1L << 25;
#  ifdef HAS_sprintf_void
	flags += 1L << 26;
#  endif
# else
#  ifdef HAS_snprintf_void
	flags += 1L << 26;
#  endif
# endif
#endif
	return flags;
}

#ifdef ZLIB_DEBUG
# ifndef verbose
#  define verbose 0
# endif
int ZLIB_INTERNAL z_verbose = verbose;

void ZLIB_INTERNAL z_error(m)
	char *m;
{
	panic("zlib_lkm: %s\n", m);
}
#endif

const char * ZEXPORT zError(err)
	int err;
{
	return ERR_MSG(err);
}

#ifndef HAVE_MEMCPY
void ZLIB_INTERNAL zmemcpy(dest, source, len)
	Bytef *dest;
	const Bytef *source;
	uInt len;
{
	if (len == 0)
		return;
	do {
		*dest++ = *source++;
	} while (--len != 0);
}

int ZLIB_INTERNAL zmemcmp(s1, s2, len)
	const Bytef *s1;
	const Bytef *s2;
	uInt len;
{
	uInt j;

	for (j = 0; j < len; j++) {
		if (s1[j] != s2[j])
			return 2 * (s1[j] > s2[j]) - 1;
	}
	return 0;
}

void ZLIB_INTERNAL zmemzero(dest, len)
	Bytef *dest;
	uInt len;
{
	if (len == 0)
		return;
	do {
		*dest++ = 0;
	} while (--len != 0);
}
#endif

#ifndef Z_SOLO
voidpf ZLIB_INTERNAL zcalloc(opaque, items, size)
	voidpf opaque;
	unsigned items;
	unsigned size;
{
	size_t bytes;
	volatile struct zutil_pic_ctx_s *ctx = &zutil_pic_ctx;

	(void)opaque;
	if (check_mul_overflow((size_t)items, (size_t)size, &bytes))
		return Z_NULL;
	if (bytes == 0)
		bytes = 1;
	return ctx->kvmalloc(bytes, GFP_KERNEL);
}

void ZLIB_INTERNAL zcfree(opaque, ptr)
	voidpf opaque;
	voidpf ptr;
{
	volatile struct zutil_pic_ctx_s *ctx = &zutil_pic_ctx;

	(void)opaque;
	ctx->kvfree(ptr);
}
#endif
