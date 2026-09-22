/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_TIME_DIRECT_H
#define VKSO_TIME_DIRECT_H

/* Linux x86-64 LP64 only. Compile with -D_GNU_SOURCE.
 * Call vkso_time_init() successfully before using these entries. Registration
 * must already be active and remain active until all users have exited.
 * Names are explicit: this header does NOT interpose libc or affect its users.
 * The inline code is API adaptation, NOT a copy of the shared time core.
 */
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/time.h>
#include <time.h>
#if !defined(__x86_64__) || defined(__ILP32__)
#error "VKSO direct time API requires Linux x86-64 LP64"
#endif
#ifdef __cplusplus
extern "C" {
#define VKSO_ASSERT static_assert
#else
#define VKSO_ASSERT _Static_assert
#endif
#include "vkso_abi.h"

VKSO_ASSERT(sizeof(void *) == 8 && sizeof(time_t) == 8, "LP64 time ABI required");
VKSO_ASSERT(sizeof(struct timespec) == sizeof(struct vkso_time_value), "timespec size");
VKSO_ASSERT(offsetof(struct timespec, tv_sec) == offsetof(struct vkso_time_value, sec), "seconds offset");
VKSO_ASSERT(offsetof(struct timespec, tv_nsec) == offsetof(struct vkso_time_value, nsec), "nanoseconds offset");
VKSO_ASSERT(sizeof(struct timeval) == sizeof(struct vkso_timeval), "timeval size");
VKSO_ASSERT(offsetof(struct timeval, tv_sec) == offsetof(struct vkso_timeval, sec), "timeval seconds offset");
VKSO_ASSERT(offsetof(struct timeval, tv_usec) == offsetof(struct vkso_timeval, usec), "microseconds offset");

/* One-time, thread-safe initialization. No hot-path once check. A failed first
 * initialization is sticky; fix deployment and start a new process to retry.
 * Preserves this thread's errno on success; returns -1/errno on failure.
 */
int vkso_time_init(void);

static inline int vkso_time_result(int result)
{
	if (__builtin_expect(result < 0, 0)) {
		errno = -result;
		return -1;
	}
	return result;
}

static inline int vkso_time_clock_gettime(clockid_t clock, struct timespec *ts)
{
	return vkso_time_result(__vkso_clock_gettime(clock, (struct vkso_time_value *)ts));
}

static inline int vkso_time_clock_getres(clockid_t clock, struct timespec *ts)
{
	return vkso_time_result(__vkso_clock_getres(clock, (struct vkso_time_value *)ts));
}

/* This entry exposes VKSO's raw timezone semantics. For comparison with libc,
 * use tz == NULL: libc need not forward its obsolete timezone argument.
 */
static inline int vkso_time_gettimeofday(struct timeval *tv, void *tz)
{
	return vkso_time_result(__vkso_gettimeofday((struct vkso_timeval *)tv,
						 (struct vkso_timezone *)tz));
}

/* Valid writable tloc or NULL. Negative seconds are valid timestamps, not a
 * generic -errno encoding: do NOT run this value through vkso_time_result().
 */
static inline time_t vkso_time_time(time_t *tloc)
{
	return (time_t)__vkso_time((int64_t *)tloc);
}

static inline int vkso_time_getcpu(unsigned int *cpu, unsigned int *node)
{
	return vkso_time_result(__vkso_getcpu(cpu, node, NULL));
}
#undef VKSO_ASSERT
#ifdef __cplusplus
}
#endif
#endif
