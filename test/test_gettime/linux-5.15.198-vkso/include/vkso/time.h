/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_H
#define _VKSO_TIME_H

#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	11U
#define VKSO_SHARED_PAGE_SIZE	4096U
#define VKSO_MM_DATA_ABI_VERSION	3U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_UNSUPPORTED_MODE = -1,
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
	u32 shift;
	u64 cycle_last;
	u64 mask;
	u32 mono_mult;
	u32 raw_mult;
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
	u32 hrtimer_resolution;
	u32 clocksource_resolution;
	struct vkso_hres_base monotonic_raw_base;
	struct vkso_time_value monotonic_coarse;
	struct vkso_timezone timezone;
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
	struct vkso_read_state state;
};

union vkso_shared_page {
	struct vkso_shared_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
};

/* Stable while the mm remains in one time namespace. */
struct vkso_mm_data {
	u32 abi_version;
	u32 clock_mask;
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
struct vkso_context {
	const void *pvclock_page;
	const void *hvclock_page;
};

/*
 * Internal shared-core entry points. They are not the user ABI: kernel and
 * user wrappers inject address-space-specific dependencies here. Typed
 * readers always return root-namespace time; a public boundary applies
 * MM_data only when its namespace mask selects that clock.
 *
 * The core never performs a syscall or enters a kernel backend. An unavailable
 * cycle provider returns VKSO_TIME_UNSUPPORTED_MODE. Public wrappers own the
 * corresponding fallback policy.
 */
int vkso_clock_gettime_realtime(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_monotonic(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_monotonic_raw(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_boottime(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_tai(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_realtime_coarse(struct vkso_time_value *value);
int vkso_clock_gettime_monotonic_coarse(struct vkso_time_value *value);
int vkso_clock_getres_hres(struct vkso_time_value *value);
int vkso_clock_getres_coarse(struct vkso_time_value *value);
int vkso_time_apply_offset(
	const struct vkso_time_value *offset,
	struct vkso_time_value *value);
int vkso_gettimeofday_core(
	struct vkso_timeval *tv, struct vkso_timezone *tz,
	const struct vkso_context *context);
s64 __vkso_time(s64 *tloc);
#ifdef CONFIG_VKSO_TIME_TEST
int __vkso_test_hres_cycle_probe_at(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample);
#endif

#endif /* _VKSO_TIME_H */
