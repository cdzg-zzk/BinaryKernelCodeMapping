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
static_assert(offsetof(struct vkso_shared_data, state) == 8);
static_assert(offsetof(struct vkso_cycle_data, cycle_last) == 8);
static_assert(offsetof(struct vkso_cycle_data, mask) == 16);
static_assert(offsetof(struct vkso_cycle_data, mono_mult) == 24);
static_assert(offsetof(struct vkso_cycle_data, raw_mult) == 28);
static_assert(offsetof(struct vkso_read_state, realtime_base) == 32);
static_assert(offsetof(struct vkso_read_state, monotonic_base) == 48);
static_assert(offsetof(struct vkso_read_state, boottime_base) == 64);
static_assert(offsetof(struct vkso_read_state, tai_base) == 80);
static_assert(offsetof(struct vkso_read_state, realtime_coarse) == 96);
static_assert(offsetof(struct vkso_read_state, hrtimer_resolution) == 112);
static_assert(offsetof(struct vkso_read_state, monotonic_raw_base) == 120);
static_assert(offsetof(struct vkso_read_state, monotonic_coarse) == 136);
static_assert(offsetof(struct vkso_read_state, timezone) == 152);
static_assert(CLOCK_REALTIME == 0);
static_assert(CLOCK_MONOTONIC == CLOCK_REALTIME + 1);
static_assert(CLOCK_MONOTONIC_COARSE == CLOCK_REALTIME_COARSE + 1);
static_assert(offsetof(struct vkso_read_state, monotonic_base) ==
	      offsetof(struct vkso_read_state, realtime_base) +
	      sizeof(struct vkso_hres_base));
static_assert(offsetof(struct vkso_shared_data, state.realtime_base.sec) == 40);
static_assert(offsetof(struct vkso_shared_data, state.monotonic_base) +
	      sizeof(struct vkso_hres_base) <= 2 * 64);
static_assert(offsetof(struct vkso_shared_data,
		       state.monotonic_raw_base) == 2 * 64);
static_assert(offsetof(struct vkso_shared_data,
		       state.monotonic_raw_base) % 64 == 0);
static_assert(sizeof(struct vkso_read_state) == 160);
static_assert(sizeof(struct vkso_shared_data) == 168);
static_assert(offsetof(struct vkso_mm_data, monotonic_offset) == 8);
static_assert(offsetof(struct vkso_mm_data, boottime_offset) == 24);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(struct vkso_context) == 4 * sizeof(void *));

static noinline notrace __vkso_text
int vkso_finish_hres_cold(s64 sec, u64 nsec,
			  struct vkso_time_value *value)
{
	u64 remainder;

	sec += __iter_div_u64_rem(nsec, NSEC_PER_SEC, &remainder);
	value->sec = sec;
	value->nsec = remainder;
	return VKSO_TIME_OK;
}

/*
 * All conversion inputs belong to one seq generation. Publish the result
 * only after that generation has been validated. Typed clock readers outline
 * the exceptional normalization path; gettimeofday keeps it inline because
 * it must continue with the usec conversion.
 */
static __always_inline int
vkso_read_hres_time(const struct vkso_shared_data *shared,
		    const struct vkso_hres_base *base,
		    const struct vkso_cycle_data *cycle_data,
		    const u32 *multiplier,
		    const struct vkso_context *context,
		    struct vkso_time_value *value,
		    bool outline_normalize)
{
	u64 cycles, cycle_last, ns;
	s64 sec;
	u32 mult, shift;
	u32 seq;
	s32 clock_mode;

	for (;;) {
		seq = vkso_read_begin(shared);
		clock_mode = READ_ONCE(cycle_data->clock_mode);
		cycles = vkso_cycles_read(context, clock_mode);
		if (unlikely((s64)cycles < 0))
			return VKSO_TIME_UNSUPPORTED_MODE;
		cycle_last = READ_ONCE(cycle_data->cycle_last);
		mult = READ_ONCE(*multiplier);
		ns = READ_ONCE(base->shifted_nsec);
		ns += vkso_cycle_delta(cycles, cycle_last) * mult;
		shift = READ_ONCE(cycle_data->shift);
		sec = READ_ONCE(base->sec);
		if (!vkso_read_retry(shared, seq))
			break;
	}

	ns >>= shift;
	if (outline_normalize && unlikely(ns >= NSEC_PER_SEC))
		return vkso_finish_hres_cold(sec, ns, value);
	value->sec = sec + __iter_div_u64_rem(ns, NSEC_PER_SEC, &ns);
	value->nsec = ns;
	return VKSO_TIME_OK;
}

/*
 * Keep the clock-ID dispatcher and conversion in one shared implementation,
 * as the native vDSO does.  Named fields preserve the compact ABI layout; the
 * selection below only chooses addresses and the conversion body is emitted
 * once.
 */
