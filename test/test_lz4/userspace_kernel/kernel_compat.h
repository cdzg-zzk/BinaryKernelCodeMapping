#ifndef VKSO_LZ4_KERNEL_COMPAT_H
#define VKSO_LZ4_KERNEL_COMPAT_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define CONFIG_64BIT 1
#define __LITTLE_ENDIAN 1
#define BITS_PER_LONG 64

#ifndef __always_inline
#define __always_inline inline __attribute__((always_inline))
#endif
#define __used __attribute__((used))
#define likely(value) __builtin_expect(!!(value), 1)
#define unlikely(value) __builtin_expect(!!(value), 0)
#define min(left, right) ((left) < (right) ? (left) : (right))
#define BUILD_BUG_ON(condition) _Static_assert(!(condition), "BUILD_BUG_ON")
#define EXPORT_SYMBOL(symbol) _Static_assert(1, "userspace export marker")
#define MODULE_LICENSE(value) _Static_assert(1, "userspace license marker")
#define MODULE_DESCRIPTION(value) \
	_Static_assert(1, "userspace description marker")

#define LZ4_MEMORY_USAGE 14
#define LZ4_MAX_INPUT_SIZE 0x7E000000
#define LZ4_COMPRESSBOUND(size) \
	((unsigned int)(size) > (unsigned int)LZ4_MAX_INPUT_SIZE \
	 ? 0 : (size) + ((size) / 255) + 16)
#define LZ4_ACCELERATION_DEFAULT 1
#define LZ4_HASHLOG (LZ4_MEMORY_USAGE - 2)
#define LZ4_HASH_SIZE_U32 (1 << LZ4_HASHLOG)
#define LZ4_STREAMSIZE_U64 ((1 << (LZ4_MEMORY_USAGE - 3)) + 4)

typedef struct {
	uint32_t hashTable[LZ4_HASH_SIZE_U32];
	uint32_t currentOffset;
	uint32_t initCheck;
	const uint8_t *dictionary;
	uint8_t *bufferStart;
	uint32_t dictSize;
} LZ4_stream_t_internal;

typedef union {
	unsigned long long table[LZ4_STREAMSIZE_U64];
	LZ4_stream_t_internal internal_donotuse;
} LZ4_stream_t;

void LZ4_resetStream(LZ4_stream_t *stream);

#define LZ4_STREAMDECODESIZE_U64 4

typedef struct {
	const uint8_t *externalDict;
	size_t extDictSize;
	const uint8_t *prefixEnd;
	size_t prefixSize;
} LZ4_streamDecode_t_internal;

typedef union {
	unsigned long long table[LZ4_STREAMDECODESIZE_U64];
	LZ4_streamDecode_t_internal internal_donotuse;
} LZ4_streamDecode_t;

#define get_unaligned(pointer) __extension__ ({ \
	__typeof__(*(pointer) + 0) value; \
	__builtin_memcpy(&value, (pointer), sizeof(value)); \
	value; \
})

#define put_unaligned(value, pointer) do { \
	__typeof__(*(pointer)) temporary = (value); \
	__builtin_memcpy((pointer), &temporary, sizeof(temporary)); \
} while (0)

static __always_inline uint16_t get_unaligned_le16(const void *pointer)
{
	uint16_t value;
	__builtin_memcpy(&value, pointer, sizeof(value));
	return value;
}

static __always_inline void put_unaligned_le16(uint16_t value, void *pointer)
{
	__builtin_memcpy(pointer, &value, sizeof(value));
}

static __always_inline unsigned long __ffs(unsigned long value)
{
	return (unsigned long)__builtin_ctzl(value);
}

static __always_inline unsigned long __fls(unsigned long value)
{
	return (unsigned long)(BITS_PER_LONG - 1 - __builtin_clzl(value));
}

#endif
