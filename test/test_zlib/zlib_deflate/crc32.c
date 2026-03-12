#include <linux/types.h>
#include <linux/crc32poly.h>
#include <linux/module.h>

// crc32defs.h
/* SPDX-License-Identifier: GPL-2.0 */

/* Try to choose an implementation variant via Kconfig */
#ifdef CONFIG_CRC32_SLICEBY8
# define CRC_LE_BITS 64
# define CRC_BE_BITS 64
#endif
#ifdef CONFIG_CRC32_SLICEBY4
# define CRC_LE_BITS 32
# define CRC_BE_BITS 32
#endif
#ifdef CONFIG_CRC32_SARWATE
# define CRC_LE_BITS 8
# define CRC_BE_BITS 8
#endif
#ifdef CONFIG_CRC32_BIT
# define CRC_LE_BITS 1
# define CRC_BE_BITS 1
#endif

/*
 * How many bits at a time to use.  Valid values are 1, 2, 4, 8, 32 and 64.
 * For less performance-sensitive, use 4 or 8 to save table size.
 * For larger systems choose same as CPU architecture as default.
 * This works well on X86_64, SPARC64 systems. This may require some
 * elaboration after experiments with other architectures.
 */
#ifndef CRC_LE_BITS
#  ifdef CONFIG_64BIT
#  define CRC_LE_BITS 64
#  else
#  define CRC_LE_BITS 32
#  endif
#endif
#ifndef CRC_BE_BITS
#  ifdef CONFIG_64BIT
#  define CRC_BE_BITS 64
#  else
#  define CRC_BE_BITS 32
#  endif
#endif

/*
 * Little-endian CRC computation.  Used with serial bit streams sent
 * lsbit-first.  Be sure to use cpu_to_le32() to append the computed CRC.
 */
#if CRC_LE_BITS > 64 || CRC_LE_BITS < 1 || CRC_LE_BITS == 16 || \
	CRC_LE_BITS & CRC_LE_BITS-1
# error "CRC_LE_BITS must be one of {1, 2, 4, 8, 32, 64}"
#endif

/*
 * Big-endian CRC computation.  Used with serial bit streams sent
 * msbit-first.  Be sure to use cpu_to_be32() to append the computed CRC.
 */
#if CRC_BE_BITS > 64 || CRC_BE_BITS < 1 || CRC_BE_BITS == 16 || \
	CRC_BE_BITS & CRC_BE_BITS-1
# error "CRC_BE_BITS must be one of {1, 2, 4, 8, 32, 64}"
#endif



#if CRC_LE_BITS > 8
# define LE_TABLE_ROWS (CRC_LE_BITS/8)
# define LE_TABLE_SIZE 256
#else
# define LE_TABLE_ROWS 1
# define LE_TABLE_SIZE (1 << CRC_LE_BITS)
#endif

static uint32_t crc32table_le[LE_TABLE_ROWS][256] __used;

static __always_inline u32 (*crc32table_le_base(void))[256]
{
	u32 (*base)[256];

	/*
	 * Force a standalone RIP-relative base load before taking the table
	 * address. This avoids R_X86_64_32S absolute relocations against .bss
	 * when the module is later mapped into user space.
	 */
	asm volatile(
		"lea crc32table_le(%%rip), %0"
		: "=r"(base)
	);
	return base;
}


/**
 * mz_crc32init_le() - initialize LE table data
 *
 * crc is the crc of the byte i; other entries are filled in based on the
 * fact that crctable[i^j] = crctable[i] ^ crctable[j].
 *
 */
static void crc32init_le_generic(const uint32_t polynomial,
				 uint32_t (*tab)[256])
{
	unsigned i, j;
	uint32_t crc = 1;

	tab[0][0] = 0;

	for (i = LE_TABLE_SIZE >> 1; i; i >>= 1) {
		crc = (crc >> 1) ^ ((crc & 1) ? polynomial : 0);
		for (j = 0; j < LE_TABLE_SIZE; j += 2 * i)
			tab[0][i + j] = crc ^ tab[0][j];
	}
	for (i = 0; i < LE_TABLE_SIZE; i++) {
		crc = tab[0][i];
		for (j = 1; j < LE_TABLE_ROWS; j++) {
			crc = tab[0][crc & 0xff] ^ (crc >> 8);
			tab[j][i] = crc;
		}
	}
}

void mz_crc32init_le(void)
{
	crc32init_le_generic(CRC32_POLY_LE, crc32table_le_base());
}


#define __cpu_to_le32(x) ((__force __le32)(__u32)(x))
#define __le32_to_cpu(x) ((__force __u32)(__le32)(x))


/* implements slicing-by-4 or slicing-by-8 algorithm */
static inline u32 __pure
crc32_body(u32 crc, unsigned char const *buf, size_t len, const u32 (*tab)[256])
{
# ifdef __LITTLE_ENDIAN
#  define DO_CRC(x) crc = t0[(crc ^ (x)) & 255] ^ (crc >> 8)
#  define DO_CRC4 (t3[(q) & 255] ^ t2[(q >> 8) & 255] ^ \
		   t1[(q >> 16) & 255] ^ t0[(q >> 24) & 255])
