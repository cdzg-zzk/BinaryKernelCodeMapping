/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_GETCPU_H
#define _LINUX_VKSO_GETCPU_H

#include <linux/compiler_types.h>
#include <vkso/getcpu.h>

/* The shared CPU/node reader has no recoverable failure return. Kernel
 * callers retain put_user() error handling; it is not a provider fallback. */
static __always_inline int
vkso_getcpu(unsigned int *cpu, unsigned int *node)
{
	(void)__vkso_getcpu(cpu, node, (void *)0);
	return VKSO_GETCPU_OK;
}

#endif /* _LINUX_VKSO_GETCPU_H */
