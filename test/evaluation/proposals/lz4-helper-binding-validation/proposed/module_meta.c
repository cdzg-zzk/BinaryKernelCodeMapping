#include <linux/module.h>
#include <linux/string.h>

/* The normal module uses native kernel helpers. build_PIC_so converts these
 * pointer initializers into explicit dynamic relocations in private data.
 * Actual user helper/ABI identity is checked by the deployment observer;
 * a dependency's name alone does not identify the implementation selected.
 */
void *(*vkso_lz4_memcpy_slot)(void *, const void *, size_t) = memcpy;
void *(*vkso_lz4_memmove_slot)(void *, const void *, size_t) = memmove;
void *(*vkso_lz4_memset_slot)(void *, int, size_t) = memset;

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("Kbuild-compiled Linux 5.15 LZ4 code for vkso benchmarking");

