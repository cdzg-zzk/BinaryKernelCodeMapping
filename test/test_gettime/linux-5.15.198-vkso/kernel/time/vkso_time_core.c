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
static_assert(sizeof(struct vkso_context) == 3 * sizeof(void *));

/* All fallback ABIs used here are two-argument x86-64 syscalls. */
static noinline notrace __vkso_text int
vkso_fallback(long first, long second, long syscall_number,
	      const struct vkso_context *context)
{
	register long number asm("rax");
	register long first_arg asm("rdi");
	register long second_arg asm("rsi");

	if (context->fallback_mode != VKSO_FALLBACK_SYSCALL)
		return VKSO_TIME_FALLBACK;
	number = syscall_number;
	first_arg = first;
	second_arg = second;
	asm volatile("syscall"
		     : "+a" (number)
		     : "D" (first_arg), "S" (second_arg)
		     : "rcx", "r11", "memory");
	return number;
}

#define VKSO_NO_OFFSET(mm_data, value)					\
	do {								\
		(void)(mm_data);						\
		(void)(value);						\
	} while (0)

#define VKSO_MM_OFFSET(clock, member, mm_data, value)			\
	do {								\
		if (unlikely(READ_ONCE((mm_data)->clock_mask) &		\
			     (1U << (clock))))				\
			vkso_apply_offset(&(mm_data)->member, value);	\
	} while (0)

/*
 * Keep one source definition while preserving per-clock functions.  The
 * private user veneer tail-jumps to these symbols, so replacing them with one
 * generic reader would add parameters and branches to the hot path.
 */
#define VKSO_DEFINE_HRES_READER(name, base_member, mult_member, clock, offset) \
	static noinline __noclone notrace __vkso_text			\
	int vkso_clock_gettime_##name(					\
		int clock_id, struct vkso_time_value *value,		\
		const struct vkso_mm_data *mm_data,			\
		const struct vkso_context *context)			\
	{								\
		const struct vkso_shared_data *shared = vkso_shared_data(); \
									\
		(void)clock_id;						\
		if (unlikely(vkso_read_hres_time(			\
				shared, &shared->state.base_member,	\
				&shared->state.cycles,			\
				&shared->state.cycles.mult_member,	\
				context, value) !=			\
			     VKSO_TIME_OK))				\
			return vkso_fallback(clock, (long)value,		\
					     __NR_clock_gettime, context);	\
		offset;							\
		return VKSO_TIME_OK;					\
	}

#define VKSO_DEFINE_COARSE_READER(name, base_member, offset)		\
	static noinline __noclone notrace __vkso_text			\
	int vkso_clock_gettime_##name(					\
		int clock_id, struct vkso_time_value *value,		\
		const struct vkso_mm_data *mm_data,			\
		const struct vkso_context *context)			\
	{								\
		const struct vkso_shared_data *shared = vkso_shared_data(); \
									\
		(void)clock_id;						\
		(void)context;						\
		vkso_read_coarse(shared, &shared->state.base_member, value); \
		offset;							\
		return VKSO_TIME_OK;					\
	}

/*
 * MM_data is stable for the read and its offsets are frozen before the mask
 * is published.  Apply offsets after the TSC/seq critical path so the root
 * namespace carries no offset dependency through that path.
 *
 * Keep the original definition order: it is part of the measured text layout.
 */
VKSO_DEFINE_HRES_READER(realtime, realtime_base, mono_mult,
			CLOCK_REALTIME, VKSO_NO_OFFSET(mm_data, value))
VKSO_DEFINE_HRES_READER(monotonic, monotonic_base, mono_mult,
			CLOCK_MONOTONIC,
			VKSO_MM_OFFSET(CLOCK_MONOTONIC, monotonic_offset,
				       mm_data, value))
VKSO_DEFINE_COARSE_READER(realtime_coarse, realtime_coarse,
			  VKSO_NO_OFFSET(mm_data, value))
