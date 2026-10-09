/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_ABI_H
#define _VKSO_TIME_ABI_H

/* One layout definition for kernel code and the user carrier interface. */
#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	11U
#define VKSO_SHARED_PAGE_SIZE	4096U
#define VKSO_MM_DATA_ABI_VERSION	3U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_UNSUPPORTED_MODE = -1,
	VKSO_TIME_NOT_SHARED = -2,
};

/* Fixed-width result used by the common kernel/user implementation. */
struct vkso_time_value {
	__s64 sec;
	__u64 nsec;
} __attribute__((__may_alias__));

struct vkso_timeval {
	__s64 sec;
	__s64 usec;
} __attribute__((__may_alias__));

struct vkso_timezone {
	__s32 minuteswest;
	__s32 dsttime;
} __attribute__((__may_alias__));

/* Nanoseconds remain shifted until the reader adds elapsed cycles. */
struct vkso_hres_base {
	__s64 sec;
	__u64 shifted_nsec;
};

struct vkso_cycle_data {
	__s32 clock_mode;
	__u32 shift;
	__u64 cycle_last;
	__u64 mask;
	__u32 mono_mult;
	__u32 raw_mult;
};

/*
 * Canonical global-time reader state.  The common cycle descriptor and
 * realtime base fit after the eight-byte shared header in the first cache
 * line.  The raw base starts at shared offset 128.
 */
struct vkso_read_state {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base realtime_base;
	struct vkso_hres_base monotonic_base;
	struct vkso_hres_base boottime_base;
	struct vkso_hres_base tai_base;
	struct vkso_time_value realtime_coarse;
	__u32 hrtimer_resolution;
	__u32 clocksource_resolution;
	struct vkso_hres_base monotonic_raw_base;
	struct vkso_time_value monotonic_coarse;
	struct vkso_timezone timezone;
};

struct vkso_shared_data {
	__u32 seq;
	__u32 abi_version;
	struct vkso_read_state state;
};

/* Stable while the mm remains in one time namespace. */
struct vkso_mm_data {
	__u32 abi_version;
	__u32 clock_mask;
	struct vkso_time_value monotonic_offset;
	struct vkso_time_value boottime_offset;
};

typedef int (*vkso_clock_gettime_failure_t)(
	__s32 clock_id, struct vkso_time_value *value,
	const struct vkso_mm_data *mm_data);
typedef int (*vkso_gettimeofday_failure_t)(
	struct vkso_timeval *tv, struct vkso_timezone *tz, int status);

/*
 * Environment-specific counter aliases and provider-failure exits. Kernel
 * and user entry code provide addresses valid in their own address spaces.
 * Clock IDs which cannot use shared time are rejected at the environment
 * boundary and never reach these callbacks.
 */
struct vkso_context {
	const void *pvclock_page;
	const void *hvclock_page;
	vkso_clock_gettime_failure_t clock_gettime_failure;
	vkso_gettimeofday_failure_t gettimeofday_failure;
};

#endif /* _VKSO_TIME_ABI_H */
