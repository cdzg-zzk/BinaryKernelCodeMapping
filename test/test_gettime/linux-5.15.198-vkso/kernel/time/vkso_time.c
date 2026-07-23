// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/sched.h>
#include <linux/stddef.h>
#include <linux/string.h>
#include <linux/time.h>
#include <linux/time64.h>
#include <linux/timekeeper_internal.h>
#include <linux/vkso_time.h>

#include <vdso/clocksource.h>

union vkso_shared_page vkso_shared_page
	__aligned(VKSO_SHARED_PAGE_SIZE) __vkso_shared_data;

static void vkso_time_prepare(struct vkso_shared_data *next,
			      const struct timekeeper *tk)
{
	u64 realtime_nsec =
		tk->tkr_mono.xtime_nsec >> tk->tkr_mono.shift;
	s64 monotonic_sec = tk->xtime_sec + tk->wall_to_monotonic.tv_sec;
	u64 monotonic_nsec = realtime_nsec + tk->wall_to_monotonic.tv_nsec;
	u64 monotonic_shifted_nsec = tk->tkr_mono.xtime_nsec +
		((u64)tk->wall_to_monotonic.tv_nsec << tk->tkr_mono.shift);
	u64 shifted_second = (u64)NSEC_PER_SEC << tk->tkr_mono.shift;
	s32 clock_mode = tk->tkr_mono.clock->vdso_clock_mode;

	if (monotonic_nsec >= NSEC_PER_SEC) {
		monotonic_nsec -= NSEC_PER_SEC;
		monotonic_sec++;
	}
	next->abi_version = VKSO_TIME_ABI_VERSION;
	next->realtime_coarse.sec = tk->xtime_sec;
	next->realtime_coarse.nsec = realtime_nsec;
	next->monotonic_coarse.sec = monotonic_sec;
	next->monotonic_coarse.nsec = monotonic_nsec;
	next->hres.clock_mode = clock_mode;
	if (clock_mode == VDSO_CLOCKMODE_NONE)
		return;
	next->hres.cycle_last = tk->tkr_mono.cycle_last;
	next->hres.mask = tk->tkr_mono.mask;
	next->hres.mult = tk->tkr_mono.mult;
	next->hres.shift = tk->tkr_mono.shift;
	next->hres.realtime_base.sec = tk->xtime_sec;
	next->hres.realtime_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->hres.monotonic_base.sec =
		tk->xtime_sec + tk->wall_to_monotonic.tv_sec;
	while (monotonic_shifted_nsec >= shifted_second) {
		monotonic_shifted_nsec -= shifted_second;
		next->hres.monotonic_base.sec++;
	}
	next->hres.monotonic_base.shifted_nsec = monotonic_shifted_nsec;
}

void vkso_time_publish(struct timekeeper *tk)
{
	struct vkso_shared_data next = { 0 };
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	size_t payload_offset = offsetof(struct vkso_shared_data, abi_version);
	u32 seq;

	/* Derive first so the reader-visible odd interval only copies data. */
	vkso_time_prepare(&next, tk);
	seq = READ_ONCE(shared->seq);
	WRITE_ONCE(shared->seq, seq + 1);
	smp_wmb();
	memcpy((u8 *)shared + payload_offset, (u8 *)&next + payload_offset,
	       sizeof(*shared) - payload_offset);
	smp_wmb();
	WRITE_ONCE(shared->seq, seq + 2);
}

bool vkso_time_get_monotonic_coarse(struct timespec64 *tp)
{
	struct vkso_time_value value;
	const struct vkso_mm_data *mm_data = vkso_time_mm_data(current->mm);

	if (__vkso_clock_gettime(mm_data, CLOCK_MONOTONIC_COARSE, &value) !=
	    VKSO_TIME_OK)
		return false;
	tp->tv_sec = value.sec;
	tp->tv_nsec = value.nsec;
	return true;
}

bool vkso_time_get_monotonic(struct timespec64 *tp)
{
	struct vkso_time_value value;
	const struct vkso_mm_data *mm_data = vkso_time_mm_data(current->mm);

	if (__vkso_clock_gettime(mm_data, CLOCK_MONOTONIC, &value) !=
	    VKSO_TIME_OK)
		return false;
	tp->tv_sec = value.sec;
	tp->tv_nsec = value.nsec;
	return true;
}

bool vkso_time_get_realtime(struct timespec64 *tp)
{
	struct vkso_time_value value;

	if (__vkso_clock_gettime(NULL, CLOCK_REALTIME, &value) !=
	    VKSO_TIME_OK)
		return false;
	tp->tv_sec = value.sec;
	tp->tv_nsec = value.nsec;
	return true;
}

bool vkso_time_get_realtime_coarse(struct timespec64 *tp)
{
	struct vkso_time_value value;

	if (__vkso_clock_gettime(NULL, CLOCK_REALTIME_COARSE, &value) !=
	    VKSO_TIME_OK)
		return false;
	tp->tv_sec = value.sec;
	tp->tv_nsec = value.nsec;
	return true;
}
