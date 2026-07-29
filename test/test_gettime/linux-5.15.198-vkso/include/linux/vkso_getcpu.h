/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_GETCPU_H
#define _LINUX_VKSO_GETCPU_H

#include <linux/compiler_types.h>
#include <vkso/getcpu.h>

static __always_inline int
vkso_getcpu(unsigned int *cpu, unsigned int *node)
{
	return __vkso_getcpu(cpu, node, (void *)0);
}

#endif /* _LINUX_VKSO_GETCPU_H */
