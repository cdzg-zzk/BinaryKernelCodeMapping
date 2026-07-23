/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_GETCPU_H
#define _LINUX_VKSO_GETCPU_H

#include <linux/compiler_types.h>
#include <vkso/getcpu.h>

#ifdef CONFIG_VKSO_TIME
static __always_inline int
vkso_getcpu(unsigned int *cpu, unsigned int *node)
{
	return __vkso_getcpu(cpu, node, (void *)0);
}
#else
static inline int vkso_getcpu(unsigned int *cpu, unsigned int *node)
{
	return VKSO_GETCPU_FALLBACK;
}
#endif

#endif /* _LINUX_VKSO_GETCPU_H */
