#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

static int check_gettimeofday_timezone(void)
{
	struct timeval timeval;
	struct timezone timezone, combined_timezone;

	if (syscall(SYS_gettimeofday, NULL, &timezone) ||
	    syscall(SYS_gettimeofday, &timeval, &combined_timezone) ||
	    syscall(SYS_gettimeofday, &timeval, NULL) ||
	    syscall(SYS_gettimeofday, NULL, NULL) ||
	    timezone.tz_minuteswest != combined_timezone.tz_minuteswest ||
	    timezone.tz_dsttime != combined_timezone.tz_dsttime ||
	    timeval.tv_usec < 0 || timeval.tv_usec >= 1000000)
		return 1;
	puts("kernel_gettimeofday_timezone=pass");
	puts("kernel_gettimeofday_null_combinations=pass combinations=4");
	return 0;
}

static int check_time(void)
{
	time_t previous = 0;
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		long current;

		errno = 0;
		current = syscall(SYS_time, NULL);
		if ((current == -1 && errno) || (i && current < previous))
			return 1;
		previous = current;
	}
	printf("kernel_time_null=pass samples=%u\n", SAMPLES);

	for (i = 0; i < SAMPLES; ++i) {
		time_t stored = (time_t)-1;
		long current;

		errno = 0;
		current = syscall(SYS_time, &stored);
		if ((current == -1 && errno) || current != stored)
			return 1;
	}
	printf("kernel_time_pointer=pass samples=%u\n", SAMPLES);
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

static int cpu_node_from_sysfs(unsigned int cpu, unsigned int *node)
{
	char path[128];
	struct dirent *entry;
	DIR *directory;

	if (snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%u", cpu) >=
	    (int)sizeof(path))
		return -1;
	directory = opendir(path);
	if (!directory)
		return -1;
	while ((entry = readdir(directory))) {
		char *end;
		unsigned long value;

		if (strncmp(entry->d_name, "node", 4))
			continue;
		errno = 0;
		value = strtoul(entry->d_name + 4, &end, 10);
		if (!errno && end != entry->d_name + 4 && !*end &&
		    value <= UINT32_MAX) {
			closedir(directory);
			*node = (unsigned int)value;
			return 0;
		}
	}
	closedir(directory);
	return -1;
}

static int check_getcpu(void)
{
	unsigned int cpus[CPU_SETSIZE];
	unsigned int nodes[CPU_SETSIZE];
	cpu_set_t original, allowed, affinity;
	unsigned int cpu_count = 0, node_count = 0;
	unsigned int cpu, cpu_index;

	if (sched_getaffinity(0, sizeof(original), &original))
		return 1;
	allowed = original;
	for (cpu = 0; cpu < CPU_SETSIZE; ++cpu)
		if (CPU_ISSET(cpu, &allowed))
			cpus[cpu_count++] = cpu;
	if (!cpu_count)
		return 1;

	for (cpu_index = 0; cpu_index < cpu_count; ++cpu_index) {
		unsigned int expected_node, node_index, i;

		if (cpu_node_from_sysfs(cpus[cpu_index], &expected_node))
			return 1;
		for (node_index = 0; node_index < node_count; ++node_index)
			if (nodes[node_index] == expected_node)
				break;
		if (node_index == node_count)
			nodes[node_count++] = expected_node;
		CPU_ZERO(&affinity);
		CPU_SET(cpus[cpu_index], &affinity);
		if (sched_setaffinity(0, sizeof(affinity), &affinity))
			return 1;
		for (i = 0; i < SAMPLES; ++i) {
			unsigned int actual_cpu, actual_node;

			if (syscall(SYS_getcpu, &actual_cpu, &actual_node, NULL) ||
			    actual_cpu != cpus[cpu_index] ||
			    actual_node != expected_node)
				return 1;
		}
	}

	CPU_ZERO(&affinity);
	CPU_SET(cpus[0], &affinity);
	if (sched_setaffinity(0, sizeof(affinity), &affinity))
		return 1;
	{
		unsigned int actual_cpu, actual_node;

		if (syscall(SYS_getcpu, &actual_cpu, &actual_node, NULL) ||
		    actual_cpu != cpus[0] ||
		    syscall(SYS_getcpu, &actual_cpu, NULL, NULL) ||
		    actual_cpu != cpus[0] ||
		    syscall(SYS_getcpu, NULL, &actual_node, NULL) ||
		    actual_node != nodes[0] ||
		    syscall(SYS_getcpu, NULL, NULL, NULL))
			return 1;
	}
	if (sched_setaffinity(0, sizeof(original), &original))
		return 1;

	printf("kernel_getcpu_cpu=pass samples_per_cpu=%u\n", SAMPLES);
	printf("kernel_getcpu_node=pass nodes=%u samples_per_cpu=%u\n",
	       node_count, SAMPLES);
	puts("kernel_getcpu_null=pass combinations=4");
	printf("kernel_getcpu_multi_cpu=pass cpus=%u samples_per_cpu=%u\n",
	       cpu_count, SAMPLES);
	return 0;
}

int main(int argc, char **argv)
{
	int status;

	if (argc == 2 && !strcmp(argv[1], "--getcpu-only"))
		return check_getcpu();
	if (check_hres_resolution())
		return 1;
	if (check_gettimeofday_timeval())
		return 1;
	if (check_gettimeofday_timezone())
		return 1;
	if (check_time())
		return 1;
	if (check_getcpu())
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
