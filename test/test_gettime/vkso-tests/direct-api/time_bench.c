// SPDX-License-Identifier: GPL-2.0
/* Direct API batch cost. No timed dlopen, resolver, provider switch or tracing. */
#include <cpuid.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sched.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#ifdef USE_VKSO
#include "vkso_time.h"
#define BACKEND "vkso-direct"
#define api_cgt clock_gettime
#define api_cgr clock_getres
#define api_gtod gettimeofday
#define api_time time
#define api_cpu getcpu
#else
#define BACKEND "native-libc"
#define api_cgt clock_gettime
#define api_cgr clock_getres
#define api_gtod gettimeofday
#define api_time time
#define api_cpu getcpu
#endif
#define PROTOCOL "clocktime-direct-api-v2"
#ifndef AT_VKSO_MM_DATA
#define AT_VKSO_MM_DATA 52
#endif

static void fail(const char *message)
{
	fprintf(stderr, "%s: %s (errno=%d: %s)\n", BACKEND, message, errno, strerror(errno));
	exit(1);
}

static uint64_t positive(const char *s, uint64_t maximum, int zero_ok)
{
	char *end;
	unsigned long long value;
	if (!s[0] || s[0] < '0' || s[0] > '9') fail("invalid numeric argument");
	errno = 0;
	value = strtoull(s, &end, 10);
	if (errno || *end || value > maximum || (!value && !zero_ok))
		fail("numeric argument outside allowed range");
	return value;
}

struct stamp { uint64_t ticks; unsigned aux; };
static inline struct stamp stamp(void)
{
	unsigned lo, hi, aux;
	/* RDTSCP is checked before use. LFENCEs and compiler memory clobber
	 * bound the batch; these ticks are NOT unhalted core cycles.
	 */
	__asm__ __volatile__("lfence\n\trdtscp\n\tlfence"
		: "=a"(lo), "=d"(hi), "=c"(aux) : : "memory");
	return (struct stamp){((uint64_t)hi << 32) | lo, aux};
}

static void require_counter(void)
{
	unsigned a, b, c, d;
	if (!__get_cpuid(0x80000001, &a, &b, &c, &d) || !(d & (1U << 27)))
		fail("RDTSCP unavailable");
	if (!__get_cpuid(0x80000007, &a, &b, &c, &d) || !(d & (1U << 8)))
		fail("invariant TSC unavailable; no alternative timer silently substituted");
}

struct sample { struct stamp start, end; uint64_t checksum; int error; };
/* Each function contains a statically selected full public API call. Dispatch
 * to the selected batch function happens BEFORE its timestamp is taken.
 */
#define BATCH(name, declarations, operation) \
static struct sample name(uint64_t iterations, uint64_t warmup) \
{ \
	declarations; \
	uint64_t checksum = 0; int error = 0; \
	for (uint64_t i = 0; i < warmup; ++i) { operation; } \
	if (error) fail("warmup API error"); \
	checksum = 0; error = 0; \
	struct stamp start = stamp(); \
	for (uint64_t i = 0; i < iterations; ++i) { operation; } \
	struct stamp end = stamp(); \
	return (struct sample){start, end, checksum, error}; \
}
#define CGT(name, clock) BATCH(name, struct timespec ts, error |= api_cgt(clock, &ts))
#define CGR(name, clock) BATCH(name, struct timespec ts, error |= api_cgr(clock, &ts))
CGT(cgt_real, CLOCK_REALTIME)
CGT(cgt_mono, CLOCK_MONOTONIC)
CGT(cgt_raw, CLOCK_MONOTONIC_RAW)
CGT(cgt_boot, CLOCK_BOOTTIME)
CGT(cgt_tai, CLOCK_TAI)
CGT(cgt_real_coarse, CLOCK_REALTIME_COARSE)
CGT(cgt_mono_coarse, CLOCK_MONOTONIC_COARSE)
CGR(cgr_real, CLOCK_REALTIME)
CGR(cgr_coarse, CLOCK_REALTIME_COARSE)
BATCH(gtod_tv, struct timeval tv, error |= api_gtod(&tv, NULL))
BATCH(time_null, int unused __attribute__((unused)), checksum += (uint64_t)api_time(NULL))
BATCH(time_ptr, time_t seconds, checksum += (uint64_t)api_time(&seconds))
BATCH(cpu_both, unsigned cpu; unsigned node, error |= api_cpu(&cpu, &node))
CGT(cgt_process, CLOCK_PROCESS_CPUTIME_ID)
CGR(cgr_process, CLOCK_PROCESS_CPUTIME_ID)
CGT(cgt_alarm, CLOCK_REALTIME_ALARM)

