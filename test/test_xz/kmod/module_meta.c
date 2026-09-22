#include "vkso_owner.h"
VKSO_DECLARE_OWNER(vkso_xz_owner);
#include <linux/init.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/string.h>
#include "xz.h"

/* Public module APIs allow ordinary kernel consumers to use this same owner. */
EXPORT_SYMBOL_GPL(xz_dec_init);
EXPORT_SYMBOL_GPL(xz_dec_run);
EXPORT_SYMBOL_GPL(xz_dec_reset);
EXPORT_SYMBOL_GPL(xz_dec_end);
EXPORT_SYMBOL_GPL(xz_crc32_init);

/*
 * These owner-private slots are part of the generated DSO's private writable
 * data. Kbuild initializes them to kernel helpers for a normal module load;
 * build_PIC_so turns the four .data relocations into libshim relocations for
 * user-space execution. The decoder calls through the same slots in both
 * environments, so no post-insmod rel32 call is mistaken for a shim call.
 */
void *(*vkso_xz_kmalloc_slot)(size_t, gfp_t) = __kmalloc;
void (*vkso_xz_kfree_slot)(const void *) = kfree;
void *(*vkso_xz_memcpy_slot)(void *, const void *, size_t) = memcpy;
void *(*vkso_xz_memmove_slot)(void *, const void *, size_t) = memmove;

static int __init vkso_xz_init(void)
{
	return vkso_initialize_owner(&vkso_xz_owner);
}

static void __exit vkso_xz_exit(void)
{
}

module_init(vkso_xz_init);
module_exit(vkso_xz_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Linux 5.15 XZ Embedded decoder for vkso evaluation");
