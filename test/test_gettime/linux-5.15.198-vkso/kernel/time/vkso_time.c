// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/stddef.h>
#include <linux/time.h>
#include <linux/vkso_time.h>

#include "vkso_time_compat.h"

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

static __always_inline void
vkso_time_publish_snapshot(struct vkso_shared_data *shared,
			   const struct vkso_shared_data *next)
{
#define VKSO_PUBLISH(member) \
	WRITE_ONCE(shared->member, next->member)

	VKSO_PUBLISH(state.cycles.clock_mode);
	VKSO_PUBLISH(state.cycles.shift);
	VKSO_PUBLISH(state.cycles.cycle_last);
	VKSO_PUBLISH(state.cycles.mask);
	VKSO_PUBLISH(state.cycles.mono_mult);
	VKSO_PUBLISH(state.cycles.raw_mult);
	VKSO_PUBLISH(state.realtime_base.sec);
	VKSO_PUBLISH(state.realtime_base.shifted_nsec);
	VKSO_PUBLISH(state.monotonic_base.sec);
	VKSO_PUBLISH(state.monotonic_base.shifted_nsec);
	VKSO_PUBLISH(state.boottime_base.sec);
	VKSO_PUBLISH(state.boottime_base.shifted_nsec);
	VKSO_PUBLISH(state.tai_base.sec);
	VKSO_PUBLISH(state.tai_base.shifted_nsec);
	VKSO_PUBLISH(state.realtime_coarse.sec);
	VKSO_PUBLISH(state.realtime_coarse.nsec);
	VKSO_PUBLISH(state.monotonic_raw_base.sec);
	VKSO_PUBLISH(state.monotonic_raw_base.shifted_nsec);
	VKSO_PUBLISH(state.monotonic_coarse.sec);
	VKSO_PUBLISH(state.monotonic_coarse.nsec);
	VKSO_PUBLISH(state.hrtimer_resolution);

#undef VKSO_PUBLISH
}

void vkso_time_publish(struct timekeeper *tk)
{
	struct vkso_shared_data next;
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq;

	vkso_time_compat_prepare(&next, tk);
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
	struct vkso_timezone *timezone =
		&vkso_shared_page.data.state.timezone;

	WRITE_ONCE(timezone->minuteswest, sys_tz.tz_minuteswest);
	WRITE_ONCE(timezone->dsttime, sys_tz.tz_dsttime);
}
