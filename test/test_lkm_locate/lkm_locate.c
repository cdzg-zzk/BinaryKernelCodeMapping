// SPDX-License-Identifier: GPL-2.0
/*
 * lkm_locate: verify LKM relocation/addressing rules and demonstrate a "pseudo
 * GOT" approach for cross-module references.
 *
 * Background:
 * - x86_64 LKMs (.ko) are ET_REL and are relocated by the kernel module loader.
 * - The kernel build does not use -fPIC for modules (default -mcmodel=kernel),
 *   so we cannot rely on a user-space style GOT/PLT mechanism.
 *
 * Pseudo-GOT idea:
 * - Put all imported symbol addresses into a module-local table (this struct).
 * - Code accesses the table via RIP-relative addressing (module-local), then
 *   performs indirect calls/loads via registers.
 * - When mapping the module code to user-space, we can initialize the table to
 *   user-space replacements, without having to patch every call site.
 */

#include <linux/errno.h>
#include <linux/init.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/slab.h>
#include <linux/string.h>

/*
 * On many distros printk() is wrapped and the undefined symbol referenced from
 * modules is _printk. We use _printk explicitly so the pseudo-GOT stores the
 * true imported symbol.
 */
static const char print_str[] = "lkm_locate_test_pseudo_got: x=%d ret=0x%x\n";
static const int glo_var = 0x101;
extern int _printk(const char *fmt, ...);

struct lkm_locate_pseudo_got {
	void *(*kmalloc)(size_t size, gfp_t flags);
	void (*kfree)(const void *objp);
	int (*kprint)(const char *fmt, ...);
	// void *(*memcpy)(void *dest, const void *src, size_t n);
	const char* print_str;
};

/*
 * This table is the only place where imported symbol addresses are stored.
 * The initializer forces the relocations for those imports into data sections.
 */
static struct lkm_locate_pseudo_got lkm_locate_got = {
	.kmalloc = __kmalloc,
	.kfree = kfree,
	.kprint = _printk,
	// .memcpy = memcpy,
	.print_str = print_str,
};

// static int lkm_locate_static_data = 0x11111111;
static volatile int lkm_locate_sink;

noinline int lkm_locate_local_add(int x)
{
	// return x + lkm_locate_static_data;
	return x + 0x11111111;
}
EXPORT_SYMBOL(lkm_locate_local_add);
noinline int lkm_locate_test_pseudo_got(int x)
{
	char src[32] = { 0 };
	char *dst;
	int ret;

	src[0] = (char)x;
	src[1] = (char)(x + 1);
	src[2] = (char)(x + 2);

	dst = lkm_locate_got.kmalloc(sizeof(src), GFP_KERNEL);
	if (!dst)
		return -ENOMEM;

	// lkm_locate_got.memcpy(dst, src, sizeof(src));
	memcpy(dst, src, sizeof(src));

	ret = (int)(unsigned char)dst[0] + glo_var;
	lkm_locate_got.kfree(dst);
	lkm_locate_got.kprint(lkm_locate_got.print_str, x, ret);
	return ret;
}
EXPORT_SYMBOL(lkm_locate_test_pseudo_got);
static int __init lkm_locate_init(void)
{
	lkm_locate_sink = lkm_locate_test_pseudo_got(42);
	return 0;
}

static void __exit lkm_locate_exit(void)
{
	lkm_locate_sink = 0;
}

module_init(lkm_locate_init);
module_exit(lkm_locate_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("LKM relocation/addressing probe with pseudo-GOT");
