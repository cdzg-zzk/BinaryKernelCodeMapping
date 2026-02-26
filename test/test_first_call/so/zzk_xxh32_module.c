#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/types.h>

u32 zzk_xxh32(const void *input, size_t len, u32 seed);
EXPORT_SYMBOL(zzk_xxh32);

static int __init zzk_xxh32_module_init(void)
{
    pr_info("zzk_xxh32 module loaded\\n");
    return 0;
}

static void __exit zzk_xxh32_module_exit(void)
{
    pr_info("zzk_xxh32 module unloaded\\n");
}

module_init(zzk_xxh32_module_init);
module_exit(zzk_xxh32_module_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("zzk");
MODULE_DESCRIPTION("LKM exposing zzk_xxh32 implemented in assembly");
