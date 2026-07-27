// SPDX-License-Identifier: GPL-2.0

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/auxv.h>

#include "vkso_abi.h"
#include "vkso_user_wrapper.h"

_Static_assert(sizeof(struct timespec) == sizeof(struct vkso_time_value),
	       "timespec and VKSO result layouts differ");
_Static_assert(offsetof(struct timespec, tv_sec) ==
	       offsetof(struct vkso_time_value, sec),
	       "timespec seconds layout differs");
_Static_assert(offsetof(struct timespec, tv_nsec) ==
	       offsetof(struct vkso_time_value, nsec),
	       "timespec nanoseconds layout differs");
_Static_assert(sizeof(struct timeval) == sizeof(struct vkso_timeval),
	       "timeval and VKSO result layouts differ");
_Static_assert(sizeof(struct timezone) == sizeof(struct vkso_timezone),
	       "timezone and VKSO result layouts differ");
_Static_assert(sizeof(time_t) == sizeof(int64_t),
	       "native x86-64 time_t is required");

int vkso_user_wrapper_init(void)
{
	unsigned long address;
	const struct vkso_mm_data *mm_data;

	errno = 0;
	address = getauxval(AT_VKSO_MM_DATA);
	if (!address || errno) {
		errno = ENOSYS;
		return -1;
	}
	mm_data = (const void *)address;
	if (mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION ||
	    (mm_data->clock_mask & ~((1U << CLOCK_MONOTONIC) |
				     (1U << CLOCK_MONOTONIC_RAW) |
				     (1U << CLOCK_MONOTONIC_COARSE) |
				     (1U << CLOCK_BOOTTIME)))) {
		errno = EPROTO;
		return -1;
	}
	return __vkso_bind_context(mm_data, NULL, NULL);
}

int vkso_user_clock_gettime(clockid_t clock_id, struct timespec *value)
{
	return __vkso_clock_gettime(
		clock_id, (struct vkso_time_value *)value);
}

int vkso_user_clock_getres(clockid_t clock_id, struct timespec *value)
{
	return __vkso_clock_getres(clock_id,
				   (struct vkso_time_value *)value);
}

int vkso_user_gettimeofday(struct timeval *tv, struct timezone *tz)
{
	return __vkso_gettimeofday(
		(struct vkso_timeval *)tv, (struct vkso_timezone *)tz);
}

time_t vkso_user_time(time_t *tloc)
{
	return __vkso_time((int64_t *)tloc);
}

int vkso_user_getcpu(unsigned int *cpu, unsigned int *node, void *unused)
{
	return __vkso_getcpu(cpu, node, unused);
}
