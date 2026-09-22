/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef APPLICABILITY_PROTOCOL_H
#define APPLICABILITY_PROTOCOL_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u32 ar_u32;
typedef u64 ar_u64;
#else
#include <stddef.h>
#include <stdint.h>
typedef uint32_t ar_u32;
typedef uint64_t ar_u64;
#endif

/* Exact119 public signatures: linux/xxhash.h, linux/sort.h, linux/types.h. */
typedef int (*ar_cmp_fn)(const void *, const void *);
typedef void (*ar_swap_fn)(void *, void *, int);
typedef ar_u32 (*ar_hash_fn)(const void *, size_t, ar_u32);
typedef void (*ar_sort_fn)(void *, size_t, size_t, ar_cmp_fn, ar_swap_fn);
#define AR_HASH_CHECKS 247
#define AR_SORT_CHECKS 1152
#define AR_MAX_HASH 4097
#define AR_MAX_NUM 64
#define AR_MAX_WIDTH 16
#define AR_GUARD 32
#define AR_RAW_SIZE (AR_MAX_HASH + 2 * AR_GUARD + 8)
#define AR_HASH_CAPACITY (AR_HASH_CHECKS * (2 * AR_MAX_HASH + 256))
#define AR_SORT_CAPACITY (AR_SORT_CHECKS * (6 * AR_MAX_NUM * AR_MAX_WIDTH + 512))

static const unsigned int ar_lengths[] = {
	0, 1, 2, 3, 4, 5, 7, 8, 15, 16, 17, 18, 19, 20, 31, 32, 33, 4095, 4096, 4097
};
static const unsigned int ar_hash_alignments[] = {0, 1, 3};
static const ar_u32 ar_seeds[] = {0, 1, 0xffffffffU, 0x9e3779b1U};
static const unsigned int ar_counts[] = {0, 1, 2, 3, 17, 64};
static const unsigned int ar_widths[] = {1, 3, 4, 8, 12, 16};
static const char *const ar_patterns[] = {"ascending", "descending", "duplicates", "permuted"};
struct ar_kat { const char *input; ar_u32 expected; };
/* Independent installed libxxhash 0.8.1 XXH32 oracle, seed=0; see README. */
static const struct ar_kat ar_kats[] = {
	{"", 0x02cc5d05U}, {"a", 0x550d7456U}, {"abc", 0x32d153ffU},
	{"message digest", 0x7c948494U},
	{"abcdefghijklmnopqrstuvwxyz", 0x63a14d5fU},
	{"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 0x9c285e64U},
	{"12345678901234567890123456789012345678901234567890123456789012345678901234567890", 0x9c05f475U},
};
#define AR_COUNT(array) (sizeof(array) / sizeof((array)[0]))

static ar_u32 ar_rotate(ar_u32 value, unsigned int count)
{
	return (value << count) | (value >> (32 - count));
}

static ar_u32 ar_little32(const unsigned char *p)
{
	return (ar_u32)p[0] | (ar_u32)p[1] << 8 | (ar_u32)p[2] << 16 | (ar_u32)p[3] << 24;
}

/* Independent portable byte-load implementation of the XXH32 specification.
 * No kernel xxhash source, assembler clone, or target API is used here. */
static ar_u32 ar_reference_hash(const unsigned char *input, size_t length, ar_u32 seed)
{
	const ar_u32 p1 = 0x9e3779b1U, p2 = 0x85ebca77U, p3 = 0xc2b2ae3dU;
	const ar_u32 p4 = 0x27d4eb2fU, p5 = 0x165667b1U;
	ar_u32 h;
	size_t offset = 0;
	if (length >= 16) {
		ar_u32 lanes[4] = {seed + p1 + p2, seed + p2, seed, seed - p1};
		unsigned int lane;
		while (length - offset >= 16) {
			for (lane = 0; lane < 4; ++lane)
				lanes[lane] = ar_rotate(lanes[lane] +
					ar_little32(input + offset + 4 * lane) * p2, 13) * p1;
			offset += 16;
		}
		h = ar_rotate(lanes[0], 1) + ar_rotate(lanes[1], 7) +
			ar_rotate(lanes[2], 12) + ar_rotate(lanes[3], 18);
	} else {
		h = seed + p5;
	}
	h += (ar_u32)length;
	while (length - offset >= 4) {
		h = ar_rotate(h + ar_little32(input + offset) * p3, 17) * p4;
		offset += 4;
	}
	while (offset < length)
		h = ar_rotate(h + input[offset++] * p5, 11) * p1;
	h = (h ^ (h >> 15)) * p2;
	h = (h ^ (h >> 13)) * p3;
	return h ^ (h >> 16);
}

static ar_u32 ar_random(ar_u32 *state)
{
	*state ^= *state << 13;
	*state ^= *state >> 17;
	*state ^= *state << 5;
	return *state;
}

static void ar_hash_input(unsigned char *data, size_t length, ar_u32 seed)
{
	size_t i;
	ar_u32 state = 0x5eeda17eU ^ seed ^ (ar_u32)length;
	for (i = 0; i < length; ++i)
		data[i] = (unsigned char)ar_random(&state);
}

static int ar_compare_bytes(const unsigned char *a, const unsigned char *b,
			    size_t width, int direction)
{
	size_t i;
	for (i = 0; i < width; ++i) {
		if (a[i] < b[i]) return -direction;
		if (a[i] > b[i]) return direction;
	}
	return 0;
}

static void ar_sort_input(unsigned char *data, size_t num, size_t width, unsigned int pattern)
{
	size_t i, j;
	ar_u32 state = 0x5eeda17eU ^ (ar_u32)num ^ ((ar_u32)width << 16);
	for (i = 0; i < num; ++i) {
		unsigned int value = pattern == 1 ? num - 1 - i : pattern == 2 ? i % 4 : i;
		for (j = 0; j < width; ++j)
			data[i * width + j] = j ? (unsigned char)(value * 37 + j * 13) : value;
	}
	if (pattern == 3) {
		for (i = num; i > 1; --i) {
			size_t chosen = ar_random(&state) % i;
			for (j = 0; j < width; ++j) {
				unsigned char byte = data[(i - 1) * width + j];
				data[(i - 1) * width + j] = data[chosen * width + j];
				data[chosen * width + j] = byte;
			}
		}
	}
}

/* Stable insertion reference, distinct from the target's heapsort. Equal
 * comparator keys imply equal complete element bytes, so stability is irrelevant. */
static void ar_reference_sort(unsigned char *data, size_t num, size_t width, int direction)
{
	unsigned char saved[AR_MAX_WIDTH];
	size_t i, j, k;
	for (i = 1; i < num; ++i) {
		for (k = 0; k < width; ++k) saved[k] = data[i * width + k];
		for (j = i; j && ar_compare_bytes(data + (j - 1) * width, saved, width, direction) > 0; --j)
			for (k = 0; k < width; ++k) data[j * width + k] = data[(j - 1) * width + k];
		for (k = 0; k < width; ++k) data[j * width + k] = saved[k];
	}
}
#endif
