/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_H
#define _VKSO_TIME_H

#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	1U
#define VKSO_SHARED_PAGE_SIZE	4096U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_FALLBACK = -1,
};

/* Fixed-width result used by the common kernel/user implementation. */
struct vkso_time_value {
	s64 sec;
	u64 nsec;
};

struct vkso_shared_data {
	u32 seq;
	u32 abi_version;
	struct vkso_time_value realtime_coarse;
};

union vkso_shared_page {
	struct vkso_shared_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
};

struct vkso_mm_data;

int __vkso_clock_gettime(int clock_id, struct vkso_time_value *value);

#endif /* _VKSO_TIME_H */
