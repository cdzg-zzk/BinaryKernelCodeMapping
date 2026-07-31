/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_H
#define _LINUX_VKSO_H

#include <linux/types.h>

#define VKSO_TEXT_SECTION		".vkso.text"
#define VKSO_SHARED_DATA_SECTION	".vkso.shared_data"

#define __vkso_text		__section(VKSO_TEXT_SECTION)
#define __vkso_shared_data	__section(VKSO_SHARED_DATA_SECTION)

extern char __vkso_text_start[];
extern char __vkso_text_end[];
extern char __vkso_shared_data_start[];
extern char __vkso_shared_data_end[];

/*
 * Secondary executable mappings preserve offsets within reused text pages,
 * but cannot reach code allocated dynamically at the kernel virtual address.
 */
static inline bool is_secondary_mapped_kernel_text(const void *addr)
{
#ifdef CONFIG_VKSO_TIME
	unsigned long address = (unsigned long)addr;

	return address >= (unsigned long)__vkso_text_start &&
	       address < (unsigned long)__vkso_text_end;
#else
	return false;
#endif
}

#endif /* _LINUX_VKSO_H */