struct testcase {
	const char *name;
	int fast;
	struct sample (*run)(uint64_t, uint64_t);
};
static const struct testcase cases[] = {
	{"clock_gettime_realtime", 1, cgt_real},
	{"clock_gettime_monotonic", 1, cgt_mono},
	{"clock_gettime_monotonic_raw", 1, cgt_raw},
	{"clock_gettime_boottime", 1, cgt_boot},
	{"clock_gettime_tai", 1, cgt_tai},
	{"clock_gettime_realtime_coarse", 1, cgt_real_coarse},
	{"clock_gettime_monotonic_coarse", 1, cgt_mono_coarse},
	{"clock_getres_realtime", 1, cgr_real},
	{"clock_getres_realtime_coarse", 1, cgr_coarse},
	{"gettimeofday_tv", 1, gtod_tv},
	{"time_null", 1, time_null},
	{"time_pointer", 1, time_ptr},
	{"getcpu_both", 1, cpu_both},
	{"clock_gettime_process_cpu_fallback", 0, cgt_process},
	{"clock_getres_process_cpu_fallback", 0, cgr_process},
	{"clock_gettime_realtime_alarm_fallback", 0, cgt_alarm},
};
#define CASE_COUNT (sizeof(cases) / sizeof(cases[0]))

static int cmp_ts(struct timespec a, struct timespec b)
{
	if (a.tv_sec != b.tv_sec) return a.tv_sec < b.tv_sec ? -1 : 1;
	return (a.tv_nsec > b.tv_nsec) - (a.tv_nsec < b.tv_nsec);
}
static void correctness(int fast_only)
{
	const clockid_t clocks[] = {CLOCK_REALTIME, CLOCK_MONOTONIC,
		CLOCK_MONOTONIC_RAW, CLOCK_BOOTTIME, CLOCK_TAI,
		CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE,
		CLOCK_PROCESS_CPUTIME_ID, CLOCK_REALTIME_ALARM};
	for (size_t j = 0; j < (fast_only ? 7 : sizeof(clocks) / sizeof(clocks[0])); ++j) {
		for (int i = 0; i < 128; ++i) {
			struct timespec before, actual, after, resolution, expected;
			if (syscall(SYS_clock_gettime, clocks[j], &before) ||
			    api_cgt(clocks[j], &actual) ||
			    syscall(SYS_clock_gettime, clocks[j], &after)) { fprintf(stderr, "clock_id=%d\n", clocks[j]); fail("clock_gettime check"); }
			if (actual.tv_nsec < 0 || actual.tv_nsec >= 1000000000L ||
			    cmp_ts(before, actual) > 0 || cmp_ts(actual, after) > 0)
				fail("clock outside syscall brackets (also check wall-clock steps)");
			if (api_cgr(clocks[j], &resolution) ||
			    syscall(SYS_clock_getres, clocks[j], &expected) ||
			    cmp_ts(resolution, expected)) fail("clock_getres mismatch");
		}
	}
	/* This comparison deliberately excludes invalid pointers and the obsolete
	 * gettimeofday timezone argument: neither is a matched fast-path workload.
	 */
	struct timeval before, actual, after;
	if (syscall(SYS_gettimeofday, &before, NULL) || api_gtod(&actual, NULL) ||
	    syscall(SYS_gettimeofday, &after, NULL)) fail("gettimeofday check");
	struct timespec a = {before.tv_sec, before.tv_usec * 1000};
	struct timespec b = {actual.tv_sec, actual.tv_usec * 1000};
	struct timespec c = {after.tv_sec, after.tv_usec * 1000};
	if (actual.tv_usec < 0 || actual.tv_usec >= 1000000 || cmp_ts(a, b) > 0 || cmp_ts(b, c) > 0)
		fail("gettimeofday outside syscall brackets");
	time_t lo = syscall(SYS_time, NULL), stored, value = api_time(&stored);
	time_t null_value = api_time(NULL), hi = syscall(SYS_time, NULL);
	if (value != stored || value < lo || value > hi || null_value < lo || null_value > hi)
		fail("time value mismatch");
	unsigned cpu, node, expected_cpu, expected_node;
	if (api_cpu(&cpu, &node) || syscall(SYS_getcpu, &expected_cpu, &expected_node, NULL) ||
	    cpu != expected_cpu || node != expected_node) fail("getcpu mismatch");
	struct timespec ts;
	errno = 0;
	if (api_cgt((clockid_t)-1, &ts) != -1 || errno != EINVAL) fail("clock_gettime errno");
	errno = 0;
	if (api_cgr((clockid_t)-1, &ts) != -1 || errno != EINVAL) fail("clock_getres errno");
	printf("public_api_check=PASS scope=%s\n", fast_only ? "fast-only" : "full");
}

static void deny_time_syscalls(void)
{
#define DENY(number) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, number, 0, 1), \
	BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
	struct sock_filter code[] = {
		BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
		BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
		BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
		BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
		DENY(SYS_clock_gettime), DENY(SYS_clock_getres), DENY(SYS_gettimeofday),
		DENY(SYS_time), DENY(SYS_getcpu),
		BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
	};
#undef DENY
	struct sock_fprog filter = {(unsigned short)(sizeof(code) / sizeof(code[0])), code};
	if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) ||
	    prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter)) fail("seccomp installation");
	/* Positive control: prove the filter is actually denying the syscall. */
	struct timespec ts;
	errno = 0;
	if (syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &ts) != -1 || errno != EPERM)
		fail("seccomp positive control failed");
}

