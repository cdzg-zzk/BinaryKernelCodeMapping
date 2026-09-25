// SPDX-License-Identifier: GPL-2.0
/* Conventional dynamically linked API. Fallbacks use syscalls, never these
 * public symbols. Initialization is explicit, before first use. */
#include "vkso_time.h"
#include <sys/syscall.h>
#include <unistd.h>
/* Keep errno's TLS lookup and result preservation off successful calls.
 * This also avoids duplicating the error conversion in every public entry.
 * No provider selection or state is introduced on the hot path.
 */
static __attribute__((cold, noinline)) int public_error(int result)
{
    errno = -result;
    return -1;
}
static inline int public_result(int result)
{
    if (__builtin_expect(result < 0, 0))
        return public_error(result);
    return result;
}
int clock_gettime(clockid_t c, struct timespec *v)
{
    return public_result(__vkso_clock_gettime(c, (struct vkso_time_value *)v));
}
int clock_getres(clockid_t c, struct timespec *v)
{
    return public_result(__vkso_clock_getres(c, (struct vkso_time_value *)v));
}
/* The carrier normally returns zero directly. Only an unsupported provider
 * reaches this callback; libc's syscall helper supplies public errno semantics.
 * Other negative statuses are used by the mock ABI test. */
__attribute__((visibility("hidden")))
int vkso_public_gettimeofday_failure(struct vkso_timeval *v,
				     struct vkso_timezone *tz, int status)
{
    if (status != VKSO_TIME_UNSUPPORTED_MODE)
        return public_error(status);
    return (int)syscall(SYS_gettimeofday, v, tz);
}
/* Resolve once at load time, as time() already does. The steady-state public
 * call enters the carrier directly and keeps the shared clock computation. */
static int (*resolve_gettimeofday(void))(struct timeval *, void *)
{
    return (int (*)(struct timeval *, void *))(void *)__vkso_gettimeofday;
}
int gettimeofday(struct timeval *, void *)
    __attribute__((ifunc("resolve_gettimeofday")));
int vkso_time_gettimeofday(struct timeval *, void *)
    __attribute__((ifunc("resolve_gettimeofday")));
/* Same LP64 signature and semantics: resolve the address, never execute the
 * carrier during relocation. Registration and vkso_time_init still precede use.
 * No extra state, copied computation, or per-call forwarding stub is needed.
 */
static time_t (*resolve_time(void))(time_t *)
{
    return __vkso_time;
}
time_t time(time_t *) __attribute__((ifunc("resolve_time")));
int getcpu(unsigned *cpu, unsigned *node)
{
    return public_result(__vkso_getcpu(cpu, node, NULL));
}
