// SPDX-License-Identifier: GPL-2.0

#include <linux/build_bug.h>
#include <linux/stddef.h>

#include "vkso_time_internal.h"

/* Keep the binary contract explicit before executable interfaces are added. */
static_assert(sizeof(struct vkso_time_value) == 16);
static_assert(offsetof(struct vkso_time_value, sec) == 0);
static_assert(offsetof(struct vkso_time_value, nsec) == 8);
static_assert(sizeof(struct vkso_timeval) == 16);
static_assert(offsetof(struct vkso_timeval, sec) == 0);
static_assert(offsetof(struct vkso_timeval, usec) == 8);
static_assert(sizeof(struct vkso_timezone) == 8);
static_assert(offsetof(struct vkso_shared_data, hres) == 8);
static_assert(offsetof(struct vkso_shared_data, realtime_coarse) == 96);
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) == 112);
static_assert(offsetof(struct vkso_shared_data, raw) == 128);
static_assert(offsetof(struct vkso_shared_data, hrtimer_resolution) == 168);
static_assert(offsetof(struct vkso_shared_data, timezone) == 176);
static_assert(offsetof(struct vkso_cycle_data, cycle_last) == 8);
static_assert(offsetof(struct vkso_cycle_data, mult) == 16);
static_assert(offsetof(struct vkso_cycle_data, shift) == 20);
static_assert(offsetof(struct vkso_hres_data, realtime_base) == 24);
static_assert(offsetof(struct vkso_hres_data, monotonic_base) == 40);
static_assert(offsetof(struct vkso_hres_data, boottime_base) == 56);
static_assert(offsetof(struct vkso_hres_data, tai_base) == 72);
static_assert(offsetof(struct vkso_raw_data, monotonic_raw_base) == 24);
static_assert(CLOCK_REALTIME == 0);
static_assert(CLOCK_MONOTONIC == CLOCK_REALTIME + 1);
static_assert(CLOCK_MONOTONIC_COARSE == CLOCK_REALTIME_COARSE + 1);
static_assert(offsetof(struct vkso_hres_data, monotonic_base) ==
	      offsetof(struct vkso_hres_data, realtime_base) +
	      sizeof(struct vkso_hres_base));
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) ==
	      offsetof(struct vkso_shared_data, realtime_coarse) +
	      sizeof(struct vkso_time_value));
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) +
	      sizeof(struct vkso_time_value) ==
	      offsetof(struct vkso_shared_data, raw));
static_assert(offsetof(struct vkso_shared_data, hres.monotonic_base) +
	      sizeof(struct vkso_hres_base) == 64);
static_assert(offsetof(struct vkso_shared_data, raw) % 64 == 0);
static_assert(offsetof(struct vkso_shared_data, raw.monotonic_raw_base) +
	      sizeof(struct vkso_hres_base) <=
	      offsetof(struct vkso_shared_data, raw) + 64);
static_assert(offsetof(struct vkso_mm_data, monotonic_offset) == 8);
static_assert(offsetof(struct vkso_mm_data, boottime_offset) == 24);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(struct vkso_cycle_context) == 2 * sizeof(void *));

__visible noinline notrace __vkso_text
int vkso_clock_gettime_core(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_cycle_context *cycle_context)
{
	const struct vkso_shared_data *shared;
	const struct vkso_time_value *offset = NULL;
	size_t value_offset;
	size_t cycle_offset = 0;
	size_t mm_offset = 0;
	u32 id = clock_id;
	bool high_resolution;

	if (likely(id <= CLOCK_MONOTONIC)) {
		value_offset = offsetof(struct vkso_shared_data,
					 hres.realtime_base) +
			id * sizeof(struct vkso_hres_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
		if (id == CLOCK_MONOTONIC)
			mm_offset = offsetof(struct vkso_mm_data,
					     monotonic_offset);
	} else if (id == CLOCK_MONOTONIC_RAW) {
		value_offset = offsetof(struct vkso_shared_data,
					 raw.monotonic_raw_base);
		cycle_offset = offsetof(struct vkso_shared_data, raw.cycles);
		high_resolution = true;
		mm_offset = offsetof(struct vkso_mm_data, monotonic_offset);
	} else if (id == CLOCK_BOOTTIME) {
		value_offset = offsetof(struct vkso_shared_data,
					hres.boottime_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
		mm_offset = offsetof(struct vkso_mm_data, boottime_offset);
	} else if (id == CLOCK_TAI) {
		value_offset = offsetof(struct vkso_shared_data, hres.tai_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
	} else {
		u32 coarse_index = id - CLOCK_REALTIME_COARSE;

		if (coarse_index >
		    CLOCK_MONOTONIC_COARSE - CLOCK_REALTIME_COARSE)
			return VKSO_TIME_FALLBACK;
		value_offset = offsetof(struct vkso_shared_data,
					 realtime_coarse) +
			coarse_index * sizeof(struct vkso_time_value);
		high_resolution = false;
		if (coarse_index)
			mm_offset = offsetof(struct vkso_mm_data,
					     monotonic_offset);
	}
	if (mm_offset && mm_data) {
		offset = (const void *)((const u8 *)mm_data + mm_offset);
	}
	shared = vkso_shared_data();
	if (high_resolution)
		return vkso_read_hres_time(shared, value_offset, cycle_offset,
					   cycle_context, offset, value);
	vkso_read_coarse(shared, value_offset, offset, value);
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
int __vkso_clock_getres(int clock_id, struct vkso_time_value *value)
{
	const u32 hres_clocks = (1U << CLOCK_REALTIME) |
		(1U << CLOCK_MONOTONIC) | (1U << CLOCK_MONOTONIC_RAW) |
		(1U << CLOCK_BOOTTIME) | (1U << CLOCK_TAI);
	const u32 coarse_clocks = (1U << CLOCK_REALTIME_COARSE) |
		(1U << CLOCK_MONOTONIC_COARSE);
	const struct vkso_shared_data *shared;
	u32 id = clock_id;
	u32 mask;
	u32 resolution;

	if (id > CLOCK_TAI)
		return VKSO_TIME_FALLBACK;
	mask = 1U << id;
	if (mask & hres_clocks) {
		shared = vkso_shared_data();
		resolution = READ_ONCE(shared->hrtimer_resolution);
	} else if (mask & coarse_clocks) {
		resolution = LOW_RES_NSEC;
	} else {
		return VKSO_TIME_FALLBACK;
	}
	if (value) {
		value->sec = 0;
		value->nsec = resolution;
	}
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
int vkso_gettimeofday_core(
	struct vkso_timeval *tv, struct vkso_timezone *tz,
	const struct vkso_cycle_context *cycle_context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	const size_t base_offset =
		offsetof(struct vkso_shared_data, hres.realtime_base);
	const size_t cycle_offset =
		offsetof(struct vkso_shared_data, hres.cycles);
	struct vkso_time_value now;

	if (likely(tv)) {
		if (vkso_read_hres_time(shared, base_offset, cycle_offset,
					cycle_context, NULL,
					&now) != VKSO_TIME_OK)
			return VKSO_TIME_FALLBACK;
		tv->sec = now.sec;
		tv->usec = now.nsec / NSEC_PER_USEC;
	}
	if (unlikely(tz)) {
		tz->minuteswest = READ_ONCE(shared->timezone.minuteswest);
		tz->dsttime = READ_ONCE(shared->timezone.dsttime);
	}
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
s64 __vkso_time(s64 *tloc)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	s64 seconds = READ_ONCE(shared->hres.realtime_base.sec);

	if (tloc)
		*tloc = seconds;
	return seconds;
}
