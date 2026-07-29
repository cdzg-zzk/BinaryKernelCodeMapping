// SPDX-License-Identifier: GPL-2.0
#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/ptrace.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/timex.h>
#include <sys/time.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifdef VKSO_BACKEND
#include "vkso_abi.h"
#include "vkso_user_wrapper.h"
#endif

#ifndef CLOCK_REALTIME_ALARM
#define CLOCK_REALTIME_ALARM 8
#endif
#ifndef CLOCK_BOOTTIME_ALARM
#define CLOCK_BOOTTIME_ALARM 9
#endif
#ifndef CLOCK_TAI
#define CLOCK_TAI 11
#endif
#ifndef CLONE_NEWTIME
#define CLONE_NEWTIME 0x00000080
#endif

#define PATH_ERRNO 222
#define REPEAT_SAMPLES 1000
#define THREAD_SAMPLES 2000
#define MAX_TEST_THREADS 4
#define NS_MONOTONIC_OFFSET_NS INT64_C(7123456789)
#define NS_BOOTTIME_OFFSET_NS INT64_C(11234567890)
#define LEAP_TIMEOUT_NS INT64_C(6000000000)
#define LEAP_DELTA_TOLERANCE_NS INT64_C(100000000)

#define TEST_CPUCLOCK_PERTHREAD_MASK 4
#define TEST_CPUCLOCK_SCHED 2
#define TEST_CLOCKFD 3

typedef int (*clock_gettime_fn)(clockid_t, struct timespec *);
typedef int (*clock_getres_fn)(clockid_t, struct timespec *);
typedef int (*gettimeofday_fn)(struct timeval *, struct timezone *);
typedef time_t (*time_fn)(time_t *);
typedef int (*getcpu_fn)(unsigned int *, unsigned int *, void *);

struct backend {
	const char *name;
	clock_gettime_fn clock_gettime;
	clock_getres_fn clock_getres;
	gettimeofday_fn gettimeofday;
	time_fn time;
	getcpu_fn getcpu;
};

static struct backend backend;
static int dynamic_clock_fd = -1;
static clockid_t dynamic_clock_id;

static void fail(const char *message)
{
	fprintf(stderr, "failure=%s errno=%d\n", message, errno);
	exit(1);
}

#ifndef VKSO_BACKEND
static void *resolve_vdso(void *handle, const char *name)
{
	void *address = dlvsym(handle, name, "LINUX_2.6");

	if (!address) {
		fprintf(stderr, "missing_vdso_symbol=%s error=%s\n", name,
			dlerror());
		exit(1);
	}
	return address;
}
#endif

static void init_backend(void)
{
#ifdef VKSO_BACKEND
	if (vkso_user_wrapper_init())
		fail("vkso wrapper init");
	backend.name = "vkso";
	backend.clock_gettime = (clock_gettime_fn)__vkso_clock_gettime;
	backend.clock_getres = (clock_getres_fn)__vkso_clock_getres;
	backend.gettimeofday = (gettimeofday_fn)__vkso_gettimeofday;
	backend.time = (time_fn)__vkso_time;
	backend.getcpu = (getcpu_fn)__vkso_getcpu;
#else
	void *handle = dlopen("linux-vdso.so.1", RTLD_NOW | RTLD_LOCAL);

	if (!handle)
		fail("open linux-vdso.so.1");
	backend.name = "raw-vdso";
	backend.clock_gettime = (clock_gettime_fn)
		resolve_vdso(handle, "__vdso_clock_gettime");
	backend.clock_getres = (clock_getres_fn)
		resolve_vdso(handle, "__vdso_clock_getres");
	backend.gettimeofday = (gettimeofday_fn)
		resolve_vdso(handle, "__vdso_gettimeofday");
	backend.time = (time_fn)resolve_vdso(handle, "__vdso_time");
	backend.getcpu = (getcpu_fn)resolve_vdso(handle, "__vdso_getcpu");
#endif
}

static int mapping_at(const void *address, char permissions[5])
{
	const uintptr_t target = (uintptr_t)address;
	char line[512], current[5];
	unsigned long start, end;
	FILE *stream;

	stream = fopen("/proc/self/maps", "r");
	if (!stream)
		fail("open process maps");
	while (fgets(line, sizeof(line), stream)) {
		if (sscanf(line, "%lx-%lx %4s", &start, &end, current) != 3)
			continue;
		if (target < start || target >= end)
			continue;
		memcpy(permissions, current, sizeof(current));
		fclose(stream);
		return 0;
	}
	fclose(stream);
	return -1;
}

#ifndef VKSO_BACKEND
static int named_mapping(const char *name, char permissions[5])
{
	char line[512], current[5];
	unsigned long start, end;
	FILE *stream;

	stream = fopen("/proc/self/maps", "r");
	if (!stream)
		fail("open named process maps");
	while (fgets(line, sizeof(line), stream)) {
		if (!strstr(line, name) ||
		    sscanf(line, "%lx-%lx %4s", &start, &end, current) != 3)
			continue;
		memcpy(permissions, current, sizeof(current));
		fclose(stream);
		return 0;
	}
	fclose(stream);
	return -1;
}
#endif

static void check_mapping_security(void)
{
	char code[5], shared[5], context[5];

	if (mapping_at((const void *)backend.clock_gettime, code) ||
	    code[0] != 'r' || code[1] != '-' || code[2] != 'x')
		fail("public code mapping permissions");
#ifdef VKSO_BACKEND
	{
		const void *mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
		const void *shared_data = __vkso_shared_data();

		if (!mm_data || !shared_data ||
		    mapping_at(shared_data, shared) ||
		    mapping_at(mm_data, context))
			fail("VKSO data mapping lookup");
	}
#else
	if (named_mapping("[vvar]", shared) ||
	    named_mapping("[vvar]", context))
		fail("Raw VVAR mapping lookup");
#endif
	if (shared[0] != 'r' || shared[1] != '-' || shared[2] != '-' ||
	    context[0] != 'r' || context[1] != '-' || context[2] != '-')
		fail("shared/context mapping permissions");
	puts("security.mapping_permissions=pass code=R-X data=R-- context=R--");
}

static int64_t timespec_ns(const struct timespec *value)
{
	return (int64_t)value->tv_sec * INT64_C(1000000000) +
		value->tv_nsec;
}

static int64_t timeval_us(const struct timeval *value)
{
	return (int64_t)value->tv_sec * INT64_C(1000000) +
		value->tv_usec;
}

static clockid_t make_test_cpuclock(unsigned int id, int per_thread)
{
	return (clockid_t)(((~id) << 3) | TEST_CPUCLOCK_SCHED |
		(per_thread ? TEST_CPUCLOCK_PERTHREAD_MASK : 0));
}

static clockid_t make_test_fd_clock(int fd)
{
	return (clockid_t)(((~(unsigned int)fd) << 3) | TEST_CLOCKFD);
}

