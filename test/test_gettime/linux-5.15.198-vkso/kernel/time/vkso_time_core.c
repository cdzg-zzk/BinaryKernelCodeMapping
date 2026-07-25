// SPDX-License-Identifier: GPL-2.0

#include <linux/build_bug.h>
#include <linux/stddef.h>

#include <asm/unistd.h>

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
static_assert(sizeof(struct vkso_context) == 3 * sizeof(void *));

static noinline notrace __vkso_text int
vkso_fallback(const struct vkso_context *context, u32 operation, int clock_id,
	      void *first, void *second)
{
	register long number asm("rax");
	register long first_arg asm("rdi");
	register long second_arg asm("rsi");

	if (!context || context->fallback_mode != VKSO_FALLBACK_SYSCALL)
		return VKSO_TIME_FALLBACK;
	if (operation == VKSO_FALLBACK_CLOCK_GETTIME) {
		number = __NR_clock_gettime;
		first_arg = clock_id;
		second_arg = (long)first;
	} else if (operation == VKSO_FALLBACK_CLOCK_GETRES) {
		number = __NR_clock_getres;
		first_arg = clock_id;
		second_arg = (long)first;
	} else {
		number = __NR_gettimeofday;
		first_arg = (long)first;
		second_arg = (long)second;
	}
	asm volatile("syscall"
		     : "+a" (number)
		     : "D" (first_arg), "S" (second_arg)
		     : "rcx", "r11", "memory");
	return number;
}

static noinline __noclone notrace __vkso_text
int vkso_clock_gettime_realtime(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();

	(void)mm_data;
	(void)clock_id;
	if (unlikely(vkso_read_hres_time(
			shared, &shared->hres.realtime_base,
			&shared->hres.cycles, context, value) != VKSO_TIME_OK))
		return vkso_fallback(context, VKSO_FALLBACK_CLOCK_GETTIME,
				     CLOCK_REALTIME, value, NULL);
	return VKSO_TIME_OK;
}

static noinline __noclone notrace __vkso_text
int vkso_clock_gettime_monotonic(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	const struct vkso_time_value *offset = NULL;

	(void)clock_id;
	if (unlikely(mm_data &&
		     (READ_ONCE(mm_data->clock_mask) &
		      (1U << CLOCK_MONOTONIC))))
		offset = &mm_data->monotonic_offset;

	if (unlikely(vkso_read_hres_time(
			shared, &shared->hres.monotonic_base,
			&shared->hres.cycles, context, value) != VKSO_TIME_OK))
		return vkso_fallback(context, VKSO_FALLBACK_CLOCK_GETTIME,
				     CLOCK_MONOTONIC, value, NULL);
	if (unlikely(offset))
		vkso_apply_offset(offset, value);
	return VKSO_TIME_OK;
}

static noinline __noclone notrace __vkso_text
int vkso_clock_gettime_coarse(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	const struct vkso_time_value *offset = NULL;
	u32 index = clock_id - CLOCK_REALTIME_COARSE;

	(void)context;
	if (unlikely(index && mm_data &&
		     (READ_ONCE(mm_data->clock_mask) &
		      (1U << CLOCK_MONOTONIC_COARSE))))
		offset = &mm_data->monotonic_offset;

	vkso_read_coarse(shared, &shared->realtime_coarse + index,
			 offset, value);
	return VKSO_TIME_OK;
}

static noinline __noclone notrace __vkso_text
int vkso_clock_gettime_other(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	const struct vkso_hres_base *base;
	const struct vkso_cycle_data *cycles;
	const struct vkso_time_value *offset = NULL;
	u32 mask;

	if (unlikely((u32)clock_id > CLOCK_TAI))
		goto fallback;
	mask = 1U << clock_id;
	if (clock_id == CLOCK_MONOTONIC_RAW) {
		base = &shared->raw.monotonic_raw_base;
		cycles = &shared->raw.cycles;
		if (unlikely(mm_data &&
			     (READ_ONCE(mm_data->clock_mask) & mask)))
			offset = &mm_data->monotonic_offset;
	} else if (clock_id == CLOCK_BOOTTIME) {
		base = &shared->hres.boottime_base;
		cycles = &shared->hres.cycles;
		if (unlikely(mm_data &&
			     (READ_ONCE(mm_data->clock_mask) & mask)))
			offset = &mm_data->boottime_offset;
	} else if (clock_id == CLOCK_TAI) {
		base = &shared->hres.tai_base;
		cycles = &shared->hres.cycles;
	} else {
		goto fallback;
	}

	if (unlikely(vkso_read_hres_time(shared, base, cycles, context,
					 value) != VKSO_TIME_OK))
		goto fallback;
	if (unlikely(offset))
		vkso_apply_offset(offset, value);
	return VKSO_TIME_OK;

fallback:
	return vkso_fallback(context, VKSO_FALLBACK_CLOCK_GETTIME,
			     clock_id, value, NULL);
}

__visible noinline notrace __vkso_text
int vkso_clock_gettime_core(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context)
{
	if (likely(clock_id == CLOCK_REALTIME))
		return vkso_clock_gettime_realtime(mm_data, clock_id,
						   value, context);
	if (likely(clock_id == CLOCK_MONOTONIC))
		return vkso_clock_gettime_monotonic(mm_data, clock_id,
						    value, context);
	if (clock_id == CLOCK_REALTIME_COARSE ||
	    clock_id == CLOCK_MONOTONIC_COARSE)
		return vkso_clock_gettime_coarse(mm_data, clock_id,
						 value, context);
	return vkso_clock_gettime_other(mm_data, clock_id, value, context);
}

__visible noinline notrace __vkso_text
int vkso_clock_getres_core(int clock_id, struct vkso_time_value *value,
			   const struct vkso_context *context)
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
		return vkso_fallback(context, VKSO_FALLBACK_CLOCK_GETRES,
				     clock_id, value, NULL);
	mask = 1U << id;
	if (mask & hres_clocks) {
		shared = vkso_shared_data();
		resolution = READ_ONCE(shared->hrtimer_resolution);
	} else if (mask & coarse_clocks) {
		resolution = LOW_RES_NSEC;
	} else {
		return vkso_fallback(context, VKSO_FALLBACK_CLOCK_GETRES,
				     clock_id, value, NULL);
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
	const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	struct vkso_time_value now;

	if (likely(tv)) {
		if (unlikely(vkso_read_hres_time(
				shared, &shared->hres.realtime_base,
				&shared->hres.cycles, context,
				&now) != VKSO_TIME_OK))
			return vkso_fallback(context,
					     VKSO_FALLBACK_GETTIMEOFDAY,
					     0, tv, tz);
		tv->sec = now.sec;
		/*
		 * vkso_read_hres_time() normalizes nsec to [0, NSEC_PER_SEC).
		 * Keep that invariant visible so x86 can use the cheaper 32-bit
		 * reciprocal division, as the native vDSO does.
		 */
		tv->usec = (u32)now.nsec / NSEC_PER_USEC;
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
