// SPDX-License-Identifier: GPL-2.0
/* Unit tests of caller-side adaptation with a clearly marked mock DSO. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "vkso_time.h"
/* The public IFUNC must resolve to the carrier, not to a forwarding stub. */
_Static_assert(__builtin_types_compatible_p(time_t, int64_t), "time ABI");
int mock_binds(void);
int mock_reads(void);
void mock_error(int);
void mock_seconds(int64_t);

static void *worker(void *argument)
{
	int number = (int)(intptr_t)argument;
	errno = EBUSY;
	assert(vkso_time_init() == 0 && errno == EBUSY);
	struct timespec ts;
	int error = number % 2 ? EACCES : EIO;
	mock_error(error);
	for (int i = 0; i < 10000; ++i) {
		errno = 0;
		assert(clock_gettime(CLOCK_MONOTONIC, &ts) == -1 && errno == error);
        assert(clock_getres(CLOCK_REALTIME, &ts) == -1 && errno == error);
        struct timeval tv;
        unsigned cpu, node;
        assert(gettimeofday(&tv, NULL) == -1 && errno == error);
        assert(getcpu(&cpu, &node) == -1 && errno == error);
	}
	return NULL;
}
int main(void)
{
	const char *mode = getenv("VKSO_TEST_MODE");
	if (mode && strcmp(mode, "success")) {
		int expected = !strcmp(mode, "missing") ? ENOSYS : !strcmp(mode, "bind") ? EIO : EPROTO;
		errno = EBUSY;
		assert(vkso_time_init() == -1 && errno == expected);
		if (!strcmp(mode, "missing")) assert(mock_reads() == 0);
		assert(mock_binds() == (!strcmp(mode, "bind") ? 1 : 0));
		unsetenv("VKSO_TEST_MODE");
		errno = 0;
		assert(vkso_time_init() == -1 && errno == expected); /* sticky failure */
		puts("MOCK initializer failure semantics PASS; NOT kernel execution");
		return 0;
	}
	assert(time == __vkso_time);
	assert((void *)gettimeofday == (void *)__vkso_gettimeofday);
	assert((void *)vkso_time_gettimeofday == (void *)__vkso_gettimeofday);
	pthread_t threads[16];
	for (int i = 0; i < 16; ++i) assert(!pthread_create(&threads[i], NULL, worker, (void *)(intptr_t)i));
	for (int i = 0; i < 16; ++i) assert(!pthread_join(threads[i], NULL));
	assert(mock_binds() == 1 && mock_reads() == 1);
	struct timespec ts;
	struct timeval tv;
	time_t t;
	unsigned cpu, node;
	errno = EBUSY;
	assert(!clock_gettime(CLOCK_MONOTONIC, &ts) && ts.tv_sec == 42 && ts.tv_nsec == 123);
	assert(errno == EBUSY);
	assert(!clock_getres(CLOCK_REALTIME, &ts) && ts.tv_sec == 0 && ts.tv_nsec == 1);
	assert(!clock_getres(CLOCK_REALTIME, NULL));
	assert(!gettimeofday(&tv, NULL) && tv.tv_sec == 42 && tv.tv_usec == 1234);
	assert(!vkso_time_gettimeofday(&tv, NULL) && tv.tv_sec == 42);
	struct timezone tz;
	assert(!gettimeofday(&tv, &tz) && tz.tz_minuteswest == 0 && tz.tz_dsttime == 0);
	assert(!getcpu(&cpu, &node) && cpu == 7 && node == 0);
	mock_seconds(-10);
	assert(time(&t) == -10 && t == -10 && errno == EBUSY);
	mock_seconds(-1);
	assert(time(NULL) == -1 && errno == EBUSY); /* seconds != encoded errno */
	assert(clock_gettime(-1, &ts) == -1 && errno == EINVAL);
	assert(clock_getres(-1, &ts) == -1 && errno == EINVAL);
	mock_error(EFAULT);
	assert(gettimeofday(&tv, NULL) == -1 && errno == EFAULT);
	assert(getcpu(&cpu, &node) == -1 && errno == EFAULT);
	mock_error(1); /* unsupported provider uses the libc syscall fallback */
	errno = 0;
	assert(gettimeofday((struct timeval *)(uintptr_t)-1, NULL) == -1 &&
	       errno == EFAULT);
	errno = 0;
	assert(vkso_time_gettimeofday((struct timeval *)(uintptr_t)-1, NULL) == -1 &&
	       errno == EFAULT);
	puts("MOCK direct-link ABI/errno/once/TLS PASS; NOT kernel execution");
	return 0;
}
