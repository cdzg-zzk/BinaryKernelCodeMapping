#include <stddef.h>

/*
 * Keep the no-SIMD backends independent of glibc's SIMD-dispatched helpers.
 * REP string operations use general-purpose registers and provide a realistic
 * optimized scalar baseline on x86-64, unlike a deliberately slow byte loop.
 */
__attribute__((visibility("hidden"), noinline))
void *memcpy(void *destination, const void *source, size_t size)
{
	void *result = destination;

	__asm__ volatile("rep movsb"
		: "+D"(destination), "+S"(source), "+c"(size)
		:
		: "memory");
	return result;
}

__attribute__((visibility("hidden"), noinline))
void *memmove(void *destination, const void *source, size_t size)
{
	void *result = destination;

	if (size == 0)
		return result;
	if (destination <= source
		|| (unsigned char *)destination >= (const unsigned char *)source + size) {
		__asm__ volatile("rep movsb"
			: "+D"(destination), "+S"(source), "+c"(size)
			:
			: "memory");
	} else {
		destination = (unsigned char *)destination + size - 1;
		source = (const unsigned char *)source + size - 1;
		__asm__ volatile("std\n\trep movsb\n\tcld"
			: "+D"(destination), "+S"(source), "+c"(size)
			:
			: "memory", "cc");
	}
	return result;
}

__attribute__((visibility("hidden"), noinline))
void *memset(void *destination, int value, size_t size)
{
	void *result = destination;

	__asm__ volatile("rep stosb"
		: "+D"(destination), "+c"(size)
		: "a"((unsigned char)value)
		: "memory");
	return result;
}
