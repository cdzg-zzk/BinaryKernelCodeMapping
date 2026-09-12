#ifndef XZ_CONFIG_H
#define XZ_CONFIG_H

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "xz.h"

#define XZ_DEC_SINGLE
#define XZ_DEC_X86
#define XZ_INTERNAL_CRC32 1

#define GFP_KERNEL 0
#define kmalloc(size, flags) malloc(size)
#define kfree(ptr) free(ptr)
#define vmalloc(size) malloc(size)
#define vfree(ptr) free(ptr)
#define memeq(a, b, size) (memcmp((a), (b), (size)) == 0)
#define memzero(buf, size) memset((buf), 0, (size))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define __used __attribute__((used))
#define fallthrough __attribute__((fallthrough))

static inline uint32_t xz_get_le32(const void *ptr)
{
	const uint8_t *p = ptr;
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
		| ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline uint32_t xz_get_be32(const void *ptr)
{
	const uint8_t *p = ptr;
	return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
		| ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static inline void xz_put_le32(uint32_t value, void *ptr)
{
	uint8_t *p = ptr;
	p[0] = (uint8_t)value;
	p[1] = (uint8_t)(value >> 8);
	p[2] = (uint8_t)(value >> 16);
	p[3] = (uint8_t)(value >> 24);
}

static inline void xz_put_be32(uint32_t value, void *ptr)
{
	uint8_t *p = ptr;
	p[0] = (uint8_t)(value >> 24);
	p[1] = (uint8_t)(value >> 16);
	p[2] = (uint8_t)(value >> 8);
	p[3] = (uint8_t)value;
}

#define get_le32(p) xz_get_le32(p)
#define get_unaligned_le32(p) xz_get_le32(p)
#define get_unaligned_be32(p) xz_get_be32(p)
#define put_unaligned_le32(v, p) xz_put_le32((v), (p))
#define put_unaligned_be32(v, p) xz_put_be32((v), (p))

#endif