static void open_dynamic_clock(void)
{
	const char *path = getenv("VKSO_TEST_DYNAMIC_CLOCK");

	if (!path || !*path)
		fail("missing dynamic clock path");
	dynamic_clock_fd = open(path, O_RDWR | O_CLOEXEC);
	if (dynamic_clock_fd < 0)
		fail("open dynamic clock");
	dynamic_clock_id = make_test_fd_clock(dynamic_clock_fd);
}

static void check_clock_value(clockid_t id, const char *name)
{
	struct timespec before, value, after, previous = { 0 };
	int sample;

	for (sample = 0; sample < REPEAT_SAMPLES; ++sample) {
		if (syscall(SYS_clock_gettime, id, &before) ||
		    backend.clock_gettime(id, &value) ||
		    syscall(SYS_clock_gettime, id, &after))
			fail("valid clock_gettime");
		if (value.tv_nsec < 0 || value.tv_nsec >= 1000000000L ||
		    timespec_ns(&value) < timespec_ns(&before) ||
		    timespec_ns(&value) > timespec_ns(&after) ||
		    (sample && timespec_ns(&value) <
			       timespec_ns(&previous)))
			fail("clock_gettime bracket/monotonicity");
		previous = value;
	}
	printf("semantics.clock_gettime.%s=pass\n", name);
}

static void check_fallback_clock_value(clockid_t id, const char *name)
{
	struct timespec probe;

	errno = 0;
	if (syscall(SYS_clock_gettime, id, &probe)) {
		int expected_errno = errno;

		errno = EDOM;
		if (backend.clock_gettime(id, &probe) != -expected_errno ||
		    errno != EDOM)
			fail("clock_gettime fallback error");
		printf("semantics.clock_gettime.%s=pass\n", name);
		return;
	}
	check_clock_value(id, name);
}

static void check_clock_gettime(void)
{
	static const struct {
		clockid_t id;
		const char *name;
	} fast[] = {
		{ CLOCK_REALTIME, "realtime" },
		{ CLOCK_MONOTONIC, "monotonic" },
		{ CLOCK_MONOTONIC_RAW, "monotonic_raw" },
		{ CLOCK_BOOTTIME, "boottime" },
		{ CLOCK_TAI, "tai" },
		{ CLOCK_REALTIME_COARSE, "realtime_coarse" },
		{ CLOCK_MONOTONIC_COARSE, "monotonic_coarse" },
	};
	static const struct {
		clockid_t id;
		const char *name;
	} fallback[] = {
		{ CLOCK_PROCESS_CPUTIME_ID, "process_cpu" },
		{ CLOCK_THREAD_CPUTIME_ID, "thread_cpu" },
		{ CLOCK_REALTIME_ALARM, "realtime_alarm" },
		{ CLOCK_BOOTTIME_ALARM, "boottime_alarm" },
	};
	struct timespec value;
	size_t index;

	for (index = 0; index < sizeof(fast) / sizeof(fast[0]); ++index)
		check_clock_value(fast[index].id, fast[index].name);
	for (index = 0; index < sizeof(fallback) / sizeof(fallback[0]);
	     ++index)
		check_fallback_clock_value(fallback[index].id,
					   fallback[index].name);
	check_fallback_clock_value(make_test_cpuclock(0, 0),
				   "encoded_process_cpu");
	check_fallback_clock_value(make_test_cpuclock(0, 1),
				   "encoded_thread_cpu");

	errno = EDOM;
	if (backend.clock_gettime((clockid_t)-1, &value) != -EINVAL ||
	    errno != EDOM)
		fail("clock_gettime invalid return ABI");
	puts("semantics.clock_gettime.invalid=pass");

	check_fallback_clock_value(make_test_fd_clock(12345),
				   "dynamic_invalid_fd");
	errno = EDOM;
	if (backend.clock_gettime((clockid_t)10, &value) != -EINVAL ||
	    errno != EDOM ||
	    backend.clock_gettime((clockid_t)12, &value) != -EINVAL ||
	    errno != EDOM ||
	    backend.clock_gettime((clockid_t)INT32_MAX, &value) != -EINVAL ||
	    errno != EDOM)
		fail("clock_gettime invalid positive IDs");
	puts("semantics.clock_gettime.invalid_positive=pass");
}

static void check_fast_null_clock_gettime(void)
{
	pid_t child = fork();
	int status;

	if (child < 0)
		fail("fork fast NULL clock_gettime");
	if (!child) {
		if (backend.clock_gettime(CLOCK_REALTIME, NULL) == -EFAULT)
			_exit(71);
		_exit(70);
	}
	if (waitpid(child, &status, 0) != child)
		fail("wait fast NULL clock_gettime");
	if ((!WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV) &&
	    (!WIFEXITED(status) || WEXITSTATUS(status) != 71))
		fail("clock_gettime NULL semantics");

	errno = EDOM;
	if (backend.clock_gettime(CLOCK_PROCESS_CPUTIME_ID, NULL) !=
	    -EFAULT || errno != EDOM)
		fail("fallback clock_gettime NULL");
	errno = EDOM;
	if (backend.clock_gettime((clockid_t)-1, NULL) != -EINVAL ||
	    errno != EDOM)
		fail("invalid clock_gettime NULL");
	puts("semantics.clock_gettime.null=pass");
}

