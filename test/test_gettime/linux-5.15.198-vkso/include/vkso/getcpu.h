/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_GETCPU_H
#define _VKSO_GETCPU_H

#define VKSO_GETCPU_OK		0
#define VKSO_GETCPU_FALLBACK	(-1)

int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* _VKSO_GETCPU_H */
