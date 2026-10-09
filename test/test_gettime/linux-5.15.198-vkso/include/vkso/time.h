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
#include "time_abi.h"

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

union vkso_shared_page {
	struct vkso_shared_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
};

union vkso_mm_page {
	struct vkso_mm_data data;
	u8 page[VKSO_SHARED_PAGE_SIZE];
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