static void check_clock_getres(void)
{
	static const struct {
		clockid_t id;
		const char *name;
		int fallback;
	} valid[] = {
		{ CLOCK_REALTIME, "realtime", 0 },
		{ CLOCK_MONOTONIC, "monotonic", 0 },
		{ CLOCK_MONOTONIC_RAW, "monotonic_raw", 0 },
		{ CLOCK_BOOTTIME, "boottime", 0 },
		{ CLOCK_TAI, "tai", 0 },
		{ CLOCK_REALTIME_COARSE, "realtime_coarse", 0 },
		{ CLOCK_MONOTONIC_COARSE, "monotonic_coarse", 0 },
		{ CLOCK_PROCESS_CPUTIME_ID, "process_cpu", 1 },
		{ CLOCK_THREAD_CPUTIME_ID, "thread_cpu", 1 },
		{ CLOCK_REALTIME_ALARM, "realtime_alarm", 1 },
		{ CLOCK_BOOTTIME_ALARM, "boottime_alarm", 1 },
	};
	struct timespec expected, value;
	size_t index;

	for (index = 0; index < sizeof(valid) / sizeof(valid[0]); ++index) {
		errno = 0;
		if (syscall(SYS_clock_getres, valid[index].id, &expected)) {
			int expected_errno = errno;

			if (!valid[index].fallback)
				fail("fast clock_getres syscall oracle");
			errno = EDOM;
			if (backend.clock_getres(valid[index].id, &value) !=
			    -expected_errno || errno != EDOM ||
			    backend.clock_getres(valid[index].id, NULL) !=
			    -expected_errno || errno != EDOM)
				fail("clock_getres fallback error");
		} else {
			if (backend.clock_getres(valid[index].id, &value) ||
			    value.tv_sec != expected.tv_sec ||
			    value.tv_nsec != expected.tv_nsec ||
			    backend.clock_getres(valid[index].id, NULL))
				fail("clock_getres value/NULL");
		}
		printf("semantics.clock_getres.%s=pass\n",
		       valid[index].name);
	}
	errno = EDOM;
	if (backend.clock_getres((clockid_t)-1, &value) != -EINVAL ||
	    errno != EDOM ||
	    backend.clock_getres((clockid_t)-1, NULL) != -EINVAL ||
	    errno != EDOM)
		fail("clock_getres invalid ABI");
	puts("semantics.clock_getres.invalid_null=pass");

	for (index = 0; index < 2; ++index) {
		clockid_t id = make_test_cpuclock(0, index != 0);

		if (syscall(SYS_clock_getres, id, &expected))
			fail("encoded CPU clock_getres oracle");
		errno = EDOM;
		if (backend.clock_getres(id, &value) ||
		    value.tv_sec != expected.tv_sec ||
		    value.tv_nsec != expected.tv_nsec ||
		    backend.clock_getres(id, NULL) || errno != EDOM)
			fail("encoded CPU clock_getres");
	}
	puts("semantics.clock_getres.encoded_cpu=pass");

	errno = 0;
	if (syscall(SYS_clock_getres, make_test_fd_clock(12345),
		    &expected) != -1)
		fail("dynamic invalid clock_getres oracle");
	{
		int expected_errno = errno;

		errno = EDOM;
		if (backend.clock_getres(make_test_fd_clock(12345), &value) !=
		    -expected_errno || errno != EDOM ||
		    backend.clock_getres(make_test_fd_clock(12345), NULL) !=
		    -expected_errno || errno != EDOM)
			fail("dynamic invalid clock_getres");
	}
	puts("semantics.clock_getres.dynamic_invalid_fd=pass");

	errno = EDOM;
	if (backend.clock_getres((clockid_t)10, &value) != -EINVAL ||
	    errno != EDOM ||
	    backend.clock_getres((clockid_t)12, NULL) != -EINVAL ||
	    errno != EDOM ||
	    backend.clock_getres((clockid_t)INT32_MAX, NULL) != -EINVAL ||
	    errno != EDOM)
		fail("clock_getres invalid positive IDs");
	puts("semantics.clock_getres.invalid_positive=pass");
}

static void check_dynamic_clock(void)
{
	struct timespec expected, value;

	check_clock_value(dynamic_clock_id, "dynamic_success");
	if (syscall(SYS_clock_getres, dynamic_clock_id, &expected) ||
	    backend.clock_getres(dynamic_clock_id, &value) ||
	    value.tv_sec != expected.tv_sec ||
	    value.tv_nsec != expected.tv_nsec ||
	    backend.clock_getres(dynamic_clock_id, NULL))
		fail("dynamic clock_getres success");
	puts("semantics.clock_getres.dynamic_success=pass");
}

static void check_gettimeofday(void)
{
	struct timeval before, value, after;
	struct timezone expected_tz, timezone;

	if (syscall(SYS_gettimeofday, &before, NULL) ||
	    backend.gettimeofday(&value, NULL) ||
	    syscall(SYS_gettimeofday, &after, NULL) ||
	    timeval_us(&value) < timeval_us(&before) ||
	    timeval_us(&value) > timeval_us(&after))
		fail("gettimeofday timeval");
	puts("semantics.gettimeofday.tv=pass");

	if (syscall(SYS_gettimeofday, NULL, &expected_tz) ||
	    backend.gettimeofday(NULL, &timezone) ||
	    memcmp(&timezone, &expected_tz, sizeof(timezone)))
		fail("gettimeofday timezone");
	puts("semantics.gettimeofday.tz=pass");

	if (syscall(SYS_gettimeofday, &before, &expected_tz) ||
	    backend.gettimeofday(&value, &timezone) ||
	    syscall(SYS_gettimeofday, &after, NULL) ||
	    timeval_us(&value) < timeval_us(&before) ||
	    timeval_us(&value) > timeval_us(&after) ||
	    memcmp(&timezone, &expected_tz, sizeof(timezone)))
		fail("gettimeofday both outputs");
	puts("semantics.gettimeofday.both=pass");

	if (backend.gettimeofday(NULL, NULL))
		fail("gettimeofday both NULL");
	puts("semantics.gettimeofday.null=pass");
}

static void check_time(void)
{
	time_t before, value, stored, after;

	before = (time_t)syscall(SYS_time, NULL);
	value = backend.time(NULL);
	after = (time_t)syscall(SYS_time, NULL);
	if (value < before || value > after)
		fail("time NULL");
	before = (time_t)syscall(SYS_time, NULL);
	value = backend.time(&stored);
	after = (time_t)syscall(SYS_time, NULL);
	if (value != stored || value < before || value > after)
		fail("time pointer");
	puts("semantics.time.null_pointer=pass");
}

static int first_allowed_cpu(cpu_set_t *original)
{
	int cpu;

	if (sched_getaffinity(0, sizeof(*original), original))
		fail("get affinity");
	for (cpu = 0; cpu < CPU_SETSIZE; ++cpu)
		if (CPU_ISSET(cpu, original))
			return cpu;
	fail("empty affinity");
	return -1;
}

static void check_getcpu(void)
{
	cpu_set_t original, pinned;
	unsigned int expected_cpu, expected_node, cpu, node;
	unsigned long cache = 0x12345678UL;
	int target = first_allowed_cpu(&original);

	CPU_ZERO(&pinned);
	CPU_SET(target, &pinned);
	if (sched_setaffinity(0, sizeof(pinned), &pinned))
		fail("pin getcpu");
	if (syscall(SYS_getcpu, &expected_cpu, &expected_node, NULL) ||
	    backend.getcpu(&cpu, &node, &cache) ||
	    cpu != expected_cpu || node != expected_node ||
	    cache != 0x12345678UL)
		fail("getcpu cpu/node/cache");
	if (backend.getcpu(&cpu, NULL, NULL) || cpu != expected_cpu ||
	    backend.getcpu(NULL, &node, NULL) || node != expected_node ||
	    backend.getcpu(NULL, NULL, NULL))
		fail("getcpu NULL combinations");
	if (sched_setaffinity(0, sizeof(original), &original))
		fail("restore affinity");
	puts("semantics.getcpu.outputs_null_cache=pass");
}

struct thread_test {
	int cpu;
	int failed;
};

static void *thread_test_main(void *opaque)
{
	struct thread_test *test = opaque;
	cpu_set_t pinned;
	int sample;

	CPU_ZERO(&pinned);
	CPU_SET(test->cpu, &pinned);
	if (pthread_setaffinity_np(pthread_self(), sizeof(pinned), &pinned)) {
		test->failed = 1;
		return NULL;
	}
	for (sample = 0; sample < THREAD_SAMPLES; ++sample) {
		struct timespec before, value, after;
		unsigned int expected_cpu, expected_node, cpu, node;

		if (syscall(SYS_getcpu, &expected_cpu, &expected_node, NULL) ||
		    backend.getcpu(&cpu, &node, NULL) ||
		    cpu != expected_cpu || node != expected_node ||
		    syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &before) ||
		    backend.clock_gettime(CLOCK_MONOTONIC, &value) ||
		    syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &after) ||
		    timespec_ns(&value) < timespec_ns(&before) ||
		    timespec_ns(&value) > timespec_ns(&after)) {
			test->failed = 1;
			break;
		}
	}
	return NULL;
}

