#include <linux/init.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/string.h>

/*
 * A normal LKM load points these slots at kernel helpers. For the generated
 * user-space DSO, build_PIC_so materializes the slots as private writable data
 * and turns these four relocations into bindings against libshim.so.
 */
void *(*vkso_bch_kmalloc_slot)(size_t, gfp_t) = __kmalloc;
void (*vkso_bch_kfree_slot)(const void *) = kfree;
void *(*vkso_bch_memcpy_slot)(void *, const void *, size_t) = memcpy;
void *(*vkso_bch_memset_slot)(void *, int, size_t) = memset;

static int __init vkso_bch_module_init(void)
{
	return 0;
}

static void __exit vkso_bch_module_exit(void)
{
}

module_init(vkso_bch_module_init);
module_exit(vkso_bch_module_exit);
