// SPDX-License-Identifier: GPL-2.0
/* VM-only syscall ABI regression. This is NOT the user carrier fast path. */
#include <assert.h>
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

int main(void)
{
	const clockid_t clocks[] = {CLOCK_REALTIME, CLOCK_MONOTONIC,
		CLOCK_MONOTONIC_RAW, CLOCK_BOOTTIME, CLOCK_TAI,
		CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE};
	struct timespec ts, resolution;
	struct timeval tv;
	cpu_set_t mask;
	unsigned cpu = ~0U, node = ~0U;
	time_t seconds;
	long time_result;

	CPU_ZERO(&mask);
	CPU_SET(0, &mask);
	assert(!sched_setaffinity(0, sizeof(mask), &mask));
	for (unsigned i = 0; i < sizeof(clocks) / sizeof(clocks[0]); ++i) {
		assert(!syscall(SYS_clock_gettime, clocks[i], &ts));
		assert(ts.tv_nsec >= 0 && ts.tv_nsec < 1000000000);
		assert(!syscall(SYS_clock_getres, clocks[i], &resolution));
		assert(resolution.tv_nsec >= 0 && resolution.tv_nsec < 1000000000);
		assert(!syscall(SYS_clock_getres, clocks[i], NULL));
	}
	assert(!syscall(SYS_gettimeofday, &tv, NULL));
	assert(tv.tv_usec >= 0 && tv.tv_usec < 1000000);
	time_result = syscall(SYS_time, &seconds);
	assert(time_result == seconds);
	assert(!syscall(SYS_getcpu, &cpu, &node, NULL) && cpu == 0);
	assert(!syscall(SYS_getcpu, NULL, NULL, NULL));
	errno = 0;
	assert(syscall(SYS_clock_gettime, -1, &ts) == -1 && errno == EINVAL);
	errno = 0;
	assert(syscall(SYS_clock_gettime, CLOCK_MONOTONIC, (void *)1) == -1 && errno == EFAULT);
	errno = 0;
	assert(syscall(SYS_getcpu, (void *)1, NULL, NULL) == -1 && errno == EFAULT);
	puts("CLOCKTIME_SYSCALL_SMOKE_PASS");
	return 0;
}
