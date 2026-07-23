// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/sched.h>
#include <linux/time.h>
#include <linux/time64.h>
#include <linux/vkso_time.h>

union vkso_shared_page vkso_shared_page
	__aligned(VKSO_SHARED_PAGE_SIZE) __vkso_shared_data;

void vkso_time_publish_coarse(s64 realtime_sec, u64 realtime_nsec,
			      s64 monotonic_sec, u64 monotonic_nsec)
{
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq = READ_ONCE(shared->seq);

	WRITE_ONCE(shared->seq, seq + 1);
	smp_wmb();
	WRITE_ONCE(shared->abi_version, VKSO_TIME_ABI_VERSION);
	WRITE_ONCE(shared->realtime_coarse.sec, realtime_sec);
	WRITE_ONCE(shared->realtime_coarse.nsec, realtime_nsec);
	WRITE_ONCE(shared->monotonic_coarse.sec, monotonic_sec);
	WRITE_ONCE(shared->monotonic_coarse.nsec, monotonic_nsec);
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
