/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_H
#define _VKSO_TIME_H

#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	1U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_FALLBACK = -1,
};

/* Fixed-width result used by the common kernel/user implementation. */
struct vkso_time_value {
	s64 sec;
	u64 nsec;
};

struct vkso_shared_data;
struct vkso_mm_data;

#endif /* _VKSO_TIME_H */
