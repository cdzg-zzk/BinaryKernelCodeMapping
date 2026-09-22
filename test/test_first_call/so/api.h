#ifndef VKSO_XXH32_API_H
#define VKSO_XXH32_API_H
#include <stddef.h>
#include <stdint.h>
/* SysV x86-64 ABI of the existing zzk_xxh32_kernel.S entry. */
uint32_t zzk_xxh32(const void *input, size_t length, uint32_t seed);
#endif
