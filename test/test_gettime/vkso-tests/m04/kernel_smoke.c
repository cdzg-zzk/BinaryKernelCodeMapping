#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define SAMPLES 10000U

static int64_t to_ns(const struct timespec *ts)
{
	return (int64_t)ts->tv_sec * INT64_C(1000000000) + ts->tv_nsec;
}

static int64_t timeval_to_us(const struct timeval *tv)
{
	return (int64_t)tv->tv_sec * INT64_C(1000000) + tv->tv_usec;
}

static int check_gettimeofday_timeval(void)
{
	struct timeval previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timeval current;

		if (syscall(SYS_gettimeofday, &current, NULL) ||
		    current.tv_usec < 0 || current.tv_usec >= 1000000 ||
		    (i && timeval_to_us(&current) < timeval_to_us(&previous)))
			return 1;
		previous = current;
	}
	printf("kernel_gettimeofday_timeval=pass samples=%u\n", SAMPLES);
	return 0;
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

static int check_optional_clock(clockid_t clock_id)
{
	struct timespec current;

	errno = 0;
	if (!syscall(SYS_clock_gettime, clock_id, &current))
		return check_clock(clock_id) ? -1 : 1;
	return errno == EINVAL ? 0 : -1;
}

static int check_hres_resolution(void)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
		CLOCK_BOOTTIME, CLOCK_TAI,
	};
	struct timespec first;
	unsigned int i, clock;

	if (syscall(SYS_clock_getres, clocks[0], &first) ||
	    first.tv_sec || first.tv_nsec <= 0)
		return 1;
	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock) {
		for (i = 0; i < SAMPLES; ++i) {
			struct timespec value;

			if (syscall(SYS_clock_getres, clocks[clock], &value) ||
			    value.tv_sec != first.tv_sec ||
			    value.tv_nsec != first.tv_nsec)
				return 1;
		}
	}
	printf("kernel_clock_getres_hres=pass clocks=%zu samples=%u resolution=%ld\n",
	       sizeof(clocks) / sizeof(clocks[0]), SAMPLES, first.tv_nsec);
	return 0;
}

static int check_coarse_resolution(void)
{
	struct timespec realtime, monotonic;

	if (syscall(SYS_clock_getres, CLOCK_REALTIME_COARSE, &realtime) ||
	    syscall(SYS_clock_getres, CLOCK_MONOTONIC_COARSE, &monotonic) ||
	    realtime.tv_sec || realtime.tv_nsec <= 0 ||
	    realtime.tv_sec != monotonic.tv_sec ||
	    realtime.tv_nsec != monotonic.tv_nsec)
		return 1;
	printf("kernel_clock_getres_coarse=pass clocks=2 resolution=%ld\n",
	       realtime.tv_nsec);
	return 0;
}

static int check_clock_getres_null(void)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
		CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE,
		CLOCK_BOOTTIME, CLOCK_TAI, CLOCK_PROCESS_CPUTIME_ID,
	};
	unsigned int clock;

	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock)
		if (syscall(SYS_clock_getres, clocks[clock], NULL))
			return 1;
	puts("kernel_clock_getres_null=pass");
	return 0;
}

static int check_clock_getres_fallback(void)
{
	static const clockid_t clocks[] = {
		CLOCK_PROCESS_CPUTIME_ID, CLOCK_THREAD_CPUTIME_ID,
		CLOCK_REALTIME_ALARM, CLOCK_BOOTTIME_ALARM,
	};
	struct timespec value;
	unsigned int clock;

	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock) {
		errno = 0;
		if (syscall(SYS_clock_getres, clocks[clock], &value) &&
		    errno != EINVAL)
			return 1;
	}
	errno = 0;
	if (syscall(SYS_clock_getres, 12345, &value) != -1 ||
	    errno != EINVAL)
		return 1;
	errno = 0;
	if (syscall(SYS_clock_getres, -1, &value) != -1 || errno != EINVAL)
		return 1;
	puts("kernel_clock_getres_fallback=pass");
	puts("kernel_clock_getres_invalid=pass errno=EINVAL");
	return 0;
}

int main(void)
{
	int status;

	if (check_hres_resolution())
		return 1;
	if (check_gettimeofday_timeval())
		return 1;
	if (check_coarse_resolution() || check_clock_getres_null() ||
	    check_clock_getres_fallback())
		return 1;
	if (check_clock(CLOCK_REALTIME))
		return 1;
	printf("kernel_realtime=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_REALTIME_COARSE))
		return 1;
	printf("kernel_realtime_coarse=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_MONOTONIC))
		return 1;
	printf("kernel_monotonic=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_MONOTONIC_RAW))
		return 1;
	printf("kernel_monotonic_raw=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_MONOTONIC_COARSE))
		return 1;
	printf("kernel_monotonic_coarse=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_BOOTTIME))
		return 1;
	printf("kernel_boottime=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_TAI))
		return 1;
	printf("kernel_tai=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_PROCESS_CPUTIME_ID))
		return 1;
	printf("kernel_process_cputime_fallback=pass samples=%u\n", SAMPLES);
	if (check_clock(CLOCK_THREAD_CPUTIME_ID))
		return 1;
	printf("kernel_thread_cputime_fallback=pass samples=%u\n", SAMPLES);
	status = check_optional_clock(CLOCK_REALTIME_ALARM);
	if (status < 0)
		return 1;
	printf("kernel_realtime_alarm_fallback=pass result=%s\n",
	       status ? "time" : "EINVAL");
	status = check_optional_clock(CLOCK_BOOTTIME_ALARM);
	if (status < 0)
		return 1;
	printf("kernel_boottime_alarm_fallback=pass result=%s\n",
	       status ? "time" : "EINVAL");
	errno = 0;
	if (syscall(SYS_clock_gettime, 12345, &(struct timespec){ 0 }) != -1 ||
	    errno != EINVAL)
		return 1;
	errno = 0;
	if (syscall(SYS_clock_gettime, -1, &(struct timespec){ 0 }) != -1 ||
	    errno != EINVAL)
		return 1;
	puts("kernel_invalid_clock_fallback=pass errno=EINVAL");
	return 0;
}
