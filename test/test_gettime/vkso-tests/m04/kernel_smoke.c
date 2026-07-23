#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define SAMPLES 10000U

static int64_t to_ns(const struct timespec *ts)
{
	return (int64_t)ts->tv_sec * INT64_C(1000000000) + ts->tv_nsec;
}

static int check_clock(clockid_t clock_id)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timespec current;

		if (syscall(SYS_clock_gettime, clock_id, &current) ||
		    current.tv_nsec < 0 || current.tv_nsec >= 1000000000L ||
		    (i && to_ns(&current) < to_ns(&previous)))
			return 1;
		previous = current;
	}
	return 0;
}

int main(void)
{
	if (check_clock(CLOCK_REALTIME))
		return 1;
	printf("kernel_realtime=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_REALTIME_COARSE))
		return 1;
	printf("kernel_realtime_coarse=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_MONOTONIC_COARSE))
		return 1;
	printf("kernel_monotonic_coarse=pass samples=%u\n", SAMPLES);
	return 0;
}
