// SPDX-License-Identifier: GPL-2.0

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/auxv.h>
#include <sys/syscall.h>

#include "vkso_abi.h"
#include "vkso_user_wrapper.h"

static const struct vkso_mm_data *vkso_mm_data;
static const struct vkso_cycle_context vkso_user_cycle_context;

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

static inline long vkso_raw_syscall2(long number, long first, long second)
{
	register long rax asm("rax") = number;
	register long rdi asm("rdi") = first;
	register long rsi asm("rsi") = second;

	asm volatile("syscall"
		     : "+a" (rax)
		     : "D" (rdi), "S" (rsi)
		     : "rcx", "r11", "memory");
	return rax;
}

int vkso_user_wrapper_init(void)
{
	unsigned long address;

	errno = 0;
	address = getauxval(AT_VKSO_MM_DATA);
	if (!address || errno) {
		errno = ENOSYS;
		return -1;
	}
	vkso_mm_data = (const void *)address;
	if (vkso_mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION ||
	    vkso_mm_data->reserved) {
		errno = EPROTO;
		vkso_mm_data = NULL;
		return -1;
	}
	return 0;
}

int vkso_user_clock_gettime(clockid_t clock_id, struct timespec *value)
{
	int status;

	status = vkso_clock_gettime_core(
		vkso_mm_data, clock_id, (struct vkso_time_value *)value,
		&vkso_user_cycle_context);
	if (status == VKSO_TIME_OK)
		return 0;
	return vkso_raw_syscall2(SYS_clock_gettime, clock_id,
				 (long)value);
}

int vkso_user_clock_getres(clockid_t clock_id, struct timespec *value)
{
	int status;

	status = __vkso_clock_getres(clock_id,
				    (struct vkso_time_value *)value);
	if (status == VKSO_TIME_OK)
		return 0;
	return vkso_raw_syscall2(SYS_clock_getres, clock_id, (long)value);
}

int vkso_user_gettimeofday(struct timeval *tv, struct timezone *tz)
{
	int status;

	status = vkso_gettimeofday_core(
		(struct vkso_timeval *)tv, (struct vkso_timezone *)tz,
		&vkso_user_cycle_context);
	if (status == VKSO_TIME_OK)
		return 0;
	return vkso_raw_syscall2(SYS_gettimeofday, (long)tv, (long)tz);
}

time_t vkso_user_time(time_t *tloc)
{
	return __vkso_time((int64_t *)tloc);
}

int vkso_user_getcpu(unsigned int *cpu, unsigned int *node, void *unused)
{
	return __vkso_getcpu(cpu, node, unused);
}
