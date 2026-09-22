/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_PUBLIC_TIME_H
#define VKSO_PUBLIC_TIME_H

/* Explicit native x86-64 dynamic-library API, not libc symbol interposition.
 * Link vkso_user_wrapper.o and the registered libkernel.so. Call
 * vkso_time_init() before creating reader threads or making ANY API call.
 * The registration must remain active until all consumers exit.
 * Only the small return-convention adaptation is inlined into the caller;
 * every time calculation still calls the carrier's __vkso_* symbol.
 */
#if !defined(__x86_64__) || !defined(__LP64__)
#error "VKSO time API requires native x86-64 LP64"
#endif
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/time.h>
#include <time.h>
#include "vkso_abi.h"
#include "vkso_user_wrapper.h"

_Static_assert(sizeof(time_t) == sizeof(int64_t), "64-bit time_t required");
_Static_assert(sizeof(struct timespec) == sizeof(struct vkso_time_value),
               "timespec ABI mismatch");
_Static_assert(offsetof(struct timespec, tv_nsec) ==
               offsetof(struct vkso_time_value, nsec), "timespec offset mismatch");
_Static_assert(sizeof(struct timeval) == sizeof(struct vkso_timeval),
               "timeval ABI mismatch");
_Static_assert(offsetof(struct timeval, tv_usec) ==
               offsetof(struct vkso_timeval, usec), "timeval offset mismatch");

static inline int vkso_time_init(void)
{
    return vkso_user_wrapper_init();
}

static inline int vkso_public_result(int result)
{
    if (__builtin_expect(result < 0, 0)) {
        errno = -result;
        return -1;
    }
    return result;
}

static inline int vkso_clock_gettime(clockid_t id, struct timespec *value)
{
    return vkso_public_result(__vkso_clock_gettime(
        id, (struct vkso_time_value *)value));
}

static inline int vkso_clock_getres(clockid_t id, struct timespec *value)
{
    return vkso_public_result(__vkso_clock_getres(
        id, (struct vkso_time_value *)value));
}

static inline int vkso_gettimeofday(struct timeval *tv, void *tz)
{
    return vkso_public_result(__vkso_gettimeofday(
        (struct vkso_timeval *)tv, (struct vkso_timezone *)tz));
}

static inline time_t vkso_time(time_t *value)
{
    /* __vkso_time reads signed seconds; it has no -errno syscall return.
     * Do NOT mistake valid pre-epoch seconds for a Linux error code. */
    return (time_t)__vkso_time((int64_t *)value);
}

static inline int vkso_getcpu(unsigned int *cpu, unsigned int *node)
{
    return vkso_public_result(__vkso_getcpu(cpu, node, NULL));
}
#endif
