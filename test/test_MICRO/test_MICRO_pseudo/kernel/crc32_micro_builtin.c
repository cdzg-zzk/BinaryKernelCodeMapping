// SPDX-License-Identifier: GPL-2.0
/*
 * Guest-kernel builtin crc32_le_micro(). This is intentionally kept close to
 * the standalone benchmark copy so we can study the same transformation both
 * outside and inside the guest kernel.
 */

#include <linux/crc32poly.h>
#include <linux/compiler.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/types.h>

#define MICRO_CRC32_ROWS 8U
#define MICRO_CRC32_TABLE_SIZE 256U

static u32 crc32table_le_micro[MICRO_CRC32_ROWS][MICRO_CRC32_TABLE_SIZE] __used
	__aligned(64);

static __always_inline u32 (*crc32table_le_micro_base(void))[MICRO_CRC32_TABLE_SIZE]
{
	u32 (*base)[MICRO_CRC32_TABLE_SIZE];

	asm volatile("lea crc32table_le_micro(%%rip), %0" : "=r"(base));
	return base;
}

static void __init init_crc32_le_micro_table(void)
{
	u32 (*table)[MICRO_CRC32_TABLE_SIZE] = crc32table_le_micro_base();
	unsigned int i, j;
	u32 crc = 1U;

	table[0][0] = 0;

	for (i = MICRO_CRC32_TABLE_SIZE >> 1; i; i >>= 1) {
		crc = (crc >> 1) ^ ((crc & 1U) ? CRC32_POLY_LE : 0U);
		for (j = 0; j < MICRO_CRC32_TABLE_SIZE; j += 2 * i)
			table[0][i + j] = crc ^ table[0][j];
	}

	for (i = 0; i < MICRO_CRC32_TABLE_SIZE; i++) {
		crc = table[0][i];
		for (j = 1; j < MICRO_CRC32_ROWS; j++) {
			crc = table[0][crc & 0xffU] ^ (crc >> 8);
			table[j][i] = crc;
		}
	}
}

static noinline u32 crc32_body_micro(u32 crc, unsigned char const *buf,
				     size_t len)
{
	u32 (*table)[MICRO_CRC32_TABLE_SIZE] = crc32table_le_micro_base();
	const u32 *t0 = table[0];
	const u32 *t1 = table[1];
	const u32 *t2 = table[2];
	const u32 *t3 = table[3];
	const u32 *t4 = table[4];
	const u32 *t5 = table[5];
	const u32 *t6 = table[6];
	const u32 *t7 = table[7];
	const u32 *b;
	size_t rem_len;
	size_t i;
	u32 q;

	if (unlikely(((unsigned long)buf & 3U) && len)) {
		do {
			crc = t0[(crc ^ *buf++) & 0xffU] ^ (crc >> 8);
		} while ((--len) && ((unsigned long)buf & 3U));
	}

	rem_len = len & 7U;
	len >>= 3;

	b = (const u32 *)buf;
	--b;
	for (i = 0; i < len; i++) {
		q = crc ^ *++b;
		crc = t7[q & 0xffU] ^ t6[(q >> 8) & 0xffU] ^
		      t5[(q >> 16) & 0xffU] ^ t4[(q >> 24) & 0xffU];
		q = *++b;
		crc ^= t3[q & 0xffU] ^ t2[(q >> 8) & 0xffU] ^
		       t1[(q >> 16) & 0xffU] ^ t0[(q >> 24) & 0xffU];
	}

	if (rem_len) {
		unsigned char const *p = (unsigned char const *)(b + 1) - 1;

		for (i = 0; i < rem_len; i++)
			crc = t0[(crc ^ *++p) & 0xffU] ^ (crc >> 8);
	}

	return crc;
}

u32 crc32_le_micro(u32 crc, unsigned char const *p, size_t len)
{
	return crc32_body_micro(crc, p, len);
}
EXPORT_SYMBOL(crc32_le_micro);

static int __init crc32_le_micro_init(void)
{
	init_crc32_le_micro_table();
	return 0;
}
core_initcall(crc32_le_micro_init);
