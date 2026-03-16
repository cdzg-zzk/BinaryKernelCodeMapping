#include <linux/init.h>
#include <linux/module.h>

#include "zlib.h"

EXPORT_SYMBOL(zlibVersion);
EXPORT_SYMBOL(get_crc_table);
EXPORT_SYMBOL(deflateInit2_);
EXPORT_SYMBOL(deflate);
EXPORT_SYMBOL(deflateEnd);
EXPORT_SYMBOL(deflateReset);
EXPORT_SYMBOL(deflateParams);
EXPORT_SYMBOL(deflatePending);
EXPORT_SYMBOL(deflatePrime);
EXPORT_SYMBOL(deflateSetDictionary);
EXPORT_SYMBOL(crc32);
EXPORT_SYMBOL(adler32);

static int __init zlib_lkm_init(void)
{
	pr_info("zlib_lkm loaded\n");
	return 0;
}

static void __exit zlib_lkm_exit(void)
{
	pr_info("zlib_lkm unloaded\n");
}

module_init(zlib_lkm_init);
module_exit(zlib_lkm_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("BinaryKernelCodeMapping");
MODULE_DESCRIPTION("Kernel module exposing zlib 1.2.11 deflate compression symbols");
