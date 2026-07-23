#define _GNU_SOURCE

#include <errno.h>
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

static int check_optional_clock(clockid_t clock_id)
{
	struct timespec current;

	errno = 0;
	if (!syscall(SYS_clock_gettime, clock_id, &current))
		return check_clock(clock_id) ? -1 : 1;
	return errno == EINVAL ? 0 : -1;
}

int main(void)
{
	int status;

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