int main(int argc, char **argv)
{
	uint64_t iterations = 500000, warmup = 10000, repeats = 31, process_index = 0;
	int cpu = -1, fast_only = 0;
	const char *mode = NULL;
	for (int i = 1; i < argc; ++i) {
		if (!strcmp(argv[i], "--probe") || !strcmp(argv[i], "--check") ||
		    !strcmp(argv[i], "--check-fast") || !strcmp(argv[i], "--bench")) {
			if (mode) fail("choose exactly one mode");
			mode = argv[i];
		} else if (!strcmp(argv[i], "--fast-only")) {
			fast_only = 1;
		} else if (i + 1 < argc && !strcmp(argv[i], "--cpu")) {
			cpu = (int)positive(argv[++i], CPU_SETSIZE - 1, 1);
		} else if (i + 1 < argc && !strcmp(argv[i], "--iterations")) {
			iterations = positive(argv[++i], 1000000000, 0);
		} else if (i + 1 < argc && !strcmp(argv[i], "--warmup")) {
			warmup = positive(argv[++i], 1000000000, 1);
		} else if (i + 1 < argc && !strcmp(argv[i], "--repeats")) {
			repeats = positive(argv[++i], 10000, 0);
		} else if (i + 1 < argc && !strcmp(argv[i], "--process-index")) {
			process_index = positive(argv[++i], 1000000, 1);
		} else {
			fprintf(stderr, "usage: %s --probe|--check|--check-fast|--bench --cpu N "
				"[--iterations N --warmup N --repeats N --process-index N --fast-only]\n", argv[0]);
			return 2;
		}
	}
	if (!mode) fail("a mode is required");
	if (!strcmp(mode, "--probe")) {
		printf("protocol=%s\nbackend=%s\nnative_vdso=%d\nvkso_mm_auxv=%d\n"
		       "measurement_unit=tsc_ticks_per_call\n", PROTOCOL, BACKEND,
		       getauxval(AT_SYSINFO_EHDR) != 0, getauxval(AT_VKSO_MM_DATA) != 0);
		return 0;
	}
	if (cpu < 0) fail("--cpu is required; no implicit CPU selection");
	cpu_set_t mask;
	CPU_ZERO(&mask); CPU_SET(cpu, &mask);
	if (sched_setaffinity(0, sizeof(mask), &mask)) fail("sched_setaffinity");
	require_counter();
#ifdef USE_VKSO
	if (getauxval(AT_SYSINFO_EHDR)) fail("VKSO experiment expects no native vDSO");
	if (vkso_time_init()) fail("VKSO initialization (grafting must precede process launch)");
#else
	if (!getauxval(AT_SYSINFO_EHDR) || getauxval(AT_VKSO_MM_DATA))
		fail("native experiment requires a Raw boot with native vDSO");
#endif
	if (!strcmp(mode, "--check")) { correctness(fast_only); return 0; }
	if (!strcmp(mode, "--check-fast")) {
		/* Separate diagnostic only; its timing is intentionally never printed. */
		for (size_t i = 0; i < CASE_COUNT; ++i) if (cases[i].fast) cases[i].run(1, 2);
		deny_time_syscalls();
		for (size_t i = 0; i < CASE_COUNT; ++i) if (cases[i].fast) {
			struct sample sample = cases[i].run(100, 0);
			if (sample.error) fail(cases[i].name);
			if (sample.checksum && sample.checksum == (uint64_t)-100)
				fail("time syscall fallback detected");
		}
		puts("time_syscall_denial_check=PASS (selected fast paths only)");
		return 0;
	}
	/* Explicit first touch even when a diagnostic caller requests zero warmup. */
	for (size_t i = 0; i < CASE_COUNT; ++i) {
		if (fast_only && !cases[i].fast) continue;
		if (cases[i].run(1, 1).error) fail("first-touch API error");
	}
	puts("protocol,backend,case,process_index,round,iterations,tsc_ticks,ticks_per_call,cpu,aux_start,aux_end,checksum");
	for (uint64_t round = 0; round < repeats; ++round) {
		for (size_t j = 0; j < CASE_COUNT; ++j) {
			/* Deterministic rotation prevents always timing one API first. */
			size_t i = (j + round + process_index) % CASE_COUNT;
			if (fast_only && !cases[i].fast) continue;
			struct sample sample = cases[i].run(iterations, warmup);
			if (sample.error || sample.end.ticks <= sample.start.ticks ||
			    sample.start.aux != sample.end.aux || sched_getcpu() != cpu)
				fail("invalid batch: API error, counter or CPU migration");
			uint64_t elapsed = sample.end.ticks - sample.start.ticks;
			printf("%s,%s,%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
			       ",%.9f,%d,%u,%u,%" PRIu64 "\n", PROTOCOL, BACKEND, cases[i].name,
			       process_index, round, iterations, elapsed, (double)elapsed / iterations,
			       cpu, sample.start.aux, sample.end.aux, sample.checksum);
		}
	}
	if (fflush(stdout) || ferror(stdout)) fail("output failure");
	return 0;
}