#define VKSO_HRES_CLOCK_MASK						\
	((1U << CLOCK_REALTIME) | (1U << CLOCK_MONOTONIC) |		\
	 (1U << CLOCK_MONOTONIC_RAW) | (1U << CLOCK_BOOTTIME) |		\
	 (1U << CLOCK_TAI))
#define VKSO_COARSE_CLOCK_MASK						\
	((1U << CLOCK_REALTIME_COARSE) |				\
	 (1U << CLOCK_MONOTONIC_COARSE))

__visible noinline __noclone notrace __vkso_text
int vkso_clock_gettime_common(s32 clock_id, struct vkso_time_value *value,
			      const struct vkso_mm_data *mm_data,
			      const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	const struct vkso_hres_base *base;
	const struct vkso_time_value *coarse;
	const struct vkso_time_value *offset = NULL;
	const u32 *multiplier;
	u32 clock_bit;
	int status;

	if (unlikely((u32)clock_id > CLOCK_TAI)) {
		status = VKSO_TIME_BACKEND_REQUIRED;
		goto backend;
	}
	clock_bit = 1U << clock_id;

	if (likely(clock_bit & VKSO_HRES_CLOCK_MASK)) {
		multiplier = &shared->state.cycles.mono_mult;
		if (likely(clock_id == CLOCK_REALTIME)) {
			base = &shared->state.realtime_base;
		} else if (likely(clock_id == CLOCK_MONOTONIC)) {
			base = &shared->state.monotonic_base;
			if (mm_data)
				offset = &mm_data->monotonic_offset;
		} else if (clock_id == CLOCK_MONOTONIC_RAW) {
			base = &shared->state.monotonic_raw_base;
			multiplier = &shared->state.cycles.raw_mult;
			if (mm_data)
				offset = &mm_data->monotonic_offset;
		} else if (clock_id == CLOCK_BOOTTIME) {
			base = &shared->state.boottime_base;
			if (mm_data)
				offset = &mm_data->boottime_offset;
		} else {
			base = &shared->state.tai_base;
		}
		status = vkso_read_hres_time(
			shared, base, &shared->state.cycles, multiplier,
			context, value, true);
		if (unlikely(status != VKSO_TIME_OK))
			goto backend;
	} else if (clock_bit & VKSO_COARSE_CLOCK_MASK) {
		if (clock_id == CLOCK_REALTIME_COARSE) {
			coarse = &shared->state.realtime_coarse;
		} else {
			coarse = &shared->state.monotonic_coarse;
			if (mm_data)
				offset = &mm_data->monotonic_offset;
		}
		vkso_read_coarse(shared, coarse, value);
	} else {
		status = VKSO_TIME_BACKEND_REQUIRED;
		goto backend;
	}

	if (offset && (READ_ONCE(mm_data->clock_mask) & clock_bit))
		vkso_apply_offset(offset, value);
	return VKSO_TIME_OK;

backend:
	return context->clock_gettime_backend(
		clock_id, value, mm_data, status);
}

#undef VKSO_COARSE_CLOCK_MASK
#undef VKSO_HRES_CLOCK_MASK

__visible noinline notrace __vkso_text
int vkso_time_apply_offset(const struct vkso_time_value *offset,
			   struct vkso_time_value *value)
{
	vkso_apply_offset(offset, value);
	return VKSO_TIME_OK;
}

__visible noinline __noclone notrace __vkso_text
int vkso_clock_getres_hres(struct vkso_time_value *value)
{
	const struct vkso_shared_data *shared = vkso_shared_data();

	if (value) {
		value->sec = 0;
		value->nsec = READ_ONCE(shared->state.hrtimer_resolution);
	}
	return VKSO_TIME_OK;
}

__visible noinline __noclone notrace __vkso_text
int vkso_clock_getres_coarse(struct vkso_time_value *value)
{
	if (value) {
		value->sec = 0;
		value->nsec = LOW_RES_NSEC;
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
		int status = vkso_read_hres_time(
			shared, &shared->state.realtime_base,
			&shared->state.cycles,
			&shared->state.cycles.mono_mult, context, &now,
			false);

		if (unlikely(status != VKSO_TIME_OK))
			return context->gettimeofday_backend(tv, tz, status);
		tv->sec = now.sec;
		/*
		 * vkso_read_hres_time() normalizes nsec to [0, NSEC_PER_SEC).
		 * Keep that invariant visible so x86 can use the cheaper 32-bit
		 * reciprocal division, as the native vDSO does.
		 */
		tv->usec = (u32)now.nsec / NSEC_PER_USEC;
	}
	if (unlikely(tz)) {
		tz->minuteswest =
			READ_ONCE(shared->state.timezone.minuteswest);
		tz->dsttime = READ_ONCE(shared->state.timezone.dsttime);
	}
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
s64 __vkso_time(s64 *tloc)
{
	const struct vkso_shared_data *shared = vkso_shared_data();
	s64 seconds = READ_ONCE(shared->state.realtime_base.sec);

	if (tloc)
		*tloc = seconds;
	return seconds;
}