static void check_multicpu_threads(void)
{
	struct thread_test tests[MAX_TEST_THREADS];
	pthread_t threads[MAX_TEST_THREADS];
	cpu_set_t allowed;
	int cpu, count = 0, index;

	if (sched_getaffinity(0, sizeof(allowed), &allowed))
		fail("get thread affinity");
	for (cpu = 0; cpu < CPU_SETSIZE && count < MAX_TEST_THREADS; ++cpu) {
		if (!CPU_ISSET(cpu, &allowed))
			continue;
		tests[count].cpu = cpu;
		tests[count].failed = 0;
		if (pthread_create(&threads[count], NULL, thread_test_main,
				   &tests[count]))
			fail("create test thread");
		count++;
	}
	if (!count)
		fail("no test CPUs");
	for (index = 0; index < count; ++index) {
		if (pthread_join(threads[index], NULL) || tests[index].failed)
			fail("multi-CPU/thread test");
	}
	printf("semantics.multicpu_threads=pass threads=%d\n", count);
}

static int install_syscall_errno_filter(int syscall_number)
{
	struct sock_filter instructions[] = {
		BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
			 offsetof(struct seccomp_data, nr)),
		BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, syscall_number, 0, 1),
		BPF_STMT(BPF_RET | BPF_K,
			 SECCOMP_RET_ERRNO | (PATH_ERRNO & SECCOMP_RET_DATA)),
		BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
	};
	struct sock_fprog program = {
		.len = sizeof(instructions) / sizeof(instructions[0]),
		.filter = instructions,
	};

	if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0))
		return -1;
	return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program);
}

enum path_operation {
	PATH_CLOCK_GETTIME,
	PATH_CLOCK_GETRES,
	PATH_GETTIMEOFDAY,
	PATH_TIME,
	PATH_GETCPU,
};

struct path_case {
	const char *name;
	enum path_operation operation;
	int syscall_number;
	clockid_t clock_id;
	unsigned int outputs;
	int fallback;
	int signal;
};

static int execute_path_case(const struct path_case *test)
{
	struct timespec ts;
	struct timeval tv;
	struct timezone tz;
	time_t stored;
	unsigned int cpu, node;
	unsigned long cache = 0;
	long result;

	switch (test->operation) {
	case PATH_CLOCK_GETTIME:
		result = backend.clock_gettime(
			test->clock_id, test->outputs ? &ts : NULL);
		break;
	case PATH_CLOCK_GETRES:
		result = backend.clock_getres(
			test->clock_id, test->outputs ? &ts : NULL);
		break;
	case PATH_GETTIMEOFDAY:
		result = backend.gettimeofday(
			(test->outputs & 1) ? &tv : NULL,
			(test->outputs & 2) ? &tz : NULL);
		break;
	case PATH_TIME:
		result = backend.time(test->outputs ? &stored : NULL);
		if (!test->fallback)
			return result > 0 ? 0 : 1;
		break;
	case PATH_GETCPU:
		result = backend.getcpu(
			(test->outputs & 1) ? &cpu : NULL,
			(test->outputs & 2) ? &node : NULL,
			(test->outputs & 4) ? &cache : NULL);
		break;
	default:
		return 1;
	}
	if (test->fallback) {
		if (result == -PATH_ERRNO)
			return 0;
		dprintf(STDERR_FILENO,
			"path_debug=%s expected=-%d actual=%ld\n",
			test->name, PATH_ERRNO, result);
		return 1;
	}
	if (result == 0)
		return 0;
	dprintf(STDERR_FILENO, "path_debug=%s expected=0 actual=%ld\n",
		test->name, result);
	return 1;
}

static void run_path_case(const struct path_case *test)
{
	pid_t child = fork();
	int status;

	if (child < 0)
		fail("fork path case");
	if (!child) {
		if (install_syscall_errno_filter(test->syscall_number))
			_exit(90);
		_exit(execute_path_case(test) ? 91 : 0);
	}
	if (waitpid(child, &status, 0) != child)
		fail("wait path case");
	if (test->signal) {
		if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV)
			fail("path signal mismatch");
		printf("path.%s=fast\n", test->name);
		return;
	}
	if (!WIFEXITED(status) || WEXITSTATUS(status)) {
		fprintf(stderr, "path_wait_debug=%s status=0x%x\n",
			test->name, status);
		fail(test->name);
	}
	printf("path.%s=%s\n", test->name,
	       test->fallback ? "fallback" : "fast");
}

#define CGT(_name, _clock, _fallback) \
	{ "clock_gettime." _name, PATH_CLOCK_GETTIME, SYS_clock_gettime, \
	  _clock, 1, _fallback, 0 }
#define CGR(_name, _clock, _outputs, _fallback) \
	{ "clock_getres." _name, PATH_CLOCK_GETRES, SYS_clock_getres, \
	  _clock, _outputs, _fallback, 0 }