#  define DO_CRC8 (t7[(q) & 255] ^ t6[(q >> 8) & 255] ^ \
		   t5[(q >> 16) & 255] ^ t4[(q >> 24) & 255])
# else
#  define DO_CRC(x) crc = t0[((crc >> 24) ^ (x)) & 255] ^ (crc << 8)
#  define DO_CRC4 (t0[(q) & 255] ^ t1[(q >> 8) & 255] ^ \
		   t2[(q >> 16) & 255] ^ t3[(q >> 24) & 255])
#  define DO_CRC8 (t4[(q) & 255] ^ t5[(q >> 8) & 255] ^ \
		   t6[(q >> 16) & 255] ^ t7[(q >> 24) & 255])
# endif
	const u32 *b;
	size_t    rem_len;
# ifdef CONFIG_X86
	size_t i;
# endif
	const u32 *t0=tab[0], *t1=tab[1], *t2=tab[2], *t3=tab[3];
# if CRC_LE_BITS != 32
	const u32 *t4 = tab[4], *t5 = tab[5], *t6 = tab[6], *t7 = tab[7];
# endif
	u32 q;

	/* Align it */
	if (unlikely((long)buf & 3 && len)) {
		do {
			DO_CRC(*buf++);
		} while ((--len) && ((long)buf)&3);
	}

# if CRC_LE_BITS == 32
	rem_len = len & 3;
	len = len >> 2;
# else
	rem_len = len & 7;
	len = len >> 3;
# endif

	b = (const u32 *)buf;
# ifdef CONFIG_X86
	--b;
	for (i = 0; i < len; i++) {
# else
	for (--b; len; --len) {
# endif
		q = crc ^ *++b; /* use pre increment for speed */
# if CRC_LE_BITS == 32
		crc = DO_CRC4;
# else
		crc = DO_CRC8;
		q = *++b;
		crc ^= DO_CRC4;
# endif
	}
	len = rem_len;
	/* And the last few bytes */
	if (len) {
		u8 *p = (u8 *)(b + 1) - 1;
# ifdef CONFIG_X86
		for (i = 0; i < len; i++)
			DO_CRC(*++p); /* use pre increment for speed */
# else
		do {
			DO_CRC(*++p); /* use pre increment for speed */
		} while (--len);
# endif
	}
	return crc;
#undef DO_CRC
#undef DO_CRC4
#undef DO_CRC8
}
/**
 * crc32_le_generic() - Calculate bitwise little-endian Ethernet AUTODIN II
 *			CRC32/CRC32C
 * @crc: seed value for computation.  ~0 for Ethernet, sometimes 0 for other
 *	 uses, or the previous crc32/crc32c value if computing incrementally.
 * @p: pointer to buffer over which CRC32/CRC32C is run
 * @len: length of buffer @p
 * @tab: little-endian Ethernet table
 * @polynomial: CRC32/CRC32c LE polynomial
 */
static inline u32 __pure crc32_le_generic(u32 crc, unsigned char const *p,
					  size_t len, const u32 (*tab)[256],
					  u32 polynomial)
{
#if CRC_LE_BITS == 1
	int i;
	while (len--) {
		crc ^= *p++;
		for (i = 0; i < 8; i++)
			crc = (crc >> 1) ^ ((crc & 1) ? polynomial : 0);
	}
# elif CRC_LE_BITS == 2
	while (len--) {
		crc ^= *p++;
		crc = (crc >> 2) ^ tab[0][crc & 3];
		crc = (crc >> 2) ^ tab[0][crc & 3];
		crc = (crc >> 2) ^ tab[0][crc & 3];
		crc = (crc >> 2) ^ tab[0][crc & 3];
	}
# elif CRC_LE_BITS == 4
	while (len--) {
		crc ^= *p++;
		crc = (crc >> 4) ^ tab[0][crc & 15];
		crc = (crc >> 4) ^ tab[0][crc & 15];
	}
# elif CRC_LE_BITS == 8
	/* aka Sarwate algorithm */
	while (len--) {
		crc ^= *p++;
		crc = (crc >> 8) ^ tab[0][crc & 255];
	}
# else
	crc = (__force u32) __cpu_to_le32(crc);
	crc = crc32_body(crc, p, len, tab);
	crc = __le32_to_cpu((__force __le32)crc);
#endif
	return crc;
}

static u32 __pure crc32_le(u32 crc, unsigned char const *p, size_t len)
{
	const u32 (*tab)[256] = (const u32 (*)[256])crc32table_le_base();

	return crc32_le_generic(crc, p, len,
			tab, CRC32_POLY_LE);
}

u32 mz_crc32(u32 crc, const unsigned char *p, size_t len)
{
	return crc32_le(crc, p, len);
}

const u32 *mz_get_crc_table(void)
{
	const u32 (*tab)[256] = (const u32 (*)[256])crc32table_le_base();

	return &tab[0][0];
}

EXPORT_SYMBOL(mz_crc32init_le);
EXPORT_SYMBOL(mz_crc32);
EXPORT_SYMBOL(mz_get_crc_table);
