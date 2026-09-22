// SPDX-License-Identifier: GPL-2.0

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/auxv.h>
#include <sys/time.h>
#include <time.h>

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
_Static_assert(sizeof(struct vkso_read_state) == 160,
	       "VKSO shared read state layout differs");
_Static_assert(sizeof(struct vkso_shared_data) == 168,
	       "VKSO shared data layout differs");
_Static_assert(sizeof(struct vkso_context) == 32,
	       "VKSO environment context layout differs");
_Static_assert(offsetof(struct vkso_shared_data,
			state.realtime_base.sec) == 40,
	       "VKSO realtime hot field moved");
_Static_assert(offsetof(struct vkso_shared_data,
			state.monotonic_raw_base) == 128,
	       "VKSO raw cache-line layout differs");

int vkso_user_wrapper_init(void)
{
	unsigned long address;
	int saved_errno = errno;
	int result;
	const struct vkso_shared_data *shared;
	const struct vkso_mm_data *mm_data;

	/* Reject a non-VKSO kernel before touching carrier-backed state. */
	errno = 0;
	address = getauxval(AT_VKSO_MM_DATA);
	if (!address || errno) {
		errno = ENOSYS;
		return -1;
	}
	shared = __vkso_shared_data();
	if (!shared || shared->abi_version != VKSO_TIME_ABI_VERSION) {
		errno = EPROTO;
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
	result = __vkso_bind_context(mm_data, NULL, NULL);
	if (result) {
		errno = result < 0 ? -result : EPROTO;
		return -1;
	}
	errno = saved_errno;
	return 0;
}