static void check_paths(int getcpu_only)
{
	static const struct path_case cases[] = {
		CGT("realtime", CLOCK_REALTIME, 0),
		CGT("monotonic", CLOCK_MONOTONIC, 0),
		CGT("monotonic_raw", CLOCK_MONOTONIC_RAW, 0),
		CGT("boottime", CLOCK_BOOTTIME, 0),
		CGT("tai", CLOCK_TAI, 0),
		CGT("realtime_coarse", CLOCK_REALTIME_COARSE, 0),
		CGT("monotonic_coarse", CLOCK_MONOTONIC_COARSE, 0),
		CGT("process_cpu", CLOCK_PROCESS_CPUTIME_ID, 1),
		CGT("thread_cpu", CLOCK_THREAD_CPUTIME_ID, 1),
		CGT("realtime_alarm", CLOCK_REALTIME_ALARM, 1),
		CGT("boottime_alarm", CLOCK_BOOTTIME_ALARM, 1),
		CGT("encoded_process_cpu", (clockid_t)-6, 1),
		CGT("encoded_thread_cpu", (clockid_t)-2, 1),
		CGT("dynamic", (clockid_t)-5, 1),
		CGT("invalid", (clockid_t)-1, 1),
		CGT("invalid_slot", (clockid_t)10, 1),
		CGT("invalid_large", (clockid_t)INT32_MAX, 1),
		{ "clock_gettime.realtime_null", PATH_CLOCK_GETTIME,
		  SYS_clock_gettime, CLOCK_REALTIME, 0, 0, 1 },
		{ "clock_gettime.process_cpu_null", PATH_CLOCK_GETTIME,
		  SYS_clock_gettime, CLOCK_PROCESS_CPUTIME_ID, 0, 1, 0 },

		CGR("realtime", CLOCK_REALTIME, 1, 0),
		CGR("monotonic", CLOCK_MONOTONIC, 1, 0),
		CGR("monotonic_raw", CLOCK_MONOTONIC_RAW, 1, 0),
		CGR("boottime", CLOCK_BOOTTIME, 1, 0),
		CGR("tai", CLOCK_TAI, 1, 0),
		CGR("realtime_coarse", CLOCK_REALTIME_COARSE, 1, 0),
		CGR("monotonic_coarse", CLOCK_MONOTONIC_COARSE, 1, 0),
		CGR("realtime_null", CLOCK_REALTIME, 0, 0),
		CGR("process_cpu", CLOCK_PROCESS_CPUTIME_ID, 1, 1),
		CGR("process_cpu_null", CLOCK_PROCESS_CPUTIME_ID, 0, 1),
		CGR("encoded_process_cpu", (clockid_t)-6, 1, 1),
		CGR("dynamic", (clockid_t)-5, 1, 1),
		CGR("invalid", (clockid_t)-1, 1, 1),
		CGR("invalid_null", (clockid_t)-1, 0, 1),
		CGR("invalid_slot", (clockid_t)10, 1, 1),
		CGR("invalid_large_null", (clockid_t)INT32_MAX, 0, 1),

		{ "gettimeofday.tv", PATH_GETTIMEOFDAY, SYS_gettimeofday,
		  0, 1, 0, 0 },
		{ "gettimeofday.tz", PATH_GETTIMEOFDAY, SYS_gettimeofday,
		  0, 2, 0, 0 },
		{ "gettimeofday.both", PATH_GETTIMEOFDAY, SYS_gettimeofday,
		  0, 3, 0, 0 },
		{ "gettimeofday.null", PATH_GETTIMEOFDAY, SYS_gettimeofday,
		  0, 0, 0, 0 },
		{ "time.null", PATH_TIME, SYS_time, 0, 0, 0, 0 },
		{ "time.pointer", PATH_TIME, SYS_time, 0, 1, 0, 0 },
		{ "getcpu.both", PATH_GETCPU, SYS_getcpu, 0, 3, 0, 0 },
		{ "getcpu.cpu", PATH_GETCPU, SYS_getcpu, 0, 1, 0, 0 },
		{ "getcpu.node", PATH_GETCPU, SYS_getcpu, 0, 2, 0, 0 },
		{ "getcpu.null", PATH_GETCPU, SYS_getcpu, 0, 0, 0, 0 },
		{ "getcpu.cache", PATH_GETCPU, SYS_getcpu, 0, 7, 0, 0 },
	};
	size_t index;

	for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
		if (getcpu_only && cases[index].operation != PATH_GETCPU)
			continue;
		run_path_case(&cases[index]);
	}
}

static void check_dynamic_paths(void)
{
	const struct path_case gettime = {
		"clock_gettime.dynamic_success", PATH_CLOCK_GETTIME,
		SYS_clock_gettime, dynamic_clock_id, 1, 1, 0,
	};
	const struct path_case getres = {
		"clock_getres.dynamic_success", PATH_CLOCK_GETRES,
		SYS_clock_getres, dynamic_clock_id, 1, 1, 0,
	};
	const struct path_case getres_null = {
		"clock_getres.dynamic_success_null", PATH_CLOCK_GETRES,
		SYS_clock_getres, dynamic_clock_id, 0, 1, 0,
	};

	run_path_case(&gettime);
	run_path_case(&getres);
	run_path_case(&getres_null);
}

enum traced_fallback {
	TRACE_CLOCK_GETTIME,
	TRACE_CLOCK_GETRES,
};

static void trace_one_fallback(enum traced_fallback operation,
			       clockid_t clock_id, int syscall_number)
{
	pid_t child;
	int status, syscall_stops = 0;

	child = fork();
	if (child < 0)
		fail("fork fallback trace");
	if (!child) {
		struct timespec value;
		int result;

		if (ptrace(PTRACE_TRACEME, 0, NULL, NULL))
			_exit(80);
		raise(SIGSTOP);
		if (operation == TRACE_CLOCK_GETTIME)
			result = backend.clock_gettime(clock_id, &value);
		else
			result = backend.clock_getres(clock_id, &value);
		_exit(result ? 81 : 0);
	}

	if (waitpid(child, &status, 0) != child || !WIFSTOPPED(status))
		fail("initial fallback trace stop");
	if (ptrace(PTRACE_SETOPTIONS, child, NULL,
		   (void *)(uintptr_t)PTRACE_O_TRACESYSGOOD))
		fail("set fallback trace options");
	if (ptrace(PTRACE_SYSCALL, child, NULL, NULL))
		fail("start fallback trace");

	for (;;) {
		struct user_regs_struct registers;

		if (waitpid(child, &status, 0) != child)
			fail("wait fallback trace");
		if (WIFEXITED(status))
			break;
		if (!WIFSTOPPED(status))
			fail("unexpected fallback trace state");
		if (WSTOPSIG(status) == (SIGTRAP | 0x80)) {
			if (ptrace(PTRACE_GETREGS, child, NULL, &registers))
				fail("read fallback trace registers");
			if ((int)registers.orig_rax == syscall_number)
				syscall_stops++;
		}
		if (ptrace(PTRACE_SYSCALL, child, NULL, NULL))
			fail("continue fallback trace");
	}
	if (WEXITSTATUS(status) || syscall_stops != 2)
		fail("fallback syscall count");
}

static void check_single_fallback(void)
{
	trace_one_fallback(TRACE_CLOCK_GETTIME, CLOCK_PROCESS_CPUTIME_ID,
			   SYS_clock_gettime);
	trace_one_fallback(TRACE_CLOCK_GETRES, CLOCK_PROCESS_CPUTIME_ID,
			   SYS_clock_getres);
	trace_one_fallback(TRACE_CLOCK_GETTIME, dynamic_clock_id,
			   SYS_clock_gettime);
	puts("path.fallback.single_syscall=pass cases=3");
}

static void check_provider_fallback(void)
{
	static const struct path_case cases[] = {
		{ "provider.clock_gettime", PATH_CLOCK_GETTIME,
		  SYS_clock_gettime, CLOCK_REALTIME, 1, 1, 0 },
		{ "provider.gettimeofday", PATH_GETTIMEOFDAY,
		  SYS_gettimeofday, 0, 1, 1, 0 },
		{ "provider.clock_getres", PATH_CLOCK_GETRES,
		  SYS_clock_getres, CLOCK_REALTIME, 1, 0, 0 },
		{ "provider.time", PATH_TIME, SYS_time, 0, 0, 0, 0 },
	};
	struct timespec value;
	size_t index;

	if (backend.clock_gettime(CLOCK_REALTIME, &value))
		fail("provider fallback value");
	for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index)
		run_path_case(&cases[index]);
	puts("event.clocksource_provider_fallback=pass");
}

static void validate_global_after_event(const char *event)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
		CLOCK_BOOTTIME, CLOCK_TAI, CLOCK_REALTIME_COARSE,
		CLOCK_MONOTONIC_COARSE,
	};
	struct timeval tv;
	time_t seconds;
	size_t index;

	for (index = 0; index < sizeof(clocks) / sizeof(clocks[0]); ++index) {
		struct timespec value;

		if (backend.clock_gettime(clocks[index], &value) ||
		    value.tv_nsec < 0 || value.tv_nsec >= 1000000000L)
			fail(event);
	}
	if (backend.gettimeofday(&tv, NULL) || tv.tv_usec < 0 ||
	    tv.tv_usec >= 1000000 || (seconds = backend.time(NULL)) <= 0 ||
	    llabs((long long)seconds - (long long)tv.tv_sec) > 1)
		fail(event);
}

