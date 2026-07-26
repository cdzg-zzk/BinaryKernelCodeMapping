// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/hrtimer.h>
#include <linux/stddef.h>
#include <linux/string.h>
#include <linux/time.h>
#include <linux/time64.h>
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
	__aligned(VKSO_SHARED_PAGE_SIZE) __vkso_shared_data = {
		.data.abi_version = VKSO_TIME_ABI_VERSION,
	};

struct vkso_context vkso_kernel_context;

void vkso_time_set_pvclock_page(const void *page)
{
	WRITE_ONCE(vkso_kernel_context.pvclock_page, page);
}

void vkso_time_set_hvclock_page(const void *page)
{
	WRITE_ONCE(vkso_kernel_context.hvclock_page, page);
}

static __always_inline void vkso_time_prepare_cycles(
	struct vkso_cycle_data *next, const struct tk_read_base *tkr)
{
	next->cycle_last = tkr->cycle_last;
	next->mult = tkr->mult;
	next->shift = tkr->shift;
}

static __always_inline void
vkso_time_prepare(struct vkso_shared_data *next,
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

static __always_inline void
vkso_time_publish_snapshot(struct vkso_shared_data *shared,
			   const struct vkso_shared_data *next)
{
#define VKSO_PUBLISH(member) \
	WRITE_ONCE(shared->member, next->member)

	VKSO_PUBLISH(hres.cycles.clock_mode);
	VKSO_PUBLISH(hres.cycles.cycle_last);
	VKSO_PUBLISH(hres.cycles.mult);
	VKSO_PUBLISH(hres.cycles.shift);
	VKSO_PUBLISH(hres.realtime_base.sec);
	VKSO_PUBLISH(hres.realtime_base.shifted_nsec);
	VKSO_PUBLISH(hres.monotonic_base.sec);
	VKSO_PUBLISH(hres.monotonic_base.shifted_nsec);
	VKSO_PUBLISH(hres.boottime_base.sec);
	VKSO_PUBLISH(hres.boottime_base.shifted_nsec);
	VKSO_PUBLISH(hres.tai_base.sec);
	VKSO_PUBLISH(hres.tai_base.shifted_nsec);
	VKSO_PUBLISH(realtime_coarse.sec);
	VKSO_PUBLISH(realtime_coarse.nsec);
	VKSO_PUBLISH(monotonic_coarse.sec);
	VKSO_PUBLISH(monotonic_coarse.nsec);
	VKSO_PUBLISH(raw.cycles.clock_mode);
	VKSO_PUBLISH(raw.cycles.cycle_last);
	VKSO_PUBLISH(raw.cycles.mult);
	VKSO_PUBLISH(raw.cycles.shift);
	VKSO_PUBLISH(raw.monotonic_raw_base.sec);
	VKSO_PUBLISH(raw.monotonic_raw_base.shifted_nsec);
	VKSO_PUBLISH(hrtimer_resolution);

#undef VKSO_PUBLISH
}

void vkso_time_publish(struct timekeeper *tk)
{
	struct vkso_shared_data next;
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq;

	/* Derive first so the reader-visible odd interval only copies data. */
	vkso_time_prepare(&next, tk);
	seq = READ_ONCE(shared->seq);
	WRITE_ONCE(shared->seq, seq + 1);
	smp_wmb();
	/*
	 * time() deliberately ignores seq, so its 64-bit source must be
	 * published by one aligned store.  Publishing every other member with
	 * the same scalar protocol also lets the compiler keep the prepared
	 * snapshot in registers instead of materializing it for memcpy().
	 */
	vkso_time_publish_snapshot(shared, &next);
	smp_wmb();
	WRITE_ONCE(shared->seq, seq + 2);
}

void vkso_time_update_timezone(void)
{
	struct vkso_timezone *timezone = &vkso_shared_page.data.timezone;

	WRITE_ONCE(timezone->minuteswest, sys_tz.tz_minuteswest);
	WRITE_ONCE(timezone->dsttime, sys_tz.tz_dsttime);
}
