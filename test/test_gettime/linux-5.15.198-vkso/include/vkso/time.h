/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_H
#define _VKSO_TIME_H

#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	8U
#define VKSO_SHARED_PAGE_SIZE	4096U
#define VKSO_MM_DATA_ABI_VERSION	2U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_FALLBACK = -1,
};

/* Fixed-width result used by the common kernel/user implementation. */
struct vkso_time_value {
	s64 sec;
	u64 nsec;
} __attribute__((__may_alias__));

struct vkso_timeval {
	s64 sec;
	s64 usec;
} __attribute__((__may_alias__));

struct vkso_timezone {
	s32 minuteswest;
	s32 dsttime;
} __attribute__((__may_alias__));

/* Nanoseconds remain shifted until the reader adds elapsed cycles. */
struct vkso_hres_base {
	s64 sec;
	u64 shifted_nsec;
};

struct vkso_cycle_data {
	s32 clock_mode;
	u32 reserved;
	u64 cycle_last;
	u32 mult;
	u32 shift;
};

struct vkso_hres_data {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base realtime_base;
	struct vkso_hres_base monotonic_base;
	struct vkso_hres_base boottime_base;
	struct vkso_hres_base tai_base;
};

struct vkso_raw_data {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base monotonic_raw_base;
};

#ifdef CONFIG_VKSO_TIME_TEST
/* Test-only result: one counter and conversion-metadata generation. */
struct vkso_hres_cycle_sample {
	u32 seq;
	u32 retries;
	s32 clock_mode;
	u32 shift;
	u64 cycles;
	u64 cycle_last;
	u32 mult;
	u32 reserved;
	struct vkso_hres_base realtime_base;
};
#endif

struct vkso_shared_data {
	u32 seq;
	u32 abi_version;
	struct vkso_hres_data hres;
	struct vkso_raw_data raw;
	struct vkso_time_value realtime_coarse;
	struct vkso_time_value monotonic_coarse;
	u32 hrtimer_resolution;
	u32 reserved;
	struct vkso_timezone timezone;
};

union vkso_shared_page {
	struct vkso_shared_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
};

/* Stable while the mm remains in one time namespace. */
struct vkso_mm_data {
	u32 abi_version;
	u32 reserved;
	struct vkso_time_value monotonic_offset;
	struct vkso_time_value boottime_offset;
};

union vkso_mm_page {
	struct vkso_mm_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
};

/*
 * Environment-specific aliases of hypervisor-owned counter pages. Kernel
 * and user wrappers provide addresses valid in their own address spaces.
 */
struct vkso_cycle_context {
	const void *pvclock_page;
	const void *hvclock_page;
};

/*
 * Internal shared-core entry points. They are not the user ABI: kernel and
 * user wrappers inject address-space-specific dependencies here.
 *
 * VKSO_TIME_FALLBACK asks the wrapper to use its native handler: the
 * clock_gettime syscall in userspace or the POSIX clock handler in-kernel.
 */
int vkso_clock_gettime_core(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_cycle_context *cycle_context);
int __vkso_clock_getres(int clock_id, struct vkso_time_value *value);
int vkso_gettimeofday_core(
	struct vkso_timeval *tv, struct vkso_timezone *tz,
	const struct vkso_cycle_context *cycle_context);
s64 __vkso_time(s64 *tloc);
#ifdef CONFIG_VKSO_TIME_TEST
int __vkso_test_hres_cycle_probe_at(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample);
#endif

#endif /* _VKSO_TIME_H */