static void check_time_events(void)
{
	struct timespec realtime, tai, next, timeout_start, now;
	struct timex current = { 0 }, change = { 0 };
	long long tai_delta, expected_tai_delta;
	int leap_observed = 0;
	int new_tai;

	if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &realtime))
		fail("read realtime before settime");
	next = realtime;
	next.tv_sec += 2;
	if (syscall(SYS_clock_settime, CLOCK_REALTIME, &next))
		fail("clock_settime event");
	validate_global_after_event("validate settime event");
	puts("event.settime=pass");

	if (syscall(SYS_adjtimex, &current) < 0)
		fail("query timex for TAI");
	new_tai = current.tai == 37 ? 38 : 37;
	change.modes = ADJ_TAI;
	change.constant = new_tai;
	if (syscall(SYS_adjtimex, &change) < 0 ||
	    syscall(SYS_clock_gettime, CLOCK_REALTIME, &realtime) ||
	    syscall(SYS_clock_gettime, CLOCK_TAI, &tai))
		fail("TAI update event");
	tai_delta = timespec_ns(&tai) - timespec_ns(&realtime);
	if (llabs(tai_delta - (long long)new_tai * 1000000000LL) >
	    10000000LL)
		fail("TAI offset publication");
	validate_global_after_event("validate TAI event");
	puts("event.tai_update=pass");

	memset(&current, 0, sizeof(current));
	if (syscall(SYS_adjtimex, &current) < 0)
		fail("query timex for frequency");
	memset(&change, 0, sizeof(change));
	change.modes = ADJ_FREQUENCY;
	change.freq = current.freq > 30000000 ?
		current.freq - 65536 : current.freq + 65536;
	if (syscall(SYS_adjtimex, &change) < 0)
		fail("NTP frequency event");
	usleep(20000);
	validate_global_after_event("validate NTP frequency event");
	puts("event.ntp_frequency=pass");

	memset(&current, 0, sizeof(current));
	if (syscall(SYS_adjtimex, &current) < 0)
		fail("query timex for leap");
	memset(&change, 0, sizeof(change));
	change.modes = ADJ_STATUS;
	change.status = current.status & ~(STA_INS | STA_DEL);
	if (syscall(SYS_adjtimex, &change) < 0)
		fail("clear leap status");

	if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &realtime))
		fail("read realtime before leap");
	next.tv_sec = (realtime.tv_sec / 86400 + 1) * 86400 - 2;
	next.tv_nsec = 0;
	if (syscall(SYS_clock_settime, CLOCK_REALTIME, &next))
		fail("position realtime before leap");

	memset(&current, 0, sizeof(current));
	if (syscall(SYS_adjtimex, &current) < 0)
		fail("query timex before leap insertion");
	memset(&change, 0, sizeof(change));
	change.modes = ADJ_STATUS;
	change.status = (current.status & ~(STA_INS | STA_DEL)) | STA_INS;
	if (syscall(SYS_adjtimex, &change) < 0)
		fail("leap schedule event");
	expected_tai_delta = (long long)(new_tai + 1) * 1000000000LL;
	if (syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &timeout_start))
		fail("start leap timeout");
	for (;;) {
		if (backend.clock_gettime(CLOCK_REALTIME, &realtime) ||
		    backend.clock_gettime(CLOCK_TAI, &tai) ||
		    syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &now))
			fail("observe leap insertion");
		tai_delta = timespec_ns(&tai) - timespec_ns(&realtime);
		if (llabs(tai_delta - expected_tai_delta) <=
		    LEAP_DELTA_TOLERANCE_NS) {
			leap_observed = 1;
			break;
		}
		if (timespec_ns(&now) - timespec_ns(&timeout_start) >
		    LEAP_TIMEOUT_NS)
			break;
		usleep(10000);
	}
	if (!leap_observed)
		fail("leap insertion transition");
	validate_global_after_event("validate leap insertion event");
	memset(&current, 0, sizeof(current));
	if (syscall(SYS_adjtimex, &current) < 0)
		fail("query timex after leap");
	memset(&change, 0, sizeof(change));
	change.modes = ADJ_STATUS;
	change.status = current.status & ~(STA_INS | STA_DEL);
	if (syscall(SYS_adjtimex, &change) < 0)
		fail("clear leap insertion");
	puts("event.leap_schedule=pass");
	puts("event.leap_transition=pass");
}

static void check_alarm_no_rtc(void)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME_ALARM,
		CLOCK_BOOTTIME_ALARM,
	};
	struct timespec value;
	size_t index;

	for (index = 0; index < sizeof(clocks) / sizeof(clocks[0]); ++index) {
		errno = EDOM;
		if (backend.clock_gettime(clocks[index], &value) != -EINVAL ||
		    errno != EDOM)
			fail("alarm clock_gettime without RTC");
		errno = EDOM;
		if (backend.clock_getres(clocks[index], &value) != -EINVAL ||
		    errno != EDOM)
			fail("alarm clock_getres without RTC");
	}
	puts("semantics.alarm.no_rtc=pass clocks=2 operations=4");
}

enum namespace_clock_index {
	NS_MONOTONIC,
	NS_MONOTONIC_RAW,
	NS_MONOTONIC_COARSE,
	NS_BOOTTIME,
	NS_TAI,
	NS_CLOCK_COUNT,
};

static const struct {
	clockid_t id;
	int64_t offset_ns;
} namespace_clocks[NS_CLOCK_COUNT] = {
	[NS_MONOTONIC] = { CLOCK_MONOTONIC, NS_MONOTONIC_OFFSET_NS },
	[NS_MONOTONIC_RAW] = {
		CLOCK_MONOTONIC_RAW, NS_MONOTONIC_OFFSET_NS
	},
	[NS_MONOTONIC_COARSE] = {
		CLOCK_MONOTONIC_COARSE, NS_MONOTONIC_OFFSET_NS
	},
	[NS_BOOTTIME] = { CLOCK_BOOTTIME, NS_BOOTTIME_OFFSET_NS },
	[NS_TAI] = { CLOCK_TAI, 0 },
};

struct namespace_sample {
	struct timespec value[NS_CLOCK_COUNT];
};

static void write_full(int fd, const void *buffer, size_t size)
{
	const char *cursor = buffer;

	while (size) {
		ssize_t written = write(fd, cursor, size);

		if (written < 0) {
			if (errno == EINTR)
				continue;
			fail("write namespace pipe");
		}
		if (!written)
			fail("short namespace pipe write");
		cursor += written;
		size -= written;
	}
}

static void read_full(int fd, void *buffer, size_t size)
{
	char *cursor = buffer;

	while (size) {
		ssize_t received = read(fd, cursor, size);

		if (received < 0) {
			if (errno == EINTR)
				continue;
			fail("read namespace pipe");
		}
		if (!received)
			fail("short namespace pipe read");
		cursor += received;
		size -= received;
	}
}

