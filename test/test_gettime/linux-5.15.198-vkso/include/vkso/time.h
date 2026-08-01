/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _VKSO_TIME_H
#define _VKSO_TIME_H

#define VKSO_CLOCK_REALTIME		0
#define VKSO_CLOCK_MONOTONIC		1
#define VKSO_CLOCK_MONOTONIC_RAW	4
#define VKSO_CLOCK_REALTIME_COARSE	5
#define VKSO_CLOCK_MONOTONIC_COARSE	6
#define VKSO_CLOCK_BOOTTIME		7
#define VKSO_CLOCK_TAI			11
#define VKSO_CLOCK_ID_MAX		VKSO_CLOCK_TAI

#define VKSO_HRES_CLOCK_MASK					\
	((1 << VKSO_CLOCK_REALTIME) | (1 << VKSO_CLOCK_MONOTONIC) |\
	 (1 << VKSO_CLOCK_MONOTONIC_RAW) | (1 << VKSO_CLOCK_BOOTTIME) |\
	 (1 << VKSO_CLOCK_TAI))
#define VKSO_COARSE_CLOCK_MASK					\
	((1 << VKSO_CLOCK_REALTIME_COARSE) |			\
	 (1 << VKSO_CLOCK_MONOTONIC_COARSE))

#if !defined(__ASSEMBLY__) && !defined(__ASSEMBLER__)

#include <linux/types.h>

#define VKSO_TIME_ABI_VERSION	11U
#define VKSO_SHARED_PAGE_SIZE	4096U
#define VKSO_MM_DATA_ABI_VERSION	3U

enum vkso_time_status {
	VKSO_TIME_OK = 0,
	VKSO_TIME_UNSUPPORTED_MODE = -1,
	VKSO_TIME_NOT_SHARED = -2,
};

enum vkso_clock_class {
	VKSO_CLOCK_NATIVE = 0,
	VKSO_CLOCK_HRES,
	VKSO_CLOCK_COARSE,
};

static __always_inline enum vkso_clock_class
vkso_clock_classify(s32 clock_id)
{
	u32 bit;

	if ((u32)clock_id > VKSO_CLOCK_ID_MAX)
		return VKSO_CLOCK_NATIVE;
	bit = 1U << clock_id;
	if (bit & VKSO_HRES_CLOCK_MASK)
		return VKSO_CLOCK_HRES;
	if (bit & VKSO_COARSE_CLOCK_MASK)
		return VKSO_CLOCK_COARSE;
	return VKSO_CLOCK_NATIVE;
}

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

typedef int (*vkso_clock_gettime_failure_t)(
	s32 clock_id, struct vkso_time_value *value,
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

/*
 * Internal shared-core entry points. They are not the user ABI: kernel and
 * user wrappers inject address-space-specific dependencies here. A NULL
 * MM_data pointer selects the root namespace; otherwise the common reader
 * applies the per-MM offset selected by clock_mask.
 *
 * The clock class is computed once at the environment boundary. These entries
 * accept only shared clocks; an unavailable cycle provider is handed to the
 * environment's failure callback. The core contains no syscall or k_clock
 * policy.
 */
int vkso_clock_gettime_hres(s32 clock_id, struct vkso_time_value *value,
			    const struct vkso_mm_data *mm_data,
			    const struct vkso_context *context);
int vkso_clock_gettime_coarse(s32 clock_id, struct vkso_time_value *value,
			      const struct vkso_mm_data *mm_data);
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

#endif /* !__ASSEMBLY__ */

#endif /* _VKSO_TIME_H */
