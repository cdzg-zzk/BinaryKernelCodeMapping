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
	struct vkso_cycle_data *next, const struct timekeeper *tk)
{
	next->clock_mode = tk->tkr_mono.clock->vdso_clock_mode;
	next->shift = tk->tkr_mono.shift;
	next->cycle_last = tk->tkr_mono.cycle_last;
	next->mask = tk->tkr_mono.mask;
	next->mono_mult = tk->tkr_mono.mult;
	next->raw_mult = tk->tkr_raw.mult;
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
	next->state.hrtimer_resolution = hrtimer_resolution;
	next->state.realtime_coarse.sec = tk->xtime_sec;
	next->state.realtime_coarse.nsec =
		tk->tkr_mono.xtime_nsec >> tk->tkr_mono.shift;
	next->state.monotonic_coarse.sec = monotonic_sec;
	next->state.monotonic_coarse.nsec =
		monotonic_shifted_nsec >> tk->tkr_mono.shift;
	/*
	 * time() reads only this naturally atomic field and remains available
	 * even when the clocksource cannot serve high-resolution VKSO reads.
	 */
	next->state.realtime_base.sec = tk->xtime_sec;
	vkso_time_compat_prepare_cycles(&next->state.cycles, tk);
	next->state.realtime_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->state.monotonic_base.sec = monotonic_sec;
	next->state.monotonic_base.shifted_nsec = monotonic_shifted_nsec;
	next->state.boottime_base.sec = boottime_sec;
	next->state.boottime_base.shifted_nsec = boottime_shifted_nsec;
	next->state.tai_base.sec = tk->xtime_sec + tk->tai_offset;
	next->state.tai_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->state.monotonic_raw_base.sec = tk->raw_sec;
	next->state.monotonic_raw_base.shifted_nsec = tk->tkr_raw.xtime_nsec;
}

#endif /* _KERNEL_TIME_VKSO_TIME_COMPAT_H */