static void write_control_file(const char *path, const char *value)
{
	int fd = open(path, O_WRONLY | O_CLOEXEC);

	if (fd < 0)
		fail(path);
	write_full(fd, value, strlen(value));
	if (close(fd))
		fail("close control file");
}

static void check_suspend_resume(void)
{
	struct timespec mono_before, boot_before, real_before;
	struct timespec mono_after, boot_after, real_after;
	char states[128] = { 0 };
	int fd;
	ssize_t length;
	int64_t mono_delta, boot_delta, real_delta;

	fd = open("/sys/power/state", O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		fail("open power state");
	length = read(fd, states, sizeof(states) - 1);
	if (length < 0 || close(fd))
		fail("read power state");
	if (!strstr(states, "mem"))
		fail("QEMU lacks suspend-to-RAM");

	if (backend.clock_gettime(CLOCK_MONOTONIC, &mono_before) ||
	    backend.clock_gettime(CLOCK_BOOTTIME, &boot_before) ||
	    backend.clock_gettime(CLOCK_REALTIME, &real_before))
		fail("read clocks before suspend");

	write_control_file("/sys/class/rtc/rtc0/wakealarm", "0\n");
	write_control_file("/sys/class/rtc/rtc0/wakealarm", "+2\n");
	write_control_file("/sys/power/state", "mem\n");

	if (backend.clock_gettime(CLOCK_MONOTONIC, &mono_after) ||
	    backend.clock_gettime(CLOCK_BOOTTIME, &boot_after) ||
	    backend.clock_gettime(CLOCK_REALTIME, &real_after))
		fail("read clocks after resume");
	mono_delta = timespec_ns(&mono_after) - timespec_ns(&mono_before);
	boot_delta = timespec_ns(&boot_after) - timespec_ns(&boot_before);
	real_delta = timespec_ns(&real_after) - timespec_ns(&real_before);
	if (mono_delta < 0 || boot_delta < 0 || real_delta < 500000000 ||
	    boot_delta + 100000000 < mono_delta)
		fail("suspend/resume clock relationship");
	validate_global_after_event("validate suspend/resume");
	puts("event.suspend_resume=pass");
}

static void syscall_namespace_sample(struct namespace_sample *sample)
{
	size_t index;

	for (index = 0; index < NS_CLOCK_COUNT; ++index) {
		if (syscall(SYS_clock_gettime, namespace_clocks[index].id,
			    &sample->value[index]))
			fail("namespace syscall sample");
	}
}

static void backend_namespace_sample(struct namespace_sample *sample)
{
	size_t index;

	for (index = 0; index < NS_CLOCK_COUNT; ++index) {
		struct timespec before, after;

		if (syscall(SYS_clock_gettime, namespace_clocks[index].id,
			    &before) ||
		    backend.clock_gettime(namespace_clocks[index].id,
					  &sample->value[index]) ||
		    syscall(SYS_clock_gettime, namespace_clocks[index].id,
			    &after) ||
		    timespec_ns(&sample->value[index]) < timespec_ns(&before) ||
		    timespec_ns(&sample->value[index]) > timespec_ns(&after))
			fail("namespace backend/syscall bracket");
	}
}

static void check_namespace_bracket(const struct namespace_sample *before,
				    const struct namespace_sample *current,
				    const struct namespace_sample *after)
{
	size_t index;

	for (index = 0; index < NS_CLOCK_COUNT; ++index) {
		int64_t value = timespec_ns(&current->value[index]);
		int64_t lower = timespec_ns(&before->value[index]) +
			namespace_clocks[index].offset_ns;
		int64_t upper = timespec_ns(&after->value[index]) +
			namespace_clocks[index].offset_ns;

		if (value < lower || value > upper)
			fail("namespace root/offset bracket");
	}
}

static void check_namespace_context(void)
{
#ifdef VKSO_BACKEND
	const struct vkso_mm_data *mm_data;

	errno = 0;
	mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
	if (!mm_data || errno ||
	    mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION ||
	    mm_data->clock_mask != ((1U << CLOCK_MONOTONIC) |
				    (1U << CLOCK_MONOTONIC_RAW) |
				    (1U << CLOCK_MONOTONIC_COARSE) |
				    (1U << CLOCK_BOOTTIME)) ||
	    mm_data->monotonic_offset.sec != 7 ||
	    mm_data->monotonic_offset.nsec != 123456789 ||
	    mm_data->boottime_offset.sec != 11 ||
	    mm_data->boottime_offset.nsec != 234567890)
		fail("VKSO namespace MM_data");
#endif
}

static void configure_time_namespace(void)
{
	static const char offsets[] =
		"monotonic 7 123456789\n"
		"boottime 11 234567890\n";
	int fd;

	if (unshare(CLONE_NEWTIME))
		fail("unshare time namespace");
	fd = open("/proc/self/timens_offsets", O_WRONLY | O_CLOEXEC);
	if (fd < 0)
		fail("open time namespace offsets");
	write_full(fd, offsets, sizeof(offsets) - 1);
	if (close(fd))
		fail("close time namespace offsets");
}

static void check_namespace_fast_paths(void)
{
	size_t index;

	for (index = 0; index < NS_CLOCK_COUNT; ++index) {
		pid_t child = fork();
		int status;

		if (child < 0)
			fail("fork namespace fast path");
		if (!child) {
			struct timespec value;

			if (install_syscall_errno_filter(SYS_clock_gettime))
				_exit(90);
			_exit(backend.clock_gettime(namespace_clocks[index].id,
						    &value) ? 91 : 0);
		}
		if (waitpid(child, &status, 0) != child ||
		    !WIFEXITED(status) || WEXITSTATUS(status))
			fail("namespace clock_gettime fast path");
	}
	puts("namespace.fast_paths=pass clocks=5");
}

static void check_frozen_time_namespace(void)
{
	static const char update[] = "monotonic 1 0\n";
	int fd;

	fd = open("/proc/self/timens_offsets", O_WRONLY | O_CLOEXEC);
	if (fd < 0)
		fail("open frozen time namespace offsets");
	errno = 0;
	if (write(fd, update, sizeof(update) - 1) != -1 || errno != EACCES)
		fail("time namespace offsets not frozen");
	if (close(fd))
		fail("close frozen time namespace offsets");
	puts("namespace.offsets_frozen=pass errno=EACCES");
}

static int namespace_exec_child(int result_fd)
{
	struct namespace_sample sample;

	check_namespace_context();
	backend_namespace_sample(&sample);
	check_namespace_fast_paths();
	write_full(result_fd, &sample, sizeof(sample));
	if (close(result_fd))
		fail("close namespace exec result");
	puts("namespace.exec.child=pass");
	fflush(NULL);
	return 0;
}

static void check_namespace_exec(void)
{
	struct namespace_sample before, current, after;
	int result_pipe[2], status;
	pid_t child;

	configure_time_namespace();
	if (pipe(result_pipe))
		fail("create namespace exec pipe");
	syscall_namespace_sample(&before);
	fflush(NULL);
	child = fork();
	if (child < 0)
		fail("fork namespace exec child");
	if (!child) {
		char fd_argument[32];

		close(result_pipe[0]);
		if (snprintf(fd_argument, sizeof(fd_argument), "%d",
			     result_pipe[1]) >= (int)sizeof(fd_argument))
			_exit(92);
		execl("/proc/self/exe", "/proc/self/exe",
		      "--namespace-exec-child", fd_argument, NULL);
		_exit(93);
	}
	close(result_pipe[1]);
	read_full(result_pipe[0], &current, sizeof(current));
	if (close(result_pipe[0]))
		fail("close namespace exec pipe");
	syscall_namespace_sample(&after);
	if (waitpid(child, &status, 0) != child ||
	    !WIFEXITED(status) || WEXITSTATUS(status))
		fail("namespace exec child");
	check_namespace_bracket(&before, &current, &after);
	puts("namespace.exec.lifecycle=pass");
}

static void root_oracle(int request_fd, int response_fd)
{
	struct namespace_sample sample;
	char request;
	int count;

	for (count = 0; count < 2; ++count) {
		read_full(request_fd, &request, sizeof(request));
		syscall_namespace_sample(&sample);
		write_full(response_fd, &sample, sizeof(sample));
	}
	close(request_fd);
	close(response_fd);
	_exit(0);
}

static void request_root_sample(int request_fd, int response_fd,
				struct namespace_sample *sample)
{
	const char request = 1;

	write_full(request_fd, &request, sizeof(request));
	read_full(response_fd, sample, sizeof(*sample));
}

static void check_namespace_setns(void)
{
	struct namespace_sample before, current, after;
	int request_pipe[2], response_pipe[2], namespace_fd, status;
	pid_t helper;

	if (pipe(request_pipe) || pipe(response_pipe))
		fail("create namespace oracle pipes");
	fflush(NULL);
	helper = fork();
	if (helper < 0)
		fail("fork namespace oracle");
	if (!helper) {
		close(request_pipe[1]);
		close(response_pipe[0]);
		root_oracle(request_pipe[0], response_pipe[1]);
	}
	close(request_pipe[0]);
	close(response_pipe[1]);
	configure_time_namespace();
	namespace_fd = open("/proc/self/ns/time_for_children",
			    O_RDONLY | O_CLOEXEC);
	if (namespace_fd < 0)
		fail("open time namespace descriptor");
	request_root_sample(request_pipe[1], response_pipe[0], &before);
	if (setns(namespace_fd, CLONE_NEWTIME))
		fail("setns time namespace");
	if (close(namespace_fd))
		fail("close time namespace descriptor");
	check_namespace_context();
	backend_namespace_sample(&current);
	request_root_sample(request_pipe[1], response_pipe[0], &after);
	if (close(request_pipe[1]) || close(response_pipe[0]))
		fail("close namespace oracle pipes");
	if (waitpid(helper, &status, 0) != helper ||
	    !WIFEXITED(status) || WEXITSTATUS(status))
		fail("namespace oracle");
	check_namespace_bracket(&before, &current, &after);
	check_namespace_fast_paths();
	check_frozen_time_namespace();
	puts("namespace.setns.commit=pass");
}

static void run_namespace_controller(void (*test)(void), const char *message)
{
	pid_t child;
	int status;

	fflush(NULL);
	child = fork();
	if (child < 0)
		fail("fork namespace controller");
	if (!child) {
		test();
		fflush(NULL);
		_exit(0);
	}
	if (waitpid(child, &status, 0) != child ||
	    !WIFEXITED(status) || WEXITSTATUS(status))
		fail(message);
}

static void check_namespace_lifecycle(void)
{
	run_namespace_controller(check_namespace_exec,
				 "namespace exec controller");
	run_namespace_controller(check_namespace_setns,
				 "namespace setns controller");
	puts("namespace.lifecycle_status=pass");
}

static int run_lifecycle_smoke(void)
{
	struct timespec time_value, resolution;
	struct timeval timeval;
	struct timezone timezone;
	time_t seconds, stored;
	unsigned int cpu, node;

	if (backend.clock_gettime(CLOCK_MONOTONIC, &time_value) ||
	    backend.clock_getres(CLOCK_MONOTONIC, &resolution) ||
	    backend.gettimeofday(&timeval, &timezone) ||
	    (seconds = backend.time(&stored)) != stored ||
	    seconds <= 0 ||
	    backend.getcpu(&cpu, &node, NULL))
		fail("lifecycle execution smoke");
	puts("lifecycle.execution=pass");
	return 0;
}

int main(int argc, char **argv)
{
	int multicpu_only = argc == 2 && !strcmp(argv[1], "--multicpu-only");
	int lifecycle_smoke = argc == 2 &&
		!strcmp(argv[1], "--lifecycle-smoke");
	int provider_fallback = argc == 2 &&
		!strcmp(argv[1], "--provider-fallback");
	int time_events = argc == 2 && !strcmp(argv[1], "--time-events");
	int suspend_resume = argc == 2 &&
		!strcmp(argv[1], "--suspend-resume");
	int alarm_no_rtc = argc == 2 &&
		!strcmp(argv[1], "--alarm-no-rtc");
	int namespace_child = argc == 3 &&
		!strcmp(argv[1], "--namespace-exec-child");
	char *end;
	long result_fd;

	if (!multicpu_only && !lifecycle_smoke && !provider_fallback &&
	    !time_events && !suspend_resume && !alarm_no_rtc &&
	    !namespace_child && argc != 1)
		fail("usage: abi-matrix [validation mode]");
	init_backend();
	open_dynamic_clock();
	if (namespace_child) {
		errno = 0;
		result_fd = strtol(argv[2], &end, 10);
		if (errno || *end || result_fd < 0 || result_fd > INT32_MAX)
			fail("namespace result descriptor");
		return namespace_exec_child((int)result_fd);
	}
	if (lifecycle_smoke)
		return run_lifecycle_smoke();
	if (provider_fallback) {
		check_provider_fallback();
		return 0;
	}
	if (time_events) {
		check_time_events();
		return 0;
	}
	if (suspend_resume) {
		check_suspend_resume();
		return 0;
	}
	if (alarm_no_rtc) {
		check_alarm_no_rtc();
		return 0;
	}
	printf("backend=%s\n", backend.name);
	if (multicpu_only) {
		check_getcpu();
		check_multicpu_threads();
		check_paths(1);
		puts("multicpu_matrix_status=pass");
		return 0;
	}
	check_clock_gettime();
	check_fast_null_clock_gettime();
	check_clock_getres();
	check_dynamic_clock();
	check_gettimeofday();
	check_time();
	check_getcpu();
	check_multicpu_threads();
	check_paths(0);
	check_dynamic_paths();
	check_single_fallback();
	check_mapping_security();
	check_namespace_lifecycle();
	if (close(dynamic_clock_fd))
		fail("close dynamic clock");
	puts("abi_matrix_status=pass");
	return 0;
}
