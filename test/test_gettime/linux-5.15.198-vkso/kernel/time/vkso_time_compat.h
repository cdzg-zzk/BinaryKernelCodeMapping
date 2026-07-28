/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _KERNEL_TIME_VKSO_TIME_COMPAT_H
#define _KERNEL_TIME_VKSO_TIME_COMPAT_H

#include <linux/hrtimer.h>
#include <linux/time64.h>
#include <linux/timekeeper_internal.h>
#include <linux/vkso_time.h>

/*
 * Compatibility adapter for the existing Linux timekeeper.
 *
 * VKSO only needs a canonical vkso_shared_data producer.  The current
 * kernel, however, must keep struct timekeeper as the private source of truth
 * for readers outside the experiment.  Keep that compatibility conversion
 * isolated here so it is not attributed to the intrinsic VKSO interface.
 *
 * These helpers stay inline in vkso_time.c: separating the source accounting
 * must not add an update-side call or change the reader-visible odd-seq
 * interval.
 */
static __always_inline void vkso_time_compat_prepare_cycles(
	struct vkso_cycle_data *next, const struct tk_read_base *tkr)
{
	next->cycle_last = tkr->cycle_last;
	next->mult = tkr->mult;
	next->shift = tkr->shift;
}

static __always_inline void
vkso_time_compat_prepare(struct vkso_shared_data *next,
			 const struct timekeeper *tk)
{
	s64 monotonic_sec = tk->xtime_sec + tk->wall_to_monotonic.tv_sec;
	u64 monotonic_shifted_nsec = tk->tkr_mono.xtime_nsec +
		((u64)tk->wall_to_monotonic.tv_nsec << tk->tkr_mono.shift);
	s64 boottime_sec;
	u64 boottime_shifted_nsec;
	u64 shifted_second = (u64)NSEC_PER_SEC << tk->tkr_mono.shift;
	s32 clock_mode = tk->tkr_mono.clock->vdso_clock_mode;

	if (monotonic_shifted_nsec >= shifted_second) {
		monotonic_shifted_nsec -= shifted_second;
		monotonic_sec++;
	}
	boottime_sec = monotonic_sec + tk->monotonic_to_boot.tv_sec;
	boottime_shifted_nsec = monotonic_shifted_nsec +
		((u64)tk->monotonic_to_boot.tv_nsec << tk->tkr_mono.shift);
	if (boottime_shifted_nsec >= shifted_second) {
		boottime_shifted_nsec -= shifted_second;
		boottime_sec++;
	}
	next->hrtimer_resolution = hrtimer_resolution;
	next->realtime_coarse.sec = tk->xtime_sec;
	next->realtime_coarse.nsec =
		tk->tkr_mono.xtime_nsec >> tk->tkr_mono.shift;
	next->monotonic_coarse.sec = monotonic_sec;
	next->monotonic_coarse.nsec =
		monotonic_shifted_nsec >> tk->tkr_mono.shift;
	/*
	 * time() reads only this naturally atomic field and remains available
	 * even when the clocksource cannot serve high-resolution VKSO reads.
	 */
	next->hres.realtime_base.sec = tk->xtime_sec;
	next->hres.cycles.clock_mode = clock_mode;
	next->raw.cycles.clock_mode = clock_mode;
	vkso_time_compat_prepare_cycles(&next->hres.cycles, &tk->tkr_mono);
	vkso_time_compat_prepare_cycles(&next->raw.cycles, &tk->tkr_raw);
	next->hres.realtime_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->hres.monotonic_base.sec = monotonic_sec;
	next->hres.monotonic_base.shifted_nsec = monotonic_shifted_nsec;
	next->hres.boottime_base.sec = boottime_sec;
	next->hres.boottime_base.shifted_nsec = boottime_shifted_nsec;
	next->hres.tai_base.sec = tk->xtime_sec + tk->tai_offset;
	next->hres.tai_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->raw.monotonic_raw_base.sec = tk->raw_sec;
	next->raw.monotonic_raw_base.shifted_nsec = tk->tkr_raw.xtime_nsec;
}

#endif /* _KERNEL_TIME_VKSO_TIME_COMPAT_H */