VKSO_DEFINE_COARSE_READER(monotonic_coarse, monotonic_coarse,
			  VKSO_MM_OFFSET(CLOCK_MONOTONIC_COARSE,
					 monotonic_offset, mm_data, value))
VKSO_DEFINE_HRES_READER(monotonic_raw, monotonic_raw_base, raw_mult,
			CLOCK_MONOTONIC_RAW,
			VKSO_MM_OFFSET(CLOCK_MONOTONIC_RAW, monotonic_offset,
				       mm_data, value))
VKSO_DEFINE_HRES_READER(boottime, boottime_base, mono_mult,
			CLOCK_BOOTTIME,
			VKSO_MM_OFFSET(CLOCK_BOOTTIME, boottime_offset,
				       mm_data, value))
VKSO_DEFINE_HRES_READER(tai, tai_base, mono_mult,
			CLOCK_TAI, VKSO_NO_OFFSET(mm_data, value))

#undef VKSO_DEFINE_COARSE_READER
#undef VKSO_DEFINE_HRES_READER
#undef VKSO_MM_OFFSET
#undef VKSO_NO_OFFSET

__visible noinline notrace __vkso_text
int vkso_clock_gettime_core(
	int clock_id, struct vkso_time_value *value,
	const struct vkso_mm_data *mm_data,
	const struct vkso_context *context)
{
	if (likely(clock_id == CLOCK_REALTIME))
		return vkso_clock_gettime_realtime(clock_id, value, mm_data,
						   context);
	if (likely(clock_id == CLOCK_MONOTONIC))
		return vkso_clock_gettime_monotonic(clock_id, value, mm_data,
						    context);
	if (clock_id == CLOCK_REALTIME_COARSE)
		return vkso_clock_gettime_realtime_coarse(clock_id, value,
							  mm_data, context);
	if (clock_id == CLOCK_MONOTONIC_COARSE)
		return vkso_clock_gettime_monotonic_coarse(clock_id, value,
							   mm_data, context);
	if (clock_id == CLOCK_MONOTONIC_RAW)
		return vkso_clock_gettime_monotonic_raw(clock_id, value,
							mm_data, context);
	if (clock_id == CLOCK_BOOTTIME)
		return vkso_clock_gettime_boottime(clock_id, value, mm_data,
						   context);
	if (clock_id == CLOCK_TAI)
		return vkso_clock_gettime_tai(clock_id, value, mm_data,
					      context);
	return vkso_fallback(clock_id, (long)value, __NR_clock_gettime,
			     context);
}

static noinline __noclone notrace __vkso_text
int vkso_clock_getres_hres(int clock_id, struct vkso_time_value *value,
			   const struct vkso_context *context)
{
	const struct vkso_shared_data *shared = vkso_shared_data();

	(void)clock_id;
	(void)context;
	if (value) {
		value->sec = 0;
		value->nsec = READ_ONCE(shared->state.hrtimer_resolution);
	}
	return VKSO_TIME_OK;
}

static noinline __noclone notrace __vkso_text
int vkso_clock_getres_coarse(int clock_id, struct vkso_time_value *value,
			     const struct vkso_context *context)
{
	(void)clock_id;
	(void)context;
	if (value) {
		value->sec = 0;
		value->nsec = LOW_RES_NSEC;
	}
	return VKSO_TIME_OK;
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
	u32 id = clock_id;
	u32 mask;

	if (id > CLOCK_TAI)
		goto fallback;
	mask = 1U << id;
	if (mask & hres_clocks)
		return vkso_clock_getres_hres(clock_id, value, context);
	if (mask & coarse_clocks)
		return vkso_clock_getres_coarse(clock_id, value, context);
fallback:
	return vkso_fallback(clock_id, (long)value, __NR_clock_getres,
			     context);
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
				shared, &shared->state.realtime_base,
				&shared->state.cycles,
				&shared->state.cycles.mono_mult, context,
				&now) != VKSO_TIME_OK))
			return vkso_fallback((long)tv, (long)tz,
					     __NR_gettimeofday, context);
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
