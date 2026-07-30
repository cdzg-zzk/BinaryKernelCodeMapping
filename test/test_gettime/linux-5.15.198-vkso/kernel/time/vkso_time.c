// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/stddef.h>
#include <linux/time.h>
#include <linux/vkso_time.h>

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

struct vkso_context vkso_kernel_context = {
	.clock_gettime_backend = vkso_posix_clock_gettime_backend,
	.gettimeofday_backend = vkso_kernel_gettimeofday_backend,
};

void vkso_time_set_pvclock_page(const void *page)
{
	WRITE_ONCE(vkso_kernel_context.pvclock_page, page);
}

void vkso_time_set_hvclock_page(const void *page)
{
	WRITE_ONCE(vkso_kernel_context.hvclock_page, page);
}

void vkso_time_update_timezone(void)
{
	struct vkso_timezone *timezone =
		&vkso_shared_page.data.state.timezone;

	WRITE_ONCE(timezone->minuteswest, sys_tz.tz_minuteswest);
	WRITE_ONCE(timezone->dsttime, sys_tz.tz_dsttime);
}
