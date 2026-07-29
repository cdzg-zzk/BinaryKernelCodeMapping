/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _KERNEL_TIME_VKSO_TIME_COMPAT_H
#define _KERNEL_TIME_VKSO_TIME_COMPAT_H

#include <linux/timekeeper_internal.h>

/*
 * M03 bridge: the producer already owns the canonical state, but the M02
 * publisher still accepts struct timekeeper.  M04 removes this adapter and
 * passes tk->read_state directly.
 */
static __always_inline void
vkso_time_compat_prepare(struct vkso_shared_data *next,
			 const struct timekeeper *tk)
{
	next->state = tk->read_state;
}

#endif /* _KERNEL_TIME_VKSO_TIME_COMPAT_H */
