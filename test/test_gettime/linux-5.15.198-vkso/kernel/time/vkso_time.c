// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/hrtimer.h>
#include <linux/sched.h>
#include <linux/stddef.h>
#include <linux/string.h>
#include <linux/time.h>
#include <linux/time64.h>
#include <linux/time_namespace.h>
#include <linux/timekeeper_internal.h>
#include <linux/vkso_time.h>

#include <vdso/clocksource.h>

static_assert(sizeof(struct timespec64) == sizeof(struct vkso_time_value) &&
	      offsetof(struct timespec64, tv_sec) ==
	      offsetof(struct vkso_time_value, sec) &&
	      offsetof(struct timespec64, tv_nsec) ==
	      offsetof(struct vkso_time_value, nsec));
static_assert(sizeof(__kernel_old_time_t) == sizeof(s64));
static_assert(sizeof(struct __kernel_old_timeval) ==
	      sizeof(struct vkso_timeval) &&
	      offsetof(struct __kernel_old_timeval, tv_sec) ==
	      offsetof(struct vkso_timeval, sec) &&
	      offsetof(struct __kernel_old_timeval, tv_usec) ==
	      offsetof(struct vkso_timeval, usec));
static_assert(sizeof(struct timezone) == sizeof(struct vkso_timezone) &&
	      offsetof(struct timezone, tz_minuteswest) ==
	      offsetof(struct vkso_timezone, minuteswest) &&
	      offsetof(struct timezone, tz_dsttime) ==
	      offsetof(struct vkso_timezone, dsttime));

union vkso_shared_page vkso_shared_page
	__aligned(VKSO_SHARED_PAGE_SIZE) __vkso_shared_data;

static __always_inline void vkso_time_prepare_cycles(
	struct vkso_cycle_data *next, const struct tk_read_base *tkr)
{
	next->cycle_last = tkr->cycle_last;
	next->mult = tkr->mult;
	next->shift = tkr->shift;
}

static void vkso_time_prepare(struct vkso_shared_data *next,
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
	next->abi_version = VKSO_TIME_ABI_VERSION;
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
	if (clock_mode == VDSO_CLOCKMODE_NONE)
		return;
	vkso_time_prepare_cycles(&next->hres.cycles, &tk->tkr_mono);
	vkso_time_prepare_cycles(&next->raw.cycles, &tk->tkr_raw);
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

void vkso_time_publish(struct timekeeper *tk)
{
	struct vkso_shared_data next = { 0 };
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	size_t payload_offset = offsetof(struct vkso_shared_data, abi_version);
	size_t seconds_offset =
		offsetof(struct vkso_shared_data, hres.realtime_base.sec);
	size_t after_seconds = seconds_offset +
		sizeof(shared->hres.realtime_base.sec);
	size_t payload_end = offsetof(struct vkso_shared_data, timezone);
	u32 seq;

	/* Derive first so the reader-visible odd interval only copies data. */
	vkso_time_prepare(&next, tk);
	seq = READ_ONCE(shared->seq);
	WRITE_ONCE(shared->seq, seq + 1);
	smp_wmb();
	memcpy((u8 *)shared + payload_offset, (u8 *)&next + payload_offset,
	       seconds_offset - payload_offset);
	/*
	 * time() deliberately ignores seq, so its 64-bit source must be
	 * published by one aligned store rather than a potentially split copy.
	 */
	WRITE_ONCE(shared->hres.realtime_base.sec,
		   next.hres.realtime_base.sec);
	memcpy((u8 *)shared + after_seconds, (u8 *)&next + after_seconds,
	       payload_end - after_seconds);
	smp_wmb();
	WRITE_ONCE(shared->seq, seq + 2);
}

void vkso_time_update_timezone(void)
{
	struct vkso_timezone *timezone = &vkso_shared_page.data.timezone;

	WRITE_ONCE(timezone->minuteswest, sys_tz.tz_minuteswest);
	WRITE_ONCE(timezone->dsttime, sys_tz.tz_dsttime);
}

notrace int vkso_time_get_context(clockid_t clock_id, struct timespec64 *tp)
{
	const struct vkso_mm_data *mm_data = NULL;

#ifdef CONFIG_TIME_NS
	if (unlikely(current->nsproxy->time_ns != &init_time_ns))
		mm_data = READ_ONCE(current->mm->context.vkso_mm_kdata);
#endif
	return __vkso_clock_gettime(mm_data, clock_id,
				   (struct vkso_time_value *)tp);
}
