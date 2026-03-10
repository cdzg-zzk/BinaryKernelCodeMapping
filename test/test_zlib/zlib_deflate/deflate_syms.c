// SPDX-License-Identifier: GPL-2.0-only
/*
 * linux/lib/mz_zlib_deflate/deflate_syms.c
 *
 * Exported symbols for the deflate functionality.
 *
 */

 #include <linux/module.h>
 #include <linux/init.h>
 
 #include "zlib.h"
 
EXPORT_SYMBOL(mz_zlib_deflate_workspacesize);
EXPORT_SYMBOL(mz_zlib_deflate_dfltcc_enabled);
EXPORT_SYMBOL(mz_zlib_deflate);
EXPORT_SYMBOL(mz_zlib_deflateInit2);
EXPORT_SYMBOL(mz_zlib_deflateEnd);
EXPORT_SYMBOL(mz_zlib_deflateReset);

static int __init mz_zlib_deflate_module_init(void)
{
	return 0;
}

static void __exit mz_zlib_deflate_module_exit(void)
{
}

module_init(mz_zlib_deflate_module_init);
module_exit(mz_zlib_deflate_module_exit);

MODULE_LICENSE("GPL");
